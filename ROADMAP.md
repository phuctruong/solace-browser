# SOLACE-BROWSER ROADMAP v1.0
**Status:** Architecture → Build Phases (OSS)
**Last Updated:** 2026-02-25
**Rung Target:** 65537 (community-driven, production-ready)
**Architecture Reference:** Phuc Forecast + OAuth3 Reference Impl
**Build Model:** OAuth3 Core → Browser Automation → Recipe Engine → Composition → Store → Multi-Platform

---

## ROADMAP PHILOSOPHY

Solace Browser proves three things:

1. **OAuth3 is feasible** (not vaporware)
   - Scoped tokens (user grants agent specific permissions)
   - Revocable (user can stop agent mid-action)
   - Auditable (every action logged, hash-chained)

2. **Browser automation + recipes = high-margin business**
   - Hit rate economics: 70% recipes → 70% cost reduction
   - Recipes compound (community submissions raise hit rate)
   - Durable capital (recipes don't need retraining)

3. **Open source + community = defensible moat**
   - GitHub stars (5,000+ target)
   - Recipe submissions (50+/month target)
   - External OAuth3 adopters (1+ by Q4 2026)

---

## PHASE 0: FOUNDATION (1 Session)
**Goal:** Directory structure, docs, skeleton
**Rung:** 641 (lint + tests pass)
**Dependencies:** None (START HERE)

### Workstreams

#### 0.1 Directory Structure
```
solace-browser/
  ├── src/
  │   ├── oauth3/          # OAuth3 implementation
  │   ├── browser/         # Playwright wrapper
  │   ├── recipes/         # Recipe engine
  │   ├── triplets/        # PM Triplet models
  │   └── util/            # Crypto + evidence
  ├── recipes/             # Canonical recipes
  ├── tests/               # Unit + integration
  ├── docs/                # API docs + spec
  ├── NORTHSTAR.md
  ├── ROADMAP.md
  ├── CLAUDE.md
  ├── README.md
  └── scratch/
      └── todo/            # Phase checklists
```

#### 0.2 Documentation
- NORTHSTAR.md (vision + metrics)
- CLAUDE.md (project constraints)
- ROADMAP.md (this file)
- README.md (developer quickstart)
- docs/oauth3-spec.md (OAuth3 reference)
- docs/recipe-format.md (Prime Mermaid format)

#### 0.3 Skeleton
- `src/oauth3/__init__.py` + imports
- `src/browser/__init__.py` + imports
- `src/recipes/__init__.py` + imports
- `src/triplets/__init__.py` + imports
- `tests/conftest.py` (pytest fixtures)
- `tests/unit/__init__.py`
- `.github/workflows/test.yml` (CI/CD)

### Acceptance Criteria (Rung 641)
- [ ] Directory structure created
- [ ] Documentation complete (README, NORTHSTAR, ROADMAP, CLAUDE)
- [ ] All code lints clean (black, flake8)
- [ ] All imports work (no circular dependencies)
- [ ] `pytest tests/ -v` passes (all fixtures work)

---

## PHASE 1: OAUTH3 CORE (2 Sessions)
**Goal:** Token management, scope gates, evidence chain
**Rung:** 274177 (replay verified)
**Dependencies:** Phase 0
**⚠️ BLOCKS:** solaceagi Phase 4 (Twin Browser Integration)

### Workstreams

#### 1.1 OAuth3 Vault (AES-256-GCM Token Storage)
```python
# src/oauth3/vault.py

class OAuth3Vault:
    def issue_token(self, user_id: str, scopes: List[str], expires_in: int = 3600) -> str:
        """Issue a scoped, time-bounded token."""
        # Generate token_id
        # Encrypt with AES-256-GCM (key from environment)
        # Store in SQLite + evidence log
        # Return token to user

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify token is valid (not revoked, not expired)."""
        # Decrypt
        # Check: revoked, expired, scopes
        # Return decoded token or raise exception

    def revoke_token(self, token: str) -> None:
        """Immediately revoke a token."""
        # Mark as revoked
        # Log to evidence chain
        # All future uses rejected
```

#### 1.2 Scope Enforcement Gates
```python
# src/oauth3/scopes.py

SCOPE_HIERARCHY = {
    "browser.read": 0,        # Read-only
    "browser.click": 1,       # Click elements
    "browser.fill": 2,        # Fill forms
    "browser.send": 3,        # Send emails (requires step-up)
    "browser.screenshot": 4,  # Take screenshots
    "browser.dom": 5,         # Capture DOM
}

def requires_step_up(scope: str) -> bool:
    """High-risk actions require explicit user consent."""
    return scope in ["browser.send"]

@decorator
def requires_scope(required_scope: str):
    """Check token has required scope before executing action."""
    def wrapper(func):
        async def inner(self, *args, **kwargs):
            token = self.token
            if required_scope not in token["scopes"]:
                evidence.log_event("SCOPE_VIOLATION", {"required": required_scope, "allowed": token["scopes"]})
                raise ScopeException(f"{required_scope} not granted")
            return await func(self, *args, **kwargs)
        return inner
    return wrapper
```

#### 1.3 Evidence Chain (Hash-Chained JSONL)
```python
# src/oauth3/evidence.py

class EvidenceChain:
    def log_event(self, event_type: str, data: dict) -> str:
        """Append event to hash-chained JSONL audit trail."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "prev_hash": self.prev_hash,
            "data": data
        }

        # Compute hash (tamper detection)
        event_hash = sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()
        event["event_hash"] = event_hash

        # Append to JSONL
        with open(self.logfile, "a") as f:
            f.write(json.dumps(event) + "\n")

        self.prev_hash = event_hash
        return event_hash
```

#### 1.4 API Endpoints (Optional, v1)
```python
POST /api/v1/auth/issue
  Input: {user_id, scopes, expires_in}
  Output: {token, expires_at, scopes}

POST /api/v1/auth/verify
  Input: {token}
  Output: {user_id, scopes, expires_at, valid}

POST /api/v1/auth/revoke
  Input: {token}
  Output: {revoked, timestamp}
```

#### 1.5 Tests
```python
# tests/unit/test_oauth3_vault.py

def test_issue_token():
    vault = OAuth3Vault()
    token = vault.issue_token("user1", ["browser.read", "browser.click"])
    assert token
    assert len(token) > 30

def test_revoke_token():
    vault = OAuth3Vault()
    token = vault.issue_token("user1", ["browser.read"])
    vault.revoke_token(token)
    with pytest.raises(TokenRevoked):
        vault.verify_token(token)

def test_scope_enforcement():
    token = issue_token(scopes=["browser.read"])
    with pytest.raises(ScopeException):
        @requires_scope("browser.send")
        async def action(self):
            pass
        await action(token)

def test_evidence_chain():
    chain = EvidenceChain()
    h1 = chain.log_event("TOKEN_ISSUED", {"token_id": "t1"})
    h2 = chain.log_event("TOKEN_REVOKED", {"token_id": "t1"})

    # Verify chain
    with open(chain.logfile) as f:
        events = [json.loads(line) for line in f]
        assert events[1]["prev_hash"] == events[0]["event_hash"]
```

### Acceptance Criteria (Rung 274177)
- [ ] OAuth3Vault class fully implemented + tested
- [ ] Scope gates enforce on every action
- [ ] Token revocation blocks subsequent requests
- [ ] Evidence chain verified (hash-chained, no tampering)
- [ ] AES-256-GCM encryption used (key in .env, not git)
- [ ] All tests pass; 95%+ code coverage on oauth3/

---

## PHASE 2: BROWSER AUTOMATION (2 Sessions)
**Goal:** Playwright integration, page interaction, evidence capture
**Rung:** 641 (deterministic execution)
**Dependencies:** Phase 1
**⚠️ BLOCKS:** solaceagi Phase 4 (Twin Browser Integration)

### Workstreams

#### 2.1 Playwright Wrapper with OAuth3 Gates
```python
# src/browser/context.py

class BrowserContext:
    def __init__(self, token: str, headless: bool = True):
        self.token = token  # OAuth3 token
        self.browser = None
        self.context = None

    async def __aenter__(self):
        self.browser = await Playwright.launch(headless=True)
        self.context = await self.browser.new_context()
        return self

    async def new_page(self) -> "SecurePageProxy":
        """Create a page with OAuth3 scope gates."""
        page = await self.context.new_page()
        return SecurePageProxy(page, self.token)

class SecurePageProxy:
    def __init__(self, page, token):
        self.page = page
        self.token = token

    @requires_scope("browser.read")
    async def goto(self, url: str):
        """Navigate to URL."""
        evidence.log_event("PAGE_NAVIGATE", {"url": url})
        await self.page.goto(url)
        await self.take_screenshot(f"step_navigate_{url_hash}.png")

    @requires_scope("browser.click")
    async def click(self, selector: str):
        """Click an element."""
        evidence.log_event("PAGE_CLICK", {"selector": selector})
        await self.page.click(selector)
        await self.take_screenshot(f"step_click_{selector_hash}.png")

    @requires_scope("browser.fill")
    async def fill(self, selector: str, text: str):
        """Fill a form field."""
        evidence.log_event("PAGE_FILL", {"selector": selector})  # Don't log text (privacy)
        await self.page.fill(selector, text)

    @requires_scope("browser.send")
    async def submit(self, selector: str = None):
        """Submit a form (high-risk, requires step-up)."""
        # In production: check step-up consent
        evidence.log_event("PAGE_SUBMIT", {"selector": selector})
        if selector:
            await self.page.click(selector)
        else:
            await self.page.evaluate("document.querySelector('form').submit()")
```

#### 2.2 Evidence Capture (Screenshots + DOM)
```python
# src/browser/evidence.py

class BrowserEvidence:
    async def take_screenshot(self, page, filename: str) -> str:
        """Capture visual evidence."""
        await page.screenshot(path=filename)
        hash_val = sha256_file(filename)
        evidence.log_event("SCREENSHOT", {"filename": filename, "hash": hash_val})
        return hash_val

    async def capture_dom(self, page, filename: str) -> str:
        """Capture DOM snapshot."""
        html = await page.content()
        with open(filename, "w") as f:
            f.write(html)
        hash_val = sha256(html.encode()).hexdigest()
        evidence.log_event("DOM_SNAPSHOT", {"filename": filename, "hash": hash_val})
        return hash_val

    async def capture_network(self, page):
        """Capture network requests (optional)."""
        requests = []
        page.on("request", lambda req: requests.append({
            "url": req.url,
            "method": req.method,
            "timestamp": datetime.utcnow().isoformat()
        }))
        return requests
```

#### 2.3 Tests
```python
def test_goto_requires_scope():
    """goto() requires browser.read scope."""
    token = issue_token(scopes=["browser.click"])  # Missing read
    with pytest.raises(ScopeException):
        await browser.goto("https://example.com")

def test_click_requires_scope():
    """click() requires browser.click scope."""
    token = issue_token(scopes=["browser.read"])  # Missing click
    with pytest.raises(ScopeException):
        await browser.click("button#submit")

def test_submit_requires_step_up():
    """submit() requires explicit step-up consent."""
    token = issue_token(scopes=["browser.send"])
    # In production: check user approved step-up
    # For now: test that event is logged
    await browser.submit("button#submit")
    assert evidence.has_event("STEP_UP_REQUIRED")

def test_evidence_capture():
    """Screenshots + DOM are captured at each step."""
    await browser.goto("https://example.com")
    await browser.click("button#login")

    # Verify evidence files exist + are hashed
    assert os.path.exists("step_navigate_*.png")
    assert os.path.exists("step_click_*.html")
```

### Acceptance Criteria (Rung 641)
- [ ] Playwright integration works (headless browser spawns)
- [ ] OAuth3 scope gates enforce on every action
- [ ] Screenshots captured at each step
- [ ] DOM snapshots captured (HTML files)
- [ ] Evidence chain logged (events + hashes)
- [ ] All tests pass; 90%+ coverage

---

## PHASE 3: RECIPE ENGINE (2 Sessions)
**Goal:** Prime Mermaid parser, deterministic execution, caching
**Rung:** 641 (deterministic output)
**Dependencies:** Phase 2

### Workstreams

#### 3.1 Prime Mermaid Parser
```python
# src/recipes/parser.py

class RecipeParser:
    def parse(self, mermaid_text: str) -> RecipeDAG:
        """Parse Prime Mermaid recipe into DAG."""
        # Extract: graph LR
        # Extract: nodes (A["Description"])
        # Extract: edges (A --> B)
        # Build: DAG with nodes + edges
        # Validate: all nodes have implementations
        return RecipeDAG(nodes, edges)

class RecipeDAG:
    def __init__(self, nodes: dict, edges: list):
        self.nodes = nodes    # {node_id: Node}
        self.edges = edges    # [(from, to), ...]
        self.topo_order = self._topological_sort()

    def _topological_sort(self) -> list:
        """Return nodes in execution order."""
        # Kahn's algorithm
        in_degree = {n: 0 for n in self.nodes}
        for src, dst in self.edges:
            in_degree[dst] += 1

        queue = [n for n in self.nodes if in_degree[n] == 0]
        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for src, dst in self.edges:
                if src == node:
                    in_degree[dst] -= 1
                    if in_degree[dst] == 0:
                        queue.append(dst)
        return order
```

#### 3.2 Deterministic Executor
```python
# src/recipes/executor.py

class RecipeExecutor:
    async def execute(self, dag: RecipeDAG, inputs: dict, token: str) -> dict:
        """Execute recipe deterministically."""
        results = {}
        for node_id in dag.topo_order:
            node = dag.nodes[node_id]
            node_inputs = self._resolve_inputs(node, inputs, results)

            # Execute node (scoped + audited)
            result = await node.execute(node_inputs, token)
            results[node_id] = result

            # Log to evidence
            evidence.log_event("RECIPE_STEP", {
                "step": node_id,
                "result_hash": sha256(json.dumps(result).encode()).hexdigest()
            })

        return results[dag.topo_order[-1]]  # Return final output
```

#### 3.3 Recipe Caching
```python
# src/recipes/cache.py

class RecipeCache:
    def cache_key(self, recipe_id: str, inputs: dict) -> str:
        """Compute cache key from recipe + inputs."""
        return sha256(f"{recipe_id}:{json.dumps(inputs, sort_keys=True)}".encode()).hexdigest()

    def get(self, recipe_id: str, inputs: dict) -> Optional[dict]:
        """Retrieve cached result if available."""
        key = self.cache_key(recipe_id, inputs)
        row = db.recipe_cache.find_one({"cache_key": key})
        if row:
            evidence.log_event("CACHE_HIT", {"recipe_id": recipe_id})
            return row["result"]
        return None

    def set(self, recipe_id: str, inputs: dict, result: dict) -> None:
        """Store result in cache."""
        key = self.cache_key(recipe_id, inputs)
        db.recipe_cache.insert({
            "cache_key": key,
            "recipe_id": recipe_id,
            "result": result,
            "timestamp": datetime.utcnow()
        })
        evidence.log_event("CACHE_STORE", {"recipe_id": recipe_id})
```

#### 3.4 Tests + Cost Analysis
```python
def test_recipe_parse():
    """Parser handles Prime Mermaid format."""
    recipe_text = """
    graph LR
      A["Fetch Gmail"] --> B["Extract Emails"]
      B --> C["Classify"]
      C --> D["Summarize"]
    """
    dag = RecipeParser().parse(recipe_text)
    assert len(dag.nodes) == 4
    assert dag.topo_order == ["A", "B", "C", "D"]

def test_recipe_determinism():
    """Same input → same output (forever)."""
    inputs = {"email": "test@example.com"}
    result1 = await executor.execute(dag, inputs, token)
    result2 = await executor.execute(dag, inputs, token)
    assert result1 == result2

def test_recipe_caching():
    """Cache hit reduces cost from $0.01 → $0.001."""
    cache = RecipeCache()
    inputs = {"email": "test@example.com"}

    # First run: no cache
    result1 = await executor.execute(dag, inputs, token)  # Cost: $0.01

    # Cache it
    cache.set("gmail/triage", inputs, result1)

    # Second run: cache hit
    result2 = cache.get("gmail/triage", inputs)
    assert result1 == result2  # Same output
    # Cost: $0.001 (cached, no LLM call)
```

### Acceptance Criteria (Rung 641)
- [ ] Prime Mermaid parser works (DAG construction)
- [ ] Topological sort correct (execution order)
- [ ] Recipe execution deterministic (red/green tests)
- [ ] Caching works (cache key + retrieval)
- [ ] Cost analysis verified (70% hit rate → 70% cost reduction)
- [ ] All tests pass; 90%+ coverage

---

## PHASE 4: PM TRIPLETS (2 Sessions)
**Goal:** User/Task/Context models, composition
**Rung:** 641 (composition enabled)
**Dependencies:** Phase 3

### Workstreams

#### 4.1 User Model
```python
# src/triplets/user.py

class User:
    id: str                    # user@example.com
    language: str = "en"       # Language preference
    tone: str = "professional"  # Tone (friendly, formal, casual)
    timezone: str = "UTC"      # Timezone for scheduling
    budget: float = 100.0      # Monthly budget ($)
    constraints: dict = {}     # Custom rules (budget per task, etc.)
```

#### 4.2 Task Model
```python
# src/triplets/task.py

class Task:
    id: str                    # task_123456
    goal: str                  # "Triage inbox to 10 messages"
    inputs: dict = {}          # Provided data ({"email": "...", ...})
    success_criteria: list = []  # How to know task is done
    deadline: Optional[datetime] = None
    context_limit: int = 2000  # Max tokens for context
```

#### 4.3 Context Model + Composition
```python
# src/triplets/context.py

class Context:
    current_step: int = 0           # Which step of multi-step task?
    decisions_made: list = []       # What has the agent decided?
    intermediate_results: dict = {} # Results from previous steps
    remaining_steps: list = []      # What's left to do?
    confidence: float = 1.0         # Confidence in execution (0.0-1.0)

    def compose_for_next_task(self) -> dict:
        """Convert this task's outputs to inputs for next task."""
        # Example: Email summarizer → LinkedIn poster
        # Summarizer's output (summary) → Poster's input
        return {
            "summary": self.intermediate_results.get("summary"),
            "tone": self.user.tone,
            "timestamp": datetime.utcnow().isoformat()
        }
```

#### 4.4 Tests
```python
def test_user_model():
    user = User(id="phuc@example.com", tone="professional", budget=50.0)
    assert user.id == "phuc@example.com"
    assert user.tone == "professional"

def test_task_model():
    task = Task(id="task_1", goal="Triage inbox", inputs={"email": "..."})
    assert task.goal == "Triage inbox"

def test_composition():
    # Email summarizer
    summarizer_result = {"summary": "3 urgent emails"}

    # LinkedIn poster uses summarizer's output as input
    context = Context(intermediate_results=summarizer_result)
    next_inputs = context.compose_for_next_task()

    assert next_inputs["summary"] == "3 urgent emails"
```

### Acceptance Criteria (Rung 641)
- [ ] User model works (id, tone, budget, constraints)
- [ ] Task model works (goal, inputs, success criteria)
- [ ] Context model works (state, decisions, results)
- [ ] Composition works (A's output = B's input)
- [ ] All tests pass

---

## PHASE 5: STORE INTEGRATION (2 Sessions)
**Goal:** Read recipes from Stillwater Store, submit recipes
**Rung:** 641 (store connectivity)
**Dependencies:** Phase 4
**⚠️ BLOCKED_BY:** solaceagi Phase 3 (Stillwater Store integration on solaceagi.com)

### Workstreams

#### 5.1 Store Client (Read Recipes)
```python
# src/recipes/store_client.py

class StillwaterStoreClient:
    def __init__(self, store_url: str = "https://api.solaceagi.com/api/v1/store"):
        self.store_url = store_url

    def list_recipes(self, category: str = None) -> list:
        """Fetch available recipes from store."""
        params = {"category": category} if category else {}
        response = requests.get(f"{self.store_url}/recipes", params=params)
        return response.json()["recipes"]

    def download_recipe(self, recipe_id: str) -> str:
        """Download recipe (Mermaid + metadata)."""
        response = requests.get(f"{self.store_url}/recipes/{recipe_id}")
        return response.json()["recipe_text"]
```

#### 5.2 Recipe Submission Pipeline
```python
# src/recipes/submission.py

class RecipeSubmission:
    def submit(self, recipe_text: str, metadata: dict) -> dict:
        """Submit recipe to Stillwater Store."""
        submission = {
            "recipe_text": recipe_text,
            "author_id": self.user.id,
            "rung": 641,  # Initial rung
            "timestamp": datetime.utcnow().isoformat()
        }
        response = requests.post(
            f"{self.store_url}/recipes/submit",
            json={**submission, **metadata}
        )
        return response.json()
```

#### 5.3 Tests
```python
def test_store_download():
    """Download recipe from store."""
    client = StillwaterStoreClient()
    recipes = client.list_recipes("gmail")
    assert len(recipes) > 0

    recipe_text = client.download_recipe(recipes[0]["id"])
    assert "graph LR" in recipe_text

def test_recipe_submission():
    """Submit recipe to store."""
    submission = RecipeSubmission(user)
    result = submission.submit(recipe_text, {"title": "My Recipe", "category": "gmail"})
    assert result["status"] == "submitted"
```

### Acceptance Criteria (Rung 641)
- [ ] Store client downloads recipes
- [ ] Recipe submission works
- [ ] Metadata correctly stored
- [ ] All tests pass

---

## PHASE 6: MULTI-PLATFORM RECIPES (3 Sessions)
**Goal:** Gmail, LinkedIn, Slack, GitHub, Notion recipes
**Rung:** 641 (per-platform)
**Dependencies:** Phase 5

### Platforms (Prioritized)
1. **Gmail** (Phase 6a, 1 session) → fetch, compose, send
2. **LinkedIn** (Phase 6b, 1 session) → post, comment, message
3. **Slack + GitHub + Notion** (Phase 6c, 1 session) → basic recipes

### Acceptance Criteria (Rung 641)
- [ ] 5+ canonical recipes shipped
- [ ] Each recipe has 90%+ test coverage
- [ ] Recipe submissions to Stillwater Store
- [ ] Community can fork + modify recipes

---

## SPRINT CADENCE

| Phase | Sessions | Dependencies | Rung | Status |
|-------|----------|--------------|------|--------|
| Phase 0 | 1 | None | 641 | **START HERE** |
| Phase 1 | 2 | Phase 0 | 274177 | OAuth3 core |
| Phase 2 | 2 | Phase 1 | 641 | Browser automation |
| Phase 3 | 2 | Phase 2 | 641 | Recipe engine |
| Phase 4 | 2 | Phase 3 | 641 | PM triplets |
| Phase 5 | 2 | Phase 4 + solaceagi Phase 3 | 641 | Store integration |
| Phase 6 | 3 | Phase 5 | 641 | Multi-platform |

**Total:** 14 sessions to rung 65537

---

## SYNCHRONIZATION WITH SOLACEAGI

**Key Cross-Dependencies:**

```
PARALLEL (independent, can run in parallel):
  solace-browser Phase 0-4 (OAuth3 + recipe engine)
  solaceagi Phase 0-2 (foundation + OAuth3)

SEQUENTIAL (must wait for other project):
  solace-browser Phase 5 (Store Integration)
    ← BLOCKED_BY: solaceagi Phase 3 (Store on solaceagi.com)

  solaceagi Phase 4 (Twin Browser)
    ← DEPENDS_ON: solace-browser Phases 1-5 (fully functional browser + recipes)

  solace-browser Phase 6 (Multi-Platform)
    → CAN RUN in parallel with solaceagi Phases 4-6
```

**Timeline:**
- **Week 1-2:** Phase 0 (both projects) + Phase 1 (solace-browser)
- **Week 3-4:** Phase 2-3 (solace-browser) + Phase 1-2 (solaceagi)
- **Week 5-6:** Phase 4 (solace-browser) + Phase 2.5-3 (solaceagi)
- **Week 7:** Phase 5 (solace-browser) ready, waits for solaceagi Phase 3
- **Week 8:** Phase 5 (solace-browser) ships, unblocks solaceagi Phase 4
- **Week 9+:** Phase 6 (solace-browser) + Phase 4-6 (solaceagi) run in parallel

---

## MEMORY + ARTIFACTS

Each phase updates:
- `dragon/evolution/phase_N.log` — session record
- `dragon/questions/stillwater.jsonl` — captured questions
- `dragon/learning/` — architectural patterns
- `scratch/todo/PHASE_N_[Name].md` — phase checklist

---

## SEE ALSO

- `NORTHSTAR.md` — Vision + metrics
- `CLAUDE.md` — Project constraints + skills
- `README.md` — Developer quickstart
- `docs/oauth3-spec.md` — OAuth3 reference
- `docs/recipe-format.md` — Prime Mermaid format
- `/home/phuc/projects/solaceagi/ROADMAP.md` — Hosted platform (synchronizes with this)
- `/home/phuc/projects/stillwater/` — Core OS + skills
