# KU Leuven test-account cookies (expiring session tokens)

Live session cookies for the two KU Leuven Admissions test accounts (`treyky@intigriti.me` /
`treyky+t2@intigriti.me` — Intigriti/Test names, no real data). SAP session tokens; they expire
on their own within hours of capture, so committing here is a short-lived convenience for the VM,
not a durable secret. If the VM's script starts returning `401`/`302` mid-run, capture fresh
cookies from DevTools (Application → Cookies → `webwsp.aps.kuleuven.be`) and overwrite these files.

## VM usage
```
cd ~/Assets && git pull
export A_COOKIES=~/Assets/intigriti/kuleuven_admissions/creds/A.cookies
export B_COOKIES=~/Assets/intigriti/kuleuven_admissions/creds/B.cookies
curl -b "$A_COOKIES" -H 'Accept: application/json' \
  'https://webwsp.aps.kuleuven.be/sap/opu/odata/sap/ZC_AD_APPLICANT_SRV/Applicants(%270%27)?sap-client=200'
```

Notes:
- The critical trio for SAP session auth is `MYSAPSSO2` + `SAP_SESSIONID_WSP_200` +
  `sap-usercontext`; the rest are supporting.
- `B.cookies` includes a device-fingerprint cookie whose *name* was truncated in the DevTools
  paste — the same 64-hex name as A was used. If B 401s and A works, that name is the first
  thing to double-check.
