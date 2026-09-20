# KU Leuven Admissions — Threat Model & Creative Attack Surface Map

The point of this doc: **IDOR is the front door, not the house.** An admissions system is a
*trust machine* — its entire job is to decide, credibly and fairly, who gets in. Every attack that
undermines a **trust pillar** is a real, high-severity bug even if it never touches a classic OWASP
category. Below: the trust pillars (the "20+ crucial parts"), the attacks against each, and how they
map to this program's reward tiers. Tagged **[E]** expected / **[U]** unconventional, and by tier.

Context (researched): SAP SLcM backend, OData `ZC_AD_APPLICANT_SRV`, SAP UI5 frontend. Applicants
create an account, enter personal data, **upload diplomas/transcripts, pay an application fee**, and
receive an **admission decision** (and, for degree-seekers, an **admission letter used for visa/enrolment**).
Recurring SAP-OData weakness in the literature: OData authz is looser and less-monitored than the SAP
GUI equivalent; `$batch`, FunctionImports, and write ops are common gaps.

---

## THE CROWN JEWEL — Admission Integrity (why this program exists)

The single most valuable class isn't data theft — it's **manufacturing or altering an admission
outcome**. If any of these land, they're Critical, and they're the "undeniable" bugs you asked for
because the impact is self-evident to any triager.

1. **[U][CRITICAL] Self-admission / decision tampering.** Can a low-priv applicant write to the
   *decision/status* field (e.g. `AdmissionStatus`, `Decision`, `Result`, `StatusCode`) via OData
   `MERGE`/`PUT`/`POST` or a FunctionImport (`SetStatus`, `Approve`, `Decide`)? SAP SLcM models
   admission as a status workflow; if object-level authz is missing on the write path, you flip your
   own "pending/rejected" → "admitted." This is *the* bug to hunt.
2. **[U][CRITICAL] Forged admission letter / offer document.** Degree-seekers get an official
   admission letter — used for **visa applications**. If you can generate, download, or trigger
   issuance of an admission letter without a genuine admit decision (or for a programme you weren't
   admitted to), that's visa-grade document fraud. Check any `PrintLetter`, `GenerateDocument`,
   `AdmissionLetter`, `/print`, or Adobe/Smartforms endpoint.
3. **[U][CRITICAL] Eligibility / prerequisite bypass.** Apply to a restricted programme (quota,
   prerequisite diploma, language cert) you don't qualify for by manipulating the eligibility check —
   client-side-only gating, or a writable `Eligible`/`Qualified` flag.
4. **[U][HIGH] Queue / priority / deadline manipulation.** Alter application submission timestamp,
   priority, intake period, or reopen a closed application after the cutoff (writable `SubmittedOn`,
   `Deadline`, `IntakeId`).

---

## THE 20+ TRUST PILLARS (attack from all sides)

Each pillar = something the system must guarantee. Break the guarantee = a finding.

### Identity & account trust
5. **[E][HIGH] Account ↔ application binding (horizontal IDOR).** Does your account only reach *your*
   application, or can you re-point an `ApplicantId`/`ApplicationId`/`SAP ID` (the program literally
   shows `IN00824795` / `000000430539` — enumerable) to read another applicant? #1 wanted class.
6. **[U][CRITICAL] Application takeover via linkage.** Can you *bind your account* to another person's
   existing application/SAP ID (claim their application), or merge/adopt an application? That's
   account-takeover-of-record without touching the IdP (which is out of scope — you attack the app's
   *use* of identity, not `idp.kuleuven.be` itself).
7. **[U][HIGH] Guest → applicant → reviewer privilege gradient.** The flow starts as a "guest
   account." Test every step-up: guest reading applicant-only entities; applicant invoking
   reviewer/staff FunctionImports; role encoded in a client-alterable token/param.

### Document trust (diplomas, transcripts, ID)
8. **[E][HIGH/CRITICAL] Cross-applicant document read.** Can you fetch another applicant's uploaded
   diploma/transcript/passport (IDOR on the file/attachment entity or a `/$value` media stream)?
   Real PII → Critical.
9. **[U][HIGH] Document swap after review (integrity/TOCTOU).** Upload a weak diploma, get it
   reviewed/verified, then *replace the file* while keeping the "verified" flag → forged credentials
   pass review. Check if the verified state is bound to a content hash or just to the record.
10. **[U][HIGH] Forge the "verified/authentic" flag.** Directly set a document's
    `Verified`/`Authenticated`/`Checked` property via OData write.
