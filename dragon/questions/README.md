# Dragon Questions Database

Questions database for solace-browser project.

Location: `stillwater.jsonl` (JSONL format for streaming + append-only)

## Schema

```json
{
  "id": "q_001",
  "text": "What happens when solace-browser first starts?",
  "asker": "phuc",
  "project": "solace-browser",
  "glow": "G",
  "pillar": "P0",
  "date": "2026-02-26T12:00:00Z",
  "context": "ARCHITECTURAL_DECISIONS_20_QUESTIONS",
  "status": "ANSWERED",
  "answer_source": "diagrams/01-browser-startup-sequence.md"
}
```

**Fields:**
- `id`: Unique question ID (q_001, q_002, etc.)
- `text`: Full question text
- `asker`: Who asked (name or context)
- `project`: Which project (solace-browser, solaceagi, solace-cli, etc.)
- `glow`: Priority (G=green/foundational, L=learning, O=optional, W=wild/unknown)
- `pillar`: Problem pillar (P0=architecture, P1=implementation, P2=testing)
- `date`: ISO 8601 timestamp
- `context`: Where it came from (document, session, etc.)
- `status`: ASKED | ANSWERED | BLOCKED | DEFERRED
- `answer_source`: Where answer is documented

---

## Current Status

**20 Canonical Questions (ANSWERED):**
1. What happens when solace-browser first starts? ✅
2. How does cron fit in? ✅
3. First install experience? ✅
4. Is solace-browser private or OSS? ✅
5. Can you use browser for free? ✅
6. What's different in paid tier? ✅
7. What does solaceagi.com offer? ✅
8. FDA Part 11: What's required? ✅
9. What are solace apps? ✅
10. Can users upload solace apps? ✅
11. Can users request more solace apps? ✅
12. If you download a solace app, what can you do? ✅
13. Are you using diagram-first development? ✅
14. Do you have diagrams to answer all the above? ✅
15. Where are they located? ✅
16. Are the codex agents using them? ✅
17. Have you been adding to dragon questions DB? ✅
18. Do solaceagi docs/papers answer these 20 questions? ✅
19. Wouldn't diagram-first have solved this? ✅
20. Should all conflicting info go to scratch/? ✅

All answers documented in: `/home/phuc/projects/solace-cli/scratch/ARCHITECTURAL_DECISIONS_20_QUESTIONS.md`

---

## Adding New Questions

When new questions arise in sessions:
1. Append to `stillwater.jsonl` with status: ASKED
2. Reference in journal entry
3. Answer when discovered
4. Update status: ANSWERED
5. Link answer source

---

**Maintained by:** Dragon Rider Twin
**Last Updated:** 2026-02-26
