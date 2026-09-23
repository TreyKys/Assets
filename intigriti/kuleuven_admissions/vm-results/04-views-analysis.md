# Track D — XML view + fragment analysis

Static read of the 17 view XMLs + 5 fragment XMLs extracted in C.1 to
`vm-results/03-bundle/{view,fragment}/`. No live probes. Purpose: identify every
place client OData data reaches the DOM, whether the render path escapes or not,
which fields are server-side-editable-only (client shows read-only), and any
server-returned properties the UI never binds (over-exposure candidates).

Model aliases surfaced (from `Component.js` and controller `setModel(name)`):
`application`, `applicationStay`, `applicant`, `personalInfo`, `addressInfo`,
`curriculum`, `higher`, `higherNew`, `interrupt`, `interruptNew`, `langModel`,
`knowModel`, `scholarModel`, `prevScholarModel`, `submitCheck`, `followUp`,
`options`, `blokken`, `programOfStudyOptions`, `springFall`, `teksten`, `custo`,
`DisciplineModel`, `TrefwoordModel`.

## 1. Every HTML-render sink

Nine `htmlText=` bindings + four `MessageStrip enableFormattedText="true"
text="…"` bindings + one `<Link href=…>` — **all** point at the `teksten>` model
(`/LongTexts('<lang>|<inst>|<year-or-appId>')`), which is staff-authored content
not writable through the current client. The applicant-side XSS impact is
gated by **Sweep-9 candidate S9-M3** in `03-bundle-summary.md` — if the server
accepts a MERGE on `/LongTexts` from an applicant session, every one of these
bindings renders whatever the applicant staged.

| View | Sink type | Binding source (all in `teksten>` unless noted) |
|---|---|---|
| `Main.view.xml` | `FormattedText htmlText` | `/infoText` |
| `ApplicationDetail.view.xml` | `FormattedText htmlText` × 6 | `/statusOmschrijving`, `/submitVinkje`, `/followUpAdmLetter`, `/followUpQuestionnair`, `/onlineTekst`, `/locatieTitel` |
| `ApplicationDetail.view.xml` | **`Link href` + `target="_blank"`** | `/submitInfo` (⚠ `href` from server data; `target="_blank"` **without `rel="noopener noreferrer"`** ⇒ tabnapping risk if the URL is `javascript:` or attacker-controlled; SAPUI5 Link does NOT auto-strip javascript: URLs) |
| `ApplicationDetailPay.view.xml` | `FormattedText htmlText` | `/payDisclaimer` |
| `ApplicationStay.view.xml` | `FormattedText htmlText` | `/opKotInfo` |
| `ApplicationStay.view.xml` | `MessageStrip enableFormattedText="true" text` × 4 | `/opKotWel`, `/opKotNiet` (×2 each) — allows anchor/em/strong/br in the rendered text |
| **also** | — controller-side `setHtmlText` calls in `PersInf` and `Main`  | see `03-controllers-analysis.md § PersInf` and `§ Main.controller` |

The two `<Image src="./img/{custo>/imageLeft}">` / `imageRight` bindings in
`Main.view.xml` interpolate a server-supplied filename into a static
`./img/<name>` prefix — so a value like `../../../evil.svg` could path-traverse
inside the ui5_ui5/ tree; the prefix is `./img/` so the request stays under
`/sap/bc/ui5_ui5/sap/zc_ad_appl/webapp/img/` after path normalization unless
`custo>/imageLeft` returns a value with URL scheme (e.g. `http://evil/x.jpg` —
then the browser fetches from evil). SAP UI5 `Image.src` does not sanitize the
value beyond what the browser does with an `<img src>`. Whether `custo>/imageLeft`
is applicant-writable: it comes from `/OrganisationCustomisations('<inst>')`,
which Track B Sweep 1 didn't test-write on — **Sweep-9 candidate S9-V1** (add).
Because it's keyed by institution (not by applicant), a successful write would
be **cross-institution, not cross-applicant**, and any applicant browsing that
institution would see the modified image.

## 2. `editable=`/`visible=`/`enabled=` gates — server-driven read-only rendering

The three views that bind editable-state on inputs all read from a single flag
`applicant>/isEditable` (via expression binding `{= ${applicant>/isEditable} }`):

- `Address.view.xml` — every address input gates on `applicant>/isEditable`.
- `PersInf.view.xml` — every personal-info input gates on `applicant>/isEditable`.
  Applies to name, email, birthdate, birth country, birth place, gender, SSN,
  refugee/family/work/study/other checkboxes and their free-text inputs.
