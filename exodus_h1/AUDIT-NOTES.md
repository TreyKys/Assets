# Exodus "Open-Source Libraries (SDK & Crypto)" — audit notes

Scope (all Critical-eligible, 0 resolved reports): `@exodus/sentry-client`,
`@exodus/safe-string`, `@exodus/keychain`, `@exodus/errors`, `ExodusOSS/hydra`,
`ExodusOSS/crypto`, `ExodusOSS/bytes`.

## Findings

### 1. base58 O(n²) DoS — REPORTABLE (Medium)
See `FINDING-base58-quadratic-dos.md` + `poc_base58_dos.mjs`. Measured, in-scope,
public API, no length bound. `base58check`/`wif` inherit it. In-scope callers on
external input: hw-trezor `getWalletId` and hw-ledger `getPublicKey` (device
responses) → malicious-device / MITM'd-bridge freeze.

### 2. `@exodus/serialization` deserialize unbounded recursion — REPORTABLE (Medium, maybe High)
See `FINDING-serialization-recursion-dos.md` + `poc_deserialize_dos.mjs`. `deserialize`
recurses on nested `{t,v}` with no depth limit → stack-overflow CRASH on a tiny
(~40-120 KB) nested payload. Wired to run on inbound RPC `data` in
`@exodus/browser-extension-rpc` (`onData(deserialize(data))`). Better High
candidate than base58: tiny input, outright crash. Untrusted-caller wiring lives
in the closed app.

### 3. `KeyIdentifier.compare` treats a missing field as a wildcard — secondary / hardening
`libraries/key-identifier/src/key-identifier.js`:

```js
static compare = (a, b) => !['derivationAlgorithm','derivationPath','assetName','keyType']
  .some((f) => hasOwnProperty(a, f) && hasOwnProperty(b, f) && a[f] !== b[f])
```

A field only counts as a difference when **both** objects own it. If either side
omits a field, that field is a wildcard and never causes inequality — so
`compare` can return "equal" for key identifiers that actually differ.

`compare` is used as an **allow/authorization check** in
`features/cached-sodium-encryptor/module/cached-sodium-encryptor.ts`
(`#checkIfAllowed` → only `WALLET_INFO`/`FUSION` keys may be cached/used). If the
allowed constants lack an own `assetName` (plausible), then `keyId.assetName`
becomes a wildcard there, and `getCacheKey()` **includes** `assetName` — so
distinct `assetName` values with the same path all pass the allow-check yet each
creates a **new entry in an unbounded `Map` with no eviction** → memory-growth
DoS.

Why it's only secondary today: the single in-scope call site validates its input
through a Zod schema that reconstructs a full `KeyIdentifier` (all own-props
present), and the `keyId` typically comes from app code rather than a remote
attacker, so practical reachability is weak. Still worth fixing: `compare` should
treat "present on one side, absent on the other" as **not equal**, and the cache
should be bounded. Flagging in case it's reachable from an app path I can't see.

## Areas audited and found solid (no bug)

- **`@exodus/keychain`** — key derivation, external-key import, ECDSA/Schnorr/
  schnorrZ/ed25519 signing, private-key locking, tweak negate/add. Exhaustive
  length/type asserts, no nonce reuse, hedged extra-entropy, frozen legacy map.
- **`ExodusOSS/crypto`** — `secp256k1.mjs` (hedged ECDSA nonces by default,
  strict low-s verify → anti-malleability, careful tweak validation),
  `curve25519.mjs` (copies on signOpen output, no 64-byte private acceptance),
  `randomBytes` (native CSPRNG, assertSize), `output.js` conversions.
- **`@exodus/errors` + `@exodus/sentry-client` + `@exodus/safe-string`** — the
  error → Sentry pipeline is **allowlist-gated**, not regex-scrubbed: `SafeError`
  keeps a hint only if it round-trips through the safe-string allowlist or a
  static prefix; `SafeContext` is a strict Zod schema with every string
  `.refine(isSafe)`. A seed phrase / private key in an arbitrary error message is
  *dropped*, not transmitted. `captureTraceId` whitelists only `*.exodus.io`
  traceparent IDs. No leak path found.
- **`@exodus/bytes`** (besides base58) — `bech32` (default `limit=90`, BIP-173
  padding/checksum correct), `base32` (linear), `base64`/`hex` (native/linear,
  strict validation), `wif` (correct copy semantics). All bounded/linear.
- **hydra `cached-sodium-encryptor` / `message-signer`** — cache restricted to 2
  fixed key-IDs; message signing delegates byte-formatting to asset libs
  (out of scope). See finding #2 for the one edge on the compare check.

## Method
Read-only source audit of the cloned repos; timing PoC run against the real
`@exodus/bytes` code on Node v22. No live Exodus service was touched.
