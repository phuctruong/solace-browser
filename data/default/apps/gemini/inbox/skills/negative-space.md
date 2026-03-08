=== SKILL: NEGATIVE-SPACE (Find What's Missing) ===

What is NOT in the spec is often MORE IMPORTANT than what IS there.

Check for these absences:
1. Missing error paths: What happens when [X] fails? Is there a defined recovery?
2. Missing security boundaries: What's NOT validated? What's NOT authenticated?
3. Missing user flows: What if the user closes the app mid-operation? What if they have no internet?
4. Missing edge cases: Empty state, first run, 1000th run, concurrent access, out of disk space
5. Missing migration: How do v1.0 users upgrade to v2.0? Data format changes?
6. Missing monitoring: How do operators know when something is broken?
7. Forbidden patterns that should be EXPLICITLY banned (not just not mentioned)
