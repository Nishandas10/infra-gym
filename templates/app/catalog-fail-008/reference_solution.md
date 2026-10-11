# Reference solution: catalog-fail-008

**Root cause:** the `productCatalogFailure` flag has a targeting rule that makes
the product-catalog service fail requests for exactly one product,
`OLJCESPC7Z`. Everything else works, so aggregate error rates stay low.

1. Reproduce: `curl http://localhost:8080/api/products/OLJCESPC7Z` returns 500;
   any other product ID returns 200.
2. `kubectl logs deploy/product-catalog --tail=50`: errors mentioning the
   product ID and the feature flag.
3. Jaeger: traces for `GetProduct` with `app.product.id=OLJCESPC7Z` are marked
   as errors.
4. Feature Flags UI: `productCatalogFailure` is on (its targeting rule returns
   `on` for `OLJCESPC7Z`).
5. Fix:
   ```
   python injectors/toggle_flag.py productCatalogFailure --off
   ```
6. Confirm the product page loads.
