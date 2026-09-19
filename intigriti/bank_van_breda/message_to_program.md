Draft message to send via Intigriti's platform messaging to the Bank J.Van Breda program
(not the physical/customer contact form — this is a direct researcher-to-program message)

Upgraded version — references the concrete Track A2 findings as leverage for a credential grant.

---

Hi,

I'm a registered researcher on your program (username: treyky). I've completed a full static analysis
of both mobile apps (be.bankvanbreda.mobile / be.bankdekremer.mobile) and have identified specific,
high-value authenticated tests I'd like to run — but I'm blocked on account access.

The onboarding path you've described requires Belgian self-employed / entrepreneur / liberal-profession
eligibility, which I don't meet as an international researcher (and it would mean becoming a real
paying customer for what's meant to be security testing). Would you be able to provide read-only
test/sandbox credentials instead — ideally two test accounts, or access to a training/acceptance
environment if one is externally reachable?

To show this is concrete and not a fishing request, the exact tests I have ready (all in-scope,
non-destructive, own-data-only):

1. Stored XSS in Conversations messaging — the client renders message bodies through
   WebUtility.HtmlDecode into a JavaScript-enabled WebView with a native bridge and no output
   encoding. I've confirmed the client-side injection sink from the decompiled code; I need an account
   to verify whether the server sanitizes on store/return and whether cross-customer messaging is
   reachable.
2. Access-control (IDOR) on GetAccountTransactions and five sibling endpoints that accept a
   client-supplied AccountID — the exact broken-authorization class your policy calls out as welcome.

I'm happy to work within any constraints (specific test accounts, a monitored window, scoped hosts).
Two accounts would let me safely demonstrate cross-customer impact without ever touching a real
customer's data.

If verifying these internally is complex or time-consuming on your side, providing me with one or two
read-only test/sandbox accounts would let me complete the verification myself, document the full
reproduction with evidence, and continue hunting the related authenticated surfaces for further issues
— testing only my own accounts and never touching real customer data.

Thanks,
treyky
