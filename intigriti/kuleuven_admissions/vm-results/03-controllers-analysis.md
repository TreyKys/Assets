# Track C — per-controller analysis

Static read of every JS file extracted from `Component-preload.js` into `vm-results/03-bundle/`.
No live probes. All OData paths are relative to `mainService`
(`/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV`, declared in `manifest.json → sap.app.dataSources`).
`getModel().setUseBatch(true)` is set in `model/services.js → setModel()`, so every write goes
through `$batch` (relevant to Track B's Sweep 2 & 9 both returning outer 403).

Legend:
- **Reads** — GET operations (`.read(path,…)` or `model.callFunction(name,{method:"GET",…})`).
- **Writes** — POST/PUT/MERGE/DELETE (`.create`, `.update`, `.remove`, `.submitChanges`,
  or raw `XMLHttpRequest.open("POST",…)`).
- **Client-only guards** — `if(…) call-with-server-effect` where the "if" is a UI state, model
  flag, or a checkbox — i.e. the server MUST re-enforce for the check to matter. Each of these is
  a candidate for Track B / Sweep-9-style tests.
- **Router params** — the URL segments the controller reads from `RouteMatched` events.

---

## `Component.js`  (small — 2 KB)

- **Purpose:** app bootstrap. Registers three additional UI5 loader paths (`be/kuleuven/utils` →
  `/sap/bc/ui5_ui5/sap/ZS_UI5_LIBRARY`, `zc_zoek_opl` → `/sap/bc/ui5_ui5/sap/zc_zoek_opl`,
  `zc_zoekhulp` → `/sap/bc/ui5_ui5/sap/ZC_ZOEKHULP`). Creates ~20 client-side JSON models for
  static reference data (`institution`, `statuut`, `status`, `nationalities`, `year`, …).
- **OData:** none directly (delegates via `services.js`).
- **Hidden endpoints:** the three UI5 loader paths (`ZS_UI5_LIBRARY`, `zc_zoek_opl`,
  `ZC_ZOEKHULP`) are **not declared as `dataSources`** in the manifest. They're UI5 asset paths
  (JS/XML), not OData services, but they widen the accessible ui5_ui5/ tree beyond
  `zc_ad_appl/*`. **Out of Track C/D scope to fetch.** Noted for future recon.
- **Dev-leftovers:** none.

## `Router.js`  (< 1 KB)

- **Purpose:** custom router extending `sap.ui.core.routing.Router` with a `myNavBack` helper
  that falls back to `navTo(target)` when browser history is empty.
- **OData/writes/HTML sinks:** none.
- **Router-param handling:** none (delegated to controllers).

## `control/HtmlMenu.js`  (< 1 KB)

- **Purpose:** subclass of `sap.m.Menu` that, when opened, uses a `MutationObserver` to walk
  every rendered `.sapUiMnuItm` and assign `menuItem.getProperty("text")` **into `innerHTML`**
  of the `.sapUiMnuItmTxt` child element.
- **HTML sink (⚠ CLASS 1):** `t.innerHTML = l` where `l = item.getProperty("text")`. If any
  bound `sap.m.MenuItem.text` originates from OData model data an applicant can influence
  (own free-text field surfaced in a menu), it renders as raw HTML — stored XSS in-session.
  Track B Sweep 7 already showed the applicant-side write-authz filter rejects `<img …>`
  payloads on the free-text sinks it tested; but the surface here is *any bound menu-item text*,
  including staff-supplied strings (LongTexts, Rubriek `text`, i18n props). See Sweep-9-candidate
  #S9-M1 in `03-bundle-summary.md`.
- **Dev-leftovers:** none.

## `controller/Main.controller.js`  (15 KB)

- **Purpose:** landing view. Loads applicant + applications, renders the sidebar menu, handles
  photo upload, application delete, cross-app chat redirect, language switch, logout.
- **Reads via `services.js`:** `getApplicantData` → `/Applicants('0')`; `getTeksten("E",inst)`
  → `/LongTexts('E|<inst>|2020')`; `getCusto(inst)` → `/OrganisationCustomisations('<inst>')`;
  `getPicture` → `/ApplicantPhotos('0')`; `getApplicationsData(inst)` → `/Applications`
  filtered by `institution eq <inst>`; `getCommunicatie(id)` →
  `/CommunicationSet(applicationId='<x>',action='ADM_START')`.
- **Writes via `services.js`:** `createApplicant(data)` (POST `/Applicants`);
  `updateApplicant(data)` (MERGE `/Applicants('0')`); `insertApplication("A|<id>",data)`
  (MERGE `/Applications('A|<id>')` — the `A|` prefix is the *self-alias for insert*);
  `deleteApplication(id)` (DELETE `/Applications('<id>')`).
- **Raw XHR write:** `uploadBlob(blob,t)` — direct `XMLHttpRequest.open("POST",
  "/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/ApplicantPhotos", true)` with headers
  `Content-Type: <attacker-controlled blob.type>` and `x-csrf-token: this.csrfToken`. Sends
  raw blob body. **Slug set separately** in `_uploadPicture` as `"ZCM_ADM027|" + uploaded-file-name`.
  Filename is user-controlled.
- **Client-only guards:**
  - `onDeleteApplication` — checks `statusCode ∈ {"022","041","101","202"}` (client-side custom
    data on the tapped list item) and refuses to call `deleteApplication(id)` otherwise.
    **Sweep-9 candidate S9-M2:** does the server enforce delete only on those statuses?
  - `onCommunicationMenuOpen` — checks `applicant./isPersInfoCompleted === true` before opening
    the chat menu (no server call directly gated — chat lives on a different host, `webwsd/wsp
    ...zc_ad_appl_chat`). UI-only.
- **Router params:** none read directly; passes URL params outward (`account`, `instelling`,
  `currentAcYear`, `applicationNumber`, `statusCode`) into other routes.
- **Hardcoded strings / flags:**
  - Default institution `"50000050"` (fallback when URL has no `instelling`).
  - Slug prefix `"ZCM_ADM027"` for photo uploads.
  - Delete-status whitelist `022|041|101|202`.
- **Cross-host redirect:**
  `_goToApplicationChat` builds a URL for `webwsd.aps.kuleuven.be/sap/bc/ui5_ui5/sap/
  zc_ad_appl_chat/index.html?…&applicationId=<id>&academicyear=<yr>&institution=<inst>` and
  substitutes `wsd` for the current host tag (`wsp`/`wsq`) via string replace. `applicationId`
  and `academicyear` come from own applicant model. Route target is a UI5 app on the neighbour
  host, hosted under the same ui5_ui5/ tree but a different app dir (`zc_ad_appl_chat`) —
  **out of Track B/C scope.**
- **Logout redirect:** `window.location.replace("https://idp.kuleuven.be/idpx/profile/Logout")`
  (three-way branch on hostname `webwsp`/`webwsq`/default). Second arg `"_blank"` is a
  `window.location.replace` API misuse — replace takes only a URL; `"_blank"` is silently
  ignored. Cosmetic bug, not a vuln.
- **HTML sinks:** `sap.ui.getCore().byId("infoTekstPictureEditor").setHtmlText(t.langeTekstFoto)`
  where `langeTekstFoto = teksten.fotoTekst` from `LongTexts('E|<inst>|2020')` (staff-content).
  Not applicant-writable through the client. If the LongTexts entity is writable via a hidden
  admin path with an XSS payload, this renders it — see Sweep-9-candidate S9-M3.
- **Dev-leftovers:** none.

## `controller/ApplicationNew.controller.js`  (22 KB — the biggest write flow)

- **Purpose:** the "create application" wizard — pick institution/statuut/program/moduleGroup,
  fill exchange/doctoral/scholarship fields, save.
- **Reads:** `services.getAcYears(inst)` → `/AcademicYears?$filter=instelling eq '<inst>'`;
  direct `model.read("/ModuleGroups", filters:[programmeId, academicYear],
  urlParameters:{$expand:"toModuleGroupCombinations"})`; `/SpringFallSet` filtered by
  programmeId + academicYear; `/ModuleGroupCombinations` filtered same. Static JSON models
  (`statuut`, `exchangeProgram`, `degreeTitle`) filtered by `Institution eq <inst>`.
- **FunctionImports (all GET):**
  - `getSwitchOpenSearch` (no params) — returns `{getSwitchOpenSearch:{active:bool}}` global
    feature flag. Sweep 5 confirmed same body for junk input.
  - `showOptions` with `{programmeId, academicYear, institution, status:"101", moduleGroup:""}`
    — Sweep 5 exercised various admCodes/programs → all 400 without valid combos.
  - `showSpringFall` with `{institution, status:"101"}` — Sweep 5 → all 400.
- **Writes:** `services.insertApplication("0", applicationModel.getData())` — MERGE
  `/Applications('0')` with body carrying every wizard field: `institution`, `program`,
  `programDescription`, `academicYear`, `statuut`, `moduleGroup`, `exchContactEmail`, `exchBegda`,
  `exchEndda`, `exchBegdaFysiek`, `exchEnddaFysiek`, `exchModus`, `exchStudentType`,
  `exchStudentTypeOther`, `exchPurpose`, `exchPurposeOther`, `exchProgram`, `exchProgramOther`,
  `exchHomeUniversity`, `exchHomeUniversityCountry`, `exchContactName`, `exchContactPhone`,
  `exchContactKUL`, `exchCompletedYears`, `exchStudyField`, `intScholarSubject`,
  `intScholarSupervisor`, `intScholarBeginDate`, `intScholarEndDate`, `specSpecialisation`,
  `specSupervisor`, `specBeginDate`, `specEndDate`, `doctIsVacantPosition`,
  `doctAanstelDossierId`, `doctAanstelDossierProject`, `doctSpecialisation`, `doctSupervisor`,
  `doctIsDualDegree`, `doctPartnerUniversity`, `doctIsApplyingForScholarship`, `doctScholarship`,
  `doctBeginDate`, `doctEndDate`, `applicationId:"0"`, `instellingOmschrijving` *(explicitly
  deleted from oData before send)*. **This is the definitive wizard write payload for
  Sweep 1 tuning.**
- **Client-only guards (pre-save):** email regex, date-order (`from<=until`), no-past-dates,
  required-field checks, module-group option combinations. All UI. **The server MUST enforce
  these for them to matter.**
- **Router params:** `applicationNew/{account}/{currentAcYear}/{instelling}` — reads all three
  from `RouteMatched`. `account` and `currentAcYear` are only used to seed model state; the
  MERGE goes to `/Applications('0')`.
- **Hardcoded strings:** `"50000050"` institution; statuut codes `"005"`/`"006"`/`"012"`/`"000"`
  for wizard branches; hardcoded `status:"101"` sent into `showOptions`/`showSpringFall`.
- **Dev-leftovers:** `console.error("Function import getSwitchOpenSearch failed",t)`.
- **Cross-refs:** none outside `mainService`.

## `controller/ApplicationDetailOverview.controller.js`  (21 KB — the "edit application" view)

- **Purpose:** re-edit a submitted application. Same wizard fields as ApplicationNew but for an
  existing record.
- **Reads:** same shape as ApplicationNew (`/ModuleGroups?$expand=toModuleGroupCombinations`,
  `/SpringFallSet`, `/ModuleGroupCombinations`). Owned Discipline/Trefwoord codes read via
  `services.getDisciplineCodes(id)`, `services.getTrefwoorden(id)`. Also uses
  `DisciplineCodeSearchModel` (out-of-scope `ZR_DISC_CODES_SRCH_SRV`) via
  `DiscCodeSearchServiceHelper.searchDiscCodeViaCode(code, cb)` → GET `/disciplineCodeSet?
  $filter=Code0 eq '<code>'`.
- **FunctionImports:** `showOptions` (with runtime `status: applicationModel.statusCode` — not
  the hardcoded `101` seen in New), `showSpringFall`.
- **Writes:** `services.insertApplication(id, applicationModel.getData())` — MERGE
  `/Applications('<id>')` — plus `services.updateDisciplineCodes(id, disciplines)` and
  `services.updateTrefwoorden(id, keywords)` if statuut is `005|006`. Both discipline/keyword
  updates are `$batch` groups that MERGE `/DisciplineSet(applicationId='<id>',key='<seq>')` and
  `/TrefwoordenSet(applicationId='<id>',key='<seq>')` for each row.
- **Client-only guards:** same as ApplicationNew (email regex, date-order, required-field
  checks). Also gate: `_configureSaveButton` walks controls with `fieldGroupId=
  "saveEnabledIfEditable"` and only enables save if any `InputBase` returns `getEditable()===
  true`. **Sweep-9 candidate S9-O1:** if server accepts a MERGE on `/Applications('<id>')` even
  when the field is server-marked read-only (`editable=false` on the OData property), that's a
  bypass.
- **Router params:** `applicationDetailOverview/{applicationNumber}` — but the actual data
  used comes from the *component-level* application model set by `ApplicationDetail`. So the URL
  param is documentation-only in this controller.
- **Hardcoded strings:** statuut branches `005|006|012`, statusCodes `101|202`, magic
  `"00000000"` used to detect an "unset" moduleGroup/choice.
- **Dev-leftovers:** none.

## `controller/ApplicationDetail.controller.js`  (17 KB)

- **Purpose:** the "application detail" page — displays the wizard read-only, hosts the
  disclaimer + Submit flow (`onLinePress`, `onLocationPress`), handles the payment-return
  route, resolves per-status text blobs from `LongTexts`, gates onward navigation.
- **Reads:** `services.getApplication("<lang>|<id>")` → MERGE-shaped read
  `/Applications('<lang>|<id>')`; `services.getSubmitCheck(id)` →
  `/Applications('<id>')/SubmitChecks`; `services.getDisciplineCodes` /
  `services.getTrefwoorden` (statuut 005/006 only); `services.getBlokken(inst,status,acjaar,
  appId)` → `/BlockSet?$filter=…`; `services.getRubrieken(appId,lang)` → `/RubriekSet?$filter=
  applicationCode eq '<id>' and language eq '<E|N>'`; `services.getTekstenWithAdmCode(lang,
  inst, appId)` → `/LongTexts('<lang>|<inst>|<appId>')`.
- **FunctionImport (paymentDone route):** `callFunction("/isPaymentDone",{urlParameters:
  {admCode:<appId>, paymentId:<payId-from-URL>}})` — GET. `paymentId` comes verbatim from the
  `paymentDone/{payId}/…` route param.
- **Writes:** `services.insertApplication(id, appData)` — with `appData.statusCode` set to
  `"211"` (onLinePress) or `"210"` (onLocationPress). This is the state-transition path.
- **Client-only guards (**⚠ **HIGH):**
  - `_rubriekenCompleet()` walks the `rubrieken` model and requires every rubriek in
    `{001,005,006,007}` to have `status === "3"`; also `003` and `004` if `instelling ∈
    {"50000050","51813768"}`. Only if all pass does `onLinePress`/`onLocationPress` MERGE
    `statusCode: "211|210"`. **Sweep-9 candidate S9-D1:** does the server enforce the same
    completeness check? Track B Sweep 1 confirmed direct `statusCode:"211"` MERGE returns 403,
    so the answer *probably* is yes — but "you cannot set 211 at all" ≠ "you can set 211 only
    if rubrieken are complete." If the client-guard bypass is the *only* thing gating a
    normally-allowed transition (client-issued Submit sends 211, server-side authorization is
    role-based), then Sweep 1's finding is complete. If not, 210 wasn't tested by Sweep 6.
  - `onSubmitDisclaimerSelect` — checkbox toggles submit-button enabled state. Trivial.
- **Router params & paymentDone flow (route pattern
  `applicationDetail/{applicationNumber}/{statusCode}/{currentAcYear}/{instelling}/paymentDone/
  {payId}/{amount}/{currency}/{date}/{returncode}/{description}/{tekst}`):** captured params:
  - `applicationNumber` — used to look up own record (self-check via `Applications('<lang>|<id>')`).
  - `payId` — sent into `isPaymentDone` FunctionImport as `paymentId`.
  - `returncode` — read into a local `i`, then never used (dead capture).
  - `tekst` — passed to `sap.m.MessageToast.show(a)`. `MessageToast.show(text)` treats input as
    plain text (escaped when rendered). **Not an XSS sink**, but *does* reflect a URL param
    into the UI unchecked — good for a phishing pretext if you can get the victim to click the
    return URL. Combined with the `appFeePayURL` finding below, this is worth documenting.
  - `amount`/`currency`/`date`/`description` — captured but never used by this controller.
    They *may* be consumed by a view binding — see Track D.
- **Cross-host redirect:** `onPressListItem` builds
  `webwsd.aps.kuleuven.be/sap/bc/ui5_ui5/sap/zc_oi_appl_<mydata>/index.html?…&adm=<id>` where
  `mydata` = `rubrieklink` (server-side value from `RubriekSet`) — server-controlled. If a
  server-writable field flows into `mydata`, this becomes an open-redirect **through a subpath
  interpolation** (`zc_oi_appl_<x>`) — `<x>` is a UI5 app dir name, so it can only redirect
  to another SAP UI5 app on the same neighbour host; wide but bounded. Out of scope for Track B
  (writes rejected on RubriekSet by design — Sweep 8 confirmed).
- **HTML-sink cleanup:** `_removeBrFromTekst` and `_removePFromTekst` strip literal `<br>` and
  `<p>`/`</p>` (single occurrence each — `.replace(str,str)` not global) from server text. The
  cleaned text goes into the `teksten` model → view. If the view uses `text` binding, escaped
  (safe); if `htmlText`, the *remaining* HTML is rendered. See Track D for which. Also, the
  strip is single-shot: `"<br><br>"` becomes `"<br>"` — the second `<br>` survives.
- **Hardcoded strings:** exhaustive `switch(statusCode)` from `"101"` through `"907"` — every
  known status code the client understands. Institution `50000050` for the `en/registration-
  completed` splash-link and `51813768` (a second known institution) for the rubriek-003 check.
- **Dev-leftovers:** none.

## `controller/ApplicationDetailPay.controller.js`  (< 1 KB, but ⚠ HIGH interest)

- **Purpose:** the "pay application fee" screen with a disclaimer checkbox and a Pay button.
- **Reads/writes/FunctionImports:** none directly.
- **⚠ Redirect sink:** `onPay: window.location.replace(this.getOwnerComponent().getModel(
  "application").getData().appFeePayURL)`. The URL comes verbatim from the OData
  `Applications` entity's `appFeePayURL` field. **Sweep-9 candidate S9-P1:** if an
  applicant can MERGE `appFeePayURL` on their own `Applications('<id>')` record, the "Pay
  processing fee" button navigates to the attacker's URL. Track B's Sweep 1 didn't include
  `appFeePayURL` in the priv-field MERGE matrix (that list was tuned to
  statusCode/caseAdmin/institution/etc.). This is a **new priv-field candidate to add to
  Sweep 1's expansion.**
- **Client-only guards:** disclaimer checkbox gates the Pay button. UI-only.
- **Router:** none read here.

## `controller/ApplicationFollowUp.controller.js`  (< 1 KB)

- **Purpose:** stub — sets a page title from the `applicationNumber` route param and does
  nothing else.
- **OData:** none. Router param `applicationNumber` — string-concatenated into a text property.
  Not an HTML sink (goes to `Page.title` which is escaped).

## `controller/ApplicationFinish.controller.js`  (< 200 B)

- **Purpose:** empty stub. `onInit(){}` only.
- Everything else: none.

## `controller/ApplicationStay.controller.js`  (6.7 KB)

- **Purpose:** the applicant "where will you stay?" address form (a "kot" is a student room in
  Belgian slang). Registers under class name **`Application<stay`** — an unescaped `<` in the
  class name is a **cosmetic bug** but not a security issue (class name is a JS string, not
  rendered).
- **Reads:** `services.getApplicationStay(id)` → `/ApplicationStaySet('<id>')`;
  `services.getRegionForPostalCode(postal)` → `/StateForCitySet('<postal>')`.
- **Writes:** `services.updateApplicationStay(id, data)` → MERGE
  `/ApplicationStaySet('<id>')`. Payload keys: `stayAddress.country`, `stayAddress.postalCode`,
  `stayAddress.city`, `stayAddress.street1`, `stayAddress.houseNumber`, `stayAddress.state`,
  `stayAddress.telephone`, `stayAddress.box`, `opKotJa`, `opKotNee`, `opKotJaMaar`,
  `opKotMisschien`.
- **Client-only guards:** phone regex `/^([0-9. /()+-]*)$/`; "kot" radio required; conditional
  address-field completeness (country/city/postal/street/house). **All can be bypassed by
  crafting the raw MERGE. Sweep-9 candidate S9-S1.**
- **Router:** none read directly (the applicationId comes from the component-level model set
  earlier).
- **Dev-leftover:** references `MessageBox.alert(…, {…, icon:Icon.ERROR, textDirection:
  TextDirection.Inherit, …})` and `MessageBox`, `Icon`, `TextDirection` are **not imported into
  the controller's `sap.ui.define` list** — code will `ReferenceError` when the phone branch
  fires. Latent runtime bug.

## `controller/Address.controller.js`  (7.4 KB — the CURRENT address controller)

- **Purpose:** applicant permanent + current address, with smart country/city/street search
  controls that call reuse-library controls (`_searchCountryPerAd`, etc.) — those controls come
  from `be/kuleuven/utils` (the `ZS_UI5_LIBRARY` loader path from `Component.js`).
- **Reads:** `services.getAddresses(account)` → `/Addresses(inAccountId='<account>',language='<lang>')`.
- **Writes:** `services.updateAddresses(account, addressModel.getData())` → MERGE
  `/Addresses(inAccountId='<account>',language='<lang>')`. Payload keys:
  `permanentAddress.{country,postalCode,city,street1,state}`,
  `currentAddress.{country,postalCode,city,street1,state}` — plus any pre-existing fields the
  server returned (echoed back verbatim).
- **Client-only guards:** each search control's ValueState check, ICE emergency-contact email
  regex, per-country BE validation. **Sweep-9 candidate S9-A1:** raw MERGE with an invalid
  country/state combo, or a missing required BE street/city, to see if server enforces.
- **Router:** `address/{account}/{instelling}` — `account` is what's used in the OData key.
  The route param **contains the account id which becomes an OData filter value directly**.
  Sweep 8 confirmed the server ignores IDs that aren't the caller's (self-substitution) —
  so passing another `account` in the URL still hits your own record.
- **Cross-refs:** none outside mainService (search controls fetch from `ZS_UI5_LIBRARY` but
  their internal endpoints are library-controlled).

## `controller/CopyOfAddress.controller.js`  (5 KB — the OLDER address controller)

- **Purpose:** an older address controller from before the smart search controls existed.
- **⚠ Class-name collision:** declares `Controller.extend("be.kuleuven.application.controller.
  Address", …)` — the **same class name as `Address.controller.js`**. If both are loaded,
  whichever `sap.ui.define` runs last silently overrides the other. Given both files are in
  the preload, load-order determines behavior. In the observed bundle order the newer
  `Address.controller.js` is listed first and `CopyOfAddress.controller.js` is listed later —
  so the copy overrides the current one. **View `Address.view.xml` will use whichever the
  namespace resolves to at controller-instantiation time.**
- **Reads/writes:** same as Address.controller.js (`getAddresses` / `updateAddresses`).
- **Behavioral deltas from `Address.controller.js`** (this is what §C.3's "CopyOfAddress diff"
  block asks for — expanded in `03-bundle-summary.md`):
  1. No ICE contact-email regex check (`_emailCheck()` in new; absent here).
  2. No `_countryChangedRegion` handler → state-visibility toggle when country changes is
     missing → user can save with a state value the country doesn't have.
  3. No pre-save ValueState checks — the new controller aborts save if a search-control's
     ValueState isn't `Success`; this one just reads the raw model and PUTs.
  4. Uses static JSON country lists (`natio` model) instead of the searchable value-help
     control — permits any country code the JSON has, not what the address service accepts.
  5. `_fillCountries` has a typo default (`"{natioLandEN}"` without `natio>` binding path) —
     latent bug.
- **Impact:** either the copy is dead code (view never instantiates a `CopyOfAddress` — the
  router's `"address"` target uses `viewName:"Address"`; `CopyOfAddress.view.xml` exists but is
  not routed), OR the class-name collision means whichever wins runs, and Address.view.xml
  gets the *older* validation logic. Behavior gap makes S9-A1 sharper: raw MERGE with
  missing/invalid address fields.

## `controller/PersInf.controller.js`  (13 KB)

- **Purpose:** personal-info form — name, INSZ (Belgian SSN), nationality, birth country/place,
  civil status, email, mother-tongue.
- **Reads:** `services.getPersonalInfo(account)` → `/PersInfos('0')`.
- **Writes:** `services.updatePersonalInfo(account, persInfModel.getData())` → MERGE
  `/PersInfos('0')`. Payload keys: `firstName`, `lastName`, `email`, `nationality1`,
  `nationality2`, `civilStatus`, `birthDate`, `birthCountry`, `birthPlace`, `sex`, `insz`,
  `motherLanguage`, plus checkbox-driven `chkRef/chkCand/chkFam/chkWork/chkStud/chkOther`
  and their `fam_input`/`dateSinceWhen`/`work_input`/`study_input`/`other_input` free-text
  inputs.
- **⚠ HTML sinks (2):** `handleRoepnaamInfoPress` and `onInfoGeslachtPress` each construct
  `new FormattedText().setHtmlText(s)` where `s = getModel("teksten").getData().roepNaamInfo`
  and `.geslachtInfo` respectively. **`teksten` = `LongTexts('E|<inst>|2020')`** —
  staff-controlled long-text. Not applicant-writable through the client. **Sweep-9 candidate
  S9-M3 (already listed):** does the server accept MERGE on `LongTexts`? If yes, an applicant
  could stage HTML into `roepNaamInfo`/`geslachtInfo` and this would render.
- **Client-only guards:** name case (`_checkHoofdletter`, `_checkKleineletter`,
  `_checkEersteLetterHoofdletter`), INSZ length + modulo-97 checksum (`_rrNumbercheck`), email
  regex, per-nationality/permit branches, `birthPlace !== "unknown"`. All can be bypassed via
  raw MERGE. **Sweep-9 candidate S9-P2:** raw MERGE bypassing the INSZ checksum + name rules.
- **Router:** `persinf/{account}/{instelling}` — `account` is used only to seed the model;
  the OData key is `PersInfos('0')` (self-alias).
- **Dev-leftover:** in `createMessageDialog` for the phone branch, references `Icon.ERROR` and
  `TextDirection.Inherit` but these aren't imported (should be `sap.ui.core.IconColor` /
  `sap.ui.core.TextDirection`). Runtime `ReferenceError` on phone-only submit-error path.

