# VM BRIEF — reflected-XSS hunt in the ui renderer via `--debug` DevTools (Critical upside)

## Confirmed enabler (from source)
`Exodus --debug` sets `globalThis.DEBUG_MODE=true` (main/index.js:5164). The ui window's
`did-finish-load` then calls the devtools opener for `windowId:"ui"` (main/index.js:236-237), which
forces `openDevTools({mode:"detach"})` (main/index.js:499). `--debug` is on the CLI-arg whitelist, so
the app does NOT self-exit. Net: a full DevTools console auto-opens on the main wallet renderer.

## Why we're doing this (the prize)
The ui renderer exposes the RAW ipc bridge (`window.exodusPreload.ipcRenderer.invoke`) and is highly
privileged (holds wallet state; can reach every IPC handler incl. `openExternal:unchecked`). React
auto-escapes text, and static analysis found no obvious HTML sink — BUT static on 15 MB of minified
React is unreliable. If ANY attacker-influenceable string reaches a DOM HTML sink (or a
`javascript:`/`data:` URL sink), that's **XSS → IPC bridge → RCE = Critical**. This session hunts that
dynamically. This is the only remaining Exodus lead with Critical upside.

## Scope/rules
Fresh wallet, no real funds, local install only. `--debug` is your own local flag (fine). Only your
own accounts/data. Do NOT touch Exchange/XOSWAP. No network attacks. If you find XSS, capture proof
and STOP; do not pivot to real user harm. Commit to `exodus_h1/vm-results/07-xss-hunt.md`.

## Launch (GUI needed — DevTools is a window you read/drive over VNC)
```
export DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 & 
x11vnc -display :99 -rfbport 5900 -localhost -nopw &     # SSH-tunnel 5900 to view/drive
~/exodus_app/Exodus-linux-x64/Exodus --debug --disable-gpu --datadir=$HOME/exo-xss-scratch &
# create a throwaway wallet in the GUI. Confirm a detached DevTools window opened on the ui view.
```

## Step 1 — plant unique markers in every attacker-influenceable field
Use a distinctive marker per field so you can find it in the DOM, e.g. `ZZQA1`, `ZZQA2`, …
Candidate fields (attacker- or semi-attacker-controlled strings that render in the ui):
- **Custom token name / symbol** (add a custom token; name it `ZZQA1<b>x</b>`).
- **Wallet/account name / portfolio name** (rename an account to `ZZQA2<img src=x>`).
- **Address-book / contact label** (if present).
- **Personal note / transaction memo/label** (the `personal-notes` feature — `ZZQA3<svg/onload=1>`).
- **Receive/send address label, amount memo, dApp/WalletConnect session name** (if reachable).
- **Fiat-onramp deep link params** (`exodus://fiatOnramp/x?probe=ZZQA4<img src=x onerror=1>`).

## Step 2 — in the DevTools console, check HTML-context reflection
For each marker, run in the ui console:
```js
// does the marker render as an ELEMENT (HTML) vs escaped text?
[...document.querySelectorAll('*')].filter(n => n.outerHTML.includes('ZZQA1')).map(n => n.outerHTML).slice(0,5)
// quick sink check: did our injected tag actually become a node?
document.querySelector('img[src="x"], svg, b') // etc — did the tag materialize?
```
- If the marker appears only as **text content** (escaped `&lt;b&gt;`) → safe, move on.
- If our injected **tag became a real DOM node** → HTML injection → likely XSS. Flag the field + the
  component/DOM path.

## Step 3 — if HTML injection found, confirm script execution → RCE chain
Escalate that one field to an executing payload (only in your own wallet):
```
ZZQA<img src=x onerror="window.__xss=1">
```
Check `window.__xss` in the console. If it runs, demonstrate the full chain (RCE-class):
```
<img src=x onerror="window.exodusPreload.ipcRenderer.invoke('openExternal:unchecked','file:///etc/hostname')">
```
If that opens the file/handler, you have XSS → IPC → arbitrary `shell.openExternal` (and the bridge
can reach other handlers). Capture screenshots/video. STOP and report — do not weaponize further.

## Step 4 — also try the sink directly (URL sinks)
Look for anywhere the app renders a clickable link from user/asset data (token website, explorer
link, dApp url). In the console, find anchors with attacker-influenced hrefs:
```js
[...document.querySelectorAll('a[href]')].map(a=>a.href).filter(h=>/^(javascript|data|file):/i.test(h))
```
Any `javascript:`/`data:`/`file:` href built from attacker data is a finding.

## Output
`07-xss-hunt.md`: for each field — marker, escaped-vs-HTML result, and (if HTML) the component + the
escalation result. If everything is escaped (React doing its job), say so plainly — that closes the
XSS lead and we're done with Exodus. If ANYTHING executes, that's the Critical we were after: stop,
screenshot, and flag for the humans to write up carefully.
