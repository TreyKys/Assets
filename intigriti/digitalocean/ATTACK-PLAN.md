# DigitalOcean — Prioritized Attack Plan (VM-free)

All lanes below are web/API only — runnable from a laptop/phone with `curl` + a browser,
no VM. Every request MUST carry `X-BBP-Researcher: treyky` and stay ≤10 req/sec. Only ever
touch resources in YOUR OWN `@intigriti.me` account(s).

Grounded in recon of DO's public API docs (2026-09-16):
- ~17 API resource families take a resource ID in the path (BOLA/IDOR candidates) and expose
  write/state-changing ops: Droplets(19), Databases(71), Kubernetes(28), Block Storage(9),
  Floating/Reserved IPs, Load Balancers(10), Domains(4), Container Registry(18), Functions(13),
  Apps(38), Certificates(4), VPCs(10), Snapshots(3), CDN(6), Firewalls(11).
- API token scopes: `resource:action` pattern, 100+ granular scopes, plus alias scopes
  `api:read` (all reads) and `api:write` (full access). Sensitive scopes to probe:
  `database:view_credentials`, `kubernetes:access_cluster`, `droplet:admin`.
- Uptime monitor probes "any URL or IP" via HTTP/HTTPS/ICMP with no documented target
  validation → strong SSRF candidate.

---

