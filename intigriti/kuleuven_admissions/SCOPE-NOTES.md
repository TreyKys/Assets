# KU Leuven — Admissions for Students (Intigriti) — program notes

## Verdict: STRONG, immediately actionable target — self-service test accounts, SAP OData IDOR surface

Unlike Bank Van Breda (blocked on eligibility-gated onboarding), this program **hands you a
self-service test account**. The full authenticated attack surface is reachable now.

## In-scope assets
- `https://www.kuleuven.be/sapredir/admissions_50000050` (enrollment entry / SAP redirect)
- `https://webwsp.aps.kuleuven.be/sap/bc/ui5_ui5/sap/zc_ad_appl/ *` — **SAP UI5 frontend** (the Admissions SPA)
- `https://webwsp.aps.kuleuven.be/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/ *` — **SAP OData API** (the backend data service — primary target)

Note: "In general we will not pay a bounty for findings that are not part of our Admissions for
Students application unless the issue is severe enough." → stay on these assets.

## Auth model
- Login via KU Leuven IAM (`idp.kuleuven.be`). **The IdP login/registration itself is OUT of scope.**
- You test the *application* (UI5 + OData), authenticated as your own test account.

## Account creation (self-service — program-sanctioned)
From the program FAQ:
- Enroll here: `https://www.kuleuven.be/sapredir/admissions_50000050`
- **First name must be `Intigriti`, last name must be `Test`.**
- **Mail address must be your Intigriti email** (the researcher's `@intigriti.me` alias / registered address).
- **DO NOT change the passwords** of any provided testing credentials.
- Create **two** accounts if the flow allows → needed to prove horizontal (cross-user) access cleanly.

## What they most want (highest interest — map every test to these)
- Horizontal or vertical privilege escalation
- Sensitive data access of other users
- Arbitrary file read/write
- Script/code execution (script/code exec)
- Exploits that allow data modification

## Reward tiers (impact → severity)
| Tier | Examples from policy |
|---|---|
| **Exceptional** | Remote code execution; access to underlying infrastructure |
| **Critical** | Acquire sensitive user data; full DB access; vertical privilege escalation; access to all/targeted user data; data loss |
| **High** | Access to random user data; **stored XSS with minimal user interaction**; user impersonation (1 user at a time) |
| **Medium** | Reflected XSS without user interaction; stored XSS requiring a lot of user interaction |
| **Low** | Reflected XSS without proven business impact; open redirect without proven business impact |

## Out of scope (do NOT report these)
- `idp.kuleuven.be` login/registration itself; **Pre-Auth Account takeover / OAuth squatting**
- **Self-XSS that can't be used to exploit other users**
- CORS on non-sensitive endpoints; missing cookie flags / security headers; low-impact CSRF
- Rate-limit bypass/absence; best-practice (password policy) violations
- Clickjacking without impact; CSV injection; session-not-invalidated; tokens leaked to third parties
- Email spoofing/SPF/DMARC/DKIM; content injection without HTML modification; username/email enumeration
- Email bombing; request smuggling without impact; homograph; XMLRPC; banner/version disclosure
- Metadata not stripped; same-site scripting; subdomain takeover without takeover
- Arbitrary file upload without proof of stored file; **Blind SSRF without proven business impact (pingbacks insufficient)**
- Disclosed Google Maps API keys; host-header injection without impact
- Duplicates; theoretical issues; DoS/DDoS/brute-force; EOL software; MITM/physical; 0-day within 14 days of patch

## Rules of engagement
- Report in Dutch or English; detailed but to-the-point repro; include a clear step-by-step attack scenario.
- **Do NOT exploit beyond proof:** collect only what's necessary to demonstrate the issue; if a small
  sample proves it, stop there. Handle any found data responsibly.
- Do not disclose before fixed. Respect scope, CoC, T&Cs.

## The primary attack plan — SAP OData IDOR / privilege escalation
SAP OData services expose entities by key; the program even shows enumerable IDs
(`SAP ID: IN00824795`, `Application ID: 000000430539`). The core question, exactly like the bank's
`GetAccountTransactions` lead but here **actually testable**:

> Does `ZC_AD_APPLICANT_SRV` authorize the authenticated caller against the requested entity key,
> or does it return any applicant's data to any logged-in user?

Recon-first steps (see VM brief):
1. Create the test account; capture the session/cookies the UI5 app uses to call OData.
2. Pull the OData **`$metadata`** document — the full entity model (EntitySets, keys, navigation
   properties, FunctionImports). This maps the entire API with no guessing.
3. For each EntitySet, note the key shape (is it your SAP ID? an application ID? enumerable integer?).
4. IDOR test: request an entity keyed to an identifier you do NOT own (your *second* test account's
   ID, or an adjacent ID) — **STOP at the first proof you can read a record that isn't yours**; do not
   enumerate or pull bulk data (program rule: prove with a small sample, go no further).
5. Also check: write ops (`POST`/`PUT`/`MERGE`/`DELETE`) and FunctionImports for missing
   authorization (data modification is an explicitly-wanted class); `$batch` endpoint for authz
   differences; property-level over-exposure ($select revealing fields the UI hides).

## Secondary surfaces
- **Stored XSS** in any applicant free-text field that is later rendered to staff/another user
  (stored XSS w/ minimal interaction = High). Self-XSS-only is out of scope — must reach another user.
- **UI5 frontend**: SAPUI5 apps sometimes expose client-side routing / unvalidated redirects; check
  the manifest and any URL-driven navigation. Arbitrary file read/write and script exec are wanted.
