# Track C — bundle-level aggregate

Aggregated over the 21 controllers + 5 utility JS + 2 fragment JS + `model/services.js` +
`model/Formatter.js` that live in `Component-preload.js`. All operations named below hit
`mainService` (`/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV`) unless flagged otherwise.

## 1. Full OData call inventory (definitive "what the client actually does")

### Reads

| EntitySet / path | Operation | Filters / expands | Called by |
|---|---|---|---|
| `/Applicants('0')` | READ (single) | — | `Main` (getApplicantData) |
| `/PersInfos('0')` | READ | — | `PersInf` |
| `/Applications` | READ (collection) | `$filter=institution eq '<inst>'` | `Main` (getApplicationsData) |
| `/Applications('<lang>|<id>')` | READ | — | `ApplicationDetail` (getApplication) |
| `/Applications('<id>')/SubmitChecks` | READ (nav) | — | `ApplicationDetail` (getSubmitCheck) |
| `/Applications('<id>')/Attachments('1')/$value` | READ (binary) | — | `ApplicationDetail` (PDF viewer, admission letter download) |
| `/Addresses(inAccountId='<account>',language='<lang>')` | READ | — | `Address` / `CopyOfAddress` |
| `/Curriculums('0')` | READ | — | `Curriculum` |
| `/Curriculums('0')/HigherEducations` | READ (nav) | `$filter=taal eq '<lang>'` | `Curriculum` (getHigherEduc) |
| `/Curriculums('0')/Interrupts` | READ (nav) | — | `Curriculum` (getInterrupts) |
| `/Languages('0')` | READ | — | `Languages` |
| `/Languages('0')/LanguageKnowledges` | READ (nav) | — | `Languages` (getLanguageKnow) |
| `/ApplicationStaySet('<id>')` | READ | — | `ApplicationStay` |
| `/ApplicantPhotos('0')` | READ | — | `Main._getPicture` |
| `/ApplicantPhotos('0')/$value` | GET (binary) | — | `Main._getPicture` (via `Image.setSrc`) |
| `/LongTexts('<lang>|<inst>|2020')` | READ | — | `Main.getTeksten` |
| `/LongTexts('<lang>|<inst>|<applicationId>')` | READ | — | `ApplicationDetail.getTekstenWithAdmCode` |
| `/OrganisationCustomisations('<inst>')` | READ | — | `Main.getCusto` |
| `/CommunicationSet(applicationId='<id>',action='ADM_START')` | READ | — | `Main.getCommunicatie` |
| `/YearsOfGraduation` | READ | — | `Curriculum` (getYearsOfGrad) |
| `/AcademicYears` | READ | `$filter=instelling eq '<inst>'` | `ApplicationNew.getAcYears` |
| `/States` | READ | `$filter=taal eq '<lang>' and country eq '<code>'` | `CopyOfAddress.getStates` |
| `/StateForCitySet('<postal>')` | READ | — | `ApplicationStay` (getRegionForPostalCode) |
| `/BlockSet` | READ | `$filter=instelling and status and acjaar and applicationCode` | `ApplicationDetail.getBlokken` |
| `/RubriekSet` | READ | `$filter=applicationCode and language` | `ApplicationDetail.getRubrieken` |
| `/DisciplineSet` | READ | `$filter=applicationId eq '<id>'` | `ApplicationDetail.getDisciplineCodes` |
| `/TrefwoordenSet` | READ | `$filter=applicationId eq '<id>'` | `ApplicationDetail.getTrefwoorden` |
| `/ModuleGroups` | READ | `$filter=programmeId and academicYear`, `$expand=toModuleGroupCombinations` | `ApplicationNew` / `ApplicationDetailOverview` |
| `/ModuleGroupCombinations` | READ | `$filter=programmeId and academicYear` | `ApplicationNew` / `ApplicationDetailOverview` |
| `/SpringFallSet` | READ | `$filter=programmeId and academicYear` | `ApplicationNew` / `ApplicationDetailOverview` |
| **`/disciplineCodeSet`** (out-of-scope service `ZR_DISC_CODES_SRCH_SRV`) | READ | `$filter=Code0 eq '<code>'` or `Field0 Contains '<x>'` | `utils/DiscCodeSearchServiceHelper` / `DiscCodeValueHelpHelper` |

