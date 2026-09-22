#!/usr/bin/env python3
"""Parse a SAPUI5 Component-preload.js and unpack every embedded module.

Format:
    //@ui5-bundle .../Component-preload.js
    sap.ui.require.preload({
        "path/to/module.js":    function(){ <source> },
        "path/to/view.xml":     "<escaped-string>",
        "path/to/data.json":    "<escaped-string>",
        ...
    });

For .js modules the value is a `function(){ ... }` — we peel one enclosing
`function()` wrapper (its body IS the module source). For .xml/.properties/.json
the value is a JS string literal — we un-escape it (json.loads on `"..."` after
escaping the raw brace/quote content).

Writes each file under <out_dir>/<path relative to a namespace root>. The bundle
paths look like "be/kuleuven/application/controller/Foo.controller.js" — we
strip the "be/kuleuven/application/" prefix so the tree lands as
    controller/Foo.controller.js
    view/Foo.view.xml
    i18n/i18n_en.properties
etc. Paths outside that namespace (e.g. "i18n/i18n.properties",
"localService/metadata.xml") are written under a _misc/ subtree so the
namespaced tree matches Track A's layout.
"""
import json
import os
import sys


def extract_payload(text):
    """Return the substring inside sap.ui.require.preload({ ... })."""
    marker = "sap.ui.require.preload("
    i = text.find(marker)
    if i < 0:
        raise SystemExit("no sap.ui.require.preload(...) call found")
    j = text.find("{", i + len(marker))
    if j < 0:
        raise SystemExit("no opening { after preload(")
    # find matching close-brace by depth counting, ignoring strings + comments
    return _slice_balanced(text, j)


def _slice_balanced(text, start):
    """Return text[start:end+1] where text[start] is '{' and end is its match."""
    assert text[start] == "{"
    depth = 0
    i = start
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"' or c == "'":
            # skip string literal; handles escapes but not template literals
            q = c
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            i = (end + 2) if end != -1 else n
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            end = text.find("\n", i + 2)
            i = (end + 1) if end != -1 else n
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1
    raise SystemExit("unbalanced { in preload payload")


def walk_entries(payload):
    """Yield (path, kind, raw_value_slice) for each top-level "key": value entry.

    kind is 'function' when the value starts with 'function(' or 'json_string' when
    it starts with a quote. Others (rare) are 'other' and skipped.
    """
    assert payload.startswith("{") and payload.endswith("}")
    body = payload[1:-1]
    i = 0
    n = len(body)
    while i < n:
        # skip whitespace / commas / comments
        while i < n and body[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break
        if body[i] == "/" and i + 1 < n and body[i + 1] == "*":
            end = body.find("*/", i + 2)
            i = (end + 2) if end != -1 else n
            continue
        if body[i] == "/" and i + 1 < n and body[i + 1] == "/":
            end = body.find("\n", i + 2)
            i = (end + 1) if end != -1 else n
            continue
        # key: a double-quoted string
        if body[i] != '"':
            # unexpected junk; skip a char to avoid infinite loop
            i += 1
            continue
        # parse key string
        j = i + 1
        while j < n:
            if body[j] == "\\":
                j += 2
                continue
            if body[j] == '"':
                break
            j += 1
        key = json.loads(body[i : j + 1])
        i = j + 1
        # skip ws then colon
        while i < n and body[i] in " \t\r\n":
            i += 1
        if i >= n or body[i] != ":":
            raise SystemExit(f"expected ':' after key {key!r} at pos {i}")
        i += 1
        while i < n and body[i] in " \t\r\n":
            i += 1
        # value: function(...) or "..."
        if body.startswith("function", i):
            # find the function's body { ... }
            # locate the '{' that opens the body
            k = body.find("{", i)
            slab = _slice_balanced(body, k)
            yield key, "function", slab
            i = k + len(slab)
        elif body[i] in ('"', "'"):
            # a JS string literal in either quote style; find its matching close
            q = body[i]
            j = i + 1
            while j < n:
                if body[j] == "\\":
                    j += 2
                    continue
                if body[j] == q:
                    break
                j += 1
            raw = body[i : j + 1]
            yield key, "json_string", raw
            i = j + 1
        else:
            # some other value; consume up to the next top-level comma
            depth = 0
            k = i
            while k < n:
                c = body[k]
                if c in "{[":
                    depth += 1
                elif c in "}]":
                    depth -= 1
                elif c == "," and depth == 0:
                    break
                k += 1
            yield key, "other", body[i:k]
            i = k


def decode_js_string(raw):
    """Decode a JS string literal wrapped in either single or double quotes.

    Handles the escapes typical inside SAPUI5's Component-preload payloads:
    \\\\, \\', \\", \\n, \\r, \\t, \\uXXXX. Anything unknown after a backslash
    passes through as the escaped character.
    """
    assert len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'")
    s = raw[1:-1]
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        if i + 1 >= n:
            out.append(c)
            i += 1
            continue
        nxt = s[i + 1]
        if nxt == "u" and i + 5 < n:
            try:
                out.append(chr(int(s[i + 2 : i + 6], 16)))
                i += 6
                continue
            except ValueError:
                pass
        mapping = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f",
                   "0": "\0", "\\": "\\", "'": "'", '"': '"', "/": "/"}
        out.append(mapping.get(nxt, nxt))
        i += 2
    return "".join(out)


def unwrap_function_body(slab):
    """Given a balanced '{ ... }' slice, return the inner code (no outer braces)."""
    assert slab.startswith("{") and slab.endswith("}")
    return slab[1:-1].strip("\n")


def relative_path(bundle_path):
    """Strip the SAPUI5 namespace to get a repo-friendly path."""
    prefix = "be/kuleuven/application/"
    if bundle_path.startswith(prefix):
        return bundle_path[len(prefix) :]
    return "_misc/" + bundle_path


def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) != 2:
        raise SystemExit("usage: bundle_extract.py <Component-preload.js> <out_dir>")
    src, out_dir = argv
    with open(src, "r", encoding="utf-8") as fh:
        text = fh.read()
    payload = extract_payload(text)
    written = []
    for key, kind, raw in walk_entries(payload):
        rel = relative_path(key)
        path = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if kind == "function":
            content = unwrap_function_body(raw)
        elif kind == "json_string":
            content = decode_js_string(raw)
        else:
            content = raw
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        written.append((key, kind, len(content), rel))
    for key, kind, n, rel in written:
        print(f"  {kind:<12} {n:>7}  {rel}")
    print(f"\nwrote {len(written)} files under {out_dir}")


if __name__ == "__main__":
    main()
