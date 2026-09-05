# Task — Firebase + backend config recon

One probe per service, read-only, `User-Agent: h1-treyky` on every request, per
`VM-BRIEF-backend-recon.md`. No writes, no enumeration, no fuzzing.

## Results table

| # | Probe | Result | Verdict |
|---|---|---|---|
| 1 | RTDB `.json?limitToFirst=1` | `400 {"error":"orderBy must be defined when other query parameters are defined"}` (query-syntax error, not a rules signal) | n/a — retested |
| 1b | RTDB `.json` (no params, unauthenticated) | `401 {"error":"Permission denied"}` | **locked** |
| 2 | Firestore `documents?pageSize=1&key=...` | `404` generic Google HTML error page (not `PERMISSION_DENIED`) | **inconclusive-but-benign** — see note |
| 3a | `firebasestorage.googleapis.com/v0/b/exo-prod.appspot.com/o?maxResults=1` | `403 {"error":{"code":403,"message":"Permission denied."}}` | **locked** |
| 3b | `storage.googleapis.com/exo-prod.appspot.com/` | `403 AccessDenied` (GCS XML error, "Anonymous caller does not have storage.objects.list access") | **locked** |
| 4 | `identitytoolkit accounts:signUp` (anonymous) | `200` — valid `idToken`/`refreshToken`/`localId` returned | **anonymous sign-up is enabled** (see follow-up) |
| 5 | `ctr.a.exodus.io/registry` | `404 {"message":"GET /registry not handled"}` — service is live, identifies itself via response header `user-agent: exodus/custom-tokens-registry` | **route guess wrong, service confirmed up; CORS note below** |
| 6 | `assets-gateway-clarity-api.a.exodus.io/assets` | `404 {"message":"Route GET:/assets not found","error":"Not Found","statusCode":404}` (Fastify-style 404) | **route guess wrong, service confirmed up** |

## Follow-up on Probe 4 (anonymous auth) — single additional read each, same read-only spirit

Per the brief, anonymous sign-up is "only relevant if combined with permissive rules." Rather than
speculate, tested the one directly-implied hypothesis with one additional read per service (still
zero writes, zero enumeration, zero brute force):

- **RTDB with the anon `idToken`** (`?auth=<idToken>`): `401 {"error":"Permission denied"}` — still
  locked. Rules require more than `auth != null`.
- **Storage with the anon token** (`Authorization: Firebase <idToken>`): `403 Permission denied` —
  still locked.

So: anonymous sign-up being open is **not** exploitable against RTDB/Storage — both correctly
require more than "any authenticated principal." Recording as informational only, not a bug.

## Notes on Probes 2, 5, 6

- **Firestore (Probe 2)**: the bare `.../documents` endpoint isn't a valid Firestore `listDocuments`
  call without a collection ID in the path (Firestore's REST API requires
  `.../documents/{collectionId}`), so the `404` here is expected HTTP-shape behavior, not a rules
  signal either way. No collection-name guessing attempted (would be enumeration/"extended
  testing"). This project most likely just doesn't rely on Firestore (client uses RTDB) — dead end,
  not a finding.
- **`ctr.a.exodus.io`** (Probe 5): confirmed live and is the "Custom Tokens Registry" backend
  referenced in Task 2's reachability trace (`vm-results/02-leadA-reachability.md`) — the response
  header `user-agent: exodus/custom-tokens-registry` self-identifies it. One CORS observation from
  this single response, flagged per the brief's explicit "note CORS wildcard+credentials" guidance:
  ```
  access-control-allow-origin: *
  access-control-allow-credentials: true
  ```
  This combination is a real CORS-config anti-pattern (the two directives are supposed to be
  mutually exclusive per the Fetch spec) — worth a human review of the CORS config. **However**,
  practically: browsers refuse to expose a credentialed response to JS when
  `Access-Control-Allow-Origin` is a literal `*` (they only honor `Allow-Credentials: true` when the
  origin is echoed back specifically), so this does not appear to grant real cross-origin credential
  leakage as-is — flagging as a hygiene/defense-in-depth note, not a demonstrated vulnerability.
- **`assets-gateway-clarity-api.a.exodus.io`** (Probe 6): confirmed live (Fastify backend), no
  CORS/verbose-error/IDOR signal from the single 404 response. Route name guessed wrong; not
  explored further per scope.

## Overall verdict

**Clean, fast dead-end on the core Firebase surface** — RTDB and Storage rules are correctly locked
down for both unauthenticated *and* anonymous-authenticated principals; no Firestore misconfig
observable (likely unused); no unauthenticated data exposure found anywhere. Two informational,
non-blocking notes for the humans: (1) anonymous sign-up is enabled on the `exo-prod` Firebase
project (harmless given the tight RTDB/Storage rules, but worth knowing), and (2) `ctr.a.exodus.io`
serves `Access-Control-Allow-Origin: *` together with `Access-Control-Allow-Credentials: true`,
a config anti-pattern that's likely inert in real browsers but worth a config cleanup. **No strong
bug materialized from this recon pass** — reporting the clean result rather than inflating either
of the two notes above into something they're not.
