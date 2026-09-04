# BRIEFING for the VM Claude instance — Exodus desktop dynamic hunt

You are the **execution/grunt-work agent** on a throwaway VM. Two humans + another Claude are
steering you: do the mechanical work, report results to the repo, and **do not make submission or
severity decisions** — we do that. Read this whole file, then the three referenced docs, then start
at Task 0.

## Context (read these first, in the repo you're in)
- `exodus_h1/DESKTOP-MAIN-AUDIT.md` — main-process audit (app is hardened; isolation on; navigation locked).
- `exodus_h1/DESKTOP-CREATIVE-LEADS.md` — the 3 live leads (A: SVG icon zip-bomb; B: openExternal:unchecked; C: DEBUG_MODE file).
- `exodus_h1/DYNAMIC-TEST-PLAN.md` — the test list.
The extracted app source is at `exodus_h1/desktop_app_src/` (already in the repo — read it directly).

## Hard rules (do not break)
- **Read-only against Exodus's servers.** All testing is against your OWN local install with a
  **fresh wallet holding no real funds**. Create a throwaway wallet.
- **No DoS against Exodus infrastructure.** Bomb/DoS tests run only against your LOCAL app process.
- **Do NOT touch Exchange / XOSWAP / any swap or order.** Fiat-onramp: only inspect deep-link parsing, never complete a purchase.
- Add `h1-treyky` to the User-Agent of any web request you make to an Exodus domain.
- **Do NOT submit anything anywhere. Do NOT open PRs. Do NOT push to any branch except
  `claude/jsonrpc-relay-resilience-yhzj9q`.** Commit results, that's it.
- Only interact with accounts/wallets you create.
- Git commit trailer to use:
  `Co-Authored-By: Claude <noreply@anthropic.com>` and a line `Claude-Session: <this VM session>`.

## Reporting protocol (so the humans + other Claude can steer)
For every task, write findings to `exodus_h1/vm-results/<NN>-<topic>.md` (create the dir), drop any
artifacts (payloads, screenshots, poc.mp4, memory logs) next to it, then:
```
cd ~/Assets && git add exodus_h1/vm-results && git commit -m "vm-results: <topic>" && git push
```
Keep each report short and factual: what you ran, exact output, and a one-line "confirmed / refuted /
inconclusive". Do not editorialize severity.

## Environment setup (once)
```
sudo apt update && sudo apt -y install xvfb x11-utils ffmpeg xdotool curl jq
npm i -g playwright && npx playwright install chromium
# app binary (from the earlier extraction):
ls ~/exodus_app/Exodus-linux-x64/         # expect an 'Exodus' binary
```

## Task 0 — DOES REMOTE DEBUGGING WORK? (decides everything; do this first)
```
export DISPLAY=:99
Xvfb :99 -screen 0 1600x1000x24 &
~/exodus_app/Exodus-linux-x64/Exodus --remote-debugging-port=9222 --no-sandbox &
sleep 8
curl -s http://localhost:9222/json | jq '.[].url'      # list debuggable targets
```
- If you get a JSON list of targets (window URLs) → **CDP is available**. This is the good path:
  you can attach with Playwright (`chromium.connectOverCDP('http://localhost:9222')`), read the DOM,
  run JS in the renderer, call IPC, and screencast. Report which targets/partitions are exposed.
- If it's refused/empty → remote debugging is disabled in the prod build. Report that, then fall back
  to GUI-only driving (xdotool + ffmpeg screenshots). Say so and STOP for us to recalibrate.

## Task 1 — Lead A sink proof (Node, no GUI needed; do regardless of Task 0)
Prove the *sink* behavior numerically with the app's own logic where possible:
1. **Unbounded gunzip:** build a gzip bomb (e.g., 10 MB of 0x00 → a few-KB `.gz`; and a nested/large
   one). Feed it through the same primitive the app uses (native `DecompressionStream('gzip')`), and
   measure peak RSS + output size vs input size. Show the amplification ratio and that there is no cap.
2. **Billion-laughs SVG:** generate an SVG using ONLY tags the trusted validator allows
   (`svg,defs,g,use,path,rect,...`) with nested `<use href="#…">` (double-quoted) that expands
   exponentially. Render it in headless chromium as `data:image/svg+xml;base64,…` inside an `<img>`
   and measure decode time / memory. Confirm whether the allowed-tag set alone yields a render bomb.
Save payloads + a measurements table to `vm-results/01-leadA-sink.md`.

## Task 2 — Lead A reachability (needs the live app)
The open question: can an ATTACKER supply `e.icon` (the base64 gzip SVG)? In the running wallet:
1. Add a **custom token** by contract address (a throwaway/unknown token). Observe how its icon is
   obtained — bundled placeholder? fetched from an Exodus host? fetched from a third-party by
   contract address? Capture the network requests (CDP Network domain, or a proxy) for the icon.
2. If any icon/asset/plugin path pulls SVG bytes from a non-Exodus, attacker-influenceable source,
   that's the reachability we need — document the exact request + who controls it.
Report `vm-results/02-leadA-reachability.md`: confirmed / refuted / inconclusive, with evidence.

## Task 3 — IPC blast radius + reflected-data hunt (only if CDP works, Task 0 good)
Attach via Playwright/CDP to the `ui` target and:
1. In the renderer, confirm `window.exodusPreload?.ipcRenderer` exists. Enumerate what
   `invoke("openExternal:unchecked","file:///etc/hostname")` does (does a handler open? capability check).
   This only proves capability — note it's not attacker-reachable without an XSS.
2. Reflected-data sweep: set unique markers as account name / address-book label / token name / memo,
   then search the live DOM for the marker rendered as an ELEMENT (HTML context) vs escaped text.
   Any HTML-context reflection = XSS lead → capture it precisely.
Report `vm-results/03-ipc-and-reflected.md`.

## Task 4 — deep-link behavior
Host a local page with `exodus://fiatOnramp/x?foo=BAR&probe=<marker>` links; trigger them; watch
(CDP) what the `fiat-onramp:data` handler does with params — any param reaching a DOM sink / href /
URL-open. Do NOT complete any purchase. Report `vm-results/04-deeplink.md`.

## Video (only once something is CONFIRMED)
Record server-side: `ffmpeg -y -f x11grab -framerate 30 -video_size 1600x1000 -i :99 poc.mp4`,
drive the repro (CDP or xdotool), Ctrl-C, save `poc.mp4` into the matching `vm-results/` folder.

## Stop conditions — hand back to the humans when:
- Task 0 shows CDP disabled (recalibrate).
- Any lead is confirmed OR refuted (we decide next move / severity / whether to write a report).
- You're unsure whether an action is in-scope. When in doubt, stop and ask via a `vm-results/QUESTION-*.md`.
