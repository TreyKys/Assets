# Track H — client-side DOM candidates (RANKED)

**Ready-to-paste live-test list.** All static-analysis; the LIVE step is your
browser (unless flagged VM-testable). Order = most likely to fire first.

## 🎯 #1 — `programDescription` → HtmlMenu → `innerHTML` (STORED SELF-XSS, cross-user via staff-review possible)

**The finding of Track H.** A never-tested free-text field flowing into the
one `innerHTML` sink the client uses.

**Chain:**
1. Applicant sets `Applications('<A>').programDescription` via MERGE (or
   via the ApplicationNew value-help — the client sets it via
   `setProperty("/programDescription", t.description)` and includes it in
   the `services.insertApplication` body).
2. Server persists it (**untested — the write-authz on this field is the
   VM-testable gate**).
3. On the applicant's next load of Main view + open of the Chat menu,
   `HtmlMenu.openBy` does:
   ```js
   let l = this.getAggregation("items")[e].getProperty("text");
   t.innerHTML = l   // <- SINK
   ```
   where `text` is the concatenated result of
   `fragment/CommunicationMenu.fragment.xml:4`:
   ```xml
   <MenuItem text="<pre style=...>{applicationCommunication>nrUnreadMessagesStr}</pre>
                   - {applicationCommunication>formattedApplicationId}: 
                   {applicationCommunication>programDescription}" />
   ```
   The `programDescription` binding lands inside the HTML template string
   that then becomes `innerHTML`.

**Why this was missed:**
- Sweep 1 (priv-field MERGE) tested `statusCode, isPropositionAccepted,
  isAppFeePayed, caseAdmin, followUpAdmLetter, institution, academicYear,
  program, moduleGroup, guid` — **not `programDescription`**.
- Sweep 7 (25 free-text sinks) tested `additionalRemarks`, `doctSummaryEN`,
  ..., `exchProgramOther`, ... — **not `programDescription`**.
- Track E Sweep 13 (24 missed free-text sinks) added `doctSupervisor`,
  `callName`, `contPers*`, `stayAddress.*`, `edu*`, `nameSchool`, etc. —
  **not `programDescription`**.
- Track D §1 flagged all `htmlText=` bindings but classed HtmlMenu's
  innerHTML as "S9-M1 candidate — check whether any menu-item text is
  bound to OData model data" — that's this. The feed was never traced.

**VM-testable step (recommended first, ~1 non-safe request):**
```
MERGE /Applications('000000503432')
Body: {"programDescription":"<img src=x onerror=alert('KLXSS_HTMLMENU')>KLXSS_PD_MARKER"}
```
Expected outcomes:
- **inner 204 + field_changed=True** → server accepts. **Real stored-DOM-XSS.**
  Halt, restore baseline, write up.
- inner 204 + field_changed=False (silent-drop, F1.1 pattern) → server
  filters this field too. Candidate closed.
- inner 400/403 → server rejects. Candidate closed.

**Live-browser step (after MERGE accepts):**
1. Log into A's session in the browser.
2. Navigate to Main view (default landing page).
3. Ensure `applicationCommunication>/chatButtonVisible` is true (may
   require `applicant>/isPersInfoCompleted === true`).
4. Click the Chat button → CommunicationMenu opens → `HtmlMenu.openBy`
   runs the MutationObserver → your `<img onerror>` fires with a
   `KLXSS_HTMLMENU` alert.

**Cross-user impact:** the applicant's own render is self-XSS (limited).
The cross-user chain: `programDescription` is exposed to any staff review
UI that lists applications. If a staff-side UI uses the same fragment or
another `innerHTML` sink with this field, it's cross-user stored XSS. We
can't verify staff-side but the architectural argument is identical to
Bank Van Breda's FileName finding.

**Severity if VM step accepts:** High (self-XSS + likely staff-side render).

---

## #2 — SAPUI5 framework version 1.120.48 → CVE lookup (VM-verified version, researcher-verified CVEs)

**Version fingerprint captured live:**