## `controller/Curriculum.controller.js`  (15 KB)

- **Purpose:** curriculum editor — secondary + higher education + interruption periods.
- **Reads:** `services.getCurriculum(account)` → `/Curriculums('0')`; `services.getInterrupts
  (account)` → `/Curriculums('0')/Interrupts`; `services.getHigherEduc(account)` →
  `/Curriculums('0')/HigherEducations?$filter=taal eq '<E|N>'`; `services.getYearsOfGrad()` →
  `/YearsOfGraduation`.
- **Writes:** `services.updateCurriculumBatch(account, curr, highers, interrupts)` — sets
  `deferredGroups:["curriculum"]`, then MERGE `/Curriculums('0')` + one MERGE per higher
  education row to `/HigherEducations('0')` and one per interruption to `/Interrupts('0')` —
  all in the same $batch group. **All row keys are `'0'`** even though multiple rows exist —
  the server must be discriminating by body payload's `higherEducationId` / `interruptedId`
  field. Interesting write shape: **collection-write via singleton key with body-encoded id**.
  This is worth an authz-write test: MERGE `/HigherEducations('0')` with body
  `higherEducationId="00001"` when your record doesn't have that id — does the server create,
  reject, or hit the wrong row? **Sweep-9 candidate S9-C1.**
- **Client-only guards:** date-order check on interruption periods, higher-ed dialog required
  fields, `editable` flag check on delete (old delete flow). **Sweep-9 candidate S9-C2:** MERGE
  a `higherEducation` with `editable:false` (server-marked) and see if it changes.
