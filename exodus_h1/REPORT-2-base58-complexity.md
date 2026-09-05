# Vulnerability Report — Uncontrolled Algorithmic Complexity (O(n²) Denial of Service) in `@exodus/bytes` base58

**Researcher:** treyky
**Program:** Exodus — Open-Source Libraries (SDK & Crypto)
**Affected asset:** `github.com/ExodusOSS/bytes` (`@exodus/bytes`) — `base58.js`; inherited by `base58check.js` and `wif.js`
**Report date:** &lt;date&gt;
**Weakness (CWE):** CWE-407 Inefficient Algorithmic Complexity → CWE-400 Uncontrolled Resource Consumption
**Severity:** Medium — CVSS:3.1 `AV:N/AC:L/PR:L/UI:R/S:U/C:N/I:N/A:H` (5.7)

---

## 1. Executive Summary

`@exodus/bytes` is the low-level byte/encoding library used across Exodus wallets.
Its base58 **encoder and decoder are both O(n²)** and impose **no maximum input
length**. base58 is the exact format wallets use to parse *untrusted* data —
recipient addresses (pasted or scanned from a QR code), extended public keys, and
WIF private keys entered on the import screen. A single crafted base58 string of
~1 MB therefore blocks the single JavaScript thread for **minutes**, freezing the
wallet UI. The effect is availability-only (no key exposure), but one malformed
input renders the application unresponsive.

---

## 2. Vulnerability Details

| Field | Detail |
|---|---|
| **Component** | `base58.js` → `toBase58core()` / `fromBase58core()`; exported as `toBase58`, `fromBase58`, `toBase58xrp`, `fromBase58xrp` |
| **Inherited by** | `base58check.js` (`toBase58check`/`fromBase58check`), `wif.js` (`toWifString`/`fromWifString`) — they call base58 on the raw string *before* any checksum/length validation |
| **Root cause** | Quadratic bignum conversion with no input-length ceiling (the `length > 60` branch is a performance path-switch, not a bound) |
| **Trigger** | One long base58 string (decode) or long byte buffer (encode) |
| **Result** | Event loop fully blocked for seconds→minutes; UI freeze / forced restart |

### Root cause

`fromBase58core()` (default V8 path) rescans the growing output big-number buffer
for **each** input character — `O(length × size) ≈ 0.75·length²`:

```js
for (let i = zeros; i < length; i++) {   // per input char
  let k = size - 1
  for (;;) { c += 58 * res[k]; res[k] = c & 0xff; c >>>= 8; k--; ... } // rescans res
}
```

`toBase58core()`'s `length > 60` branch (bignum `/58n` loop) is likewise
quadratic. No entry point imposes a maximum length.

### Attacker goal / scenario

The attacker's goal is to make the wallet **unavailable** by supplying an
over-long base58 value where the wallet expects an address / WIF key / xpub —
e.g. a malicious QR code, a crafted address in a payment URI / dApp request, or a
pasted "private key" on the import screen — causing the app to grind for minutes.

---

## 3. Proof of Concept

```bash
npm i @exodus/bytes
# save poc_base58_dos.mjs (attached), then:
node poc_base58_dos.mjs
```

### Observed output (Node v22 / desktop V8)

| input | `fromBase58` decode | `toBase58` encode |
|------:|--------------------:|------------------:|
| 32 000 | 344 ms | — |
| 64 000 | 1 343 ms | 3 502 ms |
| 128 000 | 5 245 ms | 13 601 ms |
| 256 000 | 19 572 ms | — |

Clean quadratic scaling (~4× per 2× of input). Extrapolated, a ~1 MB input blocks
the event loop for minutes — no other JS (UI, timers, callbacks) runs meanwhile.

### In-scope callers on externally-sourced input

- `features/hw-trezor/src/module/device.ts:95` (`getWalletId`): `fromBase58(xpub)`
  where `xpub` is the Trezor device response.
- `features/hw-ledger/src/module/assets/bitcoin.ts:81` (`getPublicKey`):
  `fromBase58(pubString)` from the Ledger response.

---

## 4. Risk Assessment

| Factor | Rating | Rationale |
|---|---|---|
| **Likelihood** | Medium | base58 decode is used on untrusted addresses/keys; a single long string triggers it. In-scope hydra callers are hardware-wallet responses (needs a malicious/counterfeit device or an intercepted bridge/transport). |
| **Impact** | Medium (Availability: High; Confidentiality/Integrity: None) | Multi-minute UI/thread freeze; forced restart. |
| **Overall** | **Medium** | Reliable client-side resource-exhaustion DoS; severity depends on how untrusted the reachable input is. |

**Impact on the Exodus Desktop Wallet (in-scope product):** The Desktop Wallet is
Electron (V8) — the measured V8 timings apply directly. Any desktop code path
that base58-decodes an externally-supplied address / imported WIF key without a
length pre-check inherits this freeze. *A working PoC against the shipped desktop
build — e.g. pasting/scanning a crafted address that freezes the app — is the step
that fully satisfies the program's "External Dependencies" clause; see §6.*

---

## 5. Recommended Controls (Remediation)

Impose an explicit maximum input length at the base58 entry points (and thus on
`base58check`/`wif`). Real base58 payloads are tiny (addresses < ~64 chars, WIF
< 53, xpub < 112), so a conservative cap removes the quadratic blow-up with zero
impact on legitimate use:

```js
const MAX_BASE58_LEN = 512 // larger than any real address / WIF / xpub
function fromBase58core(str, ...) {
  if (str.length > MAX_BASE58_LEN) throw new RangeError('base58 input too long')
  ...
}
// and symmetrically on the byte length in toBase58core
```

---

## 6. Notes for Triage (scope & reachability)

- The defect and its quadratic cost are demonstrated against the **real library
  code**. The in-scope hydra callers are hardware-wallet responses (a
  malicious-device / intercepted-transport vector). The remote no-privilege path
  (malicious QR / dApp-supplied address) runs through Exodus's closed
  app/asset-lib layer, which the open-source scope cannot exercise.
- I am happy to develop a PoC against the packaged Exodus Desktop build on
  request to satisfy the "External Dependencies — working Proof of Concept"
  requirement.

**Attachment:** `poc_base58_dos.mjs`
