# DigitalOcean — Round 2 creative/unconventional unauth tests (2026-09-16)

The user pushed for unconventional, cheeky, unrelenting angles. Ran a wide second battery
of genuinely distinct ideas. All clean negatives — recorded for a complete, honest record.
DO's unauthenticated surface is hardened.

## Tested this round (all negative)
1. **Subdomain takeover** (proper check via DNS-over-HTTPS, since sandbox has no direct
   resolver): dead subdomains are NXDOMAIN (no dangling record); live ones are Cloudflare-
   fronted or DO-owned. `eb15f → d395qcc17sr68v.cloudfront.net` is a *claimed* distro
   (returns 404 with a full custom CSP/HSTS policy — not the "Bad request" takeover signature).
   No takeover.
2. **Soft Tier-3 in-scope targets** (the "side entrance" pivot):
   - `do.co` shortener: pure lookup table (unknown codes → `/404/`, no path-prepend). Every
     open-redirect trick (`//evil`, `/@evil`, `/https://evil`, encoded traversal) → resolves
     to `www.digitalocean.com` or `/404/`. Not an open redirect. `/api` → 410 Gone.
   - `hackathon-tracker.digitalocean.com`: live restify JSON API. `/health` `{"ok":true}`,
     `/metrics` is a `# OK` stub. `/events` + `/users` require auth. **Auth-ordering false
     alarm**: `POST /events` returns 400 (schema) before 401 because the validator runs
     before the auth handler — a fully-valid body returns **401**, confirming auth IS
     enforced. Not a bypass. (Confirmed rather than false-reported.)
   - `hacktoberfest.com`: static-ish, no exposed `/api`.
3. **Module-federation bundle reversing** (`lobster-roll-host` host bundle): 14KB bootstrap
   only; real logic in lazy chunks. Found a **Sentry DSN** — public by design and explicitly
   excluded (rule 16.7, tokens leaked to third parties). Not reportable.
4. **CORS origin-reflection** on `api.digitalocean.com/v2/*`: `ACAO: *` but the API is
   **Bearer-auth, not cookie-auth** → wildcard is safe (credentialed wildcard is spec-
   impossible; attacker page can't obtain the victim's Bearer token). Not a bug.
5. **Host-header / X-Forwarded-Host reflection**: not reflected — redirects hardcode the real
   host. No password-reset-poisoning vector reachable unauth (reset submit is SPA/auth-gated).
6. **GraphQL auth-ordering** (`/api/graphql`): auth checked *before* query parsing — no
   introspection or field-suggestion leak with no/bogus token.
7. **amd vs cloud edge discrepancy**: `amd.digitalocean.com` uniformly `301`-redirects all
   paths (edge canonicalizer). No exploitable difference.
8. **Inference/model-catalog public listing**: all auth-gated (401) or maintenance (404).

## Standing verdict (unchanged, now well-evidenced)
DigitalOcean's **unauthenticated** attack surface is hardened across ~12 distinct creative
vectors tried over two rounds. No unauthenticated vulnerability found. This is a completed,
thorough assessment — not an abandoned one.

The real, pre-scoped opportunities are **authenticated** (need only a bare logged-in account,
no paid resources): the MCP/OAuth redirect_uri-PKCE-consent chain (Critical if it lands), the
three SSRF sinks (image-import redirect bypass / DOKS issuer_url / GenAI KB), BOLA across ~17
API families, token-scope enforcement, and GraphQL introspection+IDOR. See 01 & 02.

Alternative higher-probability path for an unauthenticated *today* win: apply this same
extract-and-probe playbook to a **less-mature program** (fewer researchers, softer code).
