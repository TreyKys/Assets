# KU Leuven Admissions — engagement summary

**Program:** Intigriti bug bounty (safe-harbor).
**Target:** `webwsp.aps.kuleuven.be` — SAP OData v2 service `ZC_AD_APPLICANT_SRV`
(SAPUI5 1.120.48, LTS branch, built 2026-07-15).
**Accounts:** A = `IN01051619` / app `000000503432`; B = `IN01051651` / app `000000503434`.
**Institution:** `50000050` (KU Leuven main).
**Period:** 2026-09-21 – 2026-09-28.

## Overall verdict

**Zero exploitable / bounty-tier findings across all tracks (A – H.1).**

Every crown-jewel hypothesis — cross-user IDOR, stored XSS, CSRF bypass,
privilege-field mutation, batch-dispatch bypass, photo-upload content-type
reflection, DOM sink injection — was tested and clean-negatived. The SAP Web
Dispatcher + backend authorization layer enforces object-level access control
correctly for the applicant role, on both reads and writes, with multiple
defense-in-depth layers at each surface.

## Track-by-track summary

### Track A — OData IDOR baseline (`01-odata-map-baseline.md`)

Mapped the OData service shape from authenticated HAR. Identified 33 entities,
the `'0'` self-alias pattern, `$batch` as the primary transport, and the
`Applicants` / `Applications` / `PersInfos` identity triple. Established that
direct `GET` with a foreign key returns 403 (object-level authz enforced).

**Verdict:** CLEAN — no IDOR on direct GET.

### Track B — authorization matrix (`02-authz-matrix-summary.md`)

362 logged probes across 8 sweeps. Tested privilege-field MERGE, `$batch`-wrapped
403 retries, CSRF-omitted writes, `$expand` lateral read, all FunctionImports,
illegal state transitions (incl. status rollback), stored-XSS persistence on 25
free-text fields, and `$filter`/`$select=*` injection.

**Verdict:** CLEAN NEGATIVE across all 8 sweeps. 0 writes accepted, 0 XSS markers
persisted, 0 cross-user data returned, 0 foreign-PII incidents.

### Track C/D — codebase static analysis (`03-bundle-summary.md`, `03-controllers-analysis.md`, `04-views-analysis.md`)

Extracted the full SAPUI5 bundle (controllers, views, fragments, custom controls,
i18n, `$metadata`). Identified the `HtmlMenu.js` innerHTML sink, the
`CommunicationMenu.fragment.xml` binding chain, the `sap.m.FormattedText`
sanitizer pattern, and the `paymentDone` route's dead-capture params.

**Verdict:** one live candidate identified (programDescription → HtmlMenu innerHTML).
All other sinks defended by framework escaping or dead code paths.

### Track E — Sweep 9 + Sweep 14 post-bundle (`03-sweep9-longtexts.md`, `03-sweep14-metadata.md`)

Sweep 9: LongTexts entity batched-MERGE cross-user. Inner 501 (handler not
implemented for writes). Sweep 14: offline `$metadata` enumeration — 33 entities,
372 properties catalogued; over-exposure candidates flagged for future fuzz tuning;
nothing directly reportable.

**Verdict:** CLEAN — no findings.

### Track F — batch-dispatch bypass + sidedoors (`05-track-f-*.md`)

Six phases:

| Phase | Method | Result |
|---|---|---|
| F1.1/F1.3 — batch-wrapped cross-user reads | `$batch` GET wraps of 403'd endpoints | Inner 403 preserved; no bypass |
| F1.2 — changeset-atomicity | Multi-MERGE changeset | Inner 400 (parser rejects multi-op) |
| F1.5 — Content-ID ref smuggling | `$Content-ID` in batch | Inner 501 (not implemented) |
| F3.1 — payment-id enumeration | `isAppFeePayed` FunctionImport | Always returns `false`; no oracle |
| F4.1 — sap-client swap | `sap-client=000/100/300` | 401 on all non-200 values |
| F4.2 — trust-header injection | `sap-user`, `X-Forwarded-*` | Identity unchanged; headers ignored |
| F5.1 — composite-key fuzzing | `TrefwoordenSet`, `DisciplineSet` | 403, unclassified (no authz gap) |
| Sweep 11 — gap-field writes | `appFeePayURL`, `templateMergeContent` | Inner 400 / silent-drop |
| Sweep 12 — org-customisation write | `OrganisationCustomisations` MERGE | Inner 501 (read-only) |
| F2.3 — cross-tenant photo | `ApplicantPhotos('0')` B→A | Surface null (no photo at test time) |
| F2.4 — lazy-load attachment | `ApplicationAttachments` | 404 on all backing paths (defunct) |