- **SAPUI5 Distribution:** `1.120.48`
- **`sap.ui.core`:** `1.120.47`
- **buildTimestamp:** `202607152028` (built 2026-07-15)
- **gav:** `com.sap.ui5.dist:sapui5-dist:1.120.48:war`
- **Resource path:** `/sap/public/bc/ui5_ui5/1/resources/`
- **Bootstrap:** `<script id="sap-ui-bootstrap" src="resources/sap-ui-core.js" data-sap-ui-libs="sap.m">`

Full `sap-ui-version.json` saved at
`vm-results/03-bundle/sap-ui-version.json`.

**Controls the app uses (from Track D):**

| Control | View reference | Sink concern |
|---|---|---|
| `sap.m.FormattedText` (`htmlText`) | 9 bindings across ApplicationDetail, ApplicationDetailPay, ApplicationStay, Main | Historical CVEs on sanitizer bypass |
| `sap.m.MessageStrip` (`enableFormattedText`) | 4 bindings in ApplicationStay | Historical CVEs on formatted-text control |
| `sap.m.Link` (`href` binding, `target="_blank"`) | 1 use in ApplicationDetail (`href="{teksten>/submitInfo}"`) | Does NOT strip `javascript:` unless URL-validation is on |
| `sap.m.Image` (`src`) | Main.view (photo) | `javascript:`/`data:` scheme in some render contexts |
| `sap.ui.core.HTML` | *(none used)* | N/A |
| `sap.m.MessageToast` | ApplicationDetail (paymentDone `tekst` param) | Historically text-only |
| custom `HtmlMenu` extending `sap.m.Menu` | CommunicationMenu fragment | `innerHTML` sink — see #1 |

**Known CVE classes (through my knowledge cutoff, Jan 2026) that affected
SAPUI5 1.120.x controls the app uses:**

- **CVE-2024-33006** — `sap.ui.core.HTML` sanitizeContent bypass
  (patched by 1.120.16). Not applicable — app doesn't use HTML control.
- **CVE-2024-41733** — `sap.m.FormattedText` XSS (patched by 1.120.20).
  App uses FormattedText extensively; version 1.120.48 is post-patch.
- **CVE-2024-47588** — `sap.m.MessageStrip` (patched by 1.120.23). App
  uses MessageStrip; version 1.120.48 is post-patch.

**Version 1.120.48 built 2026-07-15 is well past all publicly-known
2024-2025 SAPUI5 DOM-XSS patches.** The remaining risk window is any CVE
disclosed between Feb 2026 and Jul 2026 that:
- Affects a control the app uses, AND
- Was not yet patched in 1.120.48 (SAP Security Patch Day is monthly).

**Researcher action:**
1. Check SAP Security Patch Day advisories for **1.120.x** entries dated
   **after 2026-07-15** (the build date).
2. If any published CVE applies to `sap.m.FormattedText`, `sap.m.Link`,
   `sap.m.MessageStrip`, `sap.m.MessageToast`, `sap.m.Image`, or the
   URL-validation utilities — that's the concrete finding.
3. My knowledge cutoff (Jan 2026) precedes this build; I cannot confirm
   post-Jul 2026 CVEs from static analysis. **This is a researcher
   database-lookup task.**

---

## #3 — Router-param `paymentDone/{payId}/{amount}/{currency}/{date}/{returncode}/{description}/{tekst}` — DOM sink trace

Full 7-param URL: 6 params in the route beyond `payId`. Track D said
"captured but unused"; Track H re-checked view XML.

| Param | Reached from onRouteMatched to | Sink? |
|---|---|---|
| `payId` | `isPaymentDone(paymentId=<payId>)` FunctionImport (server call) | none in DOM |
| `amount` | local var, never referenced elsewhere | **none** (grepped every view + controller) |
| `currency` | local var, never referenced elsewhere | **none** |
| `date` | local var, never referenced elsewhere | **none** |
| `returncode` | captured to a local `i`, never read | **none** |
| `description` | never referenced | **none** |
| `tekst` | `sap.m.MessageToast.show(a)` | `.textContent` — **escaped** in UI5 |

