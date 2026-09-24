# Track E — Sweep 14.2 — `$metadata` over-exposure enumeration

**Verdict: clean-review artifact — 33 entities / 372 properties enumerated;
over-exposure candidates flagged for future write-fuzz tuning; nothing
directly reportable as a security finding.**

Sweep 14.2 was the offline half of Sweep 14 (14.1 = live GETs on
lazy-loaded UI5 assets; deferred). This half parses the OData
`$metadata` document (54 KB, captured live in this session) and
cross-references every entity's `<Property>` list against every view /
fragment / controller binding in the extracted bundle.

**Run:** 2026-09-24. **Method:** offline parse of
`vm-results/03-bundle/metadata.xml` (fetched live once at
`2026-09-24 21:23 UTC`, saved for reuse). **Non-safe network requests:** 0.

## 1. Service shape

- **33 EntityTypes.** All under service `ZC_AD_APPLICANT_SRV`.
- **372 properties total** across those entities.
- Client bundle binds roughly **~180** distinct property names across all
  UI models (many entities share property names — `applicationId`, `key`,
  etc. — so this isn't a strict subtraction).

Full parsed entity/property listing is saved at
`vm-results/03-bundle/entities.json` (structured JSON, also includes the
alias-binding index).

## 2. Over-exposure per entity — ranked

Property is "unbound" when its name is not referenced anywhere in the
extracted bundle's view/fragment/controller tree via the entity's client
model alias. Many "unbound" fields ARE bound via patterns the regex here
doesn't catch (`getOwnerComponent().getModel("<alias>").getData().<field>`,
computed bindings, `path:'<alias>>/<nested>'`), so this table over-counts
by ~20-30%. Numbers below are **upper bounds on the over-exposure
surface**, useful as pointers to which entities are worth a manual review.

| Entity | Aliases | Total | Bound | Unbound (upper bound) |
|---|---|---|---|---|
| `LongText` | `teksten` | 66 | 15 | **51** |
| `OrganisationCustomisation` | `custo` | 19 | 7 | **12** |
| `Application` | `application` | 66 | 56 | **10** |
| `HigherEducation` | `higher`, `higherNew` | 21 | 11 | **10** |
| `ModuleGroupCombination` | `programOfStudyOptions` | 10 | 0 | **10** |
| `Curriculum` | `curriculum` | 19 | 10 | **9** |
| `Rubriek` | `rubrieken` | 9 | 0 | **9** |
| `Applicant` | `applicant` | 16 | 8 | **8** |
| `Block` | `blokken` | 8 | 0 | **8** |
| `Attachment` | `attachments` | 7 | 0 | **7** |
| `AttachmentType` | `attachmentType` | 6 | 0 | **6** |
| `ApplicantPhoto` | `applicantPhoto` | 5 | 0 | **5** |
| `ModuleGroup` | `programOfStudyOptions` | 6 | 2 | **4** |
| `SpringFall` | `springFall` | 4 | 0 | **4** |
| `Communication` | `applicationCommunication` | 3 | 1 | **2** |
| `Discipline` | `DisciplineModel`, `addDisciplineModel` | 4 | 2 | **2** |
| `PersInfo` | `personalInfo` | 29 | 27 | **2** |
| `Trefwoorden` | `TrefwoordModel`, `addKeywordModel` | 3 | 1 | **2** |
| `Address` | `addressInfo` | 11 | 10 | 1 |
| `ApplicationStay` | `applicationStay` | 6 | 5 | 1 |
| others | — | — | — | 0-1 |

## 3. Highlights — over-exposed properties by category

### Application (10 unbound) — priv/admin fields

- `caseAdmin` — staff-admin identity for this application (Track B tested)
- `isPropositionAccepted` — decision-tampering target (Track B tested)
- `appFeePayURL` — payment-gateway URL that `ApplicationDetailPay.onPay`
  navigates to. Reachable from `getOwnerComponent().getModel("application")
  .getData().appFeePayURL` in that controller — the "unbound" here is a
  regex-false-positive. Sweep 11 targets this field.
- `status` — separate property from `statusCode`. Both exist; the UI uses
  only `statusCode`. `status` may be a lower-level SAP workflow flag.
- `guid` — 32-char application GUID (Sweep 1 tested with MERGE, got 403).
- `moduleGroup` — bound in controller code (compound-set selection); false
  positive here.
- `doctSpecialisation`, `doctDisciplineCode`, `doctKeywords`,
  `doctFinancialInfo` — doctoral-flow fields that may or may not be bound
  in the doctoral view branches. Sweep 7 tested these as XSS sinks
  (returned 403 or filter-rejected).

### LongText (51 unbound) — half of its properties never appear in the UI

The client only binds ~15 of the 66 LongText properties (the ones Track D
found `htmlText`/`FormattedText`/`Link href` sinks for). The other 51
include:

- **Status narratives:** `status101`..`status907` (34 fields — one per
  workflow status code). Sweep 9 tried MERGE on some; entity is truly
  read-only.
- **Privacy consent copy:** `privacyInfo`, `privacyAlumni`,
  `privacyZoekRobot`, `privacyAlma`, `privacyStudKringFoto`,
  `privacyStudKringAct`, `privacyStudentenKring`, `privacyTewerkstelling`,
  `privacyVacature`. The KUL admissions app has a privacy-consent flow the
  current bundle doesn't ship a view for.
