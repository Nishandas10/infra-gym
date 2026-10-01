"""HTTP probe that runs inside the gym-probe pod (stdlib only).

It plays the same user journeys as the Locust load generator, through the
shop's front door (frontend-proxy), and reports per-journey success and latency
as JSON. The verifier uses it instead of waiting on the load generator's
low request rate (~1 request/s).

usage: python3 probe.py '{"journeys": ["cart"], "repeat": 3}'
       python3 probe.py '{"raw": [{"method": "GET", "url": "http://jaeger.default:16686/api/services"}]}'
"""
import http.cookiejar
import json
import random
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = "http://frontend-proxy.default.svc.cluster.local:8080"
PRODUCTS = ["0PUK6V6EV0", "1YMWWN1N4O", "2ZYFJ3GM2N", "66VCHSJNUP", "6E92ZMYYFZ",
            "9SIQT8TOJO", "L9ECAV7KIM", "LS4PSXUNUM", "OLJCESPC7Z", "HQTGWGPNH4"]
PERSON = {
    "email": "gym-probe@example.com",
    "address": {"streetAddress": "1600 Amphitheatre Parkway", "city": "Mountain View",
                "state": "CA", "country": "United States", "zipCode": "94043"},
    "userCurrency": "USD",
    "creditCard": {"creditCardNumber": "4432-8015-6152-0454", "creditCardExpirationMonth": 1,
                   "creditCardExpirationYear": 2039, "creditCardCvv": 672},
}


class Fail(Exception):
    pass


