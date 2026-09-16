# DigitalOcean — Authenticated SSRF-sink hitlist + surface triage (2026-09-16)

Derived from mining DO's published OpenAPI spec (93,772 lines) + live unauth triage. These
are the concrete, high-value tests to run **once a session exists** — no blind exploration.

## SSRF sinks (backend fetches a user-supplied URL) — reach 169.254.169.254 / ssrf-sheriff
Ranked by promise. All are in-scope API features; the in-scope metadata IP `169.254.169.254`
and DO's `ssrf-sheriff.internal.digitalocean.com` are the proof targets.

1. **Custom image import — `POST /v2/images`, field `url`** (spec line ~18629).
   Docs: "The URL ... to be imported into DigitalOcean" — backend downloads it.
   Tests: `url` = `http://169.254.169.254/latest/meta-data/iam/...`; and the strong one —
   a URL you control that **302-redirects** to metadata/internal (many downloaders validate
   the initial URL but follow redirects blindly). Also `file://`, `gopher://`, DNS-rebind.
   Likely partially hardened (old feature) — the redirect bypass is the angle.

2. **DOKS SSO `issuer_url`** (spec line ~61380) — Kubernetes cluster SSO OIDC config.
   When `enabled=true`, the backend almost certainly fetches
   `<issuer_url>/.well-known/openid-configuration` to validate. Point `issuer_url` at
   `http://169.254.169.254/` or `https://ssrf-sheriff.internal.digitalocean.com/?researcher=treyky`.
   Fresher, less-tested sink than image import. **Priority.**

3. **GenAI Knowledge Base data sources** (`/v2/gen-ai/knowledge_bases/{uuid}/data_sources`).
   KBs ingest data sources incl. web crawling → backend fetches URLs. Inspect the
   data_source schema in-account (web_crawler/base_url/spaces source); point at internal.
   Newest surface, least picked-over.

4. **Alert/notification Slack webhook `url`** (spec lines ~62991, ~67096) — backend POSTs to
   your URL. Blind SSRF w/o impact is EXCLUDED, so only worth it if it reaches an internal
   service with a demonstrable effect (POST to an internal admin endpoint, etc.).

5. **Managed-DB external source connection URLs** (Elasticsearch/Opensearch "connection URL",
   spec ~57836/57869) — if the backend connects to a user-supplied DB URL, internal-reachable.

## Unauthenticated surface — CLEARED (honest negatives)
Thorough unauth testing found no confirmed bug; the surface is hardened:
- **OAuth DCR** (`/v1/oauth/register`): open by design (RFC 7591) — NOT a bug. No metadata
  SSRF (server drops `logo_uri`/`jwks_uri`/`sector_identifier_uri`, no server-side fetch,
  flat latency incl. to 169.254.169.254). RFC 7592 client management is properly authz'd
  (cross-client read/delete/PUT all 401). All test clients registered were deleted (204).
- **`/authorize`**: defers all validation (redirect_uri match, PKCE) to post-login → the real
  OAuth tests need a session (documented in 01).
- **MCP fleet**: `/mcp` → 401 (auth enforced).
- **inference.do-ai.run**: `/v1/models` → 401, `/v1/chat/completions` → 405 on GET (POST,
  auth-gated). OpenAI-compatible; authenticated tests = model-name injection, cross-tenant
  model/agent access, prompt-injection-with-impact, SSRF via agent/KB config.
- **GraphQL**: `/api/graphql` → 401 (real, auth-gated); `/graphql` → catch-all HTML error.

## Subdomain / app triage (from crt.sh list)
| Host | Result | Note |
|---|---|---|
| marketplace.digitalocean.com | 200 | Next.js frontend; backend elsewhere (marketplace-grpc-*), no exposed /api. |
| sonar.digitalocean.com | 404 (Cloudflare) | Exists behind CF; gated. |
| looker/beta/appsail/mako/marina/cfaccesspoc/forum/gradient-sdk | 000 / timeout | Not externally reachable — internal or Cloudflare-Access gated. Good posture, not a lead. |
| console-<region>.digitalocean.com | 000 | Droplet console; gated. |
| *.internal.digitalocean.com (dctrack, localdev, lab-codd-admin) | CT-only | Internal DCIM/admin — SSRF *targets* if a sink lands (see hitlist). |

## Consolidated verdict
Unauthenticated: hardened, no bug. The opportunity is authenticated, and now precisely scoped:
1. **MCP/OAuth redirect_uri/PKCE/consent → account takeover** (Critical if it lands).
2. **SSRF** via image-import redirect bypass / DOKS `issuer_url` / GenAI KB — reach metadata.
3. **BOLA** across ~17 API families (integer IDs on Droplets/Images/Snapshots = enumerable).
4. **Token-scope** enforcement (`database:view_credentials`, `kubernetes:access_cluster`).
5. **GraphQL** introspection + global-ID IDOR.
All five need only a **bare logged-in account** (no paid resources) except image-import
(needs an image create, still free-tier-cheap) — so the card is the only gate, not spend.
