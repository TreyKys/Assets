# Track A — Mobile app static config recon (Bank J.Van Breda & C°, Intigriti)

**Date:** 2026-09-19
**Scope:** `be.bankvanbreda.mobile` (VanBredaOnline) + `be.bankdekremer.mobile` (Bank de Kremer) Android APKs.
Zero interaction with live bank web/API infra in this session (Track B, separate).

## Task 1 — APK acquisition
Play Store direct download and the permitted mirrors (APKMirror/APKPure/APKCombo) are all behind
Cloudflare's managed JS challenge from this VM (no headless browser / adb / Google account available
here), so scripted acquisition wasn't possible. Confirmed both packages are live on Play Store
(`be.bankvanbreda.mobile` = "VanBredaOnline", `be.bankdekremer.mobile` = "Bank de Kremer") via the
store listing pages, then the user supplied both APKs directly (downloaded via their own browser,
transferred in). Both verified as valid Android packages (`file` → `Android package (APK), with
AndroidManifest.xml`, ~23MB each).

**Caveat:** both files are the **base module of an Android App Bundle**, not a universal/installable
APK — the manifest declares `android:requiredSplitTypes="base__abi,base__density"`, and there is no
`lib/` folder at all in either archive. The ABI-specific split (which carries the native runtime libs,
and very likely the compiled .NET/MAUI assemblies — see Task 3) was not available, so this analysis
covers only what ships in the base split. Task 2/3 results below should be read with that gap in mind.

