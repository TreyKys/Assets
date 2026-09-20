# VM BRIEF — KU Leuven Admissions (Intigriti) — Track A: SAP OData recon + IDOR/privilege-escalation hunt

You are the execution agent. **This is a real, in-scope Intigriti bug bounty program with safe harbor.**
Authenticated testing is explicitly sanctioned (the program hands out self-service test accounts). Stay
strictly within scope and the rules below.

## Scope (ONLY these — anything else is out of scope)
- `https://www.kuleuven.be/sapredir/admissions_50000050`
- `https://webwsp.aps.kuleuven.be/sap/bc/ui5_ui5/sap/zc_ad_appl/ *` (SAP UI5 frontend)
- `https://webwsp.aps.kuleuven.be/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/ *` (SAP OData API — primary target)

**Out of scope — never touch:** `idp.kuleuven.be` (the login/registration IdP itself), pre-auth
account takeover / OAuth squatting, self-XSS that can't reach another user, and everything else in the
program's out-of-scope list (see `SCOPE-NOTES.md`).

## Hard rules of engagement (read fully — real university data is behind this)
- **Test ONLY with your own test account(s).** Account creation: enroll at the sapredir link with
  first name `Intigriti`, last name `Test`, and the researcher's Intigriti email. Do NOT change
  passwords on any provided credentials.
- **Do NOT exploit beyond proof.** The moment you can demonstrate reading/modifying a record that isn't
  yours, STOP. Capture the single minimal proof (e.g. one foreign record's identifier + one field
  confirming it's not yours) and go no further. Do NOT enumerate IDs in bulk, do NOT exfiltrate other
  applicants' data. This is both a program rule and an ethical hard line — other people's admissions
  records are real PII.
- **No destructive tests on data you don't own.** For write/modify authz tests, prefer your own second
  test account as the "victim." Never DELETE/modify a real applicant's record to "prove" it — a
  successful *read* of the write endpoint's authorization (e.g. a 200 vs 403 on a benign MERGE to a
  foreign key using a no-op/echo field) is sufficient signal; escalate the reasoning in the report, not
  the damage.
- Max politeness on request volume; no automated bulk scanning/brute force (out of scope + rude to prod).
- Report language: English. Commit findings to `intigriti/kuleuven_admissions/vm-results/`. Do NOT
  submit anything anywhere from the VM.

## Task 0 — session acquisition
The UI5 app authenticates via KU Leuven IAM, then calls the OData service with a session
cookie/CSRF token. You need that authenticated context to talk to OData.
1. Log into the Admissions app in a browser as your test account.
2. Capture the request the UI5 app makes to
   `webwsp.aps.kuleuven.be/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/` — note the session cookie(s)
   (`MYSAPSSO2` / `SAP_SESSIONID_*`) and the CSRF token (`x-csrf-token`, fetched via a `GET` with
   header `x-csrf-token: Fetch`). SAP OData write ops require a valid CSRF token.
3. Record your own account's identifiers (SAP ID, Application ID) as the baseline for IDOR tests.

## Task 1 — map the OData service via $metadata (no guessing)
```
GET /sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/$metadata     (authenticated)
GET /sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/               (service document — lists EntitySets)
```
From `$metadata`, enumerate: every **EntitySet**, its **EntityType key(s)**, all **properties**
(and types), **NavigationProperties/associations**, and any **FunctionImports** (custom actions,
often `m:HttpMethod="POST"` or GET). Produce a table: EntitySet | key shape (SAP ID? Application ID?
integer? GUID?) | read/write ops exposed | sensitivity of properties.

## Task 2 — horizontal IDOR (other users' data — the #1 wanted class)
For each read EntitySet whose key you can influence:
1. Baseline: fetch YOUR OWN entity, e.g.
   `GET .../ZC_AD_APPLICANT_SRV/ApplicantSet('IN00824795')` (use the real EntitySet name from Task 1).
2. Authz test: request a key you do NOT own — use your **second test account's** ID first (clean,
   ethical). If that proves it, stop. Only if two accounts aren't possible, probe a single adjacent ID
   and STOP at first proof (see hard rules).
3. Watch for: a foreign record returned with `200` (BOLA), `$expand` pulling a foreign associated
   entity, `$filter`/`$select` bypassing per-record authorization, or the `$batch` endpoint applying
   weaker checks than direct GETs.
4. Record the minimal proof only.

## Task 3 — vertical privilege escalation & function imports
- Look for FunctionImports or EntitySets that imply staff/admin/reviewer operations (approve, set
  status, assign, read-all). Test whether your low-privilege applicant session can invoke them.
- Test write authorization: `POST`/`PUT`/`MERGE`/`DELETE` on an entity keyed to your second account
  (never a real user). A `200/204` where a `403` is expected = missing object-level authz on writes
  (data modification is explicitly wanted).

## Task 4 — property-level over-exposure
Compare fields the UI5 app displays vs. fields the OData entity returns (use `$select=*` / full entity).
SAP OData often exposes back-end fields the UI hides (internal status, scores, other identifiers,
national numbers). Flag any sensitive property returned that the UI never shows.

## Task 5 — stored XSS into a cross-user sink (secondary)
Identify applicant free-text fields (name, notes, address, remarks) that are later rendered to a
**different** user (admissions staff / reviewer). If such a field is stored via OData and rendered
elsewhere without encoding, that's stored XSS with cross-user impact (High). **Self-XSS that only
affects your own view is OUT of scope — it must reach another user to count.** Do not assume the staff
side renders it; note it as a candidate needing confirmation if you can't observe the staff view.

## Output
`intigriti/kuleuven_admissions/vm-results/01-odata-recon-and-idor.md`:
- The full EntitySet/key/ops table from `$metadata` (Task 1).
- Per-test result for Tasks 2–5, with the minimal proof for anything that lands, and honest
  "needs confirmation" notes for anything static/partial.
- Clear severity mapping to the program's tiers for any confirmed finding.
- If nothing lands: a clear, honest negative with the surface you covered. A clean map of the OData
  service + confirmed-enforced authorization is still a useful, submittable-quality result record.
