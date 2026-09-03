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

### Proven in-scope call chain

The vulnerable recursive walker is confirmed — from in-scope code only — to be the
`deserialize` that runs on inbound messages:

1. `libraries/domain-serialization/src/domain-serialization.js` builds the
   serializer with `createSerializeDeserialize` from **`@exodus/serialization`**
   (the vulnerable recursive one).
2. `libraries/domain-serialization/src/index.js` exposes:
   ```js
   const deserialize = (arg) =>
     serializer.deserialize(typeof arg === 'string' ? JSON.parse(arg) : arg)
   ```
   A string message is `JSON.parse`d (V8's parser is iterative, so a deeply
   nested array parses fine) and then handed to the recursive walker.
3. `libraries/browser-extension-rpc/src/index.js` runs it on inbound transport
   data: `transport.on('data', (data) => onData(deserialize(data)))`, and
   `apps/sdk-minimal-demo/src/__tests__/multi-process.ts` wires the same
   `domain-serialization` `deserialize` into `new RPC({ transport, serialize,
   deserialize })` and the port transport's inbound listener.

So an inbound RPC message body of the form
`{"t":"array","v":[{"t":"array","v":[ … ]}]}` (only a few tens of KB) is parsed
and then recursed into → `RangeError` → the message handler throws. `deserialize`
in `domain-serialization` catches and **re-throws** (`throw e`), so the error
propagates to the transport `onData` callback; an uncaught throw there crashes /
kills the background message pump.

**What remains for High:** whether the *sender* on that RPC port is a
low-privilege actor (content script / web page / other process) in the shipped
product. That trust boundary is set by the closed-source app wiring; the
open-source evidence proves the vulnerable function runs on inbound message data
with no depth guard. I propose **Medium**, → **High** if your triage confirms an
untrusted sender can reach one of these boundaries.

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
