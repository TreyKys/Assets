# Track H — client-side / DOM attack surface (per-surface findings)

**Overall verdict: one live candidate (`programDescription` → HtmlMenu
innerHTML), everything else closed by static analysis.** All seven surfaces
enumerated below; the actionable candidate is written up as #1 in
`07-track-h-candidates.md`. This file records the exhaustive per-surface
work so the negatives are provably-negative.

**Run:** 2026-09-26. **Approach:** offline grep over the extracted 03-bundle
tree (already committed) + one live GET for the SAPUI5 version file.
**Non-safe requests:** 0 for static; 2 live GETs (index.html + version json)
for framework fingerprinting.

## Surface 1 — SAPUI5 framework version + known-CVE match

**Version 1.120.48** (built 2026-07-15, sap.ui.core 1.120.47). LTS branch.
Full analysis in `07-track-h-ui5-cves.md`. **Pre-Jan-2026 CVEs all patched.**
Researcher must check post-2026-07 SAP Security Patch Day for any residual
CVE — I can't do that DB lookup from static analysis.

## Surface 2 — router/hash param transitive flows

Traced every route param through controller `onRouteMatched` handlers and
every view XML for bindings on the derived model paths.

- `paymentDone/{payId}/{amount}/{currency}/{date}/{returncode}/{description}/{tekst}` (7 params):
  - `payId` → `isPaymentDone(paymentId=...)` FunctionImport (server call).
    Never reaches DOM.
  - `tekst` → `MessageToast.show(a)` — SAPUI5 MessageToast uses
    `.textContent`. Escaped.
  - `amount`, `currency`, `date`, `returncode`, `description` — captured
    to local vars, **never referenced again anywhere in the bundle**
    (grepped all controllers, all views, all fragments). Dead captures.
- `application/{applicationNumber}`, `applicationFinish/{applicationNumber}`,
  `applicationAttach/{applicationNumber}`, `applicationDetailOverview/
  {applicationNumber}`, `applicationDetailPay/{applicationNumber}`,
  `applicationDetail/{applicationNumber}/{statusCode}/{currentAcYear}/
  {instelling}`, `applicationDetailBack/{applicationNumber}/{instelling}/
  detailBack`:
  - `applicationNumber` — interpolated into OData GET URL keys. No DOM
    render.
  - `statusCode` — captured but the model's `application>/statusCode` is
    populated from the server's Applications entity read (overwriting any
    URL value). View bindings on `application>/statusCode` go through
    formatters (`.formatter.notSubmitted` etc.) that return boolean/
    string values, not the raw statusCode. Not a sink.
  - `currentAcYear`, `instelling` — used as URL query values on
    subsequent OData reads, or as lookup keys against static client-side
    JSON models (`institution.json`). Never rendered directly.
- `persinf/{account}/{instelling}`, `address/`, `languages/`,
  `curriculum/`, `scholarships/`: `account` used only as `this.account`
  for later OData reads; `instelling` used as static-model lookup key.

**No unescaped route-param → DOM sink flow found.**

## Surface 3 — postMessage + isAppFeePayed client-trust

**postMessage / message handler:** zero hits across the bundle. No
`addEventListener("message"`, `.postMessage(`, `event.origin`,
`window.opener`, `iframe` (except as XML/HTML terminology in comments/
fragments), or `attachEvent`. **The app does not use postMessage at all.**

**`isAppFeePayed` client-trust trace:**

```js
// ApplicationDetail.controller.js — onRouteMatched, if _fromPayment:
var t = e.getParameter("arguments").payId;   // URL param
// (returncode captured to `i`, tekst captured to `a`; neither used further)

n.getOwnerComponent().getModel().callFunction("/isPaymentDone", {
    urlParameters: {admCode: o, paymentId: t},
    success: function(e) {
        if (e.isPaymentDone.paymentDone) {
            n.getOwnerComponent().getModel("application")
             .getData().isAppFeePayed = true;    // ← the flag
            u.show(a);                             // MessageToast(tekst)
            n._getRubrieken();
            n._getBlokken();
        } else {
            n.getOwnerComponent().getModel("application")
             .getData().isAppFeePayed = false;
            u.show(paymentNotOk_i18n);
            n._getRubrieken();
            n._getBlokken();
        }
    }
})
```

The `isAppFeePayed = true` branch fires ONLY when the server returns
`paymentDone: true`. **Track F F3.1 proved the server returns uniform
`{paymentDone: false}` for every input** (including with attacker-crafted
`paymentId` values from A's admCode and cross-tenant probes).

**Attacker cannot force `isAppFeePayed = true` via URL params alone** —
the server's response is authoritative. Real paid state (via a completed
KUL payment flow) is required for the flag to flip true.

**No client-side payment-state trust bypass reachable.**

## Surface 4 — a SECOND path to the HTML sinks

