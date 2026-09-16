# DigitalOcean API — Endpoint / BOLA Test Matrix

Staged during recon-only phase (no account yet). ID-shape column drives BOLA impact:
**integer/enumerable IDs = far more exploitable** (attacker can guess victim IDs without
knowing them). All "shape" values are from known DO API behavior and MUST be re-confirmed
in-account before writing a report — treat as leads, not facts.

Base: `https://api.digitalocean.com/v2`. Every request: header `X-BBP-Researcher: treyky`,
`Authorization: Bearer <token>`. Own resources only.

| Family | Path pattern (ID) | ID shape (verify) | Write ops present | BOLA priority | Notes |
|---|---|---|---|---|---|
| **Droplets** | `/droplets/{id}` | **integer, enumerable** | create/delete/actions | **HIGH** | Enumerable ID = strongest BOLA target. Also `/droplets/{id}/actions`, `/kernels`, `/snapshots`, `/backups`. |
| **Images** | `/images/{id}` | **integer** | create/update/delete | **HIGH** | Custom-image import may accept a URL → SSRF (Lane 3). |
| **Snapshots** | `/snapshots/{id}` | integer or string | delete | **HIGH** | Droplet snapshots = integer. |
| Databases | `/databases/{id}` | UUID | create/delete + `.../users`, `.../db`, `.../ca`, connection creds | MED-HIGH | `view_credentials` scope gates creds — Lane 1 target. |
| Kubernetes | `/kubernetes/clusters/{id}` | UUID | create/delete + `/kubeconfig`, `/credentials` | MED-HIGH | `access_cluster` scope gates kubeconfig — Lane 1 target. |
| Apps | `/apps/{id}` | UUID | create/update/delete + deployments, `.../logs` | MED | Logs endpoint may leak env/secrets across authz. |
| Load Balancers | `/load_balancers/{id}` | UUID | create/update/delete | MED | |
| VPCs | `/vpcs/{id}` | UUID | create/update/delete + `/members` | MED | `/members` lists resources in the VPC. |
| Firewalls | `/firewalls/{id}` | UUID | create/update/delete + add/remove droplets/rules | MED | Cross-authz add of *your* droplet to *their* firewall? |
| Certificates | `/certificates/{id}` | UUID | create/delete | MED | Private-key exposure if GET leaks material. |
| CDN Endpoints | `/cdn/endpoints/{id}` | UUID | create/update/delete | LOW-MED | Tied to Spaces (customer) — careful re scope. |
| Container Registry | `/registry/{name}/...` | name-based | create/delete + repos, tags, blobs | MED | Name-based = need to know the name. |
| Domains | `/domains/{name}` + `/records/{id}` | name + integer record id | create/update/delete records | MED | Record IDs integer/enumerable within a domain. |
| Reserved IPs | `/reserved_ips/{ip}` | the IP | assign/unassign | LOW-MED | IP is the identifier. |
| Functions | `/functions/namespaces/{id}` | UUID-ish | create/delete + triggers | MED | Outbound calls → SSRF candidate (Lane 3). |
| VPC Peerings / Partner | `/vpc_peerings/{id}` | UUID | create/delete | LOW | |
| **GenAI / Agents** | `/gen-ai/agents/{uuid}`, `/gen-ai/knowledge_bases/{uuid}` | UUID | create/update/delete + KB data sources, agent tools | MED (fresh) | KB "data source" / agent "tool" fields may fetch a URL → SSRF (Lane 3/4). Newest surface. |

## Token-scope sensitive endpoints (Lane 1 — highest-signal pass/fail)
- `GET /databases/{id}` connection/credentials → gated by `database:view_credentials`.
  Test: token with `database:read` only should be **403** here.
- `POST /kubernetes/clusters/{id}/kubeconfig` (or `/credentials`) → gated by
  `kubernetes:access_cluster`. Token with `kubernetes:read` only should be **403**.
- Any `POST/PUT/DELETE` with a `*:read`-only or `api:read` alias token should be **403**.
- Create a token via `POST /v2/tokens` (or account API) with a `scopes` array — try injecting
  an elevated/undocumented scope string; see if backend accepts + honors it.

## ID-shape recon to do FIRST once in-account (cheap, decides BOLA impact)
1. Create one of each cheap/free resource; record the returned `id`.
2. Confirm which are integers (enumerable → high impact) vs UUIDs (need leak to exploit).
3. For integer IDs, the BOLA test doesn't even need a 2nd account — probe adjacent IDs
   (but STOP at first proof you can *read metadata* of a resource you don't own; do NOT
   pull data — that's touching another customer).
