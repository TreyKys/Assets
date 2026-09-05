# Exodus Desktop v26.8.27 — main-process static audit

Source: extracted `app.asar` → `src/app/main/index.js` (beautified), `src/app/preload/index.js`,
window registry, IPC handlers. Renderer bundle `src/app/ui/index.js` is 15 MB minified React.

## Verdict: the app is well-hardened. One hardening gap found; no *confirmed* attacker-reachable High yet.

## What's locked down (no bug)

- **Window isolation** (base `isolation` config): `sandbox:true`, `contextIsolation:true`,
  `nodeIntegration:false`, `nodeIntegrationInWorker:false`, `webSecurity:true`. Classic
  nodeIntegration RCE is closed.
- **Navigation fully locked**: every `web-contents-created` gets a `will-navigate` guard that
  `preventDefault()`s anything except `mailto:`; the `ui` window repeats this. `setWindowOpenHandler`
  denies all new windows (except devtools→devtools). `will-attach-webview` → `preventDefault()`
  (webviews entirely blocked). ⇒ an attacker cannot navigate/inject a window to their content.
- **`openExternal` (checked handler)**: strict allowlist in `validate()` — only
  `support.exodus.(io|com)`, `www.exodus.com/support`, `etherscan|polygonscan /tx/0x…`, one youtube
  link, and `mailto:support@exodus…` with only subject/body. Rejects if `url.href !== input`.
- **CLI-arg kill-switch** (VM-verified): the main process exits immediately on ANY argv key not in
  `["_","datadir","debug","disable-gpu","p"]`. This forecloses launching with extra Chromium
  switches (`--remote-debugging-port`, `--inspect`, `--no-sandbox`, `--proxy-server`, `--enable-logging`),
  so CDP/remote-debugging cannot be enabled and programmatic renderer inspection is blocked.
- **Deep links** (`exodus://`): `isDeepLink` only matches `^exodus://fiat(Onramp|Offramp)`; handler
  forwards `{host,path,params}` to the UI `fiat-onramp:data` channel and shows the window. No
  transaction send / arbitrary action directly from the URL.
- **NFT window sandboxed**: `nfts` window registry has `ipc:false` and only
  `clipboard-sanitized-write` — NFT/remote metadata cannot reach any IPC handler. This closes the
  most obvious "malicious NFT metadata → privileged IPC" path.
- **Renderer HTML sinks**: 3 `dangerouslySetInnerHTML` are all static (CSS/react internals); the
  `innerHTML` hits are library internals (resize-detector, countup numeric output, d3 `.html()`);
  no DOMPurify because no untrusted HTML is injected via these. React auto-escaping covers text.

## The one soft spot (hardening gap; not yet a confirmed exploit)

`rpcMain.handle("openExternal:unchecked", …)` **bypasses `validate()`** entirely — it only checks
that the calling webContents has the `openExternal` permission (the `ui` window does). The renderer
exposes a generic helper:

```js
// ui bundle
function a(e){ return rpcRenderer.invoke("openExternal:unchecked", e) }   // e = ANY url
```

So `shell.openExternal(<url>)` runs with **no scheme validation** on whatever URL the renderer passes.
The preload also exposes the **raw** ipc bridge (`window.exodusPreload.ipcRenderer.invoke`), so *any*
JS running in the `ui` renderer can call it directly with `file://`, `smb://`, or an OS-specific
dangerous scheme.

**Why it's not yet a bug I can submit:** it's only attacker-reachable if
(a) attacker-controlled URL data reaches that helper, or (b) there's a renderer XSS to run the
`invoke` directly. The `ui` window loads a local `file://` and navigation is locked, so (b) needs an
XSS in Exodus's own React bundle, which I did **not** find statically (React escapes; NFT content is
sandboxed). (a) needs a metadata/URL field (token website, WalletConnect dApp url, address-book/ENS
link, fiat-onramp param) flowing to the helper — plausible but not confirmable in 15 MB of minified
React from the CLI.

## IPC blast radius (for reference — reachable from the `ui` renderer)

`openExternal`, `openExternal:unchecked`, `dialog:open`, `app:showPopupMenu` (renderer supplies a
native-menu template), `get-machine-id`, `has-media-access`, `nfts:*`, `wallet:qrCodeScan`,
`keyviewer-process:*`, `window:focus`, `ui:set-navbar-height`.

## Conclusion & next step

Static analysis of the main process is essentially complete: the app is solidly built. The realistic
paths to a Medium/High now require **dynamic testing** in the VM (load malicious tokens/NFTs, initiate
a WalletConnect/dApp connection, fire `exodus://fiatOnramp?…` deep links, and watch whether any
attacker-controlled string reaches a DOM sink or the `openExternal:unchecked` helper). That is also
where the mandatory video PoC gets captured. See `DYNAMIC-TEST-PLAN.md`.
