# Paper 49: Cloud Tunnel Security — Remote Browser Control
# DNA: `tunnel(outbound_only, device_key, scope_gated) = remote_control(pro+) + audit_trail(always)`
# Forbidden: `INBOUND_PORTS | PLAINTEXT_TUNNEL | UNBOUNDED_SCOPE | UNAUDITED_COMMAND`
**Date:** 2026-03-07 | **Auth:** 65537 | **Status:** CANONICAL
**Applies to:** solace-browser, solaceagi
**Cross-ref:** Paper 47 (sidebar), Paper 48 (companion), Paper 38 (remote-browser-control-tunnel)

---

## 1. The Problem

Users want to monitor and control local browser sessions from their phone, another computer, or a team dashboard. Currently only works on the local machine.

## 2. The Solution: Secure Reverse Tunnel

Companion app establishes an OUTBOUND-ONLY encrypted tunnel to `solaceagi.com`. No inbound ports opened.

```
[solaceagi.com dashboard]
  | HTTPS/WSS (encrypted)
  v
[solaceagi.com tunnel relay]
  | Reverse tunnel (outbound from user's machine)
  v
[Companion App (Tauri)]
  | localhost:8888 API (same token auth)
  v
[Solace Browser sessions]
```

## 3. Device Keypair + Pairing

- Generated via ECDH P-256 on first Tauri launch
- Private key in OS keychain (never exported)
- Pairing: 6-digit code (5-min TTL) entered on solaceagi.com
- ECDH key exchange derives AES-256-GCM session keys
- Revocation list maintained server-side

### Brute-Force Protection
- Max 5 wrong attempts -> 15-min lockout + email notification
- 1 guess/second/IP with exponential backoff
- HOTP counter (no 6-digit reuse)
- All attempts audit-logged

## 4. Scope Gating

Cloud commands CANNOT exceed locally-granted OAuth3 scopes. Every tunnelled command is logged in the evidence chain (hash-chained, tamper-evident).

## 5. Pricing

| Feature | Free | Starter | Pro+ |
|---------|------|---------|------|
| Remote view/control | No | No | Yes |
| Remote run apps | No | No | Yes |
| Team sharing | No | No | Team+ |

## 6. Kill Switch

User can disconnect tunnel instantly from companion app system tray or from solaceagi.com account settings.

---

*Paper 49 | Auth: 65537 | Pro+ Feature | Outbound-Only*