- **Router:** `curriculum/{account}/{instelling}` — `account` seeds model only.
- **Dev-leftover:** the catch-branch of `updateCurriculumBatch` calls `l.error(g)` where `l`
  isn't in scope (it's an import alias for `sap/m/MessageBox` from the deps array but not
  used elsewhere; the catch handler uses lowercase `l` while the higher-scope alias `l =
  sap/m/MessageBox` doesn't exist — the imports list is `l=sap/m/MessageBox,u=sap/m/Text`).
  Actually re-reading: `l` is `sap/m/MessageBox`. OK — no runtime bug there.

## `controller/CurriculumNew.controller.js`  (< 250 B)

- **Purpose:** empty stub. Extends Controller, declares a `heModel`. No methods.
- Registered under a route (`curriculumNew`, viewName `CurriculumNew`) but its controller does
  nothing — the view likely handles everything via the `Curriculum` controller or bindings.
- Dead file.

## `controller/Languages.controller.js`  (4.6 KB)

- **Purpose:** applicant's languages + language-knowledge grid.
- **Reads:** `services.getLanguage(account)` → `/Languages('0')`; `services.getLanguageKnow
  (account)` → `/Languages('0')/LanguageKnowledges`.
- **Writes:** `services.updateLangInfo(account, langModel.getData())` → MERGE
  `/Languages('0')`; `services.updateLangKnowBatch(account, knowledges)` — MERGE
  `/LanguageKnowledges('0')` per row via `$batch` group `"LanguageKnowledges"`. **Same
  singleton-key-with-body-id pattern as Curriculum**. See S9-C1.
