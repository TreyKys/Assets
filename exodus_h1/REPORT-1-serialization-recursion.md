# Vulnerability Report — Unbounded Recursion (Stack-Exhaustion Denial of Service) in `@exodus/serialization`

**Researcher:** treyky
**Program:** Exodus — Open-Source Libraries (SDK & Crypto)
**Affected asset:** `github.com/ExodusOSS/hydra` → `libraries/serialization` (`@exodus/serialization`); consumed via `@exodus/domain-serialization`
**Report date:** &lt;date&gt;
**Weakness (CWE):** CWE-674 Uncontrolled Recursion → CWE-400 Uncontrolled Resource Consumption
**Severity:** Medium — CVSS:3.1 `AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:H` (6.5)

---

## 1. Executive Summary

`@exodus/serialization` is the object (de)serialization library used across the
Exodus SDK to reconstruct data structures from messages exchanged between
processes (e.g. UI ↔ background over RPC). Its `deserialize()` function walks the
incoming structure by **calling itself once per nesting level, with no depth
limit**. A small, deeply-nested message (~40–120 KB) therefore drives the call
stack past its limit and throws `RangeError: Maximum call stack size exceeded`.
Because `deserialize()` runs on **inbound messages**, a single crafted message
crashes the surface that processes it (in the Exodus Desktop Wallet this is an
Electron renderer/worker/background context), rendering the application
unavailable until restart.

The input required is tiny and the effect is an immediate crash — no
authentication, user interaction, or special privilege is needed at the
deserialization boundary itself.

---

## 2. Vulnerability Details

| Field | Detail |
|---|---|
| **Component** | `libraries/serialization/src/index.js` → `deserialize()` (returned by `createSerializeDeserialize()`) |
| **Consumed by** | `libraries/domain-serialization` → `@exodus/browser-extension-rpc`, SDK RPC transport |
| **Root cause** | Recursive tree walk with no maximum-depth guard |
| **Trigger** | One inbound serialized message with deeply-nested `{ "t":"array", "v":[…] }` nodes |
| **Result** | `RangeError: Maximum call stack size exceeded` → crash of the message-handling context |

### Root cause

`deserialize()` recurses on every nested `object`/`array` node:

```js
// libraries/serialization/src/index.js
if (t === 'object') return mapValues(v, (o) => deserialize(o))
if (t === 'array')  return v.map((o) => deserialize(o))
```

There is no depth counter and no iterative fallback. Nesting depth in the input
maps 1:1 to native call-stack depth.

### Attacker goal / scenario

The attacker's goal is to make the wallet **unavailable** (crash / forced
restart), and — if the crash lands in a persistently-reloaded context that
re-reads the same stored/queued message — to cause a **repeatable crash loop**.
The attacker crafts a single serialized message consisting of thousands of nested
`{"t":"array","v":[…]}` wrappers (only tens of KB) and delivers it to any surface
that runs `deserialize()` on inbound data.

---

## 3. Proof of Concept

The nested `array`/`object` recursion path does not use the one `@exodus/bytes`
import, so it is stubbed for a self-contained run.

```bash
git clone https://github.com/ExodusOSS/hydra
cd hydra/libraries/serialization

# minimal stub for the single unused base64 import
mkdir -p node_modules/@exodus/bytes
printf '{"name":"@exodus/bytes","type":"module","exports":{"./base64.js":"./base64.js"}}' > node_modules/@exodus/bytes/package.json
printf 'export const toBase64=(u)=>Buffer.from(u).toString("base64");export const fromBase64=(s)=>new Uint8Array(Buffer.from(s,"base64"))' > node_modules/@exodus/bytes/base64.js

# save poc_deserialize_dos.mjs (attached) here, then:
node poc_deserialize_dos.mjs
```

`poc_deserialize_dos.mjs` builds `{t:'array', v:[ … ]}` nested to a given depth
and calls the real library `deserialize()`.

### Observed output (Node v22)

```
depth 1000  (~24 KB):  ok
depth 5000  (~120 KB): CRASH -> RangeError: Maximum call stack size exceeded
depth 20000+:          CRASH
```

A payload well under 1 MB reliably crashes the process. (Exact threshold depends
on the surface's configured stack size.)

### Proven in-scope call chain (deserialize runs on inbound messages)

1. `libraries/domain-serialization/src/domain-serialization.js` builds the
   serializer from `@exodus/serialization`.
2. `libraries/domain-serialization/src/index.js`:
   ```js
   const deserialize = (arg) =>
     serializer.deserialize(typeof arg === 'string' ? JSON.parse(arg) : arg)
   ```
   A string message is `JSON.parse`d (V8's parser is iterative and survives deep
   nesting) and then handed to the recursive walker, which overflows.
3. `libraries/browser-extension-rpc/src/index.js` runs it on inbound transport
   data: `transport.on('data', (data) => onData(deserialize(data)))`, and
   `apps/sdk-minimal-demo/src/__tests__/multi-process.ts` wires the same
   `deserialize` into the RPC transport.

---

## 4. Risk Assessment

| Factor | Rating | Rationale |
|---|---|---|
| **Likelihood** | Medium | Tiny, trivially-constructed payload; the vulnerable function is wired onto inbound message handling. Gated only by whether the specific transport's sender is attacker-reachable. |
| **Impact** | Medium (Availability: High; Confidentiality/Integrity: None) | Immediate crash of the message-handling context; potential crash loop if the message is replayed on reload. |
| **Overall** | **Medium** | Reliable, low-cost client-side DoS at a deserialization boundary. |

**Impact on the Exodus Desktop Wallet (in-scope product):** The Desktop Wallet is
an Electron application that uses this SDK. `deserialize()` runs on the
inter-context message path; a crafted message on that path crashes the receiving
Electron context. *A working PoC against the shipped desktop build is the step
that fully satisfies the program's "External Dependencies" clause; see §6.*

---

## 5. Recommended Controls (Remediation)

Add an explicit recursion-depth limit (or convert to an iterative walk with a
bounded work budget). A deliberately-thrown, caught `RangeError` is safe; an
unbounded native stack overflow is not.

```js
const MAX_DEPTH = 256
const deserialize = (value, depth = 0) => {
  if (depth > MAX_DEPTH) throw new RangeError('serialization: max depth exceeded')
  ...
  if (t === 'object') return mapValues(v, (o) => deserialize(o, depth + 1))
  if (t === 'array')  return v.map((o) => deserialize(o, depth + 1))
}
```

Callers at message boundaries should additionally catch deserialization errors so
one malformed message cannot take down the context.

---

## 6. Notes for Triage (scope & reachability)

- The vulnerable function and its wiring onto inbound messages are demonstrated
  **entirely from in-scope source**. What the open-source scope cannot itself
  establish is whether a **low-privilege sender** (e.g. a web page / content
  script / separate process) can reach the specific transport in the *shipped*
  Desktop Wallet — that trust boundary is set by closed app wiring. If your team
  confirms an untrusted sender reaches one of these boundaries, the vector is
  `PR:N` and the severity rises accordingly.
- I am happy to develop a PoC against the packaged Exodus Desktop build on
  request to satisfy the "External Dependencies — working Proof of Concept"
  requirement.

**Attachment:** `poc_deserialize_dos.mjs`