## LANE 1 — API token scope enforcement (BEST first target)
**Why:** DO explicitly invites it ("Granularly scope your API tokens and check access
control"). Pure `curl`, no paid resources, self-contained in one account, clean pass/fail.
**Setup:** In one account, mint several tokens with deliberately narrow scopes.
**Battery (each = does the token do something OUTSIDE its scope?):**
1. Token with only `droplet:read` → attempt `POST /v2/droplets` (create), `DELETE`,
   `POST .../actions` (reboot). Expect 403. Any success = privilege escalation bug.
2. Token with `database:read` but NOT `database:view_credentials` → call the
   get-connection-details/credentials endpoint. If creds returned = scope bypass (High:
   sensitive-data exposure via broken scope).
3. Token with `kubernetes:read` but NOT `kubernetes:access_cluster` → request the
   kubeconfig/credentials endpoint. Creds returned = bypass.
4. `api:read` alias token → attempt any write across families. A single write that lands =
   the read-only alias is broken (high impact, affects everyone using "Read Only" tokens).
5. Cross-family: token scoped to `droplet:*` only → hit Databases/Apps/Registry write
   endpoints. Any that respond = scope isn't enforced per-family.
6. Scope on the token record vs. enforcement: create token via API with a `scopes` array
   containing an invalid/elevated/undocumented scope string — see if the backend accepts and
   honors it.
**PoC:** show the token's granted scopes (GET token info) side-by-side with the out-of-scope
call succeeding.

## LANE 2 — Broken authorization across Teams / Orgs (DO's #1 wanted bug, top $)
**Why:** "Broken authorization leading to access of other customer records" = Critical/
Exceptional tier. Teams are the account boundary; Orgs group Teams. Rich role model.
**Setup:** Two of your own accounts (Account A `@intigriti.me`, Account B `@intigriti.me`);
within an account, add the low roles (viewer/member) as a second identity.
**Battery:**
1. **Cross-Team object access (BOLA):** As Account B, capture a resource ID you own
   (droplet/db/app/etc.). As Account A, replay every `GET/PUT/DELETE /v2/<resource>/<B's-id>`.
   Any 2xx returning B's data or mutating B's resource = cross-tenant authz break (Critical).
   Iterate across all ~17 ID-taking families — enforcement is often inconsistent between
   newer and older families.
2. **Role privilege boundary within a Team:** as `viewer` (read-only role), attempt
   modifier/owner actions (create/delete resource, rotate token, invite member, change
   billing). As `biller`, attempt non-billing resource actions. Any action the role
   shouldn't allow = broken function-level authz.
3. **Org boundary:** if you can create an Org, test whether a team owner can reach another
   team's resources they aren't a member of, and whether org roles (admin/biller) can cross
   into team-owned resources improperly.
4. **Invite/membership flows:** race or manipulate team-invite acceptance, role assignment
   in the invite payload (can you self-assign `owner`?), or re-add a removed member with
   elevated role.
5. **ID-shape recon first:** note whether resource IDs are sequential ints, UUIDs, or
   guessable slugs — guessable IDs make BOLA far more impactful (no need to know B's ID).

## LANE 3 — SSRF via URL-fetch features
**Why:** DO runs an `ssrf-sheriff` proof endpoint = they know these vectors exist and pay
for them. `169.254.169.254` metadata is in scope as a target.
**Candidates (backend fetches a user-supplied target):**
1. **Uptime monitor** — create a check pointed at
   `https://ssrf-sheriff.internal.digitalocean.com/?researcher=treyky` (send
   `X-BBP-Researcher` if the check lets you set headers). Then try `http://169.254.169.254/`
   metadata paths, and `http://localhost/`, internal `.internal.digitalocean.com` hosts.
   HTTP/HTTPS/ICMP all allowed, no documented validation.
2. **Custom Images "import via URL"** — if the create-image flow accepts a URL, point it at
   the sheriff / metadata / internal hosts. (Confirm the flow in-account; docs URL moved.)
3. **App Platform / Functions outbound**, **Container Registry** external image pulls,
   **Agent Platform tool/webhook config**, **Uptime/alerting webhooks** — anywhere you paste
   a URL that the backend later calls.
**Impact bar:** blind SSRF w/o business impact is EXCLUDED. Aim to reach the sheriff
(returns a code) or metadata service, or pull an internal-only response — that's the
difference between "informational" and High/Critical.

## LANE 4 — AI / Inference surface (least picked-over)
**Why:** `inference.do-ai.run`, Agent Platform, Model Playground, Knowledge Bases,
Serverless Inference — newest products, 226 researchers have hammered the classic surface
far more than this.
**Angles:**
1. Authz on inference endpoints — can one account's token invoke/read another's
   agent/model/knowledge-base? (BOLA again, on new endpoints.)
2. SSRF via Agent "tools"/retrieval config or Knowledge Base "content sources" (do they
   fetch a URL you supply? → Lane 3 technique).
3. Prompt-injection *with a security consequence* (not just "model said a bad word") — e.g.
   injection that causes the agent to call a tool it shouldn't, leak another tenant's data,
   or exfiltrate via a tool. Pure jailbreaks are low/no value; tie it to data/authz impact.
4. Model import / 1-Click model deploy — supply-chain-ish: does importing a model let you
   run code or reach internal infra?

## LANE 5 — Control-panel web app (cloud.digitalocean.com) opportunistic
Only after the API lanes, and skipping the excluded classes:
- Stored XSS with cross-user impact (self-XSS excluded).
- IDOR in panel-only endpoints not covered by the public API (the panel calls internal
  APIs the docs don't list — proxy the browser and enumerate).
- Business-logic in billing/credits/coupon flows (careful: no fraud, just logic proof).

---

## Today's VM-free execution order
1. **Decide the credit-card question** (blocks account creation). If yes → register with
   `@intigriti.me`.
2. Once account exists: **Lane 1** (token scopes) — fastest clean win, no paid resources.
3. **Lane 2** BOLA sweep across families + role-boundary tests (create 2nd account/identity).
4. **Lane 3** Uptime-monitor SSRF at the sheriff (dramatic, self-proving PoC).
5. **Lane 4** if time — the freshest surface.

## Safety / hygiene
- `X-BBP-Researcher: treyky` on EVERY request. ≤10 req/sec.
- Own resources only; on any cross-account success, STOP at proof — never read/alter B's data.
- Spin DOWN every paid resource after testing (avoid charges — DO won't reimburse).
- Detailed reproducible reports (they refuse bounties on non-reproducible reports).
- One report per underlying issue; first repro wins on dupes.