- **Client-only guards:** skip-row-if-empty (`e[i].language==="" or JSON.stringify(e[i])==="{}"`).
- **Router:** `languages/{account}/{instelling}`.

## `controller/Scholarships.controller.js`  (1.7 KB — mostly stub)

- **Purpose:** scholarships editor. Currently non-functional — calls
  `services.getScholarships(account)` and `services.getPrevScholarships(account)` but **both
  `services.getScholarships` and `services.getPrevScholarships` are declared empty in
  `services.js` (no OData call inside).** So the read is a no-op; the model gets `undefined`.
- No save button flow shown. Dead-ish.
- **Router:** `scholarships/{account}/{instelling}`.

## `controller/ErrorHandler.js`  (2.2 KB)

- **Purpose:** monkey-patches `XMLHttpRequest.prototype.send` to intercept upload responses
  ≥400; hooks the OData model's `metadataFailed` and `requestFailed` events; renders errors as
  a StandardListItem list inside a Dialog.
- **HTML "sink" investigation:** `.innerHTML` appears in `a.getElementsByTagName("error")[0].
  childNodes[1].innerHTML` — but this is a **READ** on a DOMParser-parsed tree (extracts text
  from server XML). Not a write to a live-DOM element. Not a sink.
- The `_createMessageDialog(str)` splits on `<br>` and puts each line into `new
  StandardListItem({title:" ", description: lines[l]})`. `StandardListItem.description` is a
  text binding (SAPUI5 escapes on render). **Not a sink.**
