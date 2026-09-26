# VM BRIEF — KU Leuven Admissions — Track H: the client-side / DOM attack surface

**The strategic pivot.** Every server-side authorization path is hardened: direct CRUD, batch
dispatch, FunctionImports, LongTexts, singleton/composite keys, identity confusion, payment
verifier, binary upload — all clean-negative, validly tested. Hammering the OData backend further
is diminishing returns. **So we stop attacking the server and attack the client.**

The `zc_ad_appl` app is a large SAPUI5 (JavaScript) application that runs in the *user's* browser.
Client-side bugs — DOM XSS, open redirect, postMessage abuse, prototype pollution, a vulnerable
framework version — **do not need the server's authorization to cooperate.** The server can be a
fortress and the client can still hand an attacker script execution in a victim's authenticated
session via a crafted link. This is a different bug class with its own severity ceiling, and we
have never systematically hunted it.

**Two practical advantages that make this the right move now:**
1. **No ACL risk.** This is static analysis of the bundle (GET-only, already-authorized assets)
   plus live DOM testing in the researcher's *own browser* — normal page loads, one at a time,
   indistinguishable from real use. The SAP Web Dispatcher ACL that has fought us all campaign
   is irrelevant here.
2. **Cross-user by construction.** A DOM XSS reached via a deep-link is triggered when a victim
   opens the attacker's URL while logged in — that's cross-user without needing OLBUSER routing or
   any server-side delivery mechanism. It's the render context we kept failing to reach on the
   server side, available for free on the client.

## Scope

- IN SCOPE (unambiguous): everything under
  `https://webwsp.aps.kuleuven.be/sap/bc/ui5_ui5/sap/zc_ad_appl/*` — the app bundle, its views,
  controllers, fragments, and the SAPUI5 framework it loads. This is the whole surface of Track H.
- **NOT covered by this brief:** `zc_ad_appl_chat` (sibling directory — pending explicit written
  scope confirmation from the program; if/when confirmed, it gets its own brief). Do not fetch or
  test it under this brief.
- Static bundle reads and framework-asset fetches only for the VM half. Live deep-link testing is
  the researcher's own browser against their own session (A/B), no automation.

## Methodology split

- **VM half (static):** parse the already-extracted `03-bundle/` tree + fetch the SAPUI5
  framework version assets. Produce a ranked list of concrete deep-link / DOM-sink candidates with
  exact file:line and a ready-to-paste test URL for each.
