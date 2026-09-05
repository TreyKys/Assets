# Task 0 — does remote debugging (CDP) work?

**App under test:** Exodus desktop v26.8.27, Electron/Chromium 41.0.3, Linux x64 build, extracted to
`~/exodus_app/Exodus-linux-x64/`.

## What I ran

```
export DISPLAY=:99
Xvfb :99 -screen 0 1600x1000x24 &
~/exodus_app/Exodus-linux-x64/Exodus --remote-debugging-port=9222 --no-sandbox
sleep 8
curl -s http://localhost:9222/json | jq '.[].url'
```

## Exact output

Process log (`00-exodus-app-cdp-attempt.log`):
```
ENV: production
LaunchProcess: failed to execvp:
xdg-settings
wallet-controller initialized, process.type = browser, timestamp: 1788595959420
Can only pass whitelisted args; exiting {"_":["/home/hunter/exodus_app/Exodus-linux-x64/Exodus"],"remote-debugging-port":9222,"sandbox":false}
```

`curl -s http://localhost:9222/json` → empty (connection refused / nothing listening). `ps aux |
grep -i exodus` → no process (it already exited).

## Root cause (found in source)

`exodus_h1/desktop_app_src/src/app/main/index.js`, main-process startup IIFE:

```js
if (a.ENV_TEST) console.log("TEST MODE");
else {
  const e = ["_", "datadir", "debug", "disable-gpu", "p"];   // CLI arg whitelist
  (!Object.keys(g).every(t => e.includes(t)) || g._.length > 2) &&
    (console.error("Can only pass whitelisted args; exiting", JSON.stringify(g)), o.app.exit());
}
```

`g` is the parsed `process.argv` (minimist-style). **Any** CLI flag whose key is not in
`["_", "datadir", "debug", "disable-gpu", "p"]` makes the app print the message above and call
`app.exit()` immediately — this is not "remote debugging silently ignored", it's a hard kill-switch
on unrecognized flags. `--remote-debugging-port` and `--no-sandbox` (→ minimist key `sandbox`) both
trip it. This is a stronger control than plain "devtools disabled" and is worth folding into
`DESKTOP-MAIN-AUDIT.md`'s hardening list — it forecloses the whole class of "launch with extra
Chromium switches" tricks (`--remote-debugging-port`, `--inspect`, `--enable-logging`, etc.), not
just remote debugging specifically.

## GUI-only fallback — confirmed working

Re-launched with only whitelisted args:
```
Exodus --disable-gpu --datadir=<scratch>/exodus-userdata
```
Process stayed up (main window + zygote/network-service/renderer children all present in `ps aux`),
loaded fully (`did-finish-load`, `SET WALLET LOADED action: undefined` / `true` in
`00-exodus-app-guionly.log`), and a `ffmpeg -f x11grab` screenshot of `:99`
(`00-guionly-screenshot.png`) shows the fully-rendered onboarding screen ("Start Your Journey" / Buy
Crypto / Import Wallet / live BTC price ticker). So `xdotool` + `ffmpeg` GUI-driving is viable for
the remaining tasks.

## Verdict

**Refused — CDP is not available.** Not because the switch is filtered by Chromium, but because the
app's own main-process code treats any non-whitelisted argv key as fatal and self-exits before the
Chromium debug listener would matter. GUI-only fallback (xdotool + ffmpeg) is confirmed functional.

**confirmed: CDP disabled via CLI-arg whitelist kill-switch; GUI-only fallback works.**

Per the brief, stopping here for recalibration before Tasks 2–4 (Task 1 does not depend on this and
is done separately in `01-leadA-sink.md`).
