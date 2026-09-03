# HackerOne submissions — Exodus "Open-Source Libraries (SDK & Crypto)"

Two reports below, paste-ready. Submit #1 first (stronger DoS shape), then #2.
Attach the matching PoC file to each. Both are honest **Medium** with an explicit,
evidence-backed "→ High if triage confirms an untrusted sender" note — let their
grader make the final severity call.

---

## REPORT #1 (primary)

**Title:** Unbounded recursion in `@exodus/serialization` `deserialize` — small nested payload crashes the message-handling surface (DoS)

**Asset:** `https://github.com/ExodusOSS/hydra` → `libraries/serialization` (`@exodus/serialization`)

**Weakness:** CWE-674 Uncontrolled Recursion (→ CWE-400 Uncontrolled Resource Consumption)

**Severity:** Medium (CVSS:3.1 `AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:H` = 6.5) — see note; potentially High (`PR:N`) if an untrusted sender reaches the boundary.

**Summary:**
`deserialize()` (returned by `createSerializeDeserialize()` in
`libraries/serialization/src/index.js`) recursively walks nested
`{ t:'object'|'array', v:… }` nodes with no depth limit:

```js
if (t === 'object') return mapValues(v, (o) => deserialize(o))
if (t === 'array')  return v.map((o) => deserialize(o))
```

A small (~40–120 KB) deeply-nested payload overflows the JS stack, throwing
`RangeError: Maximum call stack size exceeded`. It is wired to run on inbound
messages, so a single crafted message crashes the surface handling it.

**Steps to reproduce:**
1. `git clone https://github.com/ExodusOSS/hydra && cd hydra/libraries/serialization`
2. Provide the one `@exodus/bytes` base64 shim (the nested array/object path never
   uses it):
   ```
   mkdir -p node_modules/@exodus/bytes
   printf '{"name":"@exodus/bytes","type":"module","exports":{"./base64.js":"./base64.js"}}' > node_modules/@exodus/bytes/package.json
   printf 'export const toBase64=(u)=>Buffer.from(u).toString("base64");export const fromBase64=(s)=>new Uint8Array(Buffer.from(s,"base64"))' > node_modules/@exodus/bytes/base64.js
   ```
3. Save `poc_deserialize_dos.mjs` (attached) into `libraries/serialization/` and run `node poc_deserialize_dos.mjs`.

**Result:**
```
depth 1000  (~24 KB):  ok
depth 5000  (~120 KB): CRASH -> RangeError: Maximum call stack size exceeded
depth 20000+:          CRASH
```

**Reachability (proven from in-scope code):**
- `libraries/domain-serialization/src/domain-serialization.js` builds the
  serializer from `@exodus/serialization`.
- `libraries/domain-serialization/src/index.js`:
  `deserialize = (arg) => serializer.deserialize(typeof arg === 'string' ? JSON.parse(arg) : arg)`
  (`JSON.parse` is iterative and survives deep nesting; the recursive walker then
  overflows).
- `libraries/browser-extension-rpc/src/index.js` runs it on inbound transport
  data: `transport.on('data', (data) => onData(deserialize(data)))`;
  `apps/sdk-minimal-demo/src/__tests__/multi-process.ts` wires the same
  `deserialize` into the RPC transport.
- Payload: `{"t":"array","v":[{"t":"array","v":[ … ]}]}`, a few tens of KB.

**Impact:** A crafted inbound message crashes the message-handling surface
(extension background/service worker, worker thread, or renderer) → wallet becomes
unavailable / must be restarted. Availability only.

**Remediation:** Add an explicit depth limit (or iterative walk with a bounded
work budget) in `deserialize`:
```js
const MAX_DEPTH = 256
const deserialize = (value, depth = 0) => {
  if (depth > MAX_DEPTH) throw new RangeError('serialization: max depth exceeded')
  ...
  if (t === 'object') return mapValues(v, (o) => deserialize(o, depth + 1))
  if (t === 'array')  return v.map((o) => deserialize(o, depth + 1))
}
```

**Severity note:** I set `PR:L` because the open-source evidence proves the
vulnerable function runs on inbound RPC data but does not, by itself, establish
that a fully untrusted (web-page-level) sender reaches that port in the shipped
product — that trust boundary is in closed app wiring. If your team confirms an
untrusted sender can reach one of these boundaries, this is `PR:N` → High.

**Attachment:** `poc_deserialize_dos.mjs`

---

## REPORT #2 (secondary)

**Title:** O(n²) algorithmic complexity with no length bound in `@exodus/bytes` base58 encode/decode (DoS)

**Asset:** `https://github.com/ExodusOSS/bytes` (`@exodus/bytes`)

**Weakness:** CWE-407 Inefficient Algorithmic Complexity (→ CWE-400)

**Severity:** Medium (CVSS:3.1 `AV:N/AC:L/PR:L/UI:R/S:U/C:N/I:N/A:H` = 5.7) — potentially High depending on how you rate the library's untrusted-input usage.

**Summary:**
`base58.js` `toBase58core()` and `fromBase58core()` are both O(n²) and impose no
maximum input length (the `length > 60` branch is a perf path-switch, not a
bound). `base58check.js` and `wif.js` inherit this because they call
`fromBase58`/`toBase58` on the raw string before any checksum/length validation.
base58 is the format wallets use to parse untrusted addresses, WIF keys and
xpubs, so one crafted string blocks the single JS thread for minutes.

**Steps to reproduce:**
1. `npm i @exodus/bytes`
2. Save `poc_base58_dos.mjs` (attached) and run `node poc_base58_dos.mjs`.

**Result (Node v22, desktop V8):**
```
fromBase58 decode:  64k->1.3s  128k->5.2s  256k->19.6s
toBase58   encode:  64k->3.5s  128k->13.6s
```
Clean quadratic (~4× per 2× input); a ~1 MB input = minutes of fully-blocked
event loop.

**Reachability (in-scope callers on external input):**
- `features/hw-trezor/src/module/device.ts:95` (`getWalletId`): `fromBase58(xpub)`
  where `xpub` is the Trezor device response (via Trezor Bridge, a localhost
  service).
- `features/hw-ledger/src/module/assets/bitcoin.ts:81` (`getPublicKey`):
  `fromBase58(pubString)` from the Ledger response.
  Threat model: malicious/counterfeit device or MITM of the bridge/transport
  returns a multi-MB string → freeze.
- Library-level: base58 decode is by design used on untrusted, network-delivered
  addresses/keys; the remote no-privilege path runs through closed app code I
  can't exercise from scope.

**Impact:** Wallet UI / JS thread frozen for minutes on a single crafted input;
forced restart. Availability only.

**Remediation:** Cap input length at the base58 entry points (any real address /
WIF / xpub is < ~120 chars):
```js
const MAX_BASE58_LEN = 512
if (str.length > MAX_BASE58_LEN) throw new RangeError('base58 input too long')
```

**Attachment:** `poc_base58_dos.mjs`

---

### Secondary hardening note (mention in whichever report, or omit)
`KeyIdentifier.compare` (`libraries/key-identifier/src/key-identifier.js`) treats a
field that is missing on one side as a wildcard (a difference only counts when both
objects own the field). It gates the cache-allow check in
`features/cached-sodium-encryptor`; if the allowed constants omit `assetName`, that
becomes a wildcard while `getCacheKey` includes it → potential unbounded growth of a
`Map` with no eviction. Low practical reachability today (input is schema-reconstructed
into a full KeyIdentifier), so flagged as hardening, not a headline.
