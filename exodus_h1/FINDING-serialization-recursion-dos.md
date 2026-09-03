# Uncontrolled recursion (stack-overflow crash) in `@exodus/serialization` `deserialize`

**Asset:** `ExodusOSS/hydra` → `libraries/serialization` (`@exodus/serialization`) — HackerOne scope.
**File:** `libraries/serialization/src/index.js` → `deserialize()` (from `createSerializeDeserialize()`).
**Class:** CWE-674 Uncontrolled Recursion → CWE-400 Uncontrolled Resource Consumption (DoS by crash).
**Severity (proposed):** Medium, arguably High if the boundary below is reachable by a low-privilege remote actor (see "Reachability").

## Summary

`deserialize()` walks a serialized tree by **recursing** on every nested
`{ t:'object'|'array', v:… }` node, with **no maximum depth**:

```js
if (t === 'object') return mapValues(v, (o) => deserialize(o))
if (t === 'array')  return v.map((o) => deserialize(o))
```

A **small (~40–120 KB)** deeply-nested payload overflows the JavaScript call
stack and throws `RangeError: Maximum call stack size exceeded`. If that throw is
not caught at the boundary, it crashes the surface processing the message
(extension background page / renderer / worker). The input is tiny and the effect
is an **outright crash**, not a slowdown.

## Measured (Node v22, real library code)

`poc_deserialize_dos.mjs`:

```
depth 1000  (~24 KB):  ok
depth 5000  (~120 KB): CRASH -> RangeError: Maximum call stack size exceeded
depth 20000+ :         CRASH
```

The exact threshold depends on the surface's stack size, but a payload well under
1 MB reliably crashes it.

## Reachability

`deserialize()` is applied to **incoming messages** at deserialization
boundaries. The clearest in-scope example is `@exodus/browser-extension-rpc`
(`libraries/browser-extension-rpc/src/index.js`):

```js
transport.on('data', (data) => {
  onData(typeof data === 'string' ? deserialize(data) : data)
})
```

i.e. inbound RPC `data` is fed straight into `deserialize`. The concrete
`serialize`/`deserialize` pair is injected by the app wiring
(`@exodus/domain-serialization` / `@exodus/models` build it from
`@exodus/serialization`), which is closed-source, so I cannot prove from the
open-source scope alone that a **web page / dApp** can drive this exact port. What
I can show from in-scope code:

- the library function is unsafe on nested input (measured), and
- it is wired to run on inbound RPC/message `data`.

If a low-privilege remote actor (malicious web page talking to the extension,
compromised/MITM backend for a sync/import channel) can reach a boundary that
runs this `deserialize`, this is a remote, no-UI crash DoS (High). Absent that
proof I propose Medium and defer the reachability rating to your triage, which
can see the app wiring.

## Suggested fix

Add an explicit recursion-depth limit (and/or convert to an iterative walk with a
bounded work budget) in `deserialize`:

```js
const MAX_DEPTH = 256
const deserialize = (value, depth = 0) => {
  if (depth > MAX_DEPTH) throw new RangeError('serialization: max depth exceeded')
  ...
  if (t === 'object') return mapValues(v, (o) => deserialize(o, depth + 1))
  if (t === 'array')  return v.map((o) => deserialize(o, depth + 1))
  ...
}
```

A bounded `RangeError` thrown deliberately (and caught at the boundary) is safe;
an unbounded native stack overflow is not.

## PoC

See `poc_deserialize_dos.mjs` (self-contained; includes the one-line `@exodus/bytes`
stub needed because the array/object recursion path doesn't use base64).
