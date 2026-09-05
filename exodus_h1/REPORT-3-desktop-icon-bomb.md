# Vulnerability Report — Resource-exhaustion in the Desktop Wallet asset-icon pipeline (unbounded gzip decompression + `<use>`-permissive SVG validator)

**Researcher:** treyky
**Program:** Exodus (Desktop Wallet application)
**Affected component:** Exodus Desktop v26.8.27 — asset-icon processing:
`src/app/core/index.js` (`svgProcess`, `validate({svg,isTrusted:true})`) and
`src/app/ui/index.js` (`AssetIcons.unzipIcon` / `svgWrite`).
**Report date:** &lt;date&gt;
**Weakness (CWE):** CWE-409 Improper Handling of Highly Compressed Data (decompression bomb) +
CWE-776 Improper Restriction of Recursive Entity References (SVG billion-laughs) → CWE-400.
**Severity (proposed):** **Low — defense-in-depth / hardening.** See §4 for the honest reachability
assessment; I am *not* claiming a confirmed remote exploit.

---

## 1. Executive Summary

The Desktop Wallet processes asset icons as **gzip-compressed SVGs**. Two independent, verified flaws
sit in that pipeline:

1. The gunzip step (native `DecompressionStream('gzip')`) has **no output-size limit** — a small input
   inflates without bound (measured 1 MB → ~1 GB, ~1029×), scaling to whatever the producer chooses.
2. The SVG validator that runs on "trusted" icons **allows `<use>`** (plus `<g>`/`<defs>`), which
   permits a classic **billion-laughs** nested-reference expansion. A **1.4 KB** SVG made *only* of
   validator-allowed tags drives the Chromium renderer to **~4 GB RSS** and never finishes rendering.

Either flaw lets a single small icon payload exhaust memory / hang or crash the renderer that displays
it. I want to be upfront: in the shipped client I could **not** find a path where an external attacker
directly supplies these icon bytes (see §4) — so this is submitted as a **hardening finding**, with a
fully-reproducible demonstration of the unguarded sink and a note on the one delivery path that would
make it exploitable (a malicious icon reaching Exodus's asset registry).

---

## 2. Technical Detail

Pipeline (`AssetIcons` → core `svg` module):
```
e.icon (base64)  →  Buffer.from(e.icon,'base64')  →  svgProcess(t,{shouldGunzip:true})
   →  gunzip(t)            // DecompressionStream('gzip') + Response(...).arrayBuffer(): NO size cap
   →  .toString('utf8')    // materializes the entire inflated output
   →  validate({svg, isTrusted:true})   // tag/attribute allowlist
   →  rendered as data:image/svg+xml;base64,...
```

**Flaw 1 — unbounded gunzip.** Nothing in the path caps the inflated size; RSS scales linearly with
the attacker-chosen inflated size.

**Flaw 2 — `<use>` billion-laughs.** The trusted validator's allowlist is
`svg, defs, linearGradient, radialGradient, stop, g, path, circle, ellipse, rect, clipPath, mask,
pattern` **plus `image, use`** when `isTrusted:true`. `<script>` and `on*=` handlers are correctly
blocked (so this is a resource bomb, not XSS), and `<image href>` is correctly restricted to
`data:image/(png|jpeg|gif|webp);base64` (so no SSRF via `<image>`). **But** nested
`<g id="rN"><use href="#r(N-1)"/><use href="#r(N-1)"/></g>` chains (double-quoted fragment hrefs pass
the validator's regex) expand as 2^depth on rasterization because `<use>` is not memoized.

---

## 3. Proof of Concept (reproducible; measured against the app's exact primitives)

Scripts + payloads attached: `task1_gzip_bomb.mjs`, `task1_svg_bomb_gen.mjs`,
`task1_svg_bomb_render.mjs`, `gzip_bomb_10MB_zeros.gz`, `svg_billion_laughs_depth20.svg`.

**3.1 gunzip bomb** — the app's own `DecompressionStream('gzip')` primitive, no cap:

| input (zeros) | gz size | inflated | ratio | RSS after |
|---|---|---|---|---|
| 10 MB | 10,221 B | 10 MB | 1026× | 92 MB |
| 200 MB | 203,860 B | 200 MB | 1029× | 670 MB |
| 1 GB | 1,043,656 B | 1 GB | 1029× | 3,166 MB |

**3.2 SVG billion-laughs** — payload uses ONLY validator-allowed tags (validator regexes mirrored from
source to prove each payload passes the real gate), rendered as `data:image/svg+xml` in an `<img>`:

| depth | leaf `<use>` | SVG bytes | result | peak Chromium RSS |
|---|---|---|---|---|
| 15 | 32,768 | 1,115 | loaded 5.3 s | 953 MB |
| 18 | 262,144 | 1,301 | **timeout >20 s** | 3,814 MB |
| 20 | 1,048,576 | 1,425 | **timeout >20 s** | 3,993 MB |

A 1.4 KB icon → ~4 GB RSS / hung renderer. Video PoC shows this reproduction.

---

## 4. Reachability (honest assessment)

I traced every icon path in the shipped client. The icon bytes for both built-in and custom/unknown
tokens are supplied by **Exodus's own backend** (`fusion.exodus.io/api` "tokens" lookup), not by a
raw attacker URL, the token contract, a third-party CDN, WalletConnect/dApp metadata, or any
user-supplied field (there is no `logoURI`/`iconUrl` input in the custom-token flow). **So there is no
client-side path where an external attacker directly delivers these icon bytes** — I am not claiming
otherwise.

The one delivery path that would make this exploitable is **supply-chain**: token icons enter
`fusion.exodus.io` via Exodus's open-source asset-listing process (a reviewed pull request with a logo
file). A malicious `<use>` billion-laughs / gzip-bomb icon that passed listing review would then be
served to every wallet that views that token — a **stored client-side DoS delivered by Exodus's own
infrastructure**. I have **not** attempted this (planting a DoS payload in production would harm real
users and is out of bounds), so I report it only as the theoretical delivery vector for the proven
sink.

**Why fix it anyway:** the sink is unconditionally unsafe. Icon-listing review is not a reliable
defense against a compact bomb payload that renders as a normal-looking logo, and the client should
not depend on server-side/human review to avoid inflating a 1 KB input to 4 GB.

---

## 5. Recommended Controls

- **Cap gunzip output** (e.g. reject inflated icons over a few hundred KB — real SVG icons are tiny).
- **Disallow `<use>`** in the icon validator, or hard-cap `<use>`/element instantiation and nesting depth.
- Prefer **rasterized icons** (PNG/WebP with dimension caps) for untrusted/unverified-token icons.
- Render icons in a size/time-bounded context so a single icon can't hang the main renderer.

---

## 6. Attachments
`task1_gzip_bomb.mjs`, `task1_svg_bomb_gen.mjs`, `task1_svg_bomb_render.mjs`,
`gzip_bomb_10MB_zeros.gz`, `svg_billion_laughs_depth20.svg`, and `poc.mp4` (renderer hang demo).