- `ApplicationDetailOverview.view.xml` — application inputs gate on TWO
  formatters: `{path: 'application>/statusCode', formatter: '.formatter.notSubmitted'}`
  (allows edit if status ∈ `{022,041,101,202}`) and
  `{path: '...', formatter: '.formatter.notSubmittedBegdaDopl'}` (adds `209`).
- `Curriculum.view.xml` — higher-ed rows gate on `curriculum>/editable` **and
  on the per-row `higher>editable` property from OData** (`HigherEducations`
  entity returns an `editable` boolean).

Track B Sweep 11 already tested MERGE on `applicant.isEditable` → 403 (server
rejects). If Sweep 11's finding is complete, this whole render-gate class is
correctly server-enforced. If the server *also* honors write-authz on the
`Applications`/`Curriculums` entity's implicit "read-only when status advanced"
rule (independent of the `isEditable` boolean), then editability holds.
Otherwise **S9-O1** applies.

## 3. Router URL-param → DOM flow

`ApplicationDetail`'s **paymentDone route** captures `payId, amount, currency,
date, returncode, description, tekst`. Of those:
- `payId` — goes into `isPaymentDone` FunctionImport call, never DOM.
- `tekst` — passed to `MessageToast.show(a)`. SAPUI5 `MessageToast.show(text,
  options?)` calls its internal `_setMessageDom` which sets `.innerText` (per
  UI5 source), so **`tekst` is HTML-escaped on render**. Safe as a text sink.
- `returncode` — captured to a local var, never read.
- `amount`, `currency`, `date`, `description` — captured in the controller but
  **never referenced anywhere else in the controller**. **Cross-checked against
  every view binding** with `path: 'route>…'` or `route>/…` or route-parameter
  reads — **none of the views bind these params.** The URL params are
  effectively dead-drops in the controller state. Not currently a DOM sink.
- `ApplicationFollowUp` binds `applicationNumber` into a title string
  concatenation, then `Page.setTitle(str)` — SAPUI5 Page title uses
  `.textContent` (safe).
- `Address`/`languages`/`curriculum`/`scholarships`/`persinf` routes all take
  `{account}` and `{instelling}` — used as OData filter/key values only or
  as model seeds. **`address/{account}/…` is the one route where `account` is
  interpolated directly into an OData URL**: `Addresses(inAccountId='<account>',
  language='<lang>')` — but Track B already showed the server self-substitutes
  the caller's own id even when a different applicant id is passed (Sweep 4
  finding on `Applicants('IN01051651')?$expand=…`).

**No unescaped router-param → DOM path found.**

## 4. Free-text sinks — bound to `Input`/`TextArea` value (bidirectional)

These are the fields where the applicant types a value that becomes an OData
write. Track B's Sweep 7 already probed the ones known from Track A's
controller read; this list is now complete.

| Model.field | View | Element | Server entity |
|---|---|---|---|
| `personalInfo>/additionalRemarks` | PersInf | `TextArea maxLength="0"` (0 = unlimited) | `PersInfos('0').additionalRemarks` |
| `personalInfo>/callName` | PersInf | `Input` | `PersInfos('0').callName` |
| `personalInfo>/familyReunionWith` | PersInf | `Input` | `PersInfos('0').familyReunionWith` |
| `personalInfo>/workingWhere` | PersInf | `Input` | `PersInfos('0').workingWhere` |
| `personalInfo>/studyingWhere` | PersInf | `Input` | `PersInfos('0').studyingWhere` |
| `personalInfo>/otherReasonSpecify` | PersInf | `Input` | `PersInfos('0').otherReasonSpecify` |
| `personalInfo>/birthPlace` | PersInf | `Input` | `PersInfos('0').birthPlace` |
| `personalInfo>/ssn` | PersInf | `Input type="Number"` | `PersInfos('0').insz` |
| `personalInfo>/email` | PersInf | `Input type="Email"` | `PersInfos('0').email` |
| `personalInfo>/lastName`, `/firstName` | PersInf | `Input` | `PersInfos('0').{lastName,firstName}` |
| `addressInfo>/additionalRemarks` | Address, CopyOfAddress | `Input` | `Addresses(...).additionalRemarks` |
| `addressInfo>/contPers*` (7 fields) | Address, CopyOfAddress | inputs | `Addresses(...).contPers*` (ICE contact) |
| `addressInfo>/permanentAddress/{street1,city,postalCode,houseNumber,box,state,country}` | Address, CopyOfAddress | inputs (address search controls) | `Addresses(...).permanentAddress.*` |
| `addressInfo>/currentAddress/{same}` | Address, CopyOfAddress | inputs | `Addresses(...).currentAddress.*` |
| `applicationStay>/stayAddress/{same + telephone,box}` | ApplicationStay | inputs | `ApplicationStaySet(...).stayAddress.*` |
| `application>/additionalremarks` | ApplicationNew, ApplicationDetailOverview | Input/TextArea | `Applications('X').additionalremarks` |
| `application>/doctSummaryEN`, `/doctSummaryNL`, `/doctKeywords`, `/doctFinancialInfo`, `/doctSpecialisation`, `/doctPartnerUniversity`, `/exchProgram`, `/exchHomeUniversity`, `/exchContactName`, `/intScholarSubject`, `/specSpecialisation`, `/infoAboutProgramOther`, `/exchProgramOther`, `/exchStudentTypeOther`, `/exchPurposeOther` | ApplicationNew, ApplicationDetailOverview | inputs | `Applications('X').*` |
| `curriculum>/additionalremarks`, `/eduNameSchool`, `/eduNameProgram`, `/eduFinalGrade` | Curriculum | inputs | `Curriculums('0').*` |
| `higherNew>/{nameSchool,nameProgram,result,taalDiploma,degree}` | DialogAddHigher | inputs | inserts into `HigherEducations('0')` via batch |
| `interruptNew>/interruptedReasonOther` | DialogAddInterrupt | Input | inserts into `Interrupts('0')` via batch |
| `addDisciplineModel>/disciplineCode` | AddDiscipline fragment | Input | goes into `DisciplineSet(...)` MERGE (batch) |
| `addKeywordModel>/trefwoord` | AddKeyword fragment | Input | goes into `TrefwoordenSet(...)` MERGE (batch) |
| `langModel>/additionalRemarks` | Languages | TextArea | `Languages('0').additionalRemarks` |
| `scholarModel>/additionalRemarks` | Scholarships | TextArea | `Scholarships` (stub — service method empty) |

**Track B's Sweep 7 covered:** `PersInfos.{additionalRemarks, otherReasonSpecify,
familyReunionWith, workingWhere, studyingWhere, birthPlace, motherLanguage}`,
`Applications.{additionalremarks, doctSummaryEN, doctSummaryNL, doctKeywords,
doctFinancialInfo, doctSpecialisation, doctPartnerUniversity, exchProgram,
exchHomeUniversity, exchContactName, intScholarSubject, specSpecialisation,
infoAboutProgramOther, exchProgramOther, exchStudentTypeOther, exchPurposeOther}`,
`Addresses.{street1, city}`. All 403 or filtered.

**Fields the view binds that Sweep 7 did NOT test:** `Applications.
{doctCoSupervisor, doctPhdLanguage, doctAanstelDossierProject}` (from
ApplicationDetailOverview), `applicationStay/stayAddress.{telephone, box}`,
`addressInfo.contPers{FirstName, LastName, Email, Telephone, Relation}`,
`addressInfo/{additionalRemarks}`, `Applications.additionalremarks (via new
view path)`, `Curriculums.{eduNameSchool, eduNameProgram, additionalremarks,
eduFinalGrade}`, `HigherEducations.{nameSchool, nameProgram, result, degree,
taalDiploma}`, `Interrupts.interruptedReasonOther`, `DisciplineSet.
disciplineCode`, `TrefwoordenSet.trefwoord`, `Languages.additionalRemarks`.

**Sweep-9 candidate S9-V2** (new): re-run the stored-XSS harness against those
untested free-text sinks. If any accept `<img src=x onerror=…>` and reflect via
one of the `htmlText`/`enableFormattedText`/`Link href` sinks in §1, that's an
end-to-end stored-XSS chain — but §1's sinks all read `teksten>` (LongTexts),
so no direct chain unless the untested free-text values also feed a `teksten>`
render. They don't; the free-text values render only via `text=` (escaped) or
`value=` on an `Input` (escaped attribute serialization).

## 5. Over-exposure candidates (fields returned but never UI-bound)

Track B Sweep 8's `$select=*` results: **Applications = 76 fields**,
**PersInfos = 34 fields**. Cross-referenced against the view bindings:

- `application>` view-bound fields (union of ApplicationNew +
  ApplicationDetailOverview + ApplicationDetail): **~50 unique field names**
  (see `03-bundle-summary.md § 1 for the write inventory`).
- `personalInfo>` view-bound: **27 fields** (from PersInf.view.xml).

**Unbound fields (server returns but UI never renders / edits):**

- **`application`**: ~26 unbound fields including — per Track A's read of the
  entity — `statusCode` (bound only in formatter expressions, never as a
  writable UI field), `caseAdmin`, `submitVinkje`, `isAppFeePayed`,
  `isPropositionAccepted`, `followUpAdmLetter`, `moduleGroup` (bound but only
  as a hidden model property computed from combos), `guid`, `institution`,
  `program`, `academicYear`, `appFeePayURL`. These match the Sweep-1 priv-field
  set. **`appFeePayURL` is the only one that's NOT in Sweep 1's tested list
  and IS bound in the client** (via `ApplicationDetailPay.onPay:
  window.location.replace(appFeePayURL)`) — **already flagged as S9-P1**.
- **`personalInfo`**: ~7 unbound fields including `polRefDate` (bound in
  DatePicker but hidden behind switch), `applicationId` (never shown), any
  applicant-key ids returned in `__metadata` (safe by design).
- **`addresses`**: `contactPerson*` and `additionalRemarks` are bound; the raw
  `country_txt` display fields are bound. Nothing obviously unbound of
  security interest.

No new priv-field candidates from this pass beyond `appFeePayURL` — Track B's
Sweep 1 covered the class exhaustively.

## 6. Formatter references

Every `formatter="…"` reference in views resolves to `model/Formatter.js`. Full
list of formatter callers used in views:

- `.formatter.statusTekst`, `.formatter.statusTekst1` — status-code → localized
  text lookup. Purely local, no HTML.
- `.formatter.infoTekst`, `.formatter.infoStatusTekst`, `.formatter.getStatusInfoTekst`,
  `.formatter.getStatusInfo` — Success/Error/None state formatters.
- `.formatter.diplomaTaalTekst`, `.formatter.degreeTekst`, `.formatter.attTekst`,
  `.formatter.acJaarTekst` — reference-model lookups.
- `.formatter.notSubmitted`, `.formatter.notSubmittedBegdaDopl`,
  `.formatter.notSubmittedListMode`, `.formatter.followUpVisible`,
  `.formatter.followUpQuestionVisible`, `.formatter.followUpAdmLetterVisible`,
  `.formatter.paymentVisible`, `.formatter.followUpVisible`,
  `.formatter.saveButtonText`, `.formatter.sectionsComplete`, `.formatter.optionVisible`
  — status-based visibility/edit gates. All local logic; each is a **Sweep-9
  hypothesis** because they define "the client's view of which action is
  allowed" and, per the brief, the server MUST re-enforce.
- `.formatter.submitDisclaimer`, `.formatter.paymentDisclaimer` — return
  hardcoded EN/NL HTML strings (containing `<br>` and two hardcoded `<a href=
  "http://www.kuleuven.be/…">` links); rendered by `FormattedText htmlText`.
  Source is hardcoded, not injectable.
- `.formatter.interruptedReasonText` — local reason-code → text lookup. No HTML.

**No formatter strips or allows HTML on server-supplied data** except the two
disclaimers with hardcoded content.

## 7. `CopyOfAddress.view.xml` diff against `Address.view.xml`

**Both views bind the same 29 (Address) / 28 (CopyOfAddress) fields — the
one-field diff is that `Address.view.xml` binds `permanentAddress/state` and
`currentAddress/state` via smart `kul:AddressSearchState` reuse-library
controls, while `CopyOfAddress.view.xml` binds those state fields via a plain
`Select` populated from the static `statesPerAd>`/`statesCurAd>` model.**

Other view-layer deltas:

| Aspect | `Address.view.xml` | `CopyOfAddress.view.xml` |
|---|---|---|
| Country/city/street/state inputs | `<kul:AddressSearchCountry>`, `<kul:AddressSearchCity>`, `<kul:AddressSearchStreet>`, `<kul:AddressSearchState>` (reuse-library controls that talk to `ZS_UI5_LIBRARY`; do server-side validation of country/city/postal) | plain `<Input>`+`<Select>` bound to `statesPerAd>` / `natio>` static JSON, no server-side validation |
| Regions visibility toggle | wired via reuse-library event `regionsExistForCountry` | absent |
| ICE contact email regex feedback | `Input type="Email"` triggers browser-level HTML5 email hint | plain `Input`, no type |
| Edit-mode binding | `editable="{= ${applicant>/isEditable}}"` on every field | same |

**Practical impact:** both flows call the same server endpoint
(`updateAddresses(account, model)` → MERGE `/Addresses(...)`), so any real
authz/validation must live server-side. The client-side gap between the two
means the *raw MERGE payload could be more diverse* when driven from the copy
(no ValueState pre-filter) — a Sweep-9-A1 raw MERGE test doesn't need to run
through either controller.

The unrouted status of `CopyOfAddress.view.xml`: the manifest's `"address"`
target uses `viewName:"Address"`. There is **no route in the manifest that
targets `CopyOfAddress`** — grep `manifest.json` for `CopyOfAddress` returns
zero hits. So the view + controller pair ship in the preload bundle but are
never instantiated by the router. **Dead code** — but the shipped source still
reveals what the intended behavior once was.

## 8. Missing view: `ApplicationAttachments.view.xml`

Manifest declares:
```
routes: {name:"applicationAttach", pattern:"applicationAttach/{applicationNumber}", target:"applicationAttach"}
targets: {applicationAttach: {viewName:"ApplicationAttachments", viewId:"ApplicationAttachments", controlAggregation:"pages"}}
```

Neither `view/ApplicationAttachments.view.xml` nor `controller/
ApplicationAttachments.controller.js` ships in the preload. Two possibilities:
1. **Lazy-loaded from a separate ui5_ui5/ path** — SAPUI5 falls back to fetching
   the file on-demand from the same webapp root (`/sap/bc/ui5_ui5/sap/zc_ad_appl/
   view/ApplicationAttachments.view.xml`). This is in-scope for Track C/D and
   is the natural next fetch, but the current session has network connectivity
   trouble to that host (curl to `webwsp.aps.kuleuven.be` timed out at
   attempt time; DNS resolves but TCP connect fails).
2. **Dead route** — the manifest was pruned by a bundler; navigating to
   `#applicationAttach/…` would 404.

