# VM BRIEF — KU Leuven Admissions — Track C + D: read the full client codebase

**Purpose:** we've been probing behaviors while only ~20% of the client bundle was read. This brief
extracts and analyzes the *rest* — the other 21 controllers, the XML views, the i18n bundle — and
produces a **sharpened target list** for future write-fuzz sweeps and stored-XSS tests. **No live
requests. No writes. Pure static analysis of publicly-served client code the researcher already has
authenticated access to fetch.**

## Scope (STRICT)
- Fetch ONLY under `https://webwsp.aps.kuleuven.be/sap/bc/ui5_ui5/sap/zc_ad_appl/*`
- Use authenticated session (fresh cookies from `~/kuleuven_creds/A.cookies`)
- All requests are `GET` only. **No POST/PUT/MERGE/DELETE. No probing behavior.**
- Max 1 req/sec. Prefer fetching the single `Component-preload.js` (already bundles everything) if
  it hasn't rotated since Track A; otherwise fetch each file individually from the paths below.
- Do NOT fetch anything outside the `zc_ad_appl/*` path.

## Track C — client controllers & bundle analysis

### C.1 Extract the full bundle
1. Fetch `Component-preload.js` (main app bundle). Parse it as the JS
   `sap.ui.require.preload({...})` payload — the object literal maps every logical file to a
   function whose body is the module source.
2. Extract each of the 26 files listed in the bundle to
   `intigriti/kuleuven_admissions/vm-results/03-bundle/<original path>`.

The previously-read (from Track A) files — you MAY skip re-reading, but do extract them for
completeness of the tree:
- `controller/ApplicationDetail.controller.js`
- `controller/ApplicationDetailPay.controller.js`
- `controller/ApplicationFinish.controller.js`
- `controller/ApplicationFollowUp.controller.js`
- `model/services.js`

The 21 unread files to analyze:
- `Component.js`
- `Router.js`
- `control/HtmlMenu.js`
- `controller/Main.controller.js`
- `controller/ApplicationNew.controller.js`
- `controller/ApplicationDetailOverview.controller.js`
- `controller/ApplicationStay.controller.js`
- `controller/Address.controller.js`
- `controller/CopyOfAddress.controller.js`  ← **flag any behavior/binding that differs from `Address.controller.js`**
- `controller/PersInf.controller.js`
- `controller/Curriculum.controller.js`
- `controller/CurriculumNew.controller.js`
- `controller/Languages.controller.js`
- `controller/Scholarships.controller.js`
- `controller/ErrorHandler.js`
- `fragment/AddDiscipline.fragment.js`
- `fragment/AddKeyword.fragment.js`
- `model/models.js`
- `model/Formatter.js`
- `utils/DiscCodeSearchServiceHelper.js`
- `utils/DiscCodeValueHelpHelper.js`

### C.2 Per-controller writeup
For each of the 21 files, produce a section in `03-controllers-analysis.md`:

- **Purpose:** one sentence.
- **OData calls made (name + operation + URL template + payload keys sent):** every `.read/.create/
  .update/.remove/.callFunction/.submitChanges` and every raw `fetch(...)` — full list.
- **Client-supplied fields sent on writes:** *exact* payload keys the controller sets before the
  MERGE/POST fires. This is what turns Track B's Sweep 1 from "my guess" into "the actual writable
  surface."
- **Client-side-only guards** (any `if(condition){ enable button }` type gates, `_rubriekenCompleet()`
  style local checks that decide whether a submit is allowed). If a client-only guard protects a
  server-state-changing call, log it under **Sweep-9 candidates**.
- **URL parameters trusted from the router** (things like the payment-done route's `payId`/
  `returncode`/`tekst`/`amount` params). Note where each ends up (rendered? sent to server? if
  rendered, is it escaped?).
- **Hardcoded strings, ID lists, feature flags** (statusCode literals, institution IDs, admin-looking
  identifiers, "wsd"/"wsq"/"wsp" branching).
- **Dev-leftover flags:** references to `console.log`, `debugger`, TODO/FIXME/HACK/XXX,
  commented-out endpoints, unused imports pointing at services not in `manifest.json`.
- **Cross-references:** does this controller call any URL/service *not* declared in the
  manifest's `dataSources`? (If yes — that's a hidden/undocumented endpoint. High-value.)

### C.3 Aggregate output — `03-bundle-summary.md`
- **Full OData call inventory** across all controllers: EntitySet × operation × observed payload
  keys. This is the definitive "what the client actually does" list.
- **Sweep-9 candidates:** table of `client-only guard → server-side-changing call it protects`. Each
  row is a testable "does the server enforce this rule?" question. This directly grows Track B.
- **Hidden endpoints:** any URL/service not in `manifest.json`.
- **`CopyOfAddress.controller.js` diff:** the behavioral delta from `Address.controller.js`. Anything
  extra in the copy = candidate for testing (old bindings often skipped a validation the new one
  added).
- **Router URL-param handling map:** every route's params → where they flow. Flags any param
  that reaches the DOM/HTML unescaped.

## Track D — XML views + i18n

### D.1 Enumerate view files
Fetch `manifest.json` (again, so the file is captured under vm-results). For each `target` in
`sap.ui5.routing.targets` there's a `viewName` → view file:
`view/<viewName>.view.xml`.
Fetch each (~14 views based on the manifest we already parsed). Save to
`vm-results/03-bundle/view/*.view.xml`.

### D.2 View analysis — `04-views-analysis.md`
For each view:
- **Every field binding** (`{path}` in `<Input>`, `<TextArea>`, `<CheckBox>`, `<Select>`, etc.).
  Note: `editable="true|false"`, `visible=...`, `enabled=...` — anything gated only client-side.
- **Fields the UI *never* exposes** (present in the OData entity but not bound to any UI control).
  These are the property-level over-exposure candidates: server returns them, UI hides them.
- **Any `<html:...>` / `htmlText` / raw HTML content bindings** — potential unescaped-render sinks.
- **Any `formatter=` calls** — formatters can strip/allow HTML; the ones we should audit sit in
  `model/Formatter.js` (Track C).

### D.3 i18n bundle
Fetch `i18n/i18n.properties` and `i18n/i18n_en.properties` / `i18n_nl.properties` if they exist.
Save to `vm-results/03-bundle/i18n/`.
Grep for suggestive strings: `admin`, `staff`, `reviewer`, `internal`, `debug`, `test`, `dev`,
`hidden`, `error_`, `code_` — anything hinting at gated features. Output findings to
`04-i18n-flags.md`.

## Deliverables
- `intigriti/kuleuven_admissions/vm-results/03-bundle/` — the extracted client tree.
- `intigriti/kuleuven_admissions/vm-results/03-controllers-analysis.md` — per-controller sections.
- `intigriti/kuleuven_admissions/vm-results/03-bundle-summary.md` — aggregated call inventory,
  Sweep-9 candidates, hidden endpoints, CopyOfAddress diff, router-param map.
- `intigriti/kuleuven_admissions/vm-results/04-views-analysis.md` — view/field/binding map.
- `intigriti/kuleuven_admissions/vm-results/04-i18n-flags.md` — i18n grep hits.

Commit each file as it's produced; don't wait for the whole thing.

## Non-goals
- No live probing of any endpoint discovered here (that becomes Track E, planned after review).
- No fetching of `/esap/public/*` services (out of scope).
- No fetching from `webwsd` / `webwsq` hosts (out of scope; only `webwsp` is in scope).
- No fetching of any `zc_oi_appl_*` (hand-off apps — outside our wildcard).
