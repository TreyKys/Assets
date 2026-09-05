# Task — Firestore access-control check on Fusion (cross-tenant IDOR)

Per `VM-BRIEF-firestore-idor.md`. Fake, non-existent uids/channel-ids only — no real user data
touched at any point. `User-Agent: h1-treyky` on every request. Single requests, no enumeration.

## Probe A — unauthenticated read of a fake `Users/{uid}` doc

```
curl -s -i -A "h1-treyky" \
 "https://firestore.googleapis.com/v1/projects/exo-prod/databases/(default)/documents/Users/ZZZ_nonexistent_test_uid_treyky_0001"
```

**Result: `403`**
```json
{
  "error": {
    "code": 403,
    "message": "Missing or insufficient permissions.",
    "status": "PERMISSION_DENIED"
  }
}
```

## Probe B1 — anonymous-authed read of the same fake `Users/{uid}` doc

Fresh anonymous sign-up (`identitytoolkit accounts:signUp`) → `localId: hWKbgv6IiYZTuWkkcdyutcWf5B12`,
valid `idToken` obtained. Used it as `Authorization: Bearer <idToken>`:

```
curl -s -i -A "h1-treyky" -H "Authorization: Bearer $TOKEN" \
 "https://firestore.googleapis.com/v1/projects/exo-prod/databases/(default)/documents/Users/ZZZ_nonexistent_test_uid_treyky_0001"
```

**Result: `403`**
```json
{
  "error": {
    "code": 403,
    "message": "Missing or insufficient permissions.",
    "status": "PERMISSION_DENIED"
  }
}
```

## Probe B2 — anonymous-authed read of a fake `channels/{id}` doc

Same anon token, second collection:

```
curl -s -i -A "h1-treyky" -H "Authorization: Bearer $TOKEN" \
 "https://firestore.googleapis.com/v1/projects/exo-prod/databases/(default)/documents/channels/ZZZ_nonexistent_test_channel_treyky_0001"
```

**Result: `403`**
```json
{
  "error": {
    "code": 403,
    "message": "Missing or insufficient permissions.",
    "status": "PERMISSION_DENIED"
  }
}
```

## Interpretation

| Probe | Status | Meaning |
|---|---|---|
| A (unauth, `Users`) | 403 | denied |
| B1 (anon-auth, `Users`) | 403 | denied |
| B2 (anon-auth, `channels`) | 403 | denied |

All three land on row 1 of the brief's interpretation table (403/403) → **rules are
ownership-gated, not just `auth != null`-gated.** An anonymous (or unauthenticated) principal
cannot read another party's `Users` or `channels` document, even one that doesn't exist — Firestore
security rules are evaluating an ownership/ID-match condition (e.g. `request.auth.uid == uid`)
*before* existence is checked, which is the correct pattern and forecloses the cross-tenant IDOR
hypothesis this brief was built to test.

No FLAG condition was reached, so per the brief no write-test against a self-owned doc was
attempted, and no real uid/document was read, listed, or touched at any point.

## Verdict

**locked.** Firestore access control on both `Users` (per-user Fusion sync doc) and `channels`
(encrypted sync channel data) collections correctly denies non-owner reads for anonymous and
unauthenticated principals alike. Clean dead-end — this closes the Firestore/Fusion
cross-tenant-access chapter; no bug here.
