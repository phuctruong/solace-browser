# 21 — Deployment Surface Mapping

```mermaid
flowchart TD
    SB[Repo: phuctruong/solace-browser] --> SBQA[Push branch qa]
    SB --> SBPROD[Push branch prod]
    SBQA --> BPIPE[Browser CI/CD pipeline]
    SBPROD --> BPIPE
    BPIPE --> BDL[downloads.solaceagi.com artifacts]
    BPIPE --> BUI[browser runtime surfaces]

    SA[Repo: phuctruong/solaceagi] --> SAQA[Push branch qa]
    SA --> SAPROD[Push branch prod]
    SAQA --> QTRIG[Cloud Build trigger: solaceagi-qa]
    SAPROD --> PTRIG[Cloud Build trigger: solaceagi]
    QTRIG --> QSVC[Cloud Run service solaceagi-qa]
    PTRIG --> PSVC[Cloud Run service solaceagi]

    QSVC --> QDOM[qa.solaceagi.com]
    PSVC --> DOM1[solaceagi.com]
    PSVC --> DOM2[www.solaceagi.com]
```

## Notes
- `www.solaceagi.com` app-store is served by Cloud Run service `solaceagi`.
- `solaceagi` and `solaceagi-qa` deploy from repo `phuctruong/solaceagi`, not `phuctruong/solace-browser`.
- Deployment claims must validate domain mapping + trigger source before QA sign-off.

