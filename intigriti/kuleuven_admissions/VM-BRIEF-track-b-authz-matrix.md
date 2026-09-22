# VM BRIEF — KU Leuven Admissions — Track B: authenticated authz-matrix sweep

**Purpose:** run the systematic breadth-tests we've been deferring — one script, one session, one
results matrix — so the human researcher can pattern-match anomalies instead of hand-running probes.
Track A (browser-console probes) established that keyed reads self-substitute and privileged-field
MERGEs get silently filtered. This brief covers the ~15 untested classes the threat model calls out.

## Scope (STRICT — do NOT deviate)
- ONLY hit: `https://webwsp.aps.kuleuven.be/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/*`
- **Out of scope — do NOT touch:** `idp.kuleuven.be`, `/esap/public/odata/*`, anything outside `ZC_AD_APPLICANT_SRV`.
- ONLY use accounts A (`IN01051619` / app `000000503432`) and B (`IN01051651` / app `000000503434`)
  as targets. NEVER a random adjacent ID — those are real applicants.
- Max **1 request/second** overall. This is a live university system.
- If any request returns a response indicating real-user data (name/email/DOB that isn't
  Intigriti/Test/treyky*), STOP that test class immediately and log it as "IMMEDIATE-STOP".

## Setup (once — the human provides these)
1. Fresh session cookies for Account A (exported from Chrome DevTools or as `Cookie:` header).
   Save as `~/kuleuven_creds/A.cookies` (Netscape format or one `Cookie: ...` line).
2. Fresh session cookies for Account B — `~/kuleuven_creds/B.cookies`.
3. CSRF token capture is built into the script (HEAD with `x-csrf-token: Fetch`).

Sessions expire; if any test starts returning 401/302, halt and ask for fresh cookies.

## The matrix — 8 sweeps, all against A's session unless otherwise noted

Every request gets logged as one JSON row: `{sweep, entity_or_endpoint, method, variant,
status, response_shape, notable_flags}`. `response_shape` = first 200 chars, sanitized (strip
session cookies from any echoed request). Output a single `matrix.jsonl` for review.

### Sweep 1 — Privileged-field MERGE matrix on OWN Applications('000000503432')
Test whether each privileged field is filtered/accepted individually. Baseline read → MERGE with
`{field: value}` → re-read → compare. **All against your OWN application.**

Fields to probe (one at a time):
- `statusCode`: try `"211"` (legit), `"216"`, `"220"`, `"901"`, `"099"` (admitted-looking values)
- `isPropositionAccepted`: `true`
- `isAppFeePayed`: `true` (confirms Track A result)
- `caseAdmin`: `"HACKER"`
- `followUpAdmLetter`: `"1"`, `"X"`
- `institution`: `"12345678"` (change target institution?)
- `academicYear`: `"2099"`
- `program`: `"99999999"` (change target programme?)
- `moduleGroup`: `"99999999"`
- `guid`: `"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"`
- `caseAdmin` combined with `statusCode="211"` (compound)

For each: log MERGE status, and whether the field's value *actually changed* on re-read.

### Sweep 2 — $batch authz-bypass on every 403'd read
For each URL that returned 403 in Track A, wrap the same request inside a `$batch` multipart
POST and log the batch response's inner status. Also try nested inside a `changeset` (writes only).

Endpoints to $batch-wrap (from Track A negatives):
- `GET Applications('000000503434')/SubmitChecks`  (403)
- `GET DisciplineSet?$filter=applicationId eq '000000503434'`  (403)
- `GET TrefwoordenSet?$filter=applicationId eq '000000503434'`  (403)
- `GET Applications('000000503434|0')/Attachments('1')/$value`  (403)
- `GET RubriekSet?$filter=applicationCode eq '000000503434' and language eq 'E'`  (400 "adm code")

Compare inner-batch status to the direct-call status. **Any inner 200 where direct was 403 = finding.**

### Sweep 3 — CSRF absence on writes
Repeat the Sweep 1 write set (own application) **without** the `x-csrf-token` header. Expected:
403 "CSRF token validation failed." Any 204 = CSRF not enforced on that write = Medium.

### Sweep 4 — $expand lateral read
For each nav-property observed in `$metadata`, try `Applicants('0')?$expand=<nav>` and log what
comes back. Interesting expansions:
- `Applicants('0')?$expand=Applications`
- `Applicants('0')?$expand=Addresses,PersInfos,Curriculums,Languages,Scholarships,ApplicantPhotos`
- `Applications('000000503432')?$expand=Options,SubmitChecks,Attachments`