- **Dev-leftover:** none.

## `fragment/AddDiscipline.fragment.js`  (< 1 KB)

- **Purpose:** dialog for the "add a discipline code" flow used from
  `ApplicationDetailOverview`.
- **Bindings:** `Input.value = addDisciplineModel>/disciplineCode`, `maxLength:255`.
- Fires `handleAddDisciplineDialogConfirm` on OK → controller does the actual server call.
- No sinks, no OData.

## `fragment/AddKeyword.fragment.js`  (< 1 KB)

- Same shape as AddDiscipline — dialog with one `Input(value = addKeywordModel>/trefwoord,
  maxLength:255)`. No sinks.

## `model/Formatter.js`  (8.4 KB — hardcoded strings galore)

- **Purpose:** ~30 pure functions used as `formatter:` in view bindings for status text,
  incomplete/complete decoration, hardcoded HTML disclaimers (submit + payment), status-based
  visibility.
- **Hardcoded `<br>`-and-`<a href=…>` HTML** in `submitDisclaimer()` and `paymentDisclaimer()`
  — returns hardcoded EN and NL strings with `<br>` line breaks and two hardcoded
  `<a href="http://www.kuleuven.be/…">` links. These are typically rendered by
  `<FormattedText htmlText="{path/to/formatter-call}"/>` in views — that's a legitimate use of
  `htmlText`, source is hardcoded, no injection.
