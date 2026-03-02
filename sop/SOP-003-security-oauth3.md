# SOP-003: Security and OAuth3 Authorization

| Field | Value |
|-------|-------|
| **SOP ID** | SOP-003 |
| **Title** | Security Controls and OAuth3 Authorization Management |
| **Version** | 1.0 |
| **Effective Date** | 2026-03-01 |
| **Author** | Phuc Truong (Dragon Rider, Authority 65537) |
| **Classification** | Internal — Part 11 Architected |
| **Regulatory Alignment** | NIST 800-53, FedRAMP, CMMC Level 2, SOC 2 Type II, GDPR, EU AI Act |

---

## 1. Purpose

This SOP defines the security controls and OAuth3 authorization framework for the Solace Browser platform. It maps Solace's built-in security features to multiple regulatory frameworks.

## 2. Regulatory Alignment Matrix

### 2.1 NIST 800-53 Control Mapping

| NIST Control Family | Solace Implementation | Status |
|--------------------|-----------------------|--------|
| **AC** (Access Control) | OAuth3 scoped tokens, TTL, revocation | Architected |
| **AU** (Audit) | Hash-chained evidence, ALCOA+ | Architected |
| **IA** (Identification/Auth) | API keys, access tokens, Firebase Auth | Implemented |
| **SC** (System Communications) | TLS 1.3, AES-256-GCM vault | Implemented |
| **SI** (System Integrity) | SHA-256 hash chains, sealed store | Implemented |
| **CM** (Configuration Mgmt) | Git-tracked config, immutable deploys | Implemented |
| **IR** (Incident Response) | Evidence preservation, chain break detection | Architected |
| **RA** (Risk Assessment) | Budget gates, step-up authorization | Implemented |

### 2.2 EU AI Act Risk Classification

| Classification | Criteria | Solace Status |
|---------------|----------|---------------|
| **Unacceptable Risk** | Social scoring, real-time biometric | NOT APPLICABLE |
| **High Risk** | Safety/fundamental rights impact | NOT APPLICABLE (general purpose) |
| **Limited Risk** | Transparency obligations | COMPLIANT (user sees preview before execution) |
| **Minimal Risk** | No specific obligations | PRIMARY CLASSIFICATION |

Solace Browser is classified as **Limited/Minimal Risk** under the EU AI Act because:
- Users ALWAYS see a preview before any action executes
- Users ALWAYS explicitly approve with identity + meaning
- Evidence trails are captured by default
- No biometric data processed
- No safety-critical decisions made

### 2.3 GDPR Alignment

| GDPR Principle | Solace Implementation |
|----------------|----------------------|
| **Lawfulness** | User explicitly approves each action |
| **Purpose Limitation** | OAuth3 scopes define exactly what data is accessed |
| **Data Minimization** | Recipes process only specified data |
| **Accuracy** | Hash chains verify data integrity |
| **Storage Limitation** | Configurable retention (7/90/365 days) |
| **Integrity & Confidentiality** | AES-256-GCM encryption, TLS 1.3 |
| **Accountability** | Evidence chains prove compliance |

### 2.4 FedRAMP / DoD IL Readiness

| Requirement | Status | Notes |
|------------|--------|-------|
| FedRAMP Low | Aligned | Local-first architecture reduces attack surface |
| FedRAMP Moderate | Partial | Needs continuous monitoring automation |
| DoD IL2 | Aligned | Non-CUI data, public cloud acceptable |
| DoD IL4 | Partial | Would need dedicated infrastructure |
| CMMC Level 1 | Aligned | Basic cyber hygiene practices met |
| CMMC Level 2 | Partial | Needs formal assessment |

## 3. OAuth3 Authorization Framework

### 3.1 Token Lifecycle

```
GRANT → ACTIVE → [STEP-UP] → ACTIVE+ → EXPIRE/REVOKE
```