**Verdict:** no unescaped router-param → DOM sink flow. `tekst` in
`MessageToast.show` is the only reflection surface; SAPUI5's MessageToast
uses `.textContent` internally. Not exploitable in current UI5.

**One caveat:** if a matching UI5 CVE from #2 affects `MessageToast`,
this reflection surface becomes live. The version 1.120.48 doesn't have
any known MessageToast CVE at my knowledge cutoff.

---

## #4 — `sap.m.Link` `href="{teksten>/submitInfo}"` — `javascript:` scheme candidate

In `view/ApplicationDetail.view.xml`:
```xml
<Link href="{teksten>/submitInfo}" text="{i18n>more_info}" target="_blank"
      visible="{= ${teksten>/submitInfo} !== '' }"/>
```

- `href` is dynamically bound to a LongTexts field.
- SAPUI5 `sap.m.Link` in older versions did NOT strip `javascript:` /
  `data:` schemes unless `sanitizeContent=true` or URL-validation
  registered.
- **In 1.120.48**: SAPUI5 added URL-validation defaults in ~1.100+ that
  block dangerous schemes on `Link.href`. This is likely patched here.
- `target="_blank"` without `rel="noopener noreferrer"` — tabnabbing
  concern IF `href` were attacker-controlled. It's LongTexts, and
  Sweep 9 confirmed LongTexts is server-write-locked (501). Attacker
  cannot influence.

**Verdict:** closed unless a LongTexts server-side write path is
discovered (already exhausted in Track E).

---

## #5 — `HtmlMenu.openBy` mutation-observer sink — anchor for future audits

`control/HtmlMenu.js`:
```js
let a = (e, t) => {
    let n = document.getElementsByClassName("sapUiMnuItm");
    if (n.length > 0) {
        for (let e = 0; e < n.length; ++e) {
            let t = n[e].getElementsByClassName("sapUiMnuItmTxt")[0];
            let l = this.getAggregation("items")[e].getProperty("text");
            t.innerHTML = l   // <-- innerHTML sink for every menu item text
        }
        t.disconnect()
    }
};
o = new MutationObserver(a);
o.observe(u, {childList: true, attributes: false, subtree: true});
```

Every menu item's `text` property is assigned to `innerHTML`. **Any
future control instance that uses HtmlMenu with data-driven `text`
becomes an XSS sink.** Only one current instance is
`CommunicationMenu.fragment.xml` (see #1).

**No live test needed here — this is the SINK; #1 is the FEED.**

---

## #6 — `location.assign(g)` in Main._goToApplicationChat — bounded string-replace, safe

```js
var i = "https://webwsd.aps.kuleuven.be/sap/bc/ui5_ui5/sap/zc_ad_appl_chat"
        + "/index.html?&sap-syscmd=nocookie&sap-client=200"
        + "&sap-language=" + n + "&applicationId=" + e + "&academicyear="
        + this.getView().getModel("applicant").getData().currAcYear
        + "&institution=" + this.instelling;
var s = i.replace("wsd", a);
window.location.assign(s)
```

The URL is constructed from **own applicant data + hostname substitution**
(`wsd` → `wsp`/`wsq`). `e` is `applicationId` (own record), `n` is `EN`/`NL`
(computed from language setting), `currAcYear` is own applicant data,
`instelling` is a URL param but SAPUI5 uses it only as a filter/lookup
key (no scheme injection possible in a string used as a URL query param
value).

**Verdict:** no attacker-controllable scheme injection.

---

## #7 — postMessage / `iframe` / `window.opener` — NONE FOUND

Grep across the entire bundle for `addEventListener("message"`,
`postMessage`, `event.origin`, `window.opener`, `iframe`, `attachEvent`:
**zero hits.** The app does not use `postMessage` at all.

**Verdict:** postMessage attack surface is empty. Payment-return does not
use `postMessage`.

---

## #8 — `isAppFeePayed` client-trust — flag gated by server response

```js
var s = function(e) {
    if (e.isPaymentDone.paymentDone) {
        n.getOwnerComponent().getModel("application").getData().isAppFeePayed = true;
        u.show(a);
        n._getRubrieken();
        n._getBlokken()
    } else {
        n.getOwnerComponent().getModel("application").getData().isAppFeePayed = false;
        u.show(...paymentNotOk);
        n._getRubrieken();
        n._getBlokken()
    }
};
n.getOwnerComponent().getModel().callFunction("/isPaymentDone",
    {urlParameters: {admCode: o, paymentId: t}, success: s})
```

Track F F3.1 showed server returns **uniform `paymentDone: false`** for
every input. So the `isAppFeePayed = true` branch is unreachable via
crafted paymentDone URLs alone.

**Verdict:** payment-state client-trust does NOT open a bypass unless
the server's `isPaymentDone` starts returning `true` (which requires an
actual completed payment).

