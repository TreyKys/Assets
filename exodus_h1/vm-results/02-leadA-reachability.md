# Task 2 — Lead A reachability (Approach 1: static trace)

Question: can an attacker supply `e.icon` (the base64 gzip SVG) that reaches the confirmed
gunzip/billion-laughs sink (`vm-results/01-leadA-sink.md`)? Traced every code path in
`desktop_app_src/src/app/ui/index.js` that touches `.icon` / `unzipIcon` / `svgWrite` / `svgProcess`.
Static tracing was conclusive — Approach 2 (passive SNI/host capture) was not run: the only
remaining open question is server-side data hygiene at Exodus's backend, which passive traffic
capture cannot observe either (it would only re-confirm the hostname already found in source).

## Icon paths found, with origin of the bytes

### 1. Built-in / bundled assets — attacker-controlled: **NO**
`IconsStorage.getIcon(name)` reads an already-processed SVG from local disk (`getImagesDir()`):
```js
this.getIcon = async e => { const t = await s.default.svgRead(await i(this,p)[p](), e); return t ? `data:image/svg+xml;base64,${Buffer.from(t).toString("base64")}` : null }
```
This is a read of a previously-cached/validated file, not a live untrusted-bytes path.

### 2. Custom / unrecognized token icons — attacker-controlled: **NO (direct)**, **MAYBE (indirect, out of scope)**
The path that actually reaches the confirmed bomb sink. When `getAsset(name)` fails to resolve
locally (i.e. the asset is not in the app's bundled/known list — the custom-token-by-contract-
address case), a memoized fetcher runs:
```js
le = memoizeLruCache(async e => {
  const t = [e];
  const r = (await this.fetch("tokens", {tokenNames: t, lifecycleStatus: ["c","v","u"]}, "tokens"))[0];
  if (r?.icon) return this.iconsStorage.unzipIcon(r.icon);
}, e => e, {max: 100})
```
`this.unzipIcon` is the confirmed sink from Task 1:
```js
this.unzipIcon = async e => {
  const t = Buffer.from(e, "base64");
  const r = await svgProcess(t, {shouldGunzip: true});
  return r ? `data:image/svg+xml;base64,${Buffer.from(r).toString("base64")}` : null;
}
```
`this.fetch` is injected from the wallet DI bag as `fetch: (...e) => Object(s.fetch)(...e)`. The
only "assets/tokens"-shaped backend host found anywhere in the bundle is Exodus's own
`fusion.exodus.io/api` (from `network/index.js`); no third-party token-list/CDN host (coingecko,
trustwallet, 1inch, jsdelivr, githubusercontent, etc.) appears anywhere in `ui/index.js`,
`core/index.js`, `network/index.js`, or `wallet/index.js`.

**Conclusion:** the immediate/direct source of `e.icon` for custom tokens is an Exodus-controlled
API response (`fusion.exodus.io`), not a raw attacker URL, the token contract itself, or any
third-party host. From the client app's perspective, no attacker delivers these bytes directly.

The unresolved piece — whether `fusion.exodus.io`'s "tokens" registry itself ingests unvetted icon
data for arbitrary/newly-deployed contracts (a supply-chain path where a token author gets a
malicious SVG into Exodus's own backend) — is server-side and not observable from this repo or
from passive traffic capture. Out of scope for a client-app static/dynamic audit.

### 3. No user-supplied icon field — attacker-controlled: **N/A (doesn't exist)**
Grepped the custom-token-add flow for `logoURI|logo_uri|iconUrl|icon_url`: zero hits. The only
`tokenURI` hits are ERC-721/1155 ABI definitions used for NFTs (already confirmed sandboxed,
`ipc:false`, in `DESKTOP-MAIN-AUDIT.md`) — unrelated to fungible-token icons, and not a route to
this sink.

### 4. WalletConnect / dApp — attacker-controlled: **NO evidence of a path**
16 occurrences of `WalletConnect` in `ui/index.js`; none within ~150–250 chars of any `icon`
reference. dApp peer metadata does not appear to be wired into the icon pipeline.

### 5. `assetPlugins` / `combinedAssetsList` — attacker-controlled: **NO**
`assetPlugins: p.default` is a static bundled webpack module, not runtime/attacker-influenceable.

## Verdict

**refuted (client-side): not attacker-reachable.** The only path that reaches the confirmed
gunzip + SVG-billion-laughs sink is fed exclusively by Exodus's own backend (`fusion.exodus.io`)
responding to a lookup-by-token-name/contract call. There is no code path in this client where a
raw attacker-controlled URL, the token contract itself, a third-party CDN, WalletConnect/dApp
metadata, or a user-supplied field delivers `e.icon` bytes. Lead A's sink (Task 1) is real and
unguarded, but client-side reachability is refuted. The residual question — Exodus backend
token-ingestion hygiene — is server-side and out of scope for this audit; humans to decide whether
to pursue that angle out-of-band.