- **Payment info:** `payInfo1`, `payInfo2` — probably shown at a
  fee-payment step the bundle doesn't include.
- **Info blurbs:** `locatieTekst`, `followUpInfo`, `fotoTekst`,
  `geslachtInfo`, `roepNaamInfo`, `functieBeperking`. Some of these ARE
  bound in the PersInf controller's `setHtmlText` calls (Track D §1) —
  regex false positives.

None are directly exploitable (entity is server-side read-only), but the
51-unbound count means **half the LongText content is prepared for UI
flows the current preload doesn't ship**. Fetching those flows (Sweep 14.1
= `ApplicationAttachments`, doctoral supervisor selection, privacy consent)
would reveal additional htmlText bindings against LongText properties we
haven't seen render yet.

### OrganisationCustomisation (12 unbound) — institution-wide policy switches

- **Per-privacy-tab visibility:** `showPrivAlumni`, `showPrivTewerk`,
  `showPrivStudKring`, `showPrivStudRest`, `showPrivZoekRobot`,
  `showPrivStudKringFoto`, `showPrivStudKringAct`, `showPrivVacature`.
  Server-side switches for showing/hiding each privacy-consent option.
- **`showExchInfo`, `showPaymentTab`** — server toggles for the exchange-
  info and payment tabs.
- **`photoEditable`** — whether the applicant can upload their own photo.
- **`chatPageEnabled`** — bound in controller (`applicationCommunication>
  /chatButtonVisible`); false positive.
- **`imageCenter`** — a 3rd image alongside `imageLeft`/`imageRight`
  bound in `Main.view`. If applicant can MERGE this (Sweep 12 candidate
  S9-V1), it renders across all applicants at the same institution.

### Attachment (7 unbound) — the attachment flow's entity

- `attachmentId`, `docType`, `fileName`, `fileSize`, `mimetype`,
  `uploadDateTime`, `uploadedBy` — the whole `Attachment` entity is
  unbound in the current preload. Consistent with F2.4 (`ApplicationAttachments`
  view is lazy-loaded and not in the preload). **The `mimetype` and
  `fileName` fields are the closest analog to the Bank Van Breda XSS
  finding** — client-controlled attachment metadata that could reflect
  into a staff-side review UI. Live probing deferred to F2.4/F2.1.

### ApplicantPhoto (5 unbound) — the photo upload entity

- `inAccountId` — applicant identity on the photo. `GET
  /ApplicantPhotos('<B's account>')/\$value` from A's session is exactly
  what F2.3 asks (does the URL key alias to caller or literalize).
- `docType`, `mimetype`, `fiileSize` (server-side typo!), `fileName` —
  the photo metadata. If `mimetype` reflects into the response's
  `Content-Type` header on `\$value` read, and A can MERGE it via any
  path, this is the F2.1 Content-Type-reflection stored-XSS vector.

### Rubriek (9 unbound) — every field, no client model directly binds

The `rubrieken` client model IS populated by `services.getRubrieken(id,
lang)`, and the controller reads properties like `rubriekId`, `status`,
`description`, `text`, `icon`, `rubrieklink` via `getData()` calls. All
of these are regex false positives. Not real over-exposure.

## 4. Entities with NO client model alias (server-only surface)

None of the following EntityTypes are populated into any client model:

- `AcademicYear`, `Address` (via `Addresses` set — the `addressInfo`
  alias IS used), `ApplicationFollowUp`, `LongTextApplication`, `Option`,
  `PreviousScholarship`, `Scholarship`, `State`, `StateForCity`,
  `YearOfGraduation`, `Language`.

Most of these are look-up tables (states, years, options, languages) that
the app reads to populate dropdowns but doesn't keep in a stateful model.
`Language` is odd — the client has a `lang` model with a `Languages`
array, so this is a naming mismatch not a real over-exposure gap.

## 5. Follow-ups that emerge from this pass

1. **F2.1/F2.3 (ApplicantPhoto MIME + cross-tenant read)** — the
   `ApplicantPhoto` entity's server-returned `mimetype` field is the
   closest surface to the Bank Van Breda XSS finding, and cross-tenant
   URL-key testing (F2.3) is small (~2 GETs).
2. **F2.4 (ApplicationAttachments lazy-load fetch)** — pulling the
   view + controller from the ui5_ui5 tree would unblock probing the
   Attachment entity's 7 unbound fields (attacker-controlled
   `fileName` + `mimetype`).
3. **Sweep 12 (OrganisationCustomisations MERGE)** — 12 unbound switch
   fields including `showPaymentTab` and `photoEditable` are worth
   probing against write-authz on this institution-wide entity. Track E
   S9-V1 was already queued for this.
4. **F1.4 retry not needed** — LongText's 51 unbound properties don't
   change the F1.4 outcome (entity is server-side read-only in every
   path we can reach; batch dispatch confirmed 501-both-paths).

## Rows

`03-bundle/metadata.xml` (54 KB) and `03-bundle/entities.json`
(structured) are the deliverables for this sub-sweep.
