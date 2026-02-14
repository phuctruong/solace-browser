# Solace Browser Roadmap

**Timeline**: 7 weeks | **Investment**: $7,000 | **Phases**: 6

---

## Phase 1: Fork & Setup (Week 1)

**Goal**: Clone Thorium, verify build, establish project structure

**Tasks**:
- [ ] Clone Thorium source code
- [ ] Create solace-browser fork
- [ ] Add Solace branding (icons, version)
- [ ] Verify local compilation
- [ ] Create build scripts
- [ ] First commits to git

**Deliverables**:
- ✅ solace-browser repo initialized
- ✅ Compiles to binary: `./out/Release/solace-browser`
- ✅ Custom splash screen (Solace branding)
- ✅ Version: 0.1.0-alpha

**Timeline**: Week 1 (40 hours)
**Cost**: $1,000

---

## Phase 2: Episode Recording (Weeks 2-3)

**Goal**: Add native episode recording (like browser extension, but built-in)

**Tasks**:
- [ ] Hook DOM mutation observer
- [ ] Capture element interactions (click, type, navigate)
- [ ] Create snapshots (before/after each action)
- [ ] Serialize to Phase B episode format
- [ ] Store to ~/.solace/browser/episodes/
- [ ] Test with 10 sample episodes

**Deliverables**:
- ✅ Episodes recorded to JSON
- ✅ Snapshots canonicalized (Phase B format)
- ✅ Actions captured (navigate, click, type, etc.)
- ✅ Proof: 10 valid episodes generated

**Integration**:
- Import Phase B snapshot canonicalization
- Use Phase B action types (NAVIGATE, CLICK, TYPE)

**Timeline**: Weeks 2-3 (80 hours)
**Cost**: $2,000

---

## Phase 3: Reference Resolution (Week 4)

**Goal**: Extract semantic + structural selectors (RefMaps)

**Tasks**:
- [ ] Implement semantic selector extraction
  - aria-label, aria-describedby
  - data-testid, data-qa
  - placeholder, alt text
- [ ] Implement structural selector extraction
  - CSS selectors (id, class, attribute)
  - XPath expressions
  - Tag + position fallback
- [ ] Generate deterministic ref_id
- [ ] Build RefMap (Phase B format)
- [ ] Test: 100+ selectors

**Deliverables**:
- ✅ Semantic selectors extracted
- ✅ Structural selectors extracted
- ✅ RefMap JSON generated
- ✅ Test: 100% selector resolution rate

**Integration**:
- Use Phase B RefMap schema
- Compatible with Phase C replay

**Timeline**: Week 4 (40 hours)
**Cost**: $1,000

---

## Phase 4: Automated Posting (Week 5)

**Goal**: Add APIs to automate browser interactions

**Tasks**:
- [ ] API to fill form fields by ref_id
- [ ] API to click buttons by ref_id
- [ ] API to type text (handle shift for caps)
- [ ] API to verify action succeeded
- [ ] Handle rate limiting + timeouts
- [ ] Test: post to reddit.com (dry-run)

**Deliverables**:
- ✅ Form filling works
- ✅ Button clicking works
- ✅ Text typing works
- ✅ Dry-run: successful Reddit post (not submitted)

**Integration**:
- Works with recorded episodes
- Uses RefMap for selector resolution
- Compatible with marketing swarm

**Timeline**: Week 5 (40 hours)
**Cost**: $1,000

---

## Phase 5: Proof Generation (Week 6)

**Goal**: Add cryptographic proofs (Phase B integration)

**Tasks**:
- [ ] Hash episodes (Phase B canonicalization)
- [ ] Generate recipe IR (Phase B compiler)
- [ ] Create proof artifacts
  - episode_sha256
  - recipe_sha256
  - action_count
  - chain_hash
- [ ] Verify RTC (roundtrip)
- [ ] Sign with auth:65537

**Deliverables**:
- ✅ Proofs generated for all episodes
- ✅ RTC verified (encode/decode roundtrip)
- ✅ Offline verification works
- ✅ Cryptographic chain complete

**Integration**:
- Use Phase B snapshot canonicalization
- Use Phase B episode-to-recipe compiler
- Output matches Phase C expectations

**Timeline**: Week 6 (40 hours)
**Cost**: $1,000

---

## Phase 6: CLI Bridge (Week 7)

**Goal**: Connect Solace Browser to bash/Python CLI

**Tasks**:
- [ ] Create HTTP API (localhost:9999)
  - /record-episode
  - /play-recipe
  - /post-to-platform
  - /get-snapshot
  - /verify-interaction
- [ ] Create bash wrapper (solace-browser-cli.sh)
- [ ] Connect to solace_cli.sh
- [ ] Test from command-line
- [ ] Documentation

**Deliverables**:
- ✅ `solace-browser --record-episode`
- ✅ `solace-browser --play-recipe`
- ✅ `solace-browser --post-to-reddit`
- ✅ Works with bash scripting

**Integration**:
- Connect to existing solace_cli.sh
- Marketing swarm can use it
- Phase C replay can use it

**Timeline**: Week 7 (40 hours)
**Cost**: $1,000

---

## Phase 7: Marketing Integration (Week 8, Bonus)

**Goal**: Full integration with marketing games

**Tasks**:
- [ ] Test Reddit campaign workflow
- [ ] Test HackerNews posting
- [ ] Verify analytics hooks
- [ ] Marketing swarm integration
- [ ] Dry-run full campaign

**Deliverables**:
- ✅ Marketing campaigns executable via Solace Browser
- ✅ Reddit posting works (with approval gate)
- ✅ Analytics tracked
- ✅ Proofs generated

**Timeline**: Week 8 (optional, bonus phase)
**Cost**: Included in Phase 6

---

## Summary

| Phase | Deliverable | Hours | Cost | Timeline |
|-------|-------------|-------|------|----------|
| 1 | Fork + Setup | 40 | $1K | Week 1 |
| 2 | Episode Recording | 80 | $2K | Weeks 2-3 |
| 3 | Reference Resolution | 40 | $1K | Week 4 |
| 4 | Automated Posting | 40 | $1K | Week 5 |
| 5 | Proof Generation | 40 | $1K | Week 6 |
| 6 | CLI Bridge | 40 | $1K | Week 7 |
| **TOTAL** | **Production-ready browser** | **280** | **$7K** | **7 weeks** |

---

## Testing Strategy

### Each Phase Uses Verification Ladder

**641-Edge Tests** (Sanity)
- Basic functionality tests
- Example: "Does episode record successfully?"

**274177-Stress Tests** (Scaling)
- 100+ iterations
- Example: "Can we record 100 episodes deterministically?"

**65537-God Tests** (Approval)
- Full integration
- Example: "Can we post to Reddit + verify proof?"

---

## Success Criteria

- [ ] **Phase 1**: Compiles locally
- [ ] **Phase 2**: Episodes recorded + canonicalized
- [ ] **Phase 3**: Selectors extracted + 100% resolution
- [ ] **Phase 4**: Posting works (dry-run)
- [ ] **Phase 5**: Proofs generated + RTC verified
- [ ] **Phase 6**: CLI works from bash
- [ ] **Phase 7**: Marketing campaigns live

---

**Status**: 🟢 Ready to start Phase 1

