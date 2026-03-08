=== SKILL: FALLBACK-BAN (ABSOLUTE LAW) ===

These are BANNED in production code and architecture:
- NO "except Exception: pass" — stop and fix instead
- NO "except Exception: return None/""/{}/[]" — raise the error
- NO fake data, mock responses, or placeholder success
- NO silent degradation — if a service is down, FAIL LOUDLY
- NO broad exception catches — catch SPECIFIC exceptions only

When reviewing: flag ANY instance of silent failure, catch-all exceptions, or graceful degradation that hides real errors.
