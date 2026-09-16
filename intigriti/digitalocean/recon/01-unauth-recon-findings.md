# DigitalOcean — Unauthenticated recon findings (2026-09-16)

Done from the session with `curl` (no account, no VM). All probes carried
`X-BBP-Researcher: treyky`, low volume. **Honest status: no confirmed vulnerability yet** —
every real test bottoms out at "needs a logged-in session." But this mapped a fresh,
under-tested, in-scope surface and pinpointed the exact authenticated tests worth doing.

## FINDING-LEAD 1 (STRONGEST): MCP fleet → cloud.digitalocean.com OAuth
**New surface.** CT logs + probing revealed a fleet of Model Context Protocol servers, all
in scope (`*.digitalocean.com`):
`accounts.mcp`, `droplet(s).mcp`, `databases.mcp`, `apps.mcp`, `functions.mcp`, `docr.mcp`,
`doks.mcp`, `codex.mcp`, `insights.mcp`, `gradient-ai.mcp`, `genai-batchinference.mcp`,
`genai-custom-models.mcp`, `genai-evaluation.mcp`, `genai-inferencerouter.mcp`,
`inference-modelcatalog.mcp`, `dedicated-inference.mcp`, `docs.mcp`.

- `/mcp` → `401 "missing or invalid bearer token"` (auth enforced — good hygiene).
- `.well-known/oauth-protected-resource` →
  `authorization_servers: ["https://cloud.digitalocean.com"]`. **All MCP auth delegates to
  cloud.digitalocean.com's OAuth** (Tier-2 in scope).
- `cloud.digitalocean.com/.well-known/oauth-authorization-server`:
  - `authorization_endpoint`: `/v1/oauth/authorize`
  - `token_endpoint`: `/v1/oauth/token`
  - **`registration_endpoint`: `/v1/oauth/register` (open Dynamic Client Registration)**
  - `token_endpoint_auth_methods_supported`: `["client_secret_post","none"]` (public clients)
  - `code_challenge_methods_supported`: `["S256"]` (PKCE advertised)
  - `grant_types`: `authorization_code`, `refresh_token`; `response_modes`: `query`

### What was tested unauth (and the honest verdict)
- **Open DCR confirmed**: `POST /v1/oauth/register` (unauthenticated) accepts arbitrary
  `redirect_uris` — external domains, `http://localhost`, multiple URIs per client. Missing
  `redirect_uri` → 400. **NOT a vuln by itself** — RFC 7591 DCR is designed to let a client
  declare its own URIs. (Registered 2 test clients to confirm, then DELETEd both via RFC 7592,
  `204`. No litter left.)
- **`/authorize` defers ALL validation to post-login**: unauth requests with a mismatched
  attacker `redirect_uri`, with no PKCE `code_challenge`, with path-traversal, and with a
  `victim.example.attacker.com` subdomain trick ALL return the same `302 → /login` carrying
  the request unchanged. So redirect_uri-matching and PKCE-enforcement can't be judged
  unauthenticated.

### THE authenticated tests to run (high value — do these first once logged in)
1. **redirect_uri exact-match at consent**: register client with `redirect_uris=[A]`, log in,
   drive `/authorize` with `redirect_uri=B` (attacker domain). If a code is issued to B →
   **auth-code theft → MCP account takeover (Critical)**. Also test: A + extra path, A as a
   prefix of an attacker host, `A.attacker.com`, `//attacker`, `\@` tricks, double-encoding.
2. **PKCE enforcement**: complete the flow WITHOUT `code_challenge`. If a code is issued and
   exchangeable without a verifier → PKCE downgrade (weakens all MCP clients).
3. **Consent/auto-approval**: does a freshly-registered arbitrary DCR client get shown a
   consent screen, or is it silently approved? Silent approval + any redirect_uri laxity =
   full chain.
4. **Scope escalation at token exchange**: request broader scopes than granted; try
   undocumented/elevated scope strings in the token request.
5. **Token audience confusion**: can a token minted for one MCP resource (e.g. `accounts`) be
   replayed against another (`databases.mcp`, `droplet.mcp`)? If audience isn't enforced →
   cross-service privilege.

## LEAD 2: GraphQL (needs auth)
- `cloud.digitalocean.com/api/graphql` → `401` (real, auth-gated GraphQL endpoint).
- `cloud.digitalocean.com/graphql` → generic HTML error page (catch-all, not live GQL).
- Panel ships a `graphql-client` module-federation remote → the authenticated app uses
  GraphQL heavily. Authenticated phase: introspection (map hidden mutations), node/global-ID
  IDOR, per-field authz, query batching/aliasing abuse.

## LEAD 3: /login open-redirect (needs auth / client-side)
`/login?redirect_url=<...>` returns 200 (SPA) with no server Location — the post-login
navigation is client-side. Revisit authenticated: if the SPA follows an off-origin
`redirect_url`, that's an open redirect (chainable into the OAuth/login flow).

## Subdomain / surface intel (from crt.sh, in scope unless noted)
- **Beta**: `beta.digitalocean.com`, `betastatus.digitalocean.com` — pre-release surface.
- **AI/Gradient**: `gradient-sdk.digitalocean.com`, `gradient-ai.mcp`, `appsail.digitalocean.com`.
- **Possible standalone apps**: `looker.digitalocean.com` (Looker BI — often SSO-gated, check
  auth), `sonar.digitalocean.com` (SonarQube?), `mako`, `marina`, `cfaccesspoc`.
- **Leaked in CT (internal, NOT reachable/testable directly, but useful SSRF targets later)**:
  `*.internal.digitalocean.com` — `dctrack*` (Sunbird dcTrack DCIM), `localdev.internal`,
  `lab-codd-admin.sfo3.internal`. If an SSRF is found, these are the internal hosts to reach.
- Regional consoles: `console-<region>.digitalocean.com` (VNC/console access surface).
- Out-of-scope reminder: `deploy`, `cloudsupport`, `events`, `go`, `ideas`, `status`, etc.

## security.txt
Confirms Intigriti is the channel; `security@digitalocean.com` for leaked-secret notices.

## Next-step recommendation
The single highest-value lead (MCP/OAuth account-takeover chain) is Critical-tier IF it
lands, targets a surface most of the 226 researchers haven't focused on, and requires only a
**bare logged-in account** (no paid resources) to test. That materially strengthens the case
for the account phase — and we now know the exact 5 tests to run, no blind exploration.