### FunctionImports (GET)

| Import | Params | Called by |
|---|---|---|
| `/getSwitchOpenSearch` | none | `ApplicationNew._fetchSwitchOpenSearch` |
| `/showOptions` | `programmeId, academicYear, institution, status, moduleGroup` | `ApplicationNew`, `ApplicationDetailOverview` |
| `/showSpringFall` | `institution, status` | `ApplicationNew`, `ApplicationDetailOverview` |
| `/isPaymentDone` | `admCode, paymentId` | `ApplicationDetail` (only from the `paymentDone` route) |

### Writes

| Method | Path | Payload keys | Called by |
|---|---|---|---|
| POST | `/Applicants` | *(the whole Applicants entity — created only if `getApplicantData` → 404)* | `Main.createApplicant` |
| MERGE | `/Applicants('0')` | `voorkeurstaal`, `inAccountId` (+ echoed fields) | `Main.updateApplicant`, `Main.changeLanguage` |
| MERGE | `/PersInfos('0')` | `firstName, lastName, email, nationality1, nationality2, civilStatus, birthDate, birthCountry, birthPlace, sex, insz, motherLanguage, chkRef, chkCand, chkFam, chkWork, chkStud, chkOther, fam_input, dateSinceWhen, work_input, study_input, other_input` | `PersInf.onUpdatePress` |
| MERGE | `/Addresses(inAccountId='<account>',language='<lang>')` | `permanentAddress.{country,postalCode,city,street1,state}`, `currentAddress.{country,postalCode,city,street1,state}` (+ echoed) | `Address.onUpdatePress`, `CopyOfAddress.onUpdatePress` |
| MERGE | `/Applications('<id>')` (a.k.a. `insertApplication`) | see the full ApplicationNew payload in `03-controllers-analysis.md § ApplicationNew` | `Main._getApplicantData`, `ApplicationNew.onSavePress`, `ApplicationDetail.onLinePress` (`statusCode:"211"`), `ApplicationDetail.onLocationPress` (`statusCode:"210"`), `ApplicationDetailOverview.onSavePress` |
| DELETE | `/Applications('<id>')` | — | `Main._deleteAppl` (only if client thinks status ∈ `{022,041,101,202}`) |
| MERGE | `/ApplicationStaySet('<id>')` | `stayAddress.{country,postalCode,city,street1,houseNumber,state,telephone,box}`, `opKotJa, opKotNee, opKotJaMaar, opKotMisschien` | `ApplicationStay.onSavePress` |
| MERGE (batch) | `/Curriculums('0')` | curriculum fields | `Curriculum.onUpdatePress` (`$batch` group `"curriculum"`) |
| MERGE (batch) | `/HigherEducations('0')` × N | per-row `higherEducationId, country, startingYear, graduationYear, nameSchool, nameProgram, taalDiploma, degree, status, result, editable, infotype` | `Curriculum.onUpdatePress` (same batch) |
| MERGE (batch) | `/Interrupts('0')` × N | per-row `interruptedId, interruptedStart, interruptedEnd, interruptedReason, interruptedReasonOther` | `Curriculum.onUpdatePress` (same batch) |
| DELETE | `/HigherEducations('0')` | — | `services.deleteHigherEducation` (no controller currently invokes it) |
| MERGE | `/Languages('0')` | language-info fields | `Languages.onUpdatePressBatch → updateLangInfo` |
| MERGE (batch) | `/LanguageKnowledges('0')` × N | per-row `language, speaking, writing, reading, listening` | `Languages.onUpdatePressBatch → updateLangKnowBatch` |
| DELETE | `/LanguageKnowledges('0')` | — | `services.deleteLangKnow` (no controller currently invokes it) |
| MERGE (batch) | `/DisciplineSet(applicationId='<id>',key='<seq>')` × N | `disciplineCode, field, applicationId, key` | `ApplicationDetailOverview.onSavePress → updateDisciplineCodes` |
| MERGE (batch) | `/TrefwoordenSet(applicationId='<id>',key='<seq>')` × N | `trefwoord, applicationId, key` | `ApplicationDetailOverview.onSavePress → updateTrefwoorden` |
| POST (raw XHR) | `/ApplicantPhotos` | *(binary blob body)* + headers `x-csrf-token`, `Content-Type: <user-controlled>`, `slug: "ZCM_ADM027|<user-controlled-filename>"` | `Main.uploadBlob` (also via UploadSet in `_uploadPicture`) |
| PUT | `/ApplicantPhotos` (UploadSet upload flow) | file body | `Main._uploadPicture` (`uploadUrl` set on UploadSet) |