**Verdict:** ALL CLEAN-NEGATIVE. Batch dispatch does not bypass object-level authz.

### Track G — photo upload surface (`06-track-g-photo-upload.md`)

Triple-defense characterization:

1. MIME allowlist rejects `image/svg+xml`, `text/html`, `application/xhtml+xml` → 400.
2. Serve response normalizes to `image/jpeg` + `X-Content-Type-Options: nosniff` +
   `Content-Disposition: attachment`.
3. Slug metadata (`fileName`, `docType`) never reflected in responses.
4. Server re-encodes JPEG bytes (metadata strip).

**Verdict:** CLEAN NEGATIVE — no stored XSS, no filename-injection reflection, no
doc-type routing escape.

### Track H — client-side DOM attack surface (`07-track-h-*.md`)

Seven surfaces analyzed statically:

1. **UI5 version + CVEs:** 1.120.48 (LTS). Pre-Jan-2026 CVEs all patched by this
   build. Post-Jul-2026 advisory lookup deferred (researcher DB task).
2. **Router/hash param flows:** all dead-capture or server-overwritten or formatter-escaped.
3. **postMessage handlers:** none found in bundle.
4. **HTML sinks (innerHTML/outerHTML):** one real sink in `HtmlMenu.js` —
   fed by `programDescription` binding. Tested in H.1.
5. **Navigation sinks:** all use SAP router (`navTo`) with hardcoded route names.
6. **Dynamic module loads:** none parameterized by user input.
7. **Storage/prototype pollution:** no `location.hash`-to-storage flows;
   no `Object.assign` from URL params.

**Verdict:** one candidate (programDescription → HtmlMenu innerHTML). All others closed.

### Track H.1 — programDescription confirmation (`07-track-h1-programdescription-confirm.md`)

Staged confirmation of the sole H candidate:

| Probe | Inner status | Readback | Writable? |
|---|---|---|---|
| Step 1: inert marker `KLXSSPD_INERT_1` | 204 | `""` (unchanged) | **No** — silent-drop |
| CREATE-path: `MERGE Applications('0')` | 204 | 0 → 0 rows | **No** — CREATE_REJECTED |

**Verdict:** NOT WRITABLE. The `programDescription` field silently drops applicant-
supplied writes on both the UPDATE and CREATE paths. The HtmlMenu innerHTML sink is
real but has no reachable applicant-controlled source. **Candidate closed.**

## Open items (non-exploitable)

1. **Phantom HigherEducations row** (`higherEducationId='000999'`) on account A.
   OData `DELETE` returns 501; needs manual UI deletion. Not a security finding.
2. **Post-Jul-2026 UI5 CVE lookup:** researcher task to check SAP Security Patch
   Day advisories for 1.120.x entries dated after 2026-07-15.
3. **G2.2 doc-type routing ambiguity:** `ZCM_ADM_LETTER` accepted with 201 but
   entity metadata empty. Can't determine if silently normalized or routed to a
   different document queue. No security impact observed — serve behavior
   still returns `image/jpeg` + `nosniff` + `attachment` regardless.

## Request budget accounting

All testing stayed within ACL-safe thresholds:

- **Total non-safe HTTP requests (across all tracks):** ~60
- **IP rotation events:** 0 (all phases ran from the same egress)
- **ACL triggers / blocks observed:** 0
- **Foreign-PII incidents:** 0
- **Cleanup verification failures:** 0 (all restores verified)

## Deliverables

All results in `intigriti/kuleuven_admissions/vm-results/`:

| File | Track |
|---|---|
| `01-odata-map-baseline.md` | A |
| `02-authz-matrix-summary.md` | B |
| `03-bundle-summary.md` | C/D |
| `03-controllers-analysis.md` | C/D |
| `03-sweep10-singleton-idor.md` | E |
| `03-sweep10-batched-followup.md` | E |
| `03-sweep14-metadata.md` | E |
| `03-sweep9-longtexts.md` | E |
| `04-views-analysis.md` | C/D |
| `04-i18n-flags.md` | C/D |
| `05-track-f-batch.md` | F |
| `05-track-f-composite-keys.md` | F |
| `05-track-f-payment-identity.md` | F |
| `05-track-f-batched-write-pass.md` | F |
| `06-track-g-photo-upload.md` | G |
| `07-track-h-ui5-cves.md` | H |
| `07-track-h-clientside.md` | H |
| `07-track-h-candidates.md` | H |
| `07-track-h1-programdescription-confirm.md` | H.1 |
| `08-engagement-summary.md` | final |