## Task 2 — extract + scan
`openfirebase` is not published on PyPI (brief's own fallback anticipated this) — fell back to
`apktool d` (clean decompile, no errors) + manual grep sweep (Task 3) for both APKs.

- `be.bankvanbreda.mobile` — versionCode 104, versionName **2.21.2**
- `be.bankdekremer.mobile` — versionCode 104, versionName **3.21.2**

Both apps are built on **.NET MAUI / Xamarin** (`mono.MonoRuntimeProvider`,
`microsoft_maui_essentials_fileprovider_file_paths.xml`, `crc64*`-prefixed activity/service names).
The actual app logic (screens, API client, request building) lives in compiled C# assemblies that are
**not present in the base split we have** — they weren't found under `assets/` or anywhere else in
either decompiled tree. This is the main reason the URL/endpoint sweep below is thin: the real HTTP
client code isn't in this artifact. Getting the ABI split (or a full universal/XAPK bundle) would be
needed to recover it.

## Task 3 — manual grep sweep

### Firebase / Google config — found, real production projects
Both apps ship first-party (not third-party-SDK) Firebase projects, pulled from `res/values/strings.xml`:

| | VanBredaOnline (`be.bankvanbreda.mobile`) | Bank de Kremer (`be.bankdekremer.mobile`) |
|---|---|---|
| Firebase project ID | `vbol-smartphone-production` | `bdk-smartphone-production` |
| RTDB URL | `https://vbol-smartphone-production.firebaseio.com` | `https://bdk-smartphone-production.firebaseio.com` |
| Storage bucket | `vbol-smartphone-production.appspot.com` | `bdk-smartphone-production.appspot.com` |
| `google_api_key` / crash-reporting key | found, type Google API key (Firebase), location `res/values/strings.xml` | found, type Google API key (Firebase), location `res/values/strings.xml` |
| `google_app_id` | found, type Firebase app ID, location `res/values/strings.xml` | found, type Firebase app ID, location `res/values/strings.xml` |
| `default_web_client_id` (Google Sign-In OAuth client) | found, type OAuth client ID, location `res/values/strings.xml` | found, type OAuth client ID, location `res/values/strings.xml` |
| `gcm_defaultSenderId` | found, type FCM sender ID, location `res/values/strings.xml` | found, type FCM sender ID, location `res/values/strings.xml` |

These are the normal client-side Firebase config values Google's own SDKs expect apps to ship
(they're not secret by design — the actual security boundary is server-side Firebase Rules), so listing
the project IDs/URLs themselves isn't a finding; what matters is Task 4's rules check below.

**No Firestore SDK** is bundled in either app (`grep -c firestore` = 0 in both decompiled trees), so
no Firestore probe was applicable.

### Backend hosts found in the base split
Grepping for `bankvanbreda|bankdekremer|jvanbreda|vanbredacarfinance|vanbredavendor` domains across
both decompiled trees turned up **no results in the compiled code** (expected — the HTTP client living
in the missing assemblies), but the **AndroidManifest.xml deep-link / App Link intent-filters** name
these first-party hosts explicitly:

**VanBredaOnline (`be.bankvanbreda.mobile`):**
- `xs2a-api-web.bankvanbreda.be`
- `wero.bankvanbreda.be`
- `pub.mobile.bankvanbreda.be`
- `connective.bankvanbreda.be`
- `itsme.bankvanbreda.be` (with `pathPrefix` `/sharedata`, `/confirm` — itsme® identity-app handoff)

**Bank de Kremer (`be.bankdekremer.mobile`):**
- `xs2a-api-web.bankdekremer.be`
- `pub.mobile.bankdekremer.be`
- `itsme.bankdekremer.be`

All other URL-shaped strings in both trees are inert (Google/AndroidX/OkHttp/Gson/Guava library
metadata, license/proguard files, javadoc references — third-party SDK noise, not the bank's infra).

### Hardcoded secrets/keys sweep — clean
Broad grep for `secret|private_key|BEGIN (RSA|EC) PRIVATE KEY|client_secret|aws_access_key|Authorization: Bearer ...`
across both trees returned only SDK boilerplate: VASCO/OneSpan Digipass 2FA SDK method/constant names
(`calculateSecret`, `CLIENT_PRIVATE_KEY_*`, `SRP6VascoClient`/`SRP6VascoServer` — SRP6 challenge-response
crypto, no embedded key material) and `okio`/`javax.crypto` `SecretKeySpec` constructor calls (generic
crypto API usage, not a leaked value). **No actual hardcoded API keys, private key material, or bearer
tokens found** in either base split.

## Task 4 — Firebase rules check (read-only, single probe each, per playbook golden rules)
Used a nonexistent/fake path (not the real data tree) for each RTDB check, and a listing-only probe
for Storage, one request per target, user-agent `bugbounty-research-treyky-intigriti`:

| Target | Probe | Result |
|---|---|---|
| `vbol-smartphone-production` RTDB | `GET /bugbounty_treyky_nonexistent_probe_9f3a1c.json` | HTTP 423 — `"The Firebase database 'vbol-smartphone-production' has been deactivated."` |
| `bdk-smartphone-production` RTDB | same | HTTP 423 — `"The Firebase database 'bdk-smartphone-production' has been deactivated."` |
| `vbol-smartphone-production.appspot.com` Storage | `GET /v0/b/.../o?maxResults=1` | HTTP 404 — `Not Found` |
| `bdk-smartphone-production.appspot.com` Storage | same | HTTP 412 — GCP-side service-account/bucket-link error, not data exposure |

**Clean result — no open Firebase access.** Both Realtime Databases are deactivated outright (the
strongest possible negative — not just rule-locked, the DB resource itself is off). Neither Storage
bucket returned a listing; the responses are infrastructure-level errors, not content. No further
probing done (no anonymous-auth test run — not warranted once RTDB/Storage were both clean, and it
has a minor side effect of creating an object in their project for no signal gained).

## Task 5 — in-scope API host inventory (for Track B)

| Host | Tier / scope match | Notes |
|---|---|---|
| `xs2a-api-web.bankvanbreda.be` | Tier 1 — covers `web-xs2a.bankvanbreda.be` intent; **not the exact hostname listed in scope** (scope says `web-xs2a.bankvanbreda.be`, app manifest says `xs2a-api-web.bankvanbreda.be` — word order differs) | **Flag for scope clarification before testing** — looks like the same PSD2 XS2A service but confirm with the program before treating it as in-scope, since the literal hostname doesn't match the published scope string. |
| `xs2a-api-web.bankdekremer.be` | Same caveat, mirrored for Bank de Kremer | Same flag. |
| `pub.mobile.bankvanbreda.be` | Tier 1 (`*.mobile.bankvanbreda.be` wildcard) | Clean match, in scope. |
| `pub.mobile.bankdekremer.be` | Tier 1 (`*.mobile.bankdekremer.be` wildcard) | Clean match, in scope. |
| `wero.bankvanbreda.be` | Tier 2 (`*.bankvanbreda.be` wildcard) | Wero = pan-European instant-payment scheme; likely a payment-initiation deep link. |
| `connective.bankvanbreda.be` | Tier 2 (`*.bankvanbreda.be` wildcard) | Connective = Belgian e-signature vendor; third-party integration, but hostname itself is bank-owned subdomain. |
| `itsme.bankvanbreda.be` / `itsme.bankdekremer.be` | Tier 2 (`*.bankvanbreda.be` / `*.bankdekremer.be` wildcards) | itsme® identity-app handoff endpoint (`/sharedata`, `/confirm` paths) — bank-owned subdomain brokering to the itsme identity provider. |

None of these are Firebase/third-party-analytics hosts — every hostname found is a first-party
`bankvanbreda.be`/`bankdekremer.be` subdomain, already inside the published wildcard scope (modulo the
`xs2a-api-web` vs `web-xs2a` naming flag above). No out-of-scope or unexpected third-party backend was
uncovered.

## Summary
- Both APKs obtained and statically analyzed (base App Bundle split only — native/ABI split unavailable).
- Both apps: .NET MAUI/Xamarin, first-party production Firebase projects, but **both projects' RTDBs
  are deactivated and Storage buckets aren't open** — clean negative, no Firebase misconfig to report.
- No hardcoded secrets, private keys, or bearer tokens found.
- Host inventory compiled for Track B; one naming discrepancy (`xs2a-api-web.*` vs scope's `web-xs2a.*`)
  flagged for confirmation before any Track B testing touches it.
- Limitation: the missing ABI/native split means the actual .NET HTTP-client code (where hardcoded
  API base URLs would most likely live) wasn't available for review. If a full bundle/XAPK becomes
  available, re-running Task 3's grep sweep against it is the natural follow-up.