- **Researcher half (live):** paste each candidate deep-link into the browser against your own
  logged-in session, watch for execution. This is where a candidate becomes a confirmed finding.
  The VM cannot do this half (it can't drive an authenticated browser DOM safely); its job is to
  hand you a short list of high-confidence URLs so your live testing is minutes, not hours.

---

## SURFACE 1 — SAPUI5 framework version fingerprint + known-CVE match (attack the framework)

"Take SAP out of the equation" done legitimately: the app loads a specific SAPUI5 version, and
SAPUI5 controls have had real DOM-XSS CVEs (`sap.m.FormattedText`, `sap.ui.core.HTML`,
`sap.ui.richtexteditor.RichTextEditor`, URL-validation bypasses in `sap.m.Link`, etc.). If the
deployed version is old and the app uses an affected control, the app is running vulnerable
framework code regardless of how well the *app's own* code is written.

1. Fetch `sap-ui-core.js` / `sap-ui-version.json` from the bootstrap path the bundle references
   (look in `index.html` / `Component.js` for the UI5 resource root). Extract the exact version
   (e.g. `1.71.x`, `1.84.x`, `1.108.x`).
2. Cross-reference that version against public SAPUI5 security advisories / CVEs for DOM-XSS or
   URL-validation issues in the controls the app actually instantiates (from Track D's view
   inventory: `FormattedText`, `Link`, `Image`, `MessageStrip`, `HTML` if present).
3. Output: version + a table of applicable CVEs + which app view/control would be the delivery
   point. Each applicable CVE is a candidate the researcher can validate live.

**This is the single highest-EV probe** — a framework CVE affecting a control the app uses is a
concrete, defensible finding that the app team can't "we validate server-side" their way out of.

---

## SURFACE 2 — router/hash param → DOM sink flow (the SPA DOM-XSS core)

The app is hash-routed (`index.html#/applicationDetail/<params>`). Route params are fully
attacker-controlled (victim clicks a crafted link). Track D did a first-pass router map and found
no *direct* unescaped sink, but DOM XSS usually hides in **transitive** flows: param → model
property → formatter → binding → sink. First reads miss these.

For EVERY route in `manifest.json → routing.routes`, trace each param through the controller's
`onInit`/`_onRouteMatched` handler to its final resting place, following it through model writes
and formatter calls, not just direct uses:

- Does any param reach `setHtmlText` / an `htmlText` binding / a `sap.ui.core.HTML` content?
- Does any param reach `window.open(...)`, `location.href =`, `location.replace(...)`,
  `URLHelper.redirect(...)`? (open redirect, or `javascript:`/`data:` scheme XSS)
- Does any param reach a `sap.m.Link` `href` binding? (SAPUI5 Link does NOT strip `javascript:`
  unless `sanitizeContent`/URL-validation is on — check per instance)
- Does any param reach `Image.src` / `src` binding? (`javascript:`/`data:` in some contexts)
- Does any param reach `sap.ui.require([...])` or a component/view name used to load a module?
  (dynamic-load → arbitrary module fetch)

Pay special attention to the params Track D flagged as "captured but unused" on the paymentDone
route (`amount`, `currency`, `date`, `description`) — "unused by the controller" doesn't mean
"unbound by the view." Re-check every view XML for a binding to a route-model path carrying those.

Output: table of `route × param × transitive path × sink × escaped?`, and for every unescaped or
scheme-injectable sink, a **ready-to-paste test URL** with an inert marker payload.

---

## SURFACE 3 — postMessage handlers + the payment-return flow (high EV)

The fee-payment flow leaves the app (`window.location.replace(appFeePayURL)`) and the payment
provider returns to the app. Return integrations frequently use `postMessage`, and postMessage
handlers that don't validate `event.origin` are a classic cross-origin → DOM XSS / state-spoof
vector.

1. Grep the entire bundle for `addEventListener("message"`, `onmessage`, `window.attachEvent`,
   and any `postMessage` usage.
2. For each handler found:
   - Does it check `event.origin` against an allowlist? If not → any page can message it.
   - What does it do with `event.data`? Render it (sink)? Act on it (set app state)? Navigate?
3. **The payment-state spoof chain (creative core):** the client sets local
   `isAppFeePayed=true` around the payment return. If a `message` handler (or the redirect-param
   parser) flips a local "paid" flag *before/without* the server's `isPaymentDone` confirming,
   AND any subsequent server-affecting action (submit, admission-letter fetch) trusts that local
   flag rather than re-checking server-side — that's a client-trust logic bug the server sweeps
   could not see. Trace `isAppFeePayed` / `_fromPayment` end to end: who sets it, who reads it,
   does any write depend on it.

Output: every message handler with its origin-check status and data-flow; the full
`isAppFeePayed` client-trust trace with a verdict on whether a spoofed return can reach a
server-affecting action.

---

## SURFACE 4 — a SECOND path to the HTML sinks (the one we assumed closed)

Sweep 9 found the 14 `htmlText`/`setHtmlText` sinks all bind to `teksten>` (LongTexts), and
LongTexts is server-write-locked (501). We concluded the XSS chain is closed. But that only closes
the *LongTexts* feed. The question we never asked: **is there any OTHER source that reaches those
same sinks?**

- Grep every `setHtmlText(` call and every `htmlText=` binding. For each, identify the *model
  path* it reads. Is any of them bound to a model OTHER than `teksten>` — one that's client-
  writable (a value the user types, a URL param, a client-computed formatter output, a value from
  `localStorage`)?
- Check `model/Formatter.js` functions used in any `htmlText` binding: does a formatter ever
  concatenate a user/param value into the HTML string it returns? A formatter that builds
  `"<b>" + someValue + "</b>"` from a client-controlled `someValue` is a sink even if the base
  binding looks safe.
- Check `HtmlMenu` (Track C flagged S9-M1: renders `menuItem.getProperty("text")` as innerHTML).
  What feeds the menu item text? If any menu item text is client-influenced → innerHTML XSS.

Output: every HTML sink with its *complete* set of feeding sources, flagging any non-LongTexts,
client-controllable feed.

---

## SURFACE 5 — client-side open redirect + scheme injection

- Enumerate every `window.open`, `location.href/assign/replace`, `URLHelper.redirect`. For each,
  is the URL argument ever derived from a route param, a query param, `document.referrer`,
  `postMessage` data, or `localStorage`? If a client-controllable value reaches a navigation sink
  → open redirect (Medium; phishing pretext) or, if `javascript:`/`data:` schemes aren't
  filtered, DOM XSS.
- `appFeePayURL` is server-supplied, but re-check: is there ANY client path that lets a param or
  client value override it before the `replace`?

Output: navigation-sink table with source + scheme-filtering status.

---

## SURFACE 6 — dynamic module / component load abuse

Track C found the app builds cross-app navigations like `zc_oi_appl_<x>` where `<x>` comes from a
server field `rubrieklink`, and registers UI5 loader paths. Dynamic loading driven by data is a
sink if the data is influenceable:

- Trace `rubrieklink` from its OData source to the navigation. Is `<x>` ever influenced by a
  client-writable field or a route param? (We proved most writes are locked, but a create-on-
  demand field or a reflected param might reach it.)
- Grep for `sap.ui.require([var])`, `Component.create({name: var})`, `loadLibrary(var)`,
  `jQuery.sap.registerModulePath(var, ...)` with a non-constant argument. Any data-driven module
  path is a candidate for loading attacker-influenced code or a path-traversal fetch.

---

## SURFACE 7 — client-side storage → render (stored client XSS) + prototype pollution

- **Storage → render:** does the app persist any user input to `localStorage`/`sessionStorage`
  and later render it through a sink? That's a stored client-side XSS (persists in the victim's
  browser across sessions; self-scoped but a real vector, and sometimes chainable).