Enumerated every `htmlText=` binding, every `setHtmlText(` call, every
`MessageStrip enableFormattedText="true"` binding, every `HtmlMenu`
instantiation.

**Results:**

- 9 `htmlText=` bindings: all bound to `teksten>/...` (LongTexts model).
  Server-locked (Sweep 9 confirmed 501). No non-LongTexts feed.
- 4 `setHtmlText(x)` calls: all `x` derived from `teksten` model. Same.
- 4 `MessageStrip enableFormattedText text="{teksten>/...}"`: same.
- 1 `HtmlMenu` instance in `CommunicationMenu.fragment.xml`. **Its
  MenuItem `text` binding is a TEMPLATE STRING that includes
  `programDescription`** (see #1 in `07-track-h-candidates.md`).

**`programDescription` is the ONE non-LongTexts feed reaching an HTML
sink.** This is the finding of Track H.

## Surface 5 — client-side open redirect + scheme injection

Enumerated every `window.open`, `location.href = / .assign / .replace`,
`URLHelper.redirect`, and `Image.src` / view `href=`.

**Categories:**

- **Hardcoded external navigations** (safe): 3 × `window.open("https://
  www.kuleuven.be/english/...")` after successful submit; ~30 ×
  `location.replace("https://idp.kuleuven.be/idpx/profile/Logout")` etc.
- **Constructed cross-host chat URL** (`Main._goToApplicationChat`,
  `ApplicationDetail.onPressListItem`): built from own applicant data
  (`applicationId`, `currAcYear`, `instelling`) with hostname-tag
  substitution (`wsd` → `wsp/wsq`). No attacker-controllable scheme.
- **`ApplicationDetailPay.onPay`**:
  `window.location.replace(this.getOwnerComponent().getModel(
   "application").getData().appFeePayURL)`. `appFeePayURL` is server-
   supplied on the Application entity. Track F1.1 (batched) and Sweep 11
   (batched Applications gaps) both confirmed MERGE on this field
   silent-drops. Applicant cannot influence.
- **`_getPicture`**: `Image.setSrc('/.../ApplicantPhotos(\'0\')/$value?...')`
  and fallback `img/OliFotoEN.jpg`. All constant URIs.
- **`sap.m.Link href="{teksten>/submitInfo}"`**: dynamically bound, but
  source is server-locked LongTexts. UI5 1.120+ blocks `javascript:`
  schemes on `Link.href` by default. Closed.

**No client-controllable navigation-sink flow.**

## Surface 6 — dynamic module / component load

Grepped: `sap.ui.require(...)`, `sap.ui.xmlfragment(...)`,
`sap.ui.jsfragment(...)`, `sap.ui.loader.config(...)`,
`jQuery.sap.registerModulePath(...)`, `.loadLibrary(...)`,
`Component.create({name:...})`.

- All `sap.ui.xmlfragment` / `sap.ui.jsfragment` args are CONSTANT
  strings (fragment names like `be.kuleuven.application.fragment.picture`).
- `sap.ui.loader.config({paths: {"be/kuleuven/utils":
  "/sap/bc/ui5_ui5/sap/ZS_UI5_LIBRARY"}})` — all constant paths.
- `sap.ui.require([componentName.replace(/\./g,"/")])` in `utils/
  locate-reuse-libs.js` — `componentName` comes from a reuse-libs
  manifest field that the framework fetches; not URL-param controllable.
- `jQuery.sap.registerModulePath(e.componentId, e.url)` — same source.

**No data-driven module load with attacker-influenceable argument.**

## Surface 7 — localStorage / sessionStorage / prototype pollution

Grepped: `localStorage.`, `sessionStorage.`, `jQuery.extend(true, ...)`,
`$.extend(true, ...)`, `Object.assign(...)`, `.__proto__`, `JSON.parse(...)`.

- **Zero `localStorage.` / `sessionStorage.` calls** in any app source
  file (bundle-internal only; not user-facing).
- Zero `jQuery.extend(true, ...)`, zero `$.extend(true, ...)` — no
  recursive-merge patterns.
- 3 × `JSON.parse(...)` — all on OData server response bodies inside
  error handlers. No user-controlled parse.

**No storage → render vector. No prototype-pollution primitive.**

## Cumulative

- Track H hunted 7 client-side surfaces via 100% static analysis + 2
  framework fingerprint GETs.
- 6 of 7 surfaces are provably empty or closed.
- Surface 4 has one live candidate: `programDescription` → HtmlMenu
  innerHTML. That's the write-up in `07-track-h-candidates.md` #1 with a
  VM-testable step (~1 non-safe MERGE) and researcher's live-browser
  confirmation step.

Rows: no new rows appended to `02-authz-matrix.jsonl` for the static
half. The framework GETs are outside the OData harness. When the VM
step for candidate #1 runs, its rows will land under `"sweep": "h1"`.
