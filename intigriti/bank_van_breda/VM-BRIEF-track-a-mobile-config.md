# VM BRIEF — Bank J.Van Breda (Intigriti) — Track A: mobile app / config recon

You are the execution agent. **This is a real bank's live bug bounty program — be conservative.**
This session covers **Track A only**: static analysis of the two mobile apps. Do NOT touch the
bank's live web/API infrastructure (`secure.*`, `web-xs2a.*`, etc.) in this session — that's Track B,
gated on test credentials we don't have yet. Track A needs zero interaction with the bank's live
systems; it only touches public app binaries from the Play Store.

## Program rules (read fully — this is a real financial institution)
- In scope: `*.mobile.bankdekremer.be`, `*.mobile.bankvanbreda.be`, the two Android apps
  (`be.bankvanbreda.mobile`, `be.bankdekremer.mobile`), two iOS apps, `secure.bankdekremer.be`,
  `secure.bankvanbreda.be`, `web-xs2a.bankvanbreda.be` (Tier 1); `*.bankdekremer.be`,
  `*.bankvanbreda.be`, `*.vanbredacarfinance.be`, `secure.vanbredavendor.com`, `vpn.jvanbreda.be`
  (Tier 2). Anything else is OUT OF SCOPE.
- Any test account/registration must use an **@intigriti.me** email (program requirement).
- Max 5 requests/sec for automated tooling — N/A this session (no live requests planned).
- **Never** touch real customer accounts or data. **Never** attempt DoS, brute-force, social
  engineering, or physical/MITM attacks. Personnel of the bank are excluded from participating.
- Safe harbor applies only within scope and these rules.
- Do not discuss or disclose anything about this program outside of it.
- Commit findings to `intigriti/bank_van_breda/vm-results/`. Do NOT submit anything anywhere.

## Task 1 — get both APKs
```
# From the Play Store (on the VM, via a browser/adb, or download links you can reach):
#   be.bankvanbreda.mobile
#   be.bankdekremer.mobile
# If direct Play Store download isn't practical from the VM, use a reputable APK mirror
# (APKMirror/APKPure) ONLY for these exact package names/versions — verify package name matches.
mkdir -p ~/bvb_apks && cd ~/bvb_apks
# place bankvanbreda.apk and bankdekremer.apk here
```

## Task 2 — extract + scan each APK
```
pip install --user pipx 2>/dev/null; pipx install openfirebase 2>/dev/null || pip install --user openfirebase
sudo apt -y install apktool
# jadx (decompiler) if not present:
# download latest release from github.com/skylot/jadx or apt if available

for apk in bankvanbreda bankdekremer; do
  openfirebase --apk ~/bvb_apks/${apk}.apk --output ~/bvb_apks/${apk}_openfirebase.json 2>&1 | tee ~/bvb_apks/${apk}_openfirebase.log
  apktool d ~/bvb_apks/${apk}.apk -o ~/bvb_apks/${apk}_decompiled -f
done
```

## Task 3 — manual grep sweep (in case OpenFirebase misses something, or isn't installable)
```
for apk in bankvanbreda bankdekremer; do
  echo "=== $apk ==="
  grep -rniE "firebaseio|firebaseapp|appspot|google-services|databaseURL|apiKey|api_key|AIza[0-9A-Za-z_-]{35}" ~/bvb_apks/${apk}_decompiled 2>/dev/null | head -30
  grep -rniE "https?://[a-z0-9.-]*\.(bankvanbreda|bankdekremer|jvanbreda|vanbredacarfinance|vanbredavendor)\.[a-z]+" ~/bvb_apks/${apk}_decompiled 2>/dev/null | sort -u | head -50
  # any other backend hosts referenced (helps map Track B's real API surface)
  grep -rnoE "https?://[a-zA-Z0-9.-]+\.[a-z]{2,}(/[a-zA-Z0-9._~:/?#\[\]@!$&'()*+,;=%-]*)?" ~/bvb_apks/${apk}_decompiled 2>/dev/null | sed -E 's#https?://([^/]+).*#\1#' | sort -u | grep -viE "schemas.android|w3.org|apache.org|google.com/(fonts|apis)$" | head -60
  # hardcoded secrets / keys / tokens (broad net, triage manually)
  grep -rniE "secret|private_key|BEGIN (RSA|EC) PRIVATE KEY|client_secret|aws_access_key|Authorization: Bearer [A-Za-z0-9._-]{20,}" ~/bvb_apks/${apk}_decompiled 2>/dev/null | grep -viE "\.smali:.*(R\$|resource|string/)" | head -30
done
```

## Task 4 — IF a Firebase project is found, check rules (read-only, single probe each — see
`firebase_hunt/PLAYBOOK.md` for the exact request templates). Use a FAKE/non-existent doc id for
any Firestore/RTDB read test, per that playbook's golden rules. If nothing Firebase-related turns
up, say so plainly — many banks don't use Firebase and that's a fine, fast result.

## Task 5 — inventory the real backend API surface (feeds Track B later)
From Task 3's host list, compile: which hostnames are in-scope (Tier 1/2 lists above) vs
out-of-scope (third-party SDKs — analytics, crash reporting, ad networks — these are NOT the
bank's own infra, don't test them). Note any API base URL that looks like it serves
`web-xs2a.bankvanbreda.be` or similar transaction/account data — that's the priority target for
Track B once we have test credentials.

## Output
`intigriti/bank_van_breda/vm-results/01-mobile-config-recon.md`: what was found per APK — any
Firebase config + rules-check result, any hardcoded secrets (redact/truncate anything sensitive
in the report itself, just note "found, type X, location Y"), and the compiled in-scope API host
inventory for Track B. If nothing notable, report that plainly — a clean result here is still a
useful, fast answer.