- **Prototype pollution:** SAPUI5 model binding and any `jQuery.extend(true, ...)` / manual deep-
  merge over user-influenced data can be pollutable. Grep for deep-merge patterns and
  `JSON.parse` of client-controllable input flowing into an object merge. A pollution gadget that
  reaches a sink (e.g., a template option, an `innerHTML` default) is DOM XSS; even without a
  sink, pollution can break authz-adjacent client logic. Fingerprint the jQuery version too (UI5
  bundles jQuery) — old jQuery has its own DOM-XSS and pollution CVEs.

---

## Deliverables

Under `vm-results/`:
- `07-track-h-clientside.md` — per-surface findings, but the payload is the **candidate table**:
  every viable sink with `file:line`, the source that feeds it, the escaping status, and a
  **ready-to-paste live test URL / repro step** for the researcher's browser half.
- `07-track-h-ui5-cves.md` — framework version + applicable CVE table (Surface 1).
- `07-track-h-candidates.md` — the short, ranked "test these live, in this order" list, most
  likely to fire first. This is the file the researcher actually works from.

Commit each as produced. Because this is static + framework-fetch only, there's no ACL budget to
manage — but keep framework-asset fetches to a handful.

## Ranked priority (most likely to reach the goal)

1. **Surface 1** — UI5 version + CVE match. A framework DOM-XSS CVE in a used control is the
   fastest path to a real, defensible cross-user finding.
2. **Surface 3** — postMessage + payment-state client-trust. High EV: origin-unchecked handlers
   are common, and the payment-trust chain is a logic bug with real impact.
3. **Surface 2** — router param → sink transitive flows. The classic SPA DOM XSS; deep-link
   delivery = cross-user for free.
4. **Surface 4** — second feed to the HTML sinks. If any non-LongTexts client-controllable source
   reaches `setHtmlText`, the "closed" XSS chain reopens.
5. **Surfaces 5–7** — open redirect, dynamic load, storage/pollution. Broader net, lower
   individual odds, but cheap to enumerate in the same static pass.

## Non-goals

No `zc_ad_appl_chat` (pending written scope confirmation). No server write-fuzzing (that surface
is exhausted). No IdP / `esap/public` / `webwsd` / `webwsq`. The live browser half tests the
researcher's own A/B sessions only — a deep-link "victim" test uses your own second account, never
a real user.
