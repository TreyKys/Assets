# Track B — authz-matrix — live-run summary

**Program:** KU Leuven — Admissions for Students (Intigriti, safe-harbor). **Run:** 2026-09-22.
**Harness:** `tools/authz_matrix.py`. **Rows:** 362 in `02-authz-matrix.jsonl`.
**Sessions:** own test accounts A (`IN01051619` / app `000000503432`) and B (`IN01051651` /
app `000000503434`). Global rate ≥1.1 s/req; ~290 live requests total.

## Headline

> **Clean negative across all 8 sweeps.** No writes were accepted, no XSS payload
> persisted, no cross-user data returned, no `$batch` bypass, no CSRF gap, no illegal state
> transition, no property over-exposure via `$select=*`, no `$filter` injection. Object-level
> authorization on `ZC_AD_APPLICANT_SRV` looks correctly enforced for the applicant role, both
> on reads and on writes.

**Safety accounting (from the log itself):**
- writes accepted (any 204) — **0**
- responses echoing the XSS marker `KLXSSPROBE` or `<img` — **0**
- IMMEDIATE-STOP triggers (foreign PII in a response) — **0**
- scope violations / session expiries during the run — **0**
- Sweep 6 baseline `statusCode` restored and re-verified — **`restored_ok=True`**
- Sweep 7 free-text cleanup — 23/25 verified empty on readback; **2/25** (`Addresses.street1`,
  `Addresses.city`) show non-empty on readback because those fields already held **baseline
  test-address content** — the inject MERGE was 403'd and the payload marker is **absent** from
  the readback (no residual). Not a leak.

## Sweep × status

| Sweep | total | 200/204 | 403 | 400 | 404 | ERR | n/a¹ |
|---|---|---|---|---|---|---|---|
| 1 — priv-field MERGE matrix (own) | 48 | 17 | 16 | 0 | 0 | 0 | 15 |
| 2 — `$batch` wrap of Track-A 403s | 10 | 0 | 9 | 1 | 0 | 0 | 0 |
| 3 — CSRF-omitted writes         | 10 | 0 | 10 | 0 | 0 | 0 | 0 |
| 4 — `$expand` lateral read      | 5  | 4  | 0  | 1 | 0 | 0 | 0 |
| 5 — FunctionImports             | 114| 2  | 0  |102|10 | 0 | 0 |
| 6 — illegal state transitions   | 19 | 10 | 7  | 0 | 0 | 0 | 2 |
| 7 — stored-XSS persistence      | 150| 50 | 50 | 0 | 0 | 0 | 50|
| 8 — `$filter`/`$select=*`       | 6  | 5  | 0  | 1 | 0 | 0 | 0 |

¹ `n/a` = COMPARE / CLASSIFY / NOTE bookkeeping rows (no HTTP request).

## Sweep-by-sweep findings

### Sweep 1 — Privileged-field MERGE matrix on OWN `Applications('000000503432')`
- **Every** MERGE that set a privileged field (`statusCode`, `isPropositionAccepted`,
  `isAppFeePayed`, `caseAdmin`, `followUpAdmLetter`, `institution`, `academicYear`, `program`,
  `moduleGroup`, `guid`, and the compound `caseAdmin+statusCode`) returned **403**.
- Every subsequent re-read confirms `field_changed=False`: baseline values (`statusCode='000'`,
  `isPropositionAccepted=False`, `isAppFeePayed=False`, etc.) persist unchanged.
- **Verdict: CLEAN NEGATIVE.** Confirms and extends Track A's finding that write authz filters
  privileged fields — the server *rejects* the whole request rather than silently dropping
  the field.

### Sweep 2 — `$batch`-wrap of every Track-A 403/400 read (± changeset)
- 4 direct GETs that Track A saw 403 on → still 403 direct.
- 1 direct GET that Track A saw 400 on (`RubriekSet` malformed adm code) → still 400.
- All 5 batch-wrapped variants returned **outer 403** ("CSRF token validation failed" on the
  first; `403` on the rest). Inner-status list `[]` — server refused the whole batch.
- **Verdict: CLEAN NEGATIVE.** No `$batch` bypass. Object-level authz applies uniformly.

### Sweep 3 — Sweep-1 writes **without** `x-csrf-token`
- All 10 CSRF-omitted MERGEs returned **403**.
- **Verdict: CLEAN NEGATIVE.** CSRF is enforced on every privileged write — no gap.

### Sweep 4 — `$expand` lateral read
- `Applicants('0')?$expand=Applications` → 200; own record only.
- `Applicants('0')?$expand=Addresses,PersInfos,Curriculums,Languages,Scholarships,ApplicantPhotos`
  → **400** with SAP error envelope `/IWBEP/CM_MGW_RT/022 "Exception raised without specific
  error"` (backend nav-property implementation issue — not a leak; server refused).
- `Applications('000000503432')?$expand=Options,SubmitChecks,Attachments` → 200; own record only.
- `Applicants('IN01051651')?$expand=Applications,PersInfos` — cross-user attempt from A's
  session → **200 but returns A's own record** (`__metadata.id` = `Applicants('IN01051619')`).
  This is the same server-side self-substitution Track A already documented for keyed reads.
- **Verdict: CLEAN NEGATIVE.** `$expand` does not lateralize to another user; the keyed-read
  self-substitution behavior applies to expansions too.

### Sweep 5 — FunctionImports (114 calls across the four imports)
- `isPaymentDone` — 30 numeric guesses × { own admCode / B admCode / empty } = 90 calls:
  **all 400** ("Not a Number" for numeric-guess values that don't match a real payment id;
  400 for the empty/`TESTPAY` cases). **Zero 200s. No shape variance implying cross-user data.**