def call(method, url, body=None, timeout=8.0, opener=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    hdrs = dict(headers or {})
    if data:
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    t0 = time.time()
    try:
        with (opener or urllib.request.build_opener()).open(req, timeout=timeout) as resp:
            payload = resp.read()
            return resp.status, (time.time() - t0) * 1000, payload
    except urllib.error.HTTPError as e:
        return e.code, (time.time() - t0) * 1000, e.read()[:300]
    except Exception as e:  # timeouts, connection refused, DNS errors
        return 0, (time.time() - t0) * 1000, f"{type(e).__name__}: {e}".encode()


def expect_ok(status, payload, what):
    if status < 200 or status >= 300:
        raise Fail(f"{what} -> {status or 'no response'} {payload[:160]!r}")


def as_json(payload, what):
    try:
        return json.loads(payload)
    except Exception:
        raise Fail(f"{what} -> not JSON: {payload[:120]!r}")


def j_home(o, t):
    s, ms, p = call("GET", BASE + "/", timeout=t, opener=o)
    expect_ok(s, p, "GET /")
    return ms


def j_browse(o, t):
    pid = random.choice(PRODUCTS)
    s, ms, p = call("GET", f"{BASE}/api/products/{pid}", timeout=t, opener=o)
    expect_ok(s, p, f"GET /api/products/{pid}")
    if as_json(p, "product").get("id") != pid:
        raise Fail(f"product {pid}: unexpected body {p[:120]!r}")
    return ms


def j_catalog(o, t):
    s, ms, p = call("GET", BASE + "/api/products", timeout=t, opener=o)
    expect_ok(s, p, "GET /api/products")
    if len(as_json(p, "products")) < 1:
        raise Fail("product list empty")
    return ms


def j_currency(o, t):
    s, ms, p = call("GET", BASE + "/api/products?currencyCode=EUR", timeout=t, opener=o)
    expect_ok(s, p, "GET /api/products?currencyCode=EUR")
    items = as_json(p, "products")
    if not items or items[0].get("priceUsd", {}).get("currencyCode") != "EUR":
        raise Fail(f"prices not converted to EUR: {p[:120]!r}")
    return ms


def j_browse_burst(o, t):
    """12 product requests at the same time, like several shoppers at once. Contention
    (locks, pools) only shows up under concurrency; returns the slowest request's time."""
    import concurrent.futures
    urls = [f"{BASE}/api/products/{random.choice(PRODUCTS)}" for _ in range(12)]
    with concurrent.futures.ThreadPoolExecutor(12) as ex:
        res = list(ex.map(lambda u: call("GET", u, timeout=t), urls))
    bad = [r for r in res if not 200 <= r[0] < 300]
    if bad:
        raise Fail(f"{len(bad)}/12 concurrent product requests failed: {bad[0][0] or 'no response'}")
    return max(r[1] for r in res)


def j_recommendations(o, t):
    pid = random.choice(PRODUCTS)
    s, ms, p = call("GET", f"{BASE}/api/recommendations?productIds={pid}", timeout=t, opener=o)
    expect_ok(s, p, "GET /api/recommendations")
    return ms


def j_ads(o, t):
    s, ms, p = call("GET", BASE + "/api/data/?contextKeys=telescopes", timeout=t, opener=o)
    expect_ok(s, p, "GET /api/data")
    return ms


def _add_to_cart(o, t, user):
    pid = random.choice(PRODUCTS)
    s, ms, p = call("POST", BASE + "/api/cart", {"item": {"productId": pid, "quantity": 1}, "userId": user},
                    timeout=t, opener=o)
    expect_ok(s, p, "POST /api/cart")
    return ms


def j_cart(o, t):
    user = str(uuid.uuid4())
    ms = _add_to_cart(o, t, user)
    s, ms2, p = call("GET", f"{BASE}/api/cart?sessionId={user}&currencyCode=USD", timeout=t, opener=o)
    expect_ok(s, p, "GET /api/cart")
    if not as_json(p, "cart").get("items"):
        raise Fail(f"cart empty after add: {p[:120]!r}")
    return ms + ms2


def _checkout(o, t, person):
    user = str(uuid.uuid4())
    ms = _add_to_cart(o, t, user)
    body = dict(person, userId=user)
    s, ms2, p = call("POST", BASE + "/api/checkout", body, timeout=t * 2, opener=o)
    expect_ok(s, p, "POST /api/checkout")
    if not as_json(p, "checkout").get("orderId"):
        raise Fail(f"no orderId in checkout response: {p[:160]!r}")
    return ms + ms2


def j_checkout(o, t):
    return _checkout(o, t, PERSON)


def j_checkout_intl(o, t):
    person = dict(PERSON, address={"streetAddress": "Unter den Linden 1", "city": "Berlin", "state": "BE",
                                   "country": "Germany", "zipCode": "10117"})
    return _checkout(o, t, person)


def j_images(o, t):
    s, ms, p = call("GET", BASE + "/api/products/OLJCESPC7Z", timeout=t, opener=o)
    expect_ok(s, p, "GET product for picture")
    pic = as_json(p, "product").get("picture")
    s, ms2, p = call("GET", f"{BASE}/images/products/{pic}", timeout=t, opener=o)
    expect_ok(s, p, f"GET /images/products/{pic}")
    if len(p) < 1000:
        raise Fail(f"image too small ({len(p)} bytes)")
    return ms + ms2


def j_images_browser(o, t):
    """Fetch a product image the way the shop's browser code does: it reads the numeric
    imageSlowLoad flag and passes it to Envoy as an x-envoy-fault-delay-request header."""
    s, _, p = call("POST", "http://flagd.default.svc.cluster.local:8016/ofrep/v1/evaluate/flags/imageSlowLoad",
                   {"context": {}}, timeout=t, opener=o)
    delay = 0
    if s == 200:
        try:
            delay = int(float(json.loads(p).get("value", 0)))
        except (ValueError, TypeError):
            delay = 0
    s, ms, p = call("GET", f"{BASE}/images/products/NationalParkFoundationExplorascope.jpg", timeout=t, opener=o,
                    headers={"x-envoy-fault-delay-request": str(delay), "Cache-Control": "no-cache"})
    expect_ok(s, p, "GET product image (browser-style)")
    return ms


def j_email(o, t):
    """Checkout only logs email failures, so call the email service directly."""
    order = {"order_id": "gym-probe-" + str(uuid.uuid4())[:8], "shipping_tracking_id": "gym-probe",
             "shipping_cost": {"currency_code": "USD", "units": 1, "nanos": 0},
             "shipping_address": {"street_address": "1 Main St", "city": "Mountain View", "state": "CA",
                                  "country": "United States", "zip_code": "94043"},
             "items": [{"item": {"product_id": "OLJCESPC7Z", "quantity": 1},
                        "cost": {"currency_code": "USD", "units": 1, "nanos": 0}}]}
    s, ms, p = call("POST", "http://email.default.svc.cluster.local:8080/send_order_confirmation",
                    {"email": "gym-probe@example.com", "order": order}, timeout=t, opener=o)
    expect_ok(s, p, "POST email/send_order_confirmation")
    return ms


def _simple(path):
    def j(o, t):
        s, ms, p = call("GET", BASE + path, timeout=t, opener=o)
        expect_ok(s, p, f"GET {path}")
        return ms
    return j


JOURNEYS = {
    "home": j_home, "browse": j_browse, "browse_burst": j_browse_burst, "catalog": j_catalog,
    "currency": j_currency,
    "recommendations": j_recommendations, "ads": j_ads, "cart": j_cart, "checkout": j_checkout,
    "checkout_intl": j_checkout_intl,
    "images": j_images, "images_browser": j_images_browser, "email": j_email,
    "grafana": _simple("/grafana/api/health"), "jaeger_ui": _simple("/jaeger/ui/"),
    "flags_ui": _simple("/feature/"), "loadgen_ui": _simple("/loadgen/"),
}


def main():
    plan = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {"journeys": list(JOURNEYS)}
    timeout = float(plan.get("timeout", 8))
    out = {}
    for name in plan.get("journeys", []):
        res = {"n": 0, "ok": 0, "ms": [], "errors": []}
        for _ in range(int(plan.get("repeat", 3))):
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            res["n"] += 1
            t0 = time.time()
            try:
                JOURNEYS[name](opener, timeout)
                res["ok"] += 1
            except Fail as e:
                res["errors"].append(str(e)[:200])
            res["ms"].append(round((time.time() - t0) * 1000))
        out[name] = res
    for i, r in enumerate(plan.get("raw", [])):
        s, ms, p = call(r.get("method", "GET"), r["url"], r.get("body"), timeout=float(r.get("timeout", timeout)),
                        headers=r.get("headers"))
        out[r.get("name", f"raw{i}")] = {"status": s, "ms": round(ms), "body": p.decode(errors="replace")[:3000000]}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