**Composite key patterns observed:**

- `LongTexts('<lang>|<inst>|<year-or-appId>')` — bar-separated.
- `Addresses(inAccountId='<x>',language='<Y>')` — 2-key.
- `CommunicationSet(applicationId='<x>',action='ADM_START')` — 2-key, action literal.
- `DisciplineSet(applicationId='<x>',key='<Y>')` — 2-key.
- `TrefwoordenSet(applicationId='<x>',key='<Y>')` — 2-key.

**Also relevant:** `services.js` calls `model.setUseBatch(true)`, so every write above is
funneled through `POST /$batch` (with a changeset holding the MERGE). Track B Sweep 2 & 9
already showed the server rejects the whole batch on any authz violation.

## 2. Sweep-9 candidates — testable client-only guards

Each row is a hypothesis: **the server should re-enforce this rule, and if it doesn't, an
applicant can bypass a client-side check.** These extend Track B's Sweep 1 field matrix.

| # | Guard (client-side) | Server-side action gated | Test to run |
|---|---|---|---|
| **S9-M2** | Delete button only shows / delete-call only fires if `statusCode ∈ {022,041,101,202}` (`Main.onDeleteApplication`, `Formatter.notSubmittedListMode`) | DELETE `/Applications('<id>')` | From A's session, MERGE own app's statusCode to something legal (Track B S1 says server rejects all priv-field MERGE — so this is already gated by field-authz). Then attempt DELETE — check if server accepts DELETE regardless of status. Existing Track B tools already have the harness. |
| **S9-D1** | `_rubriekenCompleet()` — MERGE statusCode `210` / `211` only if all mandatory rubrieks have `status===3` (`ApplicationDetail.onLine/onLocationPress`) | MERGE `Applications('<id>').statusCode = "210"` or `"211"` | Track B Sweep 1 tested `"211"` → 403. Add `"210"` (onLocationPress path, never tested). If server enforces write-authz uniformly on statusCode transitions, this too returns 403. |
| **S9-O1** | `_configureSaveButton` — Save button enabled only if any input has `getEditable()===true`; edit-ability comes from OData property flags (`ApplicationDetailOverview`) | MERGE `/Applications('<id>')` after submission, when server thinks the record is locked | Attempt a MERGE on `/Applications('<id>')` after `statusCode` has advanced past a "no more edits" threshold (server-defined). If server permits the MERGE despite the read-only property flag, it's a bypass. |
| **S9-P1** ⚠ HIGH | `ApplicationDetailPay.onPay` navigates to `application.appFeePayURL` — server-supplied but not on Sweep 1's tested priv-field list | MERGE `/Applications('<id>').appFeePayURL = 'http://attacker/'` | Add `appFeePayURL` to Sweep 1's priv-field MERGE matrix. If server accepts (204), it's a stored-open-redirect on own record (weak by itself, useful as phishing pretext or ATO chain). |
| **S9-P2** | `PersInf` client validates INSZ modulo-97, name-case rules, email regex, `birthPlace !== "unknown"` | MERGE `/PersInfos('0')` with invalid INSZ/blank required fields | Craft raw MERGE that bypasses each check individually and observe. If server accepts empty `firstName`/`lastName` or a broken INSZ, that's a data-integrity bug (not a security bug in classical sense, but violates the program's data trust boundary). |
| **S9-S1** | `ApplicationStay` client validates phone regex, address completeness | MERGE `/ApplicationStaySet('<id>')` with malformed phone | Raw MERGE with `stayAddress.telephone = "<img src=x onerror=alert(1)>"` — but Track B Sweep 7 already showed free-text sinks 403'd on the pattern used. Worth verifying `telephone` specifically. |
| **S9-A1** | `Address.controller` (current) validates search-control ValueState, BE country/street/city completeness, ICE email regex. `CopyOfAddress` (older) validates *none* of it | MERGE `/Addresses(...)` with invalid combos | Raw MERGE with mismatched `country`/`state` (e.g. `country=DE, state=<some-BE-state-code>`) — server should reject. |
| **S9-C1** ⚠ interesting | The `HigherEducations('0')`, `Interrupts('0')`, `LanguageKnowledges('0')` writes all target the *singleton* key `'0'` but the body carries a per-row id (`higherEducationId`, `interruptedId`, `language`); the server MUST demux by body-payload key | MERGE `/HigherEducations('0')` with body `higherEducationId="00099"` when your record has no such id | Two outcomes worth checking: (a) server CREATES a new row (implicit create-via-MERGE with an attacker-chosen id — can it collide with another applicant?); (b) server writes to *your* row 00099 that doesn't exist yet (creates), or refuses. If (a) crosses tenants, that's the crown-jewel. |
| **S9-C2** | `Curriculum.onDeleteItemOld` — deletes higher-ed row only if `editable===true` | DELETE via `services.deleteHigherEducation` (unused by controllers but declared in services) | Direct call: DELETE `/HigherEducations('0')` — see what the server does. Currently no client path triggers this, so no client-side observability from black-box. |
| **S9-M1** | `HtmlMenu` renders `menuItem.getProperty("text")` as `innerHTML` — if any menu item's text ever comes from OData model data an applicant/staff can influence, that's XSS-in-menu | any MERGE that ends up bound as a MenuItem text | Search XML views for `<Menu>` with data-bound items — see Track D (`04-views-analysis.md`). |
| **S9-M3** | `PersInf.handleRoepnaamInfoPress` / `onInfoGeslachtPress` and `Main.onPhotoUpload` call `FormattedText.setHtmlText(<teksten field>)` where `teksten` = `/LongTexts('<lang>|<inst>|2020')` — staff-populated | MERGE `/LongTexts('<lang>|<inst>|2020')` from an applicant session | Sweep 1's priv-field matrix didn't test LongTexts. Try MERGE from A's session with body `{roepNaamInfo:"<img src=x onerror=alert(1)>"}`. If accepted, HTML renders next time the popover opens. |