Then: `Applicants('IN01051651')?$expand=Applications,PersInfos` (cross-user + expand).

Compare full $expand response against the base entity read — any extra sensitive fields exposed?

### Sweep 5 — FunctionImports (all four)
- `isPaymentDone` × { own admCode / B admCode / empty admCode / paymentId in [empty, "0", "1",
  "TESTPAY", 30 numeric guesses 1..30] }.  Log every distinct response shape.
- `showSpringFall` × { own admCode, B admCode, empty, malformed }
- `showOptions` × { same set, plus with various programme IDs }
- `getSwitchOpenSearch` × { call with no params, with junk }

Any 200 that varies by input in a way that implies cross-user data disclosure = finding.

### Sweep 6 — Illegal state transitions (own application only)
Client only ever writes `statusCode` ∈ {209, 210, 211}. Test each of these:
- `MERGE Applications('000000503432')` with `statusCode="211"` **WITHOUT** completing the
  required rubrieken (skip the client-side `_rubriekenCompleet` gate).
- Same but with `statusCode="216"`/`"217"`/etc. (values the client never writes).
- MERGE + set `institution` to a different valid institution ID (if any exposed).
- MERGE while `isAppFeePayed=false` and try to set `statusCode` = a post-payment value.

For each: re-read the application and log the persisted `statusCode` + any workflow side effects
(does `getBlokken` change, does a `_getRubrieken` re-evaluation flip status).

### Sweep 7 — Stored-XSS-to-staff surface (persistence only, no cross-user render yet)
Write HTML/JS payloads into every free-text field on OWN records, re-read, and log whether the
server stored raw or encoded. Fields:
- `PersInfos('0')` : `additionalRemarks`, `otherReasonSpecify`, `familyReunionWith`,
  `workingWhere`, `studyingWhere`, `birthPlace`, `motherLanguage`
- `Applications('000000503432')` : `additionalremarks`, `doctSummaryEN`, `doctSummaryNL`,
  `doctKeywords`, `doctFinancialInfo`, `doctSpecialisation`, `doctPartnerUniversity`,
  `exchProgram`, `exchHomeUniversity`, `exchContactName`, `intScholarSubject`, `specSpecialisation`,
  `infoAboutProgramOther`, `exchProgramOther`, `exchStudentTypeOther`, `exchPurposeOther`
- `Addresses(inAccountId='0',language='E')` : `street1`, `city`

Payload: `<img src=x onerror=alert(1)>` and a marker `KLXSSPROBE`. Read back and diff:
- If server returns the payload **verbatim** (with `<img`) → stored raw. Then the question
  becomes whether staff/reviewer view renders it unescaped (needs their view — flag for report
  as "confirmed stored, cross-user render unverified but demonstrable to program").
- If HTML-encoded (`&lt;img`) → stored safely.
- If stripped (empty) → sanitized on store.

**CLEANUP MANDATORY:** immediately overwrite every probed field back to `""`.

### Sweep 8 — $filter injection & property projection
On any allowed collection/$filter endpoint (or nested nav that accepts $filter):
- `$filter=applicationCode eq '000000503432' or applicationCode eq '000000503434'`
  (OR-injection: does A see B's row?)
- `$filter=1 eq 1`
- `$filter=applicationCode eq '' or 1 eq 1`
- Malformed: `$filter=applicationCode eq '''`  (single-quote injection)
- `$select=*` on `Applications('000000503432')`, `PersInfos('0')` — any hidden fields returned?

## Deliverable

`intigriti/kuleuven_admissions/vm-results/02-authz-matrix.jsonl` — one row per request.
Plus `intigriti/kuleuven_admissions/vm-results/02-authz-matrix-summary.md`:
- Table: sweep × count-200 × count-403 × count-anomaly
- Every "anomaly" row expanded with expected-vs-actual and severity guess (per program tiers)
- Explicit "CLEAN NEGATIVE" statement for sweeps that produced no anomaly, so we don't retest
- Cleanup verification: for Sweep 7, confirm every probed field back to `""`

## Non-goals for this brief
- No document uploads (Sweep 9 later, needs a fake-PDF flow)
- No cross-user writes beyond what Track A already ruled out
- No fuzz beyond the fields explicitly named
