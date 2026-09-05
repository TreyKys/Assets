# RECALIBRATION — Task 2 (reachability) is now the whole ballgame

Task 0 verdict: **CDP is hard-disabled** by the main-process CLI-arg kill-switch (any argv key not in
`_,datadir,debug,disable-gpu,p` → `app.exit()`). So `--remote-debugging-port` AND `--proxy-server`
both kill the app. Programmatic renderer inspection (Tasks 3) is OFF. Task 1 sink is CONFIRMED.

**The only question that matters now:** can an ATTACKER deliver the bytes into `e.icon` /
`svgProcess({shouldGunzip:true})` / `unzipIcon()` — i.e. is the confirmed bomb sink attacker-reachable?
If yes → we have a real (Medium, client-side DoS) bug with a ready PoC. If no → Lead A is a
latent-hardening note only. Decide this, then STOP.

## Approach 1 — STATIC trace (do this FIRST; fastest, no GUI)
You have the full source at `exodus_h1/desktop_app_src/`. Trace where `e.icon` (base64 gzip SVG) and
`unzipIcon(...)` inputs ORIGINATE, distinguishing:
- **built-in / registry assets** — icons shipped by Exodus (`*.a.exodus.io`, bundled). NOT attacker-controlled.
- **custom tokens** (user adds by contract address) — does the icon come from a third-party
  (token-list, per-contract URL, on-chain tokenURI, coingecko/trustwallet), i.e. attacker-influenceable?
- **any dApp / WalletConnect / deep-link / asset-plugin** path that can set an icon.

Grep leads: `unzipIcon`, `svgWrite`, `setIcon`, `\.icon\b`, `iconUrl|logoURI|logo_uri`, `customToken`,
`addCustomToken`, `tokenURI`, `assetlist|token-?list`, and how the ui `AssetIcons` `f`/`h` setters are
called. Report the exact origin of the bytes for each icon path in
`vm-results/02-leadA-reachability.md`: for each path say **attacker-controlled: yes/no/maybe** with the
source line. This may fully answer reachability without the GUI.

## Approach 2 — DYNAMIC host/SNI confirmation (only if static is inconclusive)
We can't MITM easily (proxy flag is killed; Exodus likely pins its own hosts). But we don't need to
decrypt — we only need to see WHICH HOST the icon is fetched from.
1. Launch GUI with whitelisted args only: `Exodus --disable-gpu --datadir=<scratch>` under Xvfb.
2. Start a passive capture of TLS SNI + DNS:
   `tcpdump -n -i any -s0 'tcp port 443 or udp port 53' -w cap.pcap` (or `tshark -Y 'tls.handshake.extensions_server_name' -T fields -e tls.handshake.extensions_server_name`).
3. Drive the GUI with xdotool: create a throwaway wallet, then **add a custom token** (use a couple of
   real but obscure ERC-20 contract addresses on Ethereum, and one random/garbage address). Screenshot
   each step (ffmpeg/x11grab) so we can see whether a real icon or a placeholder renders.
4. From the capture, list the hostnames contacted during the add-token flow. If an icon is fetched from
   a **non-Exodus host** → attacker-reachability is plausible (a token author controlling that icon
   source could deliver the bomb). If everything is `*.exodus.io`/`*.a.exodus.io` and unknown tokens
   get a placeholder → not attacker-reachable via this path.
Record hosts + screenshots in `vm-results/02-leadA-reachability.md`.

## Scope reminders (unchanged)
Fresh wallet, no funds. No Exchange/XOSWAP. `h1-treyky` UA on any Exodus web request. Local-only.
Do NOT submit anything. Commit results to this branch. STOP after the reachability verdict — do not
start writing a HackerOne report (the humans decide severity/submission).

## If reachable → what we'll need for the video (don't do yet, just so you know)
A malicious-token icon (gzip'd `<use>` billion-laughs SVG, ≤ any icon size cap), the victim adding/
viewing that token, and the wallet hanging/OOMing — captured via server-side ffmpeg. We already have
the payload generators (`task1_svg_bomb_gen.mjs`, `task1_gzip_bomb.mjs`).