**Total: 11 fresh Sweep-9 candidates.** Prioritise **S9-P1** (appFeePayURL stored-redirect,
own-record), **S9-C1** (collection-write via singleton key — potential IDOR-by-body-id), and
**S9-M3** (LongTexts write path to reach the `setHtmlText` sinks).

## 3. Hidden endpoints — services referenced from code but not in `manifest.json → dataSources`

The manifest declares exactly two `dataSources`:
- `mainService` → `/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV` (in Track B scope).
- `ZR_DISC_CODES_SRCH_SRV` → `/esap/public/odata/sap/ZR_DISC_CODES_SRCH_SRV/` (out of scope
  per Track B/C — `esap/public/*`).

**Not in manifest but referenced by code:**

- **`/sap/bc/ui5_ui5/sap/ZS_UI5_LIBRARY`** — UI5 loader path registered in `Component.js` for
  the `be/kuleuven/utils` namespace (reused libraries: search controls used by `Address` and
  `ApplicationStay`). Serves JS assets, not OData. Widens the `ui5_ui5/` tree.
- **`/sap/bc/ui5_ui5/sap/zc_zoek_opl`** — UI5 loader path for `be/kuleuven/zc_zoek_opl` (a
  program-search UI referenced from `ApplicationNew`'s value-help fragment (`fragment/search`)
  and `ApplicationDetailOverview`).
- **`/sap/bc/ui5_ui5/sap/ZC_ZOEKHULP`** — UI5 loader path for `be/kuleuven/zc_zoekhulp`
  (help-search UI, similar).
- **`webwsd.aps.kuleuven.be/sap/bc/ui5_ui5/sap/zc_ad_appl_chat/index.html`** — cross-host UI5
  app for the applicant↔staff chat (`Main._goToApplicationChat`). String-rewritten to the
  caller's hostname tag (`wsd`→`wsp`/`wsq`) before navigation.
- **`webwsd.aps.kuleuven.be/sap/bc/ui5_ui5/sap/zc_oi_appl_<x>/index.html`** — cross-host UI5
  apps for follow-up flows (`ApplicationDetail.onPressListItem`) where `<x>` is set from a
  `rubrieklink` server-supplied field.
- **External `www.kuleuven.be`** — three hardcoded browser navigations
  (`/english/application-submitted`, `/english/request-for-registration-submitted`,
  `/english/registration-completed`) after successful submit.
