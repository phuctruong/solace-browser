# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |
| < 1.0   | No        |

## Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, email: **phuc@phuc.net**

Include:
- Description of the vulnerability
- Steps to reproduce
- Impact assessment
- Suggested fix (if any)

We will acknowledge within 48 hours and provide a fix timeline within 7 days.

## Security Architecture

Solace Browser is built with security as a foundational requirement:

- **OAuth3 Governance**: All browser actions require scoped, time-bound, revocable agency tokens
- **4-Gate Cascade**: Token exists? Not expired? Has scope? Step-up confirmed?
- **Step-Up Authorization**: Destructive actions (delete, send, execute) require re-confirmation
- **Path Traversal Prevention**: All file operations validated against allowlist
- **Command Blocklist**: Terminal execution uses hard-coded blocklist (never overridable)
- **Evidence Chains**: SHA-256 hash-chained audit trails for all actions
- **Fail-Closed**: When in doubt, deny (403)

## Scope

The following are in scope for security reports:
- OAuth3 token bypass or escalation
- Path traversal in machine access layer
- Command injection in terminal execution
- Session hijacking or token leakage
- Evidence chain tampering
- Step-up authorization bypass

## Hall of Fame

Security researchers who responsibly disclose vulnerabilities will be credited here.
