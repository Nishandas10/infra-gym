"""Extended JSON-patch ops used by fault specs.

Besides standard RFC 6902 ops, specs may use:
  set     add/replace a value, creating missing parent objects first
  append  add to the end of a list, creating the list if it does not exist
Paths may contain placeholders resolved against the live object:
  $c          index of fault.container (or 0) in the list at that point
  $name:NAME  index of the element whose .name is NAME
"""
from __future__ import annotations

from .. import kube


def resolve_path(obj, path, container=None):
    out, cur = [], obj
    for tok in path.strip("/").split("/"):
        if tok == "$c":
            tok = str(next((i for i, c in enumerate(cur) if c.get("name") == container), 0) if container else 0)
        elif tok.startswith("$name:"):
            want = tok[len("$name:"):]
            idx = next((i for i, c in enumerate(cur or []) if c.get("name") == want), None)
            if idx is None:
                raise KeyError(f"no element named {want!r} at /{'/'.join(out)}")
            tok = str(idx)
        out.append(tok)
        if isinstance(cur, list) and tok.isdigit() and int(tok) < len(cur):
            cur = cur[int(tok)]
        elif isinstance(cur, dict):
            cur = cur.get(tok.replace("~1", "/").replace("~0", "~"))
        else:
            cur = None
    return "/" + "/".join(out)


def expand(obj, ops, container=None):
    """Turn spec ops into plain JSON-patch ops against the live object."""
    result = []
    for op in ops:
        path = resolve_path(obj, op["path"], container)
        kind = op["op"]
        if kind == "set":
            toks = path.strip("/").split("/")
            for i in range(1, len(toks)):
                parent = "/" + "/".join(toks[:i])
                exists, _ = kube.pointer_get(obj, parent)
                if not exists and not any(r["path"] == parent for r in result):
                    result.append({"op": "add", "path": parent, "value": {}})
            result.append({"op": "add", "path": path, "value": op["value"]})
        elif kind == "append":
            exists, _ = kube.pointer_get(obj, path)
            if exists:
                result.append({"op": "add", "path": path + "/-", "value": op["value"]})
            else:
                result.append({"op": "add", "path": path, "value": [op["value"]]})
        else:
            new = dict(op)
            new["path"] = path
            result.append(new)
    return result
