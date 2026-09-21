# KU Leuven Admissions — OData service map + baseline (from authenticated HAR)

Derived from an authenticated HAR capture of the live Admissions app (test account A). No session
tokens recorded here. All data below is from test account A (fake applicant data).

## Hosts & services (in scope: `webwsp.aps.kuleuven.be`)
- **App (SAPUI5):** `/sap/bc/ui5_ui5/sap/zc_ad_appl/index.html` (SSO via `idp.kuleuven.be`, `instelling=50000050`)
- **Primary OData:** `/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/` (`sap-client=200`, `sap-language=EN`)
- **Also observed:**
  - `/esap/public/odata/sap/ZA_ADDRESS_SRV/` — note the **`/public/`** path; some `$batch` returned **403**, others **202** (investigate authz/CSRF difference)
  - `/esap/public/odata/sap/ZR_DISC_CODES_SRCH_SRV/` (discipline-code search)
  - `/sap/opu/odata/sap/ZC_ZOEKHULP_SRV/` (search help)
- App talks almost entirely via **`$batch` POST** (multipart), but direct `GET` works (metadata GET = 200).

## Baseline identifiers (test account A — our own)
- **Applicant ID: `IN01051619`** (enumerable; program's own example was `IN00824795`)
- **Application ID: `000000503432`** (enumerable)
- Self-alias: the app requests `Applicants('0')`, `PersInfos('0')`, `Applications('0')`,
  `ApplicantPhotos('0')` — server resolves `'0'` → the logged-in user. Records are **also** addressable
  by real key (`Applicants('IN01051619')`, `PersInfos('IN01051619')` seen in responses).

## EntitySets (33) — ZC_AD_APPLICANT_SRV
Applicants, PersInfos, Addresses, Curriculums, HigherEducations, Languages, LanguageKnowledges,
Scholarships, PreviousScholarships, Applications, **Attachments**, AttachmentTypes, ApplicantPhotos,
SubmitChecks, ApplicationStaySet, ApplicationFollowUps, CommunicationSet, LongTexts, LongTextApplSet,
Options, OrganisationCustomisations, RubriekSet, TrefwoordenSet, SpringFallSet, StateForCitySet,
States, YearsOfGraduation, Interrupts, AcademicYears, ModuleGroupCombinations, ModuleGroups, BlockSet,
DisciplineSet.

## FunctionImports (4)
`showSpringFall`, `showOptions`, **`isPaymentDone`**, `getSwitchOpenSearch`.

## Sensitive properties observed (attack payoff)
- **PII:** `ssn`, `birthDate`, `birthPlace`, `birthCountry`, `nationality(1/2)`, `email`,
  `permTelephone`, **`functieBeperking`** (disability), `civilStatus`, `hasBelgianResPerm`, `familyReunionWith`
- **Payment / fee:** `isAppFeePayed`, `appFeePayURL`, `showPaymentTab`, `payDisclaimer`, `payInfo1/2`
- **Decision / status workflow:** `statusCode`, `transition`, `isPropositionAccepted`, `isEditable`,
  `status101..217`, `status901..907`, **`followUpAdmLetter`** (admission letter), `caseAdmin`
- **Submission / eligibility gating:** `submitVinkje`, `isPersInfoCompleted`, `isAddressCompleted`,
  `isCurriculumCompleted`, `isLanguageCompleted`, `isScholarshipCompleted`, `SubmitChecks`
- **Internal account IDs (binding attacks):** `bAccountId`, `inAccountId`, `stAccountId`, `uAccountId`, `guid`, `studentNummer`
- **Free-text (stored-XSS candidates → staff view):** `additionalRemarks`, `additionalremarks`,
  `doctSummaryEN`, `doctSummaryNL`, `doctKeywords`, `infoText`, `otherReasonSpecify`

## Prioritized test plan (map → threat model)
Ordered by undeniability × reachability. **Ethics: use account B as the victim, never a random
adjacent ID (those are real applicants). Stop at first minimal proof; never harvest.**

1. **[CRITICAL] Horizontal IDOR — cross-applicant read.** From A's session:
   `GET .../Applicants('<B_ID>')`, `PersInfos('<B_ID>')`, `Applications('<B_APPID>')`,
   `Attachments(...)` (B's uploaded docs), `ApplicantPhotos('<B_ID>')`,
   `CommunicationSet(applicationId='<B_APPID>',...)`. If A reads B's `ssn`/PII/documents → Critical.
   (Need B's IDs first — capture from account B's own `Applicants('0')`.)
2. **[HIGH/CRITICAL] Fee-payment bypass.** App uses `MERGE Applications('0')`. Test writing
   `isAppFeePayed=true` (and check `isPaymentDone` FunctionImport) on your OWN application without
   paying → if the server trusts it, that's fee bypass / data modification. Own account only.
3. **[CRITICAL] Self-admission / status write.** Test `MERGE` on your own Applications/Applicants
   writing `statusCode`/`transition`/`isPropositionAccepted`/`followUpAdmLetter` — does the server
   let an applicant move their own decision state or trigger an admission letter?
4. **[HIGH] Submission / eligibility gating bypass.** Write `submitVinkje` / `isXxxCompleted` to submit
   without required data, or reach a programme you're not eligible for (`SubmitChecks`).
5. **[HIGH] Cross-applicant write (IDOR on MERGE).** `MERGE Applications('<B_APPID>')` from A → can A
   modify B's application? Use B (own account) as victim only.
6. **[MEDIUM/HIGH] Stored XSS into staff view.** Put HTML/JS in `additionalRemarks`/`doctSummaryEN`;
   determine if it renders unescaped anywhere a *different* user (staff/reviewer) sees it. Self-only = OOS.
7. **[INVESTIGATE] `/esap/public/odata/ZA_ADDRESS_SRV` 403-vs-202 `$batch`.** Why do some batches 403?
   CSRF token missing vs present, or authz? A "public" path with weaker checks is worth probing.
8. **[MEDIUM] FunctionImport authz.** `isPaymentDone`, `showOptions`, `getSwitchOpenSearch` — do they
   leak or accept another applicant's context?

## Execution notes
- Direct `GET`/`MERGE` with the session cookies works; `MERGE`/writes need a valid `x-csrf-token`
  (fetch via `GET ... -H 'x-csrf-token: Fetch'`, read the response header, reuse on the write).
- SAP sessions expire — re-capture a fresh authenticated request right before a test run.
