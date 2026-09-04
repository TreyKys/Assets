# Exodus Desktop — dynamic test plan (VM phase)

Static audit (`DESKTOP-MAIN-AUDIT.md`) found the app well-hardened + one hardening gap
(`openExternal:unchecked` has no scheme validation). Confirming any real Medium/High now needs
running the app. Do these in the VM with a fresh, ~empty wallet. Add `h1-treyky` to any web UA.
Record with server-side `ffmpeg` (see playbook) so the video is smooth.

## Rules (do not skip)
- Fresh wallet, little/no funds. Only your own accounts.
- No DoS. Do NOT touch Exchange / XOSWAP / any swap or order. Fiat-onramp is scope-adjacent —
  test only the *deep-link parsing/DOM behavior*, never complete a purchase.
- These are the tests most likely to reveal a submittable bug, ordered by value.

## Test 1 — `openExternal:unchecked` scheme validation (the static lead)
Goal: prove a non-`https` / dangerous scheme reaches `shell.openExternal` from the renderer.
1. If devtools is reachable (try the app's dev menu / `Ctrl+Shift+I`), in the `ui` window console run:
   `window.exodusPreload.ipcRenderer.invoke("openExternal:unchecked","file:///etc/passwd")`
   - If a file/handler opens → the handler does no scheme check (capability confirmed).
   - This alone is only "capability", not attacker-reachable — but it proves the missing validation.
2. Attacker-reachable version: find a UI element that opens an *attacker-controlled* URL:
   - add a **custom token** whose "website"/project URL is `file:///…` or `smb://…` or (Win) `ms-msdt:…`;
   - or a **WalletConnect/dApp** connection whose peer `url` is a dangerous scheme;
   then click the "visit website / open" affordance and see if it opens **without** validation.
   A malicious-metadata URL → dangerous-scheme open on one click is a legit Medium.

## Test 2 — fiat-onramp deep link parameter handling (remote trigger)
`exodus://fiatOnramp/<path>?<params>` is the only accepted deep link; it forwards
`{host,path,params}` to the renderer `fiat-onramp:data` handler.
1. Host a page with `<a href="exodus://fiatOnramp/x?foo=BAR&url=https://evil">click</a>` (and try
   `location.href=` auto-trigger). Click it; the OS routes it to Exodus.
2. In devtools, watch what the fiat-onramp UI does with `params`: does any param get rendered into
   the DOM as HTML, used as an `href`/`src`, or passed to a URL open? A param reaching a sink =
   remote one-click bug. (Stop before initiating any actual purchase.)

## Test 3 — WalletConnect / dApp metadata rendering (untrusted → DOM)
1. Stand up a malicious dApp (or a WC pairing) whose peer metadata `name`/`description`/`url`/`icons`
   contain HTML/`javascript:`/`<img onerror>`.
2. Trigger the connection prompt in Exodus and inspect whether name/description/url render as HTML
   (XSS) or the `url` is opened via the unchecked opener. This is the highest-value chain: XSS in the
   `ui` renderer → `window.exodusPreload.ipcRenderer.invoke(...)` → RCE-class.

## Test 4 — reflected-data sweep (if devtools available)
With a unique marker string, set it as: token name/symbol, address-book label, ENS name, tx memo,
account name. Then in devtools run `document.body.innerHTML.includes("<marker as HTML>")` checks /
search the DOM for the marker rendered as an element rather than text. Any HTML-context reflection
of attacker data = XSS lead.

## If a test lands
Capture the full chain on video (fresh install → attacker artifact → impact), save the trigger
artifact (HTML page / URI / token contract), and I'll write it up in the capstone report format.

## If nothing lands
Then the honest outcome is: desktop app is hardened; the submittable material is the
`openExternal:unchecked` missing-validation as a **Medium hardening/logic bug** (if Test 1.2 or a
metadata-URL path confirms a dangerous-scheme open), plus the two library DoS findings. We report
what we can actually demonstrate — no inflation.
