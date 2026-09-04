# Exodus Desktop v26.8.27 — creative/deep leads (backdoors + amplification "zip-bomb" class)

Second static pass, hunting architectural backdoors and decompression/expansion bombs
(adapting the zip-bomb concept). Main process confirmed clean of exec backdoors:
**no `spawn`/`exec`** (only a hardcoded macOS `sysctl` for Rosetta), no dynamic `require`/`eval`,
updater host is fixed (`updates.exodus.io`) + Linux auto-update disabled + OS-signature-protected.

Three latent weaknesses found. All three share the SAME gap: the sink is real and unguarded, but
the **attacker-controlled input source is not confirmable from static analysis** — it needs the
dynamic (VM) phase. None is a confirmed exploit yet; none should be submitted without a working PoC.

## Lead A — SVG asset-icon pipeline: unbounded `gunzip` + `<use>`-permissive "trusted" validator  ★ best zip-bomb candidate
Path (ui `AssetIcons` class → core `svg` module):
```
e.icon (base64)  →  Buffer.from(e.icon,'base64')  →  svgProcess(t,{shouldGunzip:true})
   →  gunzip(t)               // native DecompressionStream, NO size cap
   →  .toString('utf8')       // materializes full inflated output
   →  cleanupTrusted(svg)     // validate({svg, isTrusted:true})
   →  rendered as data:image/svg+xml;base64,...
```
Two bombs in one sink:
1. **Decompression bomb** — `gunzip` on `e.icon` has no output-size limit; a few-KB gzip inflating
   to GBs allocates unbounded memory *before* validation runs → renderer OOM/crash.
2. **SVG billion-laughs render bomb** — the "trusted" validator's tag allowlist is
   `[svg,defs,linearGradient,radialGradient,stop,g,path,circle,ellipse,rect,clipPath,mask,pattern]`
   **plus `image` and `use` when `isTrusted:true`**. Nested `<use href="#…">` referencing `<g>`/`<defs>`
   groups (double-quoted hrefs pass; the validator only rejects `'` and backtick) expands
   exponentially on rasterization → CPU/memory bomb. `<script>`/`on*=` are blocked, so this is a
   *bomb/SSRF-via-`<image href>`* vector, not XSS.

**Reachability gap:** `e.icon` is delivered as a compressed SVG by Exodus's asset registry
(`*.a.exodus.io`), which is Exodus-controlled. Need to confirm dynamically whether a **custom token**
(added by contract address) or any third-party/asset-plugin path can supply `e.icon` /reach
`unzipIcon()` with attacker bytes. If yes → Medium (DoS) at least; if the SVG is ever inlined (not
`<img>`-sandboxed) → higher.

## Lead B — `openExternal:unchecked` (from first pass) — missing URL scheme validation
`rpcMain.handle("openExternal:unchecked")` skips the strict `validate()` allowlist; reachable via a
generic renderer helper `invoke("openExternal:unchecked", url)` and the raw ipc bridge. Needs an
attacker-controlled URL reaching it (or a renderer XSS). See `DESKTOP-MAIN-AUDIT.md`.

## Lead C — `DEBUG_MODE` file "backdoor" (local activation)
`DEBUG_MODE` turns on if the file `<userData>/debug` exists (empty file suffices), or via `--debug` /
`--datadir` CLI args. `getDebugFile()` = `join(userData||datadir, "debug")`. Activation is **local**
(needs a local file-write primitive or CLI access), so limited on its own — but a useful escalation
target if chained with any file-write bug. Worth checking what DEBUG_MODE unlocks dynamically
(devtools auto-open / extra IPC / dev menu → `nfts:showDevTools` opens devtools via IPC).

## Amplification family recap (for the report set)
- `@exodus/bytes` base58 O(n²)  — confirmed (library).
- `@exodus/serialization` deserialize recursion — confirmed (library).
- Lead A icon `gunzip` — desktop-specific decompression bomb — **reachability pending**.

## Next: dynamic confirmation (VM)
Add `DYNAMIC-TEST-PLAN.md` Test 5: add a **custom token** and, if its icon is fetched/settable,
point it at a crafted gzip'd SVG (billion-laughs `<use>` and/or a high-ratio gzip blob); watch for
renderer memory spike / crash. Also test whether any dApp/deep-link/asset-plugin path reaches
`unzipIcon`/`svgWrite`.