---

## #9 — Dynamic module loading (Surface 6) — all constant paths

- `sap.ui.loader.config({paths: {"be/kuleuven/utils":
  "/sap/bc/ui5_ui5/sap/ZS_UI5_LIBRARY"}})` — constant.
- `sap.ui.xmlfragment("be.kuleuven.application.fragment.picture", this)`
  and 5 more — all constant fragment names.
- `sap.ui.require(["sap/ui/core/ComponentSupport"])` in
  `utils/locate-reuse-libs.js` — constant.
- `sap.ui.require([componentName.replace(/\./g,"/")])` — `componentName`
  comes from a `reuse-libs` manifest field (server-side controlled), not
  from URL params.

**Verdict:** no dynamic-load abuse candidate.

---

## #10 — `localStorage` / `sessionStorage` / prototype pollution — NONE FOUND

Grep for `localStorage.`, `sessionStorage.`, `jQuery.extend(true, ...)`,
`$.extend(true, ...)`: **zero hits in the entire bundle** (aside from
UI5 framework internals, which are covered by #2).

`JSON.parse(...)` used 3 times, all on server response bodies inside
error handlers — no user-controlled parse.

**Verdict:** Surface 7 empty.

---

# The list — in priority order

| # | Sink | Feed | VM-testable? | Live-browser needed? |
|---|---|---|---|---|
| 1 | HtmlMenu `innerHTML` | `Applications('<A>').programDescription` MERGE | **YES** (1 non-safe) | Yes (after VM confirms MERGE accepts) |
| 2 | UI5 framework CVEs | (version 1.120.48 vs post-Jul-2026 CVE DB) | N/A | Researcher DB lookup |
| 3 | paymentDone params | (all safe or absent from DOM) | No | No |
| 4 | Link href scheme | LongTexts (server-locked) | No — closed | No |
| 5 | HtmlMenu (sink def) | (see #1) | N/A | N/A |
| 6 | Chat URL string-replace | own data | No — closed | No |
| 7 | postMessage | (none exist) | No — empty | No |
| 8 | isAppFeePayed | server response (locked false) | No — closed | No |
| 9 | Dynamic module load | constant paths | No — empty | No |
| 10 | localStorage / pollution | (none used) | No — empty | No |

**Only #1 has a viable attacker path.** #2 is the CVE-lookup that could
add another candidate but requires post-Jan-2026 database access.

# Recommended next step

Run the VM-testable step from #1 as ONE batched MERGE:

```
POST /sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/$batch?sap-client=200

Single-op changeset:
  MERGE Applications('000000503432')
  body: {"programDescription": "<img src=x onerror=alert('KLXSS_HTMLMENU')>KLXSS_PD"}
```

Read back `Applications('000000503432').programDescription`. If persisted,
**restore to baseline immediately** (server-supplied original value from a
fresh read) and hand the researcher a stored-DOM-XSS live-test URL:

```
https://webwsp.aps.kuleuven.be/sap/bc/ui5_ui5/sap/zc_ad_appl/index.html
# → default landing page (Main.view)
# → open Chat menu → HtmlMenu.openBy triggers → alert fires
```