- `showSpringFall` — 4 variants: all 400 ("no admCode"/"malformed"). No data disclosure.
- `showOptions` — 6 variants: all 400. No data disclosure.
- `getSwitchOpenSearch` — 2 variants (no-params, junk): both **200** with the exact same body
  `{"getSwitchOpenSearch":{"active":true}}` — a global feature-flag with no user context. Junk
  input is ignored.
- **Verdict: CLEAN NEGATIVE.** No FunctionImport leaks or accepts another applicant's context.

### Sweep 6 — Illegal state transitions on OWN application
- MERGE `statusCode` ∈ {`"211"`,`"216"`,`"217"`,`"220"`} → **403** each; re-read confirms
  `persisted_statusCode='000'` (baseline). Zero `ANOMALY_status_transition_persisted`.
- MERGE `isAppFeePayed=false` then MERGE `statusCode="216"` (post-payment) → both 403.
- Workflow side-effect probe (`BlockSet?$top=1`) shows the block set is unaffected.
- Baseline captured at start (`statusCode='000'`); restore MERGE at end + verification →
  **`restored_ok=True`**.
- **Verdict: CLEAN NEGATIVE.** The **crown-jewel class** — self-admission / decision tampering
  from an applicant session — is not reachable via OData writes.

### Sweep 7 — Stored-XSS persistence probe on OWN free-text fields (+ mandatory cleanup)
- 25 field probes across `PersInfos('0')`, `Applications('000000503432')`, `Addresses(...)`.
- Every inject MERGE (`<img src=x onerror=alert(1)>KLXSSPROBE`) returned **403** — the field
  filter rejected the payload; nothing was ever stored.
- Every readback body verified: **`KLXSSPROBE` and `<img` are absent from every response**.
- Classifier verdicts: **23 × `stored_stripped_or_empty`, 2 × `unknown`.** The two `unknown`
  rows are the Addresses `street1`/`city` fields that already held **legitimate test-address
  content** from the account's baseline — not our payload, just pre-existing text (payload
  markers absent).
- Cleanup verification: 23/25 confirm empty on readback; 2/25 remain non-empty **because their
  baseline was non-empty and the inject was rejected — no state change occurred either way**.
- **Verdict: CLEAN NEGATIVE.** Free-text sinks either reject the payload or aren't reached at
  all. No stored-XSS candidate to promote for cross-user render.

### Sweep 8 — `$filter` injection & property projection on `RubriekSet`
Verified live post-run (URL-encoding harness fix pushed):
- `applicationCode eq '<A>'` (baseline) → **200, 4 result rows** with A's data.
- `applicationCode eq '<A>' or applicationCode eq '<B>'` (OR-injection) → **200, 0 result rows**
  (20-byte empty `results` array).
- `1 eq 1` → **200, 0 result rows.**
- `applicationCode eq '' or 1 eq 1` → **200, 0 result rows.**
- `applicationCode eq '''` (malformed single-quote) → **400** (parser rejects).
- `$select=*` on `Applications('000000503432')` → 200, 76 fields; on `PersInfos('0')` → 200, 34
  fields — all belong to the caller's own record. No hidden foreign fields.
- **Verdict: CLEAN NEGATIVE.** Server enforces per-record authz *inside* `$filter`, silently
  filtering out rows the caller can't see rather than 403'ing the whole request. No IDOR via
  filter-broadening. No property over-exposure via `$select=*`.

## Severity against program tiers

Nothing in this matrix rises to any program tier. Everything the brief and threat model
called out as high-value — self-admission (`statusCode` write), fee-payment bypass
(`isAppFeePayed=true`), admission-letter forgery (`followUpAdmLetter`), cross-user PII via
`$expand`, `$batch` authz bypass, CSRF absence, `$filter` broadening, `$select=*` field leak —
is **enforced correctly server-side** in ZC_AD_APPLICANT_SRV for the applicant role.

The single `ANOMALY_or_injection_returned_B` flag observed in the first run was a
**false positive caused by a harness bug** (Python's `urllib` refused URLs containing raw
spaces, so 7 requests never left the client; the "response body" was the `InvalidURL` error
string, which echoed B's id from the URL back into the message and tripped my substring flag).
The harness now URL-encodes the path+query before dispatch; the re-issued Sweep 2/8 requests
return **without** the flag, and the manual full-body inspection above confirms empty result
sets. Fix committed in `tools/authz_matrix.py` (`quote(safe="...")` in `Client.request`) + an
`--append` flag so partial re-runs don't clobber the matrix.

## Non-goals (still deferred)
- **Cross-user *read* proof from B's session.** The brief scoped Track B to A's session; a
  cross-user read from B via nav-property fetch or WSFilter chain remains an open probe if
  further breadth is worth doing.
- **Document uploads (Sweep 9).** Attachment path (`Applications(...)/Attachments(...)`)
  needs a fake-PDF flow — brief keeps this deferred.
- **Staff-side stored-XSS render.** N/A here anyway — no payload survived the sink.
- **`/esap/public/odata/*`.** Out of scope for Track B by design.

## Recommendation
The Admissions OData surface's applicant-side authz looks solid. Reporting this to the
program as a **submittable-quality authz-enforcement record** (per Track A's fallback plan)
is defensible; the matrix + methodology + safety controls demonstrate coverage worth writing
up whether or not the program treats a clean-negative security-review artifact as bounty-relevant.
Do **not** re-run this matrix without re-capturing cookies first (SAP sessions expire fast).
