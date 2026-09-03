# Exodus Desktop Wallet — vulnerability hunting playbook

Goal: find an in-scope **Medium/High** bug in the Exodus **Desktop Wallet**
(Electron) with a **video PoC** (mandatory per program). Class focus:
deep-link / protocol-handler abuse, IPC exposure, webview/navigation, and
"deep-link → sensitive action" logic bugs.

## Scope & rules (read first)
- **In scope:** Exodus Desktop Wallet application; Exodus websites/subdomains.
- **Add `h1-<your-h1-username>` to the User-Agent** for any web traffic to Exodus.
- **Only your own wallet/accounts.** Create a FRESH wallet with little/no funds.
- **Do NOT:** DoS, touch Exodus Exchange / XOSWAP (any order/swap), the contact
  form, or create support tickets. No MITM/physical-access-based attacks. No
  social engineering.
- **Avoid** address-bar spoofing (program says it's known & unpaid).
- Reverse-engineering YOUR OWN installed copy and testing deep links/IPC against
  your OWN local instance is authorized conduct under the program's Safe Harbor.

---

## Sequencing (minimize cost before we have a target)

**Step A — get the code to me (tiny box, no GUI needed).**
The whole app logic ships as bundled JS in `app.asar`. Extracting it needs almost
no resources — do it on the smallest VPS (or even locally, since we're not running
the GUI yet). Push the JS to our repo; I audit it statically (my strength).

**Step B — I hunt statically**, produce a ranked candidate list + exact repro idea.

**Step C — only THEN** stand up the heavier "streaming" VM to run the real app and
record the video PoC for the confirmed bug. Don't pay for the GUI/stream box until
we know what we're filming.

---

## Step A — download + extract `app.asar`

On a Linux box (Ubuntu 22.04/24.04). Get the Linux build from the official
download page only:

```bash
# 1) Download the Linux .zip from https://www.exodus.com/download
#    (use a browser, or curl WITH your h1 UA):
curl -A "h1-<your-username> exodus-research" -L -o exodus.zip "<linux-zip-url-from-download-page>"

# 2) Unzip; the Electron app is inside. Find the asar:
unzip -q exodus.zip -d exodus_app
find exodus_app -name "app.asar" -o -name "*.asar"     # usually resources/app.asar

# 3) Extract the bundled JS:
npx --yes @electron/asar extract exodus_app/**/resources/app.asar app_src
#    (fallback: npx --yes asar extract <path>/app.asar app_src)

# 4) Also grab the unpacked native bits list + electron version:
cat app_src/package.json | grep -E '"version"|electron'
ls app_src
```

**Then push the JS to me** (skip node_modules if huge; I most want the
**main-process** code, preload scripts, and any `exodus://`/ipc/webview logic):

```bash
# from the repo working copy:
mkdir -p exodus_h1/desktop_app_src
cp -r app_src/*.js app_src/main* app_src/preload* app_src/build* exodus_h1/desktop_app_src/ 2>/dev/null
# (or just: cp -r app_src exodus_h1/desktop_app_src, minus node_modules)
git add exodus_h1/desktop_app_src && git commit -m "desktop app.asar extracted JS for audit" && git push
```

If it's minified into a few big bundles, push them anyway — I'll read them.

---

## Step B — static-analysis target list (what I grep/read)

Ranked by impact for a remotely-triggerable desktop bug:

1. **Protocol / deep-link handler**
   - `setAsDefaultProtocolClient`, `app.on('open-url')`, `app.on('second-instance')`,
     `process.argv` parsing, any `exodus:` / custom-scheme string handling.
   - Trace: URI → parser → **what action it triggers** (navigation? send-tx
     prefill? WalletConnect pair? IPC call?). This is the #1 vein.
2. **IPC surface**
   - `ipcMain.handle(`, `ipcMain.on(`, preload `contextBridge.exposeInMainWorld`,
     and window opts: `nodeIntegration`, `contextIsolation`, `sandbox`,
     `webSecurity`, `allowRunningInsecureContent`. A privileged IPC method reachable
     from a context that can load untrusted content = High.
3. **Navigation / external content**
   - `<webview`, `webContents`, `will-navigate`, `setWindowOpenHandler`,
     `'new-window'`, `loadURL`, and especially **`shell.openExternal(`** with any
     attacker-influenced argument (arbitrary scheme/file → code-exec/SSRF class).
4. **Content-Security-Policy** in the renderer HTML / session headers; any `unsafe-eval`,
   missing CSP, or `webview`/iframe loading remote origins.
5. **Update / signature** paths (`autoUpdater`, signature checks) — high bar, but high reward.

I'll produce, per candidate: the code path, the trust boundary, the attack
scenario (a web page the victim visits, or a link they click), severity, and the
exact repro to film.

---

## Candidate bug theses to validate (Medium/High, video-able)

- **T1 — Deep-link transaction/again pre-fill (phishing-with-one-click):** an
  `exodus://…` link that opens the Send screen pre-populated with an
  attacker-controlled address/amount/asset. If a single confirm sends funds, that's
  a strong Medium (interaction-based fund theft). Verify what fields the URI controls.
- **T2 — `shell.openExternal` with attacker-controlled URL/scheme** reached from a
  deep link or dApp message → open `file://`/`smb://`/other handlers → local file
  or secondary-handler abuse. Medium/High.
- **T3 — Privileged IPC reachable from untrusted content** (a webview/dApp browser
  with a broad preload bridge) → read seed/keys, trigger sign, or main-process
  capability. High if reachable.
- **T4 — Navigation of a *trusted* window/webview to attacker content** (not mere
  address-bar spoof) such that attacker HTML runs with the trusted context's
  privileges/CSP. High.
- **T5 — WalletConnect/dApp pairing auto-approval** via deep link. Medium.

---

## Step C — VM for the video PoC (only after we pick a bug)

Spec: Ubuntu 22.04/24.04, **2 vCPU / 4 GB** (enough to run the Exodus GUI +
lightweight desktop). Add XFCE + a display:

```bash
sudo apt update && sudo apt install -y xfce4 xfce4-goodies xvfb x11vnc tigervnc-standalone-server ffmpeg
# install Exodus from the .deb, or run the unpacked binary
```

### Smooth video = record ON the server, don't film the stream
The trick to a non-laggy PoC: **capture the video locally on the VPS with ffmpeg**,
then download the finished .mp4. Your remote-desktop connection only *drives* the
demo — the recording is pristine regardless of your bandwidth.

```bash
# start a virtual display (or use the real X)
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
# (start XFCE + Exodus on :99, drive it via VNC)
x11vnc -display :99 -rfbport 5900 -localhost -nopw &   # tunnel over SSH: ssh -L 5900:localhost:5900

# RECORD the display straight to a smooth file:
ffmpeg -y -f x11grab -framerate 30 -video_size 1920x1080 -i :99 \
       -c:v libx264 -preset veryfast -pix_fmt yuv420p poc.mp4
# ...perform the exploit in the VNC session..., then Ctrl-C, then scp poc.mp4 down.
```

- Drive it with **TigerVNC/x11vnc over an SSH tunnel** (simple) or **RustDesk**
  (easier NAT). For interactive low-latency, **Sunshine (host) + Moonlight (client)**.
- But for the deliverable, the **server-side ffmpeg recording is what you submit** —
  it never stutters because it isn't going over the network while recording.

### Video content (what the PoC must show)
1. A clean Exodus install + fresh wallet (show it's default, unmodified).
2. The attack trigger (victim clicks a link / visits your page / opens a URI).
3. The impact (funds send screen pre-filled and sent to attacker / key exposed /
   command executed) — clearly, on screen.
4. Keep it < ~2 min, no cuts through the critical step.

---

## Deliverable back to HackerOne
Per confirmed bug: the report (capstone-style, like REPORT-1/2) + the `poc.mp4` +
the trigger artifact (the HTML page / URI). One report per underlying issue.