- **`idp.kuleuven.be` / `idp.q.icts.kuleuven.be`** — logout redirects.

**All non-manifest endpoints are outside the Track B/C `zc_ad_appl` scope and NOT probed by
this analysis.** Filing them for future recon awareness. The `esap/public/*` service, in
particular, is *unauthenticated* by the path convention (`/esap/public/`) — worth a Track E
pass if opened up.

## 4. `CopyOfAddress.controller.js` vs `Address.controller.js` behavioral diff

Both files register the **same class name** `be.kuleuven.application.controller.Address` and
both call the identical server endpoint (`updateAddresses(account, model)` → MERGE
`/Addresses(inAccountId='<account>',language='<lang>')`). Whichever `sap.ui.define` runs last
overwrites the other. **What the "copy" is missing** (and therefore would let a raw MERGE
bypass, if it wins the load race):

| Check | `Address.controller.js` (new) | `CopyOfAddress.controller.js` (older) |
|---|---|---|
| Country/city/street ValueState pre-save | ✅ blocks save if any control not `Success` | ❌ reads raw model, PUTs anyway |
| ICE emergency-contact email regex (`_emailCheck`) | ✅ | ❌ (function absent) |
| Region visibility toggle on country change (`_countryChangedRegion`) | ✅ | ❌ |
| BE-specific street/city required | ✅ | ❌ (any country goes) |
| Reuse-library smart search controls (network-validated country/city/postal) | ✅ | ❌ (static JSON only) |
| Static-JSON country binding fallback | ❌ (uses smart control) | ✅ (has a latent typo: `"{natioLandEN}"` unbound) |

**Behavior in practice:** neither client-side check protects the server. Both flows end at the
same MERGE with the same payload. The **surface for Sweep-9-A1 doesn't depend on which
controller wins** — it depends on whether the server accepts a MERGE that would fail either
client's local rules. If the server does its own address validation, both are safe; if it
trusts the client, the "copy" removed protective checks that the "new" restored, and only
raw-MERGE bypasses matter.

## 5. Router URL-param handling — where each param flows

Route patterns from `manifest.json → sap.ui5.routing.routes`, with param sink flagged as
`OData-URL` (interpolated into an OData path/filter), `OData-body` (sent in a MERGE payload),
`UI-only` (populates a form/model with no server call), or `Reflected-in-DOM` (rendered to the
page — check escaping in Track D).