| Phase | Description | Evidence Event |
|-------|-------------|---------------|
| **GRANT** | Token issued with specific scopes + TTL | `token_granted` |
| **ACTIVE** | Token valid for authorized operations | Per-operation audit |
| **STEP-UP** | High-risk operation requires re-consent | `step_up_requested` |
| **ACTIVE+** | Elevated permissions for single operation | `step_up_granted` |
| **EXPIRE** | TTL exceeded, token invalidated | `token_expired` |
| **REVOKE** | Manual or automatic revocation | `token_revoked` |

### 3.2 Scope Hierarchy

| Scope Level | Example | Risk | Requires Step-Up |
|------------|---------|------|-----------------|
| Read | `gmail.read.inbox` | Low | No |
| Draft | `gmail.draft.create` | Medium | No |
| Send | `gmail.send` | High | YES |
| Delete | `gmail.delete` | Critical | YES + confirmation |

### 3.3 Budget Gates (6 Fail-Closed Gates)

| Gate | Purpose | Fail Behavior |
|------|---------|--------------|
| B1: Action Cap | Max operations per session | BLOCKED |
| B2: Spend Cap | Max cost per session | BLOCKED |
| B3: Time Cap | Max duration per session | BLOCKED |
| B4: Rate Limit | Max operations per minute | THROTTLED |
| B5: Cross-App MIN | Lowest budget across partner apps | BLOCKED |
| B6: Step-Up Gate | High-risk requires re-consent | APPROVAL_REQUIRED |

## 4. Encryption Standards

| Context | Algorithm | Key Length | Standard |
|---------|-----------|-----------|---------|
| Token Storage (CLI) | AES-256-GCM | 256-bit | NIST SP 800-38D |
| Key Derivation | PBKDF2-HMAC-SHA256 | 600K iterations | NIST SP 800-132 |
| Evidence Hashing | SHA-256 | 256-bit | FIPS 180-4 |
| Transport | TLS 1.3 | 256-bit | RFC 8446 |
| Token Storage (Browser) | Memory only | N/A | Cleared on session end |

## 5. Sealed Store Security

### 5.1 Why No Plugins

The sealed store model (no third-party code) is a direct response to the OpenClaw ClawHub incident (Feb 2026) where ~20% of store entries delivered malware. Solace's approach:

| Feature | OpenClaw (Open Store) | Solace (Sealed Store) |
|---------|----------------------|----------------------|
| Third-party code | YES (anyone can publish) | NO (we implement) |
| Malware rate | ~20% (ClawHavoc campaign) | 0% (no external code) |
| Code review | Community (optional) | Mandatory (rung 641+) |
| Audit trail | None | Hash-chained evidence |
| Revocation | Manual takedown | Instant, cross-vertex |

### 5.2 Store Submission Process

```
User suggests → Solace implements → Rung 641 QA → Hub review → Rung 274177 → Public store
```

No user-submitted code ever executes. Users suggest, we implement.

## 6. Incident Response

### 6.1 Security Incident Classification

| Severity | Example | Response Time | Escalation |
|----------|---------|--------------|-----------|
| P0 Critical | Token compromise, data breach | 1 hour | CEO + Legal |
| P1 High | Evidence chain break, auth bypass | 4 hours | Engineering Lead |
| P2 Medium | Budget gate failure, scope violation | 24 hours | On-call engineer |
| P3 Low | UI issue, non-security bug | 72 hours | Normal triage |

### 6.2 Response Procedure

1. **DETECT** — Automated monitoring or user report
2. **CONTAIN** — Revoke affected tokens, halt affected operations
3. **PRESERVE** — Capture all evidence (never delete)
4. **INVESTIGATE** — Root cause analysis with evidence chain
5. **REMEDIATE** — Fix, test, deploy
6. **COMMUNICATE** — Notify affected users per regulatory requirements
7. **DOCUMENT** — Incident report with timeline, root cause, remediation

## 7. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-01 | Phuc Truong | Initial release |