11. **[E][MEDIUM/HIGH] Malicious file upload.** SAP attachment uploads require the Virus Scan
    Interface to be *configured* (often isn't). Test stored file type/extension handling, SVG/HTML
    with script (stored XSS via document preview), path traversal in filename, oversized/zip-bomb.
    Only counts if it reaches another user or executes — self-only is out of scope.
12. **[U][HIGH] Document access-control confusion across intakes/faculties.** Multi-faculty system —
    can a document uploaded in one programme context be read from another?

### Money trust (application fee)
13. **[U][HIGH] Fee-payment bypass (business logic).** Mark `FeePaid=true` / `PaymentStatus=Complete`
    via OData write without paying; replay/forge the payment-gateway callback; manipulate the
    client-side "payment success" transition. Getting admitted-to-review without paying = data
    modification with financial impact.
14. **[U][HIGH] Fee category / tuition-bracket manipulation.** Change EEA vs non-EEA status,
    scholarship flag, or fee-exemption to pay a lower/zero fee — writable financial classification.
15. **[U][MEDIUM] Payment amount / currency tampering** in the initiation request if amount is
    client-supplied.

### Data confidentiality (the PII goldmine)
16. **[E][CRITICAL] Bulk applicant data exposure.** `$filter`/`$top`/`$skip`/`$orderby` on an
    EntitySet that should be self-scoped but isn't → read many applicants. **STOP at minimal proof
    (program rule) — one foreign record, don't harvest.**
17. **[E][HIGH] Property-level over-exposure.** OData entity returns fields the UI hides — internal
    reviewer notes, scores, **Belgian national number (rijksregisternummer)**, other identifiers.
    Compare `$select=*` / full entity vs. what the UI5 app displays.
18. **[U][HIGH] `$expand` lateral read.** Navigation properties pulling *associated* foreign entities
    (e.g. `Applicant?$expand=Documents,Decisions,Payments`) that skip per-record authz.
19. **[U][MEDIUM/HIGH] GDPR "download my data" / export abuse.** If a data-subject export exists,
    IDOR on it dumps another person's full profile in one call.

### Workflow & state-machine trust
20. **[U][HIGH] Illegal state transitions.** Drive the application through transitions the UI forbids
    (submit without required docs; un-reject; re-open; skip mandatory steps) via direct OData writes —
    the state machine's server-side enforcement is the real question.
21. **[U][MEDIUM] Race conditions / TOCTOU.** Double-submit for two fee outcomes; concurrent writes to
    decision/fee; parallel document verify vs. swap.

### Communication & audit trust
22. **[U][MEDIUM/HIGH] Stored XSS into the staff/reviewer view.** Applicant free-text (name, address,
    motivation letter, remarks) rendered in an admissions officer's dashboard without encoding =
    stored XSS w/ minimal interaction (**High** per their tiers). Must reach another user — self-XSS
    is explicitly out of scope.
23. **[U][MEDIUM] Notification/e-mail content injection** into messages sent to staff or the applicant
    (letter merge fields, template injection — note SAP Smartforms/Adobe form injection).
24. **[U][LOW/MEDIUM] Audit-trail tampering** — if the app writes an activity log the applicant can
    influence or clear.

### Platform / SAP-technical trust
25. **[E][INFO→pivot] `$metadata` full model disclosure** — not a bug alone, but it hands you every
    EntitySet, key, and FunctionImport to test the above. First recon step.
26. **[U][HIGH] `$batch` authorization bypass.** Documented SAP class: `$batch` sometimes applies
    weaker authz than direct calls, and OpenUI5 had a batch-parsing linebreak bug. Wrap a
    forbidden operation in a `$batch` multipart and compare.
27. **[U][HIGH/CRITICAL] FunctionImport abuse.** Custom RFC-backed actions exposed as OData functions
    — often the least-authz-checked surface. Enumerate from `$metadata`, test each with your low-priv
    session.
28. **[U][CRITICAL] Injection through OData params.** ABAP/SQL injection via `$filter` or key values
    that flow into dynamic OpenSQL; SAP has shipped injection CVEs. Test `$filter` with SQL/ABAP
    metacharacters against string fields.
29. **[U][HIGH] CSRF-token weakness on writes.** SAP requires `x-csrf-token`; test whether writes are
    accepted without it, with a reused/guessable token, or cross-origin.
30. **[E][MEDIUM] SAPUI5 client-side trust.** `manifest.json`/`Component.js` may reveal backend
    destinations, hidden routes, feature flags, or role checks done *only* client-side (bypass by
    calling OData directly). Source maps / debug endpoints.
31. **[U][MEDIUM] SAP standard-service exposure.** Beyond `ZC_AD_APPLICANT_SRV`, are standard SAP
    Gateway services reachable on the same host (`/sap/opu/odata/sap/...`, `CATALOGSERVICE`,
    `GWSAMPLE`, `/sap/bc/...`)? Careful: only in-scope hosts, and only the Admissions app is paid
    "unless severe enough."

---

## How we adapt OUR skills to land an undeniable bug here

- **From the bank work you already have the muscle:** map the API from its own schema, hunt
  client-supplied identifiers, test object-level authz. Here the schema is `$metadata` (richer than
  the bank's OpenAPI) and — critically — **you can actually authenticate and run the tests.**
- **Prioritize by undeniability × reachability:**
  1. **Decision/status write authz** (#1) and **cross-applicant read** (#5/#8/#16) — highest
     value, directly testable with two free accounts, impact self-evident.
  2. **Fee-bypass** (#13/#14) and **document swap/verify-forge** (#9/#10) — business-logic, very
     credible to a triager, need careful own-account-only proof.
  3. **FunctionImport / $batch authz** (#26/#27) — the SAP-specific gaps most researchers skip.
- **Two accounts = clean ethics.** Every cross-user test uses account A vs. account B, both yours.
  Never a real applicant. Prove with one record, then stop (program rule + PII ethics).
- **Undeniable = reproducible + self-evident impact.** A screenshot of account A reading account B's
  national number, or account A's status flipping to "admitted" via a raw OData call, needs no
  argument. That's the bar.

## Sequencing
1. Create **two** test accounts (Intigriti/Test).
2. Pull `$metadata`; build the EntitySet/key/FunctionImport map (VM brief Task 1).
3. Baseline both accounts' IDs and records.
4. Run authz matrix: read + write, direct + `$expand` + `$batch` + FunctionImport, A-against-B.
5. Layer in business-logic (fee, documents, state machine) and the staff-sink stored-XSS check.
6. Everything lands in `vm-results/`, mapped to the reward tiers, minimal-proof only.