| Route | Params | Sink per param |
|---|---|---|
| `""` (main) | — | — |
| `persinf/{account}/{instelling}` | `account` → UI-only (model seed; OData key is `PersInfos('0')`); `instelling` → UI-only |
| `address/{account}/{instelling}` | `account` → **OData-URL** (in `/Addresses(inAccountId='<account>',...)`); `instelling` → UI-only |
| `languages/{account}/{instelling}` | `account` → UI-only (OData key is `Languages('0')`); `instelling` → UI-only |
| `curriculum/{account}/{instelling}` | `account` → UI-only (OData key `Curriculums('0')`); `instelling` → UI-only |
| `scholarships/{account}/{instelling}` | `account` → UI-only (services methods are stubs); `instelling` → UI-only |
| `applicationNew/{account}/{currentAcYear}/{instelling}` | `account` → OData-body (in the created `Applications('0')` payload as `applicationId:"0"`? — actually not directly used); `currentAcYear` → OData-body (`academicYear`); `instelling` → OData-body (`institution`, propagated to `showOptions`/`showSpringFall` FunctionImport params too) |
| `application/{applicationNumber}` | `applicationNumber` → Reflected-in-DOM (`Page.title` = `"title_appl_followup" + " " + <num>`), no OData |
| `applicationFinish/{applicationNumber}` | unused in controller |
| `applicationAttach/{applicationNumber}` | route defined but no controller code present in bundle; target `applicationAttach` → view `ApplicationAttachments` (also not in bundle) — **implies the manifest references a view file NOT shipped in Component-preload.js.** |
| `applicationDetail/{applicationNumber}/{statusCode}/{currentAcYear}/{instelling}` | all → UI seed; the `<lang>|<num>` OData key is built from the current UI language + `applicationNumber` → OData-URL |
| `applicationStay` | — |
| `applicationDetailOverview/{applicationNumber}` | UI-only in overview controller (component model has been set already) |
| `applicationDetailPay/{applicationNumber}` | UI-only (payment URL comes from server-side field) |
| `curriculumNew` | — |
| **`applicationDetail/{applicationNumber}/{statusCode}/{currentAcYear}/{instelling}/paymentDone/{payId}/{amount}/{currency}/{date}/{returncode}/{description}/{tekst}`** | `payId` → **OData-URL** (`isPaymentDone(paymentId=<payId>)`); `returncode` → captured then ignored; `tekst` → **Reflected via `MessageToast.show(a)`** (SAPUI5's MessageToast escapes; safe); `amount`, `currency`, `date`, `description` → **captured but never consumed by controller code** — may be bound in the view (see Track D). |
| `applicationDetail/{applicationNumber}/{instelling}/detailBack` | UI-only (route just marks `_fromBack=true`) |

**Findings from the router map:**
- **The `paymentDone/…` route is the widest attacker-controlled URL param surface** — 7
  params from a redirect. Only `payId` reaches an OData call; the others are captured and (per
  controller) either ignored or shown via safe wrappers. **Track D must verify no view bindings
  render `amount`/`currency`/`date`/`description` unescaped.**
- **`address/{account}/…`** — `account` is interpolated *directly* into the OData URL as
  `inAccountId='<account>'`. Track B's target-ID guard would already refuse a non-A/non-B id
  here, but the server-side self-substitution behavior for `Applicants('IN01051651')` (Sweep 4)
  suggests the server aliases the id to the caller's — worth an explicit re-check for
  `/Addresses` with a spoofed `inAccountId` from A's session.
- **`applicationAttach` route + `ApplicationAttachments` view referenced in `manifest.json →
  targets` but neither the view file nor a controller ship in the preload bundle.** Either the
  server lazy-loads them from a separate ui5_ui5/ path, or the route is dead. **This is
  worth verifying with one more GET to `/sap/bc/ui5_ui5/sap/zc_ad_appl/view/
  ApplicationAttachments.view.xml` and `/controller/ApplicationAttachments.controller.js` (both
  in-scope).**

## 6. Dev leftovers rolled up

- `ApplicationNew.controller.js`: `console.error("Function import getSwitchOpenSearch failed",t)`.
- `PersInf.controller.js`, `ApplicationStay.controller.js`: reference `Icon.ERROR` and
  `TextDirection.Inherit` in the phone-only error path without importing them (latent
  `ReferenceError`; only fires on mobile submit-error path).
- `ApplicationStay.controller.js`: class name typo `"be.kuleuven.application.controller.
  Application<stay"` (unescaped `<`).
- `Component.js` and every logout redirect passes `"_blank"` as a second arg to
  `window.location.replace` — silently ignored (`replace(url)` takes one arg).
- No `TODO`, `FIXME`, `HACK`, `XXX`, or `debugger` markers survived minification.

## 7. Comparison to Track A's earlier findings

Track A already documented most of the OData reads/writes from the 5 controllers it looked at
(`ApplicationDetail`, `ApplicationDetailPay`, `ApplicationFinish`, `ApplicationFollowUp`,
`services`). This bundle read confirms and extends:

- **New writable endpoints not yet in Sweep 1's priv-field matrix:** `appFeePayURL`,
  `LongTexts('<...>')`, `HigherEducations('0')`, `Interrupts('0')`, `LanguageKnowledges('0')`,
  `DisciplineSet(applicationId=,key=)`, `TrefwoordenSet(applicationId=,key=)`,
  `ApplicantPhotos` (raw XHR upload).
- **New FunctionImports not in Sweep 5:** none — Sweep 5's list of 4 matches (`isPaymentDone`,
  `showSpringFall`, `showOptions`, `getSwitchOpenSearch`) is complete.
- **New client-side guards** (11 candidates listed above) — the definitive list of "server
  had better re-check this."
- **New composite-key patterns** — collection-write-via-singleton-key with body-encoded id is
  the interesting authz shape for Sweep 9.

## Next step

Track D (views + i18n) is in `04-views-analysis.md` and `04-i18n-flags.md`. Look there for
which of the Sweep-9 candidates and reflected router params actually render — that determines
which are exploitable vs. which are theoretical write-fuzz targets.