- **Status-code whitelists (client-only):**
  - `notSubmitted(code)` → true iff code in `{022,041,101,202}`.
  - `notSubmittedBegdaDopl(code)` → adds `209`.
  - `notSubmittedListMode(code)` → same as `notSubmitted` (returns `"Delete"`).
  - `followUpVisible(code)` → `{013,011,014,019,020,021,012,054,055,056,208}`.
  - `followUpQuestionVisible(code)` → `{013,011,014,019,020,021,012}`.
  - `followUpAdmLetterVisible(code)` → `{054,055,056,208}`.
  - `paymentVisible(app,flag)` → `flag && statusCode∈{022,041,101} && statuut∉{005,006,012,018,013}`.
  
  Each of these decides only *whether the UI is shown/enabled*; the actual server call is what
  matters. But taken together they define the client's model of "when this action is legal".
  **Sweep-9 candidates:** DELETE `/Applications('<id>')` when status is NOT one of
  `{022,041,101,202}` → same as S9-M2. MERGE followUp-* fields when status isn't in
  `followUpVisible` — the followUp-* fields include `followUpAdmLetter` which Sweep 1 already
  tested (403); the others (`followUpQuestion*`) weren't in Sweep 1.

## `model/models.js`  (< 200 B)

- **Purpose:** `createDeviceModel()` — returns a `JSONModel` wrapping `sap/ui/Device` in OneWay
  binding. Trivial.

## `utils/DiscCodeSearchServiceHelper.js`  (< 400 B)

- **Purpose:** thin wrapper that reads `/disciplineCodeSet?$filter=Code0 eq '<code>'` on the
  `DisciplineCodeSearchModel` — which is bound to the **out-of-Track-B `ZR_DISC_CODES_SRCH_SRV`
  dataSource** (`/esap/public/odata/sap/ZR_DISC_CODES_SRCH_SRV/`). Out-of-scope by the brief's
  §Scope — the `esap/public/*` path is expressly excluded.
- **Note:** the `esap/public/…` path suggests an *unauthenticated* endpoint. Worth flagging
  for a possible Track E without probing it now.

## `utils/DiscCodeValueHelpHelper.js`  (2.7 KB)

- **Purpose:** builds a SAPUI5 `ValueHelpDialog` populated by GET
  `/disciplineCodeSet` (same out-of-scope service) with `Field0 Contains <live-typed value>`
  filter. Table columns bind `Code0..Code3` and `Field0..Field3`.
- **All bindings are `Text.text` (escaped).** No HTML sinks.
- Out-of-scope for probing (same as above).