Either way, this is a documented **gap** worth chasing when network access
returns — the attachments-upload flow is where Track A already noted the
`slug` header manipulation risk.

## 9. Client-only-guarded server calls to test

Consolidating from all views:

- Status-driven visibility that gates a server call: `submitButton` visibility
  ← `.formatter.notSubmitted(statusCode)`; delete-mode of the applications
  list ← `.formatter.notSubmittedListMode(statusCode)`. **Sweep 9 targets:**
  send `POST/DELETE /Applications('<id>')` at a status the client doesn't allow.
- Field editability ← `applicant>/isEditable` (Track B Sweep 11 already 403'd
  MERGE on that flag; server-enforced).
- Rubriek completeness gate on `onLinePress/onLocationPress` in the controller
  (already listed as S9-D1).
- Payment button enabled ← disclaimer checkbox; **redirect target is
  `application>/appFeePayURL`** → S9-P1.

## 10. Non-manifest URLs reached from the view layer

- `<Image src="./img/{custo>/imageLeft}">` and `imageRight` — relative
  path under `webapp/img/`. Filename comes from `OrganisationCustomisations`.
- `Link href="{teksten>/submitInfo}"` — arbitrary URL from `LongTexts`.
- No `<a href="http://…"` hardcoded in view templates (only in
  Formatter.js's disclaimer HTML).
- The reuse-library controls `<kul:*>` come from `be/kuleuven/utils` →
  `/sap/bc/ui5_ui5/sap/ZS_UI5_LIBRARY` (already noted in `03-bundle-summary.md
  § 3`).

## 11. Summary — new Sweep-9-etc. candidates from Track D

| # | Origin | Test |
|---|---|---|
| **S9-V1** (new) | Track D §1 — `<Image src="./img/{custo>/imageLeft}">` | Attempt MERGE on `/OrganisationCustomisations('<inst>')` from an applicant session with `imageLeft` set to `../evil.svg` and to `javascript:alert(1)`. If accepted, cross-institution image swap or javascript-URI in an `<img src>` (browsers don't fire `javascript:` for `<img>` — but data-URIs to malicious SVGs would). |
| **S9-V2** (new) | Track D §4 — untested free-text sinks (contact-person fields, stay address telephone/box, curriculum eduNameSchool/eduNameProgram, higher-ed nameSchool/nameProgram/result, dialog inputs) | Extend Sweep 7's XSS-payload MERGE matrix. Same shape as Track B's existing harness. |
| S9-D1..S9-M3 | already in `03-bundle-summary.md § 2` | — |

No new sinks/routes/params beyond what Track C flagged; Track D confirms
which of Track C's hypotheses have a *view-layer* render path (the `htmlText`
class does; the free-text write class does not, since Input/TextArea render
via escaped `value=`).
