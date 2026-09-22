# Track B authz-matrix harness — runbook

`authz_matrix.py` executes **VM-BRIEF-track-b-authz-matrix.md**: 8 authenticated authorization
sweeps against the SAP OData service `ZC_AD_APPLICANT_SRV`, from the researcher's **own** two test
accounts (A/B), logging one JSON row per request for pattern-matching.

Scope, targets, and rules of engagement are hard-coded (see `SCOPE-NOTES.md` and the brief). The
tool is deliberately bound to this one sanctioned engagement — do not repoint it.

## Prerequisites
- Python 3.8+ (stdlib only; no `pip install`). Verified on 3.12.
- Fresh SAP session cookies for **both** test accounts, captured from the already-authenticated
  Admissions app (the `idp.kuleuven.be` login is out of scope — never automated here):

  ```
  ~/kuleuven_creds/A.cookies      # account A: IN01051619 / app 000000503432
  ~/kuleuven_creds/B.cookies      # account B: IN01051651 / app 000000503434
  ```

  Each file may be **either** a single line `Cookie: name=value; name=value; …`, **or** a Netscape
  `cookies.txt` export, **or** a bare `name=value; …` blob. Capture from DevTools → Network → any
  `ZC_AD_APPLICANT_SRV` request → copy the `Cookie` header. SAP sessions expire fast — capture right
  before running.

## Run
```bash
python3 authz_matrix.py --dry-run          # plan only; no network, no session (safe to run anytime)
python3 authz_matrix.py                     # LIVE: all 8 sweeps  (~293 reqs, ~5.4 min @ 1 req/s)
python3 authz_matrix.py --sweeps 1,4,8      # LIVE: a subset
python3 authz_matrix.py --summary-only      # rebuild the summary md from an existing jsonl
```

## Output (written to ../vm-results/)
- `02-authz-matrix.jsonl` — one row per request: `{ts, sweep, entity_or_endpoint, method, variant,
  status, response_shape, notable_flags}`. `response_shape` = first 200 chars, session cookies
  scrubbed.
- `02-authz-matrix.plan.jsonl` — the `--dry-run` plan (no network).
- `02-authz-matrix-summary.md` — regenerated on each live run: sweep×200×403×anomaly table, anomaly
  expansions, Sweep-7 cleanup verification.

## Built-in guardrails (do not remove)
| Control | Behaviour |
|---|---|
| Host/path allow-list | only `webwsp.aps.kuleuven.be` + `/…/ZC_AD_APPLICANT_SRV/`; everything else → `ScopeViolation` (fatal) |
| Target-ID guard | any applicant/application id in a URL must be A's or B's; an adjacent id **aborts the run** |
| Rate limit | ≥1.1 s between every request, globally |
| IMMEDIATE-STOP | a response with a non-own name/email/DOB halts that sweep-class |
| Session-death | 401 / 302→IdP → halt and ask for fresh cookies |
| Sweep 7 cleanup | every free-text probe reset to `""` in `finally:` and re-read to verify |
| Sweep 6 restore | baseline `statusCode` captured and restored after the transition tests |

## Interpreting anomalies
Flags beginning `ANOMALY_` are the ones to triage:
- `ANOMALY_inner200_direct403` (Sweep 2) — `$batch` bypassed a per-record authz check → likely High/Critical.
- `ANOMALY_csrf_not_enforced_204` (Sweep 3) — write accepted without CSRF token → Medium.
- `ANOMALY_status_transition_persisted` (Sweep 6) — applicant moved their own decision state → **Critical** (self-admission).
- `ANOMALY_stored_raw` (Sweep 7) — free-text field stored `<img…>` verbatim → stored-XSS **candidate**; cross-user (staff) render still needs confirmation before it counts as High.
- `ANOMALY_or_injection_returned_B` (Sweep 8) — `$filter` OR exposed the other account's row → IDOR.
- `field_changed=True` in Sweep 1 on a privileged field → the write was accepted **and persisted**.

Report findings in English to `vm-results/`; do **not** submit anything from the VM.
