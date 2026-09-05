# Task 1 — Lead A sink proof (gunzip bomb + SVG billion-laughs render bomb)

Both tests exercise the exact sink primitives used by `core/index.js`'s `svgProcess()`
(`AssetIcons` pipeline): native `DecompressionStream('gzip')` with no output-size cap, and
`validate({svg, isTrusted:true})`'s tag/attribute allowlist. Source citations below are pulled
directly from `exodus_h1/desktop_app_src/src/app/core/index.js`.

## 1.1 — Unbounded gunzip

`svgProcess`'s gunzip path (confirmed in source):
```
const { DecompressionStream } = globalThis;
... new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip')) ...
new Response(stream).arrayBuffer()   // materializes the ENTIRE inflated output, no cap
```

Script: `task1_gzip_bomb.mjs`. Method: gzip `N` bytes of `0x00` (maximally compressible) at
level 9, then run the app's own gunzip primitive on it, measuring wall time and process RSS
before/after.

Run: `node --expose-gc --max-old-space-size=8192 task1_gzip_bomb.mjs`

| label | raw input | gz size | inflated | ratio | time | RSS before | RSS after |
|---|---|---|---|---|---|---|---|
| 10MB-zeros | 10,485,760 B | 10,221 B | 10,485,760 B | 1026x | 220 ms | 41.2 MB | 92.5 MB |
| 200MB-zeros | 209,715,200 B | 203,860 B | 209,715,200 B | 1029x | 1,672 ms | 73.0 MB | 670.1 MB |
| 1GB-zeros | 1,073,741,824 B | 1,043,656 B | 1,073,741,824 B | 1029x | 9,517 ms | 270.2 MB | 3,165.6 MB |

A **1 MB gzip file inflates to ~1 GB** (consistent ~1029x ratio, the practical ceiling for
DEFLATE on all-zero input) with **no size cap anywhere in the path** — RSS scales linearly with
the attacker-chosen inflated size, and there's nothing stopping a larger raw source (bigger than
zeros-only, still highly compressible, e.g. repeated real SVG markup) from pushing this to
whatever the process's memory limit is. Sample payload: `gzip_bomb_10MB_zeros.gz` (10,221 bytes
→ 10 MB).

**Confirmed: unbounded decompression amplification, no cap, in the exact code path the app uses.**

## 1.2 — SVG billion-laughs render bomb (allowed-tag-set only)

Built a payload using **only** tags/attributes the trusted validator (`validate({isTrusted:true})`
in `core/index.js`) accepts — the exact regexes were extracted from source and mirrored in a
validator clone (`task1_svg_bomb_gen.mjs`) so every generated payload is proven to pass the real
gate's rules before testing:
- Tags: `svg, defs, g, rect, use` (subset of the full allowlist
  `svg,defs,linearGradient,radialGradient,stop,g,path,circle,ellipse,rect,clipPath,mask,pattern`
  `+image,use` when trusted).
- `<use>` may **only** carry `href="#id"` (fragment-local) or a `translate/rotate/scale/matrix`
  `transform=` — confirmed via the exact regex
  `/^(href|xlink:href)="#[\w:-]+"$/` and the transform regex in source. No external/`javascript:`
  href is syntactically possible.
- `g`/`use` must use explicit open/close tags — the validator's self-close (`/>`) exemption list
  is `path,stop,circle,ellipse,rect,image` only, **not** `g`/`use`/`svg`.
- Bonus finding: `<image>` `href`/`xlink:href` is restricted to
  `^data:image/(png|jpeg|gif|webp);base64,...$` — i.e. **no external URL or SVG data URI is
  syntactically possible for `<image>`**. This refutes the "SSRF via `<image href>`" half of Lead
  A as written in `DESKTOP-CREATIVE-LEADS.md` — worth correcting there. The billion-laughs
  amplification via `<use>` is unaffected by this and stands on its own.

Payload shape: a chain of `depth` `<g id="rN"><use href="#r(N-1)"/><use href="#r(N-1)"/></g>`
groups (fan-out 2) rooted at a single `<rect>`, then one top-level `<use href="#r{depth}">`. Byte
size grows linearly with depth; **instantiated leaf count grows as 2^depth** if the renderer
doesn't memoize `<use>` expansion.

Test: encode as `data:image/svg+xml;base64,...`, load into an `<img>` in headless Chromium
(Playwright/CDP), measure time-to-`onload` and peak Chromium RSS (server-side `ps` polling, since
the renderer becomes CDP-unresponsive at high depth). Script: `task1_svg_bomb_render.mjs`.

| depth | leaf `<use>` instantiations | SVG bytes | result | wall time | peak Chromium RSS |
|---|---|---|---|---|---|
| 5 | 32 | 508 | loaded | 17 ms | — |
| 10 | 1,024 | 805 | loaded | 116 ms | — |
| 15 | 32,768 | 1,115 | loaded | 5,281 ms | **952.8 MB** |
| 18 | 262,144 | 1,301 | **timeout (>20s, never rendered)** | ≥20,000 ms | **3,814.5 MB** |
| 20 | 1,048,576 | 1,425 | **timeout (>20s, never rendered)** | ≥20,000 ms | **3,992.6 MB** |

A **1.4 KB SVG** (well within any plausible icon-size limit) made entirely of tags/attributes the
"trusted" validator allows drives Chromium's renderer process to ~4 GB RSS and it never finishes
rendering within 20 seconds — clear exponential (not linear) growth matching the leaf-instantiation
count, confirming `<use>` is **not memoized** by this renderer and the nested-reference chain is a
genuine CPU/memory bomb. Sample payload: `svg_billion_laughs_depth20.svg` /
`svg_billion_laughs_depth20.datauri.txt`.

**Confirmed: the allowed-tag set alone (no `<image>`, no `<script>`, no external refs — just
`g`/`use`/`rect` with double-quoted fragment `href`s) yields a render bomb.**

## Summary

- **1.1 gunzip bomb: confirmed** — unbounded, ~1029x ratio, no cap, scales to whatever the
  attacker picks.
- **1.2 SVG billion-laughs: confirmed** — allowed-tag-set alone is sufficient; ~4 GB RSS / hung
  renderer from a 1.4 KB payload.
- **Correction to `DESKTOP-CREATIVE-LEADS.md`**: the `<image href>` SSRF/external-fetch angle is
  refuted by the validator's `data:image/(png|jpeg|gif|webp);base64,...` restriction on that
  attribute — not reachable as written. The billion-laughs `<use>` bomb is a separate, confirmed
  mechanism, unaffected by that restriction.
- **Still open (Task 2, blocked pending recalibration per Task 0):** whether an attacker can
  actually deliver `e.icon` bytes into this pipeline (custom-token icon fetch, or another
  asset/plugin path) — that's the reachability question, not proven here. This task only proves
  the sink is real and unguarded.
