# Uncontrolled algorithmic complexity (O(n²)) in `@exodus/bytes` base58 encode/decode

**Asset:** `https://github.com/ExodusOSS/bytes` (`@exodus/bytes`) — HackerOne "Open-Source Libraries (SDK & Crypto)"
**File:** `base58.js` → `toBase58core()` / `fromBase58core()`
**Also affects:** `base58check.js` (`toBase58check`/`fromBase58check`), `wif.js` (`toWifString`/`fromWifString`) — they call `fromBase58`/`toBase58` on the raw string *before* any checksum/length validation.
**Class:** CWE-407 Inefficient Algorithmic Complexity / CWE-400 Uncontrolled Resource Consumption (DoS)
**Severity (proposed):** Medium (CVSS:3.1 AV:N/AC:L/PR:N/UI:R/S:U/C:N/I:N/A:H ≈ 6.5) — see "Severity & reachability".

## Summary

`@exodus/bytes` is the low-level byte/encoding library used across Exodus wallets.
Its base58 encoder and decoder both run in **O(n²)** time and impose **no maximum
input length**. Because base58 is the format used to parse *untrusted* data —
recipient addresses (pasted or scanned from a QR), extended public keys, and WIF
private keys entered on the import screen — a single crafted string of ~1 MB
blocks the wallet's single JavaScript thread for **minutes**, hanging the UI
(and, on mobile, the whole Hermes runtime). No key material is exposed, but the
application is rendered unresponsive by one malformed input.

## Root cause

`fromBase58core()` (the default path on V8/Node — `shouldUseBigIntFrom` is false
off-Hermes) decodes with a nested loop: for **each** of the `length` input
characters it rescans the growing output big-number buffer (`res`, up to
`~0.75·length` bytes):

```js
for (let i = zeros; i < length; i++) {      // O(length)
  ...
  let k = size - 1
  for (;;) {                                // inner pass over res (O(size))
    c += 58 * res[k]; res[k] = c & 0xff; c >>>= 8; k--
    ...
  }
}
```

Total work ≈ `length × size` ≈ **0.75·length²**. The Hermes path
(`x = x * 58n + BigInt(c)`) is likewise quadratic (bignum multiply of a growing
value). `toBase58core()`'s `length > 60` branch is the same story on encode
(`x / 58n` in a loop over a growing bignum).

The only length check in the file is a **performance** path-switch
(`if (length > 60)`), **not** a security bound. There is no maximum-length guard
anywhere in `base58.js`, `base58check.js`, or `wif.js`.

## Measured impact (Node v22, desktop V8 — worst-case is worse on a phone)

Reproduced with the actual library code (`poc_base58_dos.mjs`):

| input | `fromBase58` decode | `toBase58` encode |
|------:|--------------------:|------------------:|
| 8 000 | 22 ms | — |
| 16 000 | 93 ms | 234 ms |
| 32 000 | 344 ms | — |
| 64 000 | 1 343 ms | 3 502 ms |
| 128 000 | 5 245 ms | 13 601 ms |
| 256 000 | 19 572 ms | — |

Clean quadratic scaling (≈4× per 2× of input). Extrapolating: a **~1 MB** input
blocks the event loop for **minutes**. The thread is fully blocked — no other
JS (UI, timers, network callbacks) runs during that window.

## Severity & reachability

- The vulnerability is in an **in-scope library** and its **public, exported
  API** (`fromBase58`, `toBase58`, `fromBase58xrp`, `toBase58xrp`, and
  transitively `fromBase58check`/`fromWifString`).
- In a wallet these functions parse **attacker-supplied, unbounded-length**
  strings:
  - a recipient **address pasted or scanned from a QR code**,
  - a **WIF private key** typed/pasted on "import private key",
  - an **address delivered by a dApp / WalletConnect / payment URI** that the
    wallet decodes to validate.
- Impact is availability only (UI/thread freeze, forced restart). No
  confidentiality/integrity impact.
- I have proven the defect and its quadratic cost against the real library code.
  The end-to-end "malicious QR freezes the app" path runs through Exodus's
  closed-source app/asset-lib layer, which I cannot exercise from the
  open-source scope — so I am proposing **Medium** and deferring to your triage
  on whether an app-level auto-decode path (e.g. address validation on paste/scan
  or on an incoming dApp request) with no length pre-check raises it to High.

## Suggested fix

Impose an explicit maximum input length on the base58 entry points (and thus on
`base58check`/`wif`). Real-world base58 payloads are tiny — addresses ≤ ~64
chars, WIF ≤ 53, xpub ≤ 112. A conservative cap (e.g. reject inputs longer than
a few hundred bytes/chars) fully removes the quadratic blow-up with zero impact
on legitimate use:

```js
const MAX_BASE58_LEN = 512 // > any real address / WIF / xpub
function fromBase58core(str, ...) {
  if (str.length > MAX_BASE58_LEN) throw new RangeError('base58 input too long')
  ...
}
// and symmetrically on the byte length in toBase58core
```

## PoC

`poc_base58_dos.mjs` (in this folder):

```
npm i @exodus/bytes
node poc_base58_dos.mjs
```

Prints the timing table above and demonstrates the unbounded quadratic growth.
