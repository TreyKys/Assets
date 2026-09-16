# DigitalOcean (Intigriti) — Program Vetting & Scope Notes

Vetted 2026-09-16. Researcher: treyky (username), `@intigriti.me` email required on all testing.

## Verdict: STRONG target, can start today, no VM required for the top lanes.

Unlike Bank J.Van Breda (blocked on real-customer onboarding), DigitalOcean has **no
eligibility wall**: you self-register and test your own account. This is the right pivot for
a VM-free session.

## Eligibility check (the thing that killed the bank)
- **Self-registration** at `https://cloud.digitalocean.com/registrations/new` with the
  `@intigriti.me` email. That is the entire gate.
- **Sanctions clause**: excluded only if resident in a comprehensively sanctioned country
  (Iran/NK/Cuba/Syria/Crimea-type per OFAC/EU/UN/UK). Nigeria is **not** on that list →
  eligible.
- **Friction point — credit card required.** Account creation needs a linked card. You get
  $5 non-expiring credit. DO will **not** reimburse charges beyond that, and you **must spin
  down any resources you create** or you get billed. NOTE: the highest-value lanes
  (authz/API-token/SSRF-config) need only a *bare account* — no paid resources spun up — so
  card risk is minimal if we stay in those lanes.

## Rules of engagement (hard constraints)
- Email: `@intigriti.me`. Required.
- Custom header encouraged on all requests: `X-BBP-Researcher: treyky` (helps them
  attribute our traffic as research, not an attacker — ALWAYS send it).
- Automated tooling capped at **max 10 requests/sec**.
- **Only test your own accounts/resources.** Targeting other DO customers' resources
  (Droplets, Spaces, DBs, etc.) is forbidden and repeat offenders get expelled.
- If you find an authz bypass that *could* reach another account, **stop** — prove the
  capability, do not actually pull another account's data.
- No DoS/DDoS/brute-force. No exfil of DO or customer content.
- No public disclosure / PoC videos without written consent.
- Create **dedicated** testing accounts; non-`@intigriti.me` accounts may be locked/banned
  for "perceived malicious activity."

## Payout (Tier 2 = higher, Tier 3 = lower). USD.
| Severity | Tier 2 min–max | Tier 3 min–max |
|---|---|---|
| Low (0.1–3.9) | $100–$450 | $50–$150 |
| Medium (4.0–6.9) | $700–$1,500 | $300–$500 |
| High (7.0–8.9) | $2,000–$4,000 | $600–$1,500 |
| Critical (9.0–9.4) | $5,000–$8,000 | $1,500–$3,000 |
| Exceptional (9.5–10) | $8,000–$10,000 | $3,000 |
- No CVSS; DO assesses impact+likelihood contextually. Good threat narrative = higher payout.
- Retest bonus: min $50, up to 10% of bounty, for validating a fix (and hunting bypasses).
- SLA: Exceptional/Critical 2 biz days, High 5, Medium/Low 15.

## In-scope assets that matter
**Tier 2 (higher pay):**
- `*.digitalocean.com` (wildcard — but see out-of-scope subdomain list)
- `cloud.digitalocean.com` — **main control panel**; file own-resource findings here.
- `amd.digitalocean.com` — same backend codebase as cloud.
- `api.digitalocean.com` — public REST API.
- `inference.do-ai.run` — Serverless Inference API (AI surface, newer).
- `marketplace.digitalocean.com`
- `www.digitalocean.com`
- `169.254.169.254` — **Droplet metadata service** (in scope! = valid SSRF target to reach).

**Tier 3 (lower pay):** `digitaloceanmirrors.com`, `digitaloceanpartners.com`,
`digitaloceanstatus.com`, `digitaloceantest.com`, `do.co` (shortlink),
`hackathon-tracker.digitalocean.com`, `hacktoberfest.com`.

## OUT OF SCOPE — do NOT touch (corrects an earlier bad assumption)
- **`*.digitaloceanspaces.com` — customer buckets, OUT OF SCOPE.** Earlier I floated "hunt
  exposed Spaces buckets" as a Firebase cousin — that is WRONG for this program. DO
  explicitly warns Shodan-style bucket scanning = testing customers = **expulsion**. The bug
  class here is flaws in DO's *own platform*, not customer data at rest.
- Other customer resources: `*.ondigitalocean.app`, `*.db.ondigitalocean.com`,
  `*.k8s.ondigitalocean.com`, `*.doserverless.co`, `registry.digitalocean.com/*`, any asset
  owned by another customer, any public IP in AS14061.
- `paperspace.com` (no bounty), `*.snapshooter.com` (out of scope).
- The GitHub repos (do-agent, droplet-agent, doctl = no bounty; others out of scope).
- Marketplace third-party vendor apps/add-ons.
- Long out-of-scope `*.digitalocean.com` subdomain list (anchor, brand, cloudsupport,
  deploy, email, events, go, groove, helpdesk, ideas, investor(s), ir, mirrors, pilot,
  rewards, segment, status, tracking, waves) — all OUT.

## What DO explicitly wants (top-payout targets)
- Broken authorization → access other customers' records.
- Process/hypervisor escape from a guest.
- RCE on core infra.
- Cross-VM / multi-tenancy breaks.

## Acceptable PoCs (use these exact, non-destructive proofs)
- Command exec: `whoami`, `hostname`, `uname`.
- File read: `/etc/hostname`.
- File write: `/tmp/bbp_treyky`.
- SQLi: `' OR 1='1` returns all rows / `' AND 0='1` returns none; may extract DB username.
- SSRF: hit their sheriff — `https://ssrf-sheriff.internal.digitalocean.com/` or
  `https://ssrf-sheriff.s2r1.internal.digitalocean.com/`, include `X-BBP-Researcher: treyky`
  header + username query param; success returns a unique code to paste in the report.

## Excluded bug classes (don't waste time)
Self-XSS; CORS on non-sensitive endpoints; missing headers/cookie flags; rate-limit
issues; clickjacking/tabnabbing/CSV injection; email spoofing/SPF/DMARC/DKIM; subdomain
takeover *without* actual takeover; blind SSRF w/o business impact; pre-auth ATO / OAuth
squatting; session non-invalidation; host-header injection w/o impact; known/duplicate
issues; theoretical issues; leaked secrets from 3rd-party lists (email security@ instead).
