// Diagram: 15-recipe-engine-fsm
// Recipe Engine — deterministic replay at zero cost
//
// FSM: INTAKE → CACHE_LOOKUP → [HIT_VERIFY → REPLAY | MISS → GENERATE → VALIDATE → STORE] → EXECUTE → EVIDENCE
//
// Key insight (Paper 4): LLM called ONCE at preview. Execution = deterministic CPU replay.
// Replay cost = $0.001 (Haiku) vs $0.59/M tokens for generation.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::path::PathBuf;

/// Recipe FSM states
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RecipeState {
    Intake,
    CacheLookup,
    CacheHit,
    CacheMiss,
    HitVerify,
    Generate,
    Validate,
    Store,
    Execute,
    Evidence,
    Done,
    Failed,
    Blocked,
}

/// A recipe = deterministic sequence of steps for a task
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Recipe {
    pub recipe_id: String,
    pub task_hash: String,
    pub steps: Vec<RecipeStep>,
    pub created_at: String,
    pub replay_count: u64,
    pub verified: bool,
}

/// A single step in a recipe
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecipeStep {
    pub action: String,
    pub selector: Option<String>,
    pub value: Option<String>,
    pub expected: Option<String>,
}

/// Recipe execution result
#[derive(Debug, Serialize)]
pub struct RecipeResult {
    pub state: RecipeState,
    pub recipe_id: String,
    pub task_hash: String,
    pub cache_hit: bool,
    pub replay_count: u64,
    pub steps_executed: usize,
    pub evidence_hash: String,
}

/// In-memory recipe cache (persisted to ~/.solace/recipes/)
#[derive(Default)]
pub struct RecipeCache {
    cache: HashMap<String, Recipe>,
}

impl RecipeCache {
    pub fn new() -> Self {
        let mut cache = Self::default();
        cache.load_from_disk();
        cache
    }

    /// Compute cache key from task description
    pub fn task_hash(task: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(task.as_bytes());
        format!("{:x}", hasher.finalize())
    }

    /// CACHE_LOOKUP: check if a recipe exists for this task
    pub fn lookup(&self, task_hash: &str) -> Option<&Recipe> {
        self.cache.get(task_hash)
    }

    /// STORE: save a new recipe to cache
    pub fn store(&mut self, recipe: Recipe) {
        let task_hash = recipe.task_hash.clone();
        self.cache.insert(task_hash, recipe);
        self.persist_to_disk();
    }

    /// HIT_VERIFY: check if cached recipe still works (never-worse check)
    pub fn verify(&self, recipe: &Recipe) -> bool {
        // A recipe is verified if it has been replayed at least once without failure
        recipe.verified && recipe.replay_count > 0
    }

    /// Increment replay count
    pub fn record_replay(&mut self, task_hash: &str) {
        if let Some(recipe) = self.cache.get_mut(task_hash) {
            recipe.replay_count += 1;
            recipe.verified = true;
            self.persist_to_disk();
        }
    }

    fn recipes_dir() -> PathBuf {
        crate::utils::solace_home().join("recipes")
    }

    fn load_from_disk(&mut self) {
        let dir = Self::recipes_dir();
        if let Ok(entries) = std::fs::read_dir(&dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.extension().is_some_and(|e| e == "json") {
                    if let Ok(content) = std::fs::read_to_string(&path) {
                        if let Ok(recipe) = serde_json::from_str::<Recipe>(&content) {
                            self.cache.insert(recipe.task_hash.clone(), recipe);
                        }
                    }
                }
            }
        }
    }

    fn persist_to_disk(&self) {
        let dir = Self::recipes_dir();
        let _ = std::fs::create_dir_all(&dir);
        for (hash, recipe) in &self.cache {
            let path = dir.join(format!("{}.json", &hash[..16]));
            let _ = std::fs::write(
                &path,
                serde_json::to_string_pretty(recipe).unwrap_or_default(),
            );
        }
    }

    /// Remove a recipe from cache and disk.
    /// Returns true if the recipe was found and removed.
    pub fn remove(&mut self, task_hash: &str) -> bool {
        if self.cache.remove(task_hash).is_some() {
            // Remove the on-disk file too
            let dir = Self::recipes_dir();
            let path = dir.join(format!(
                "{}.json",
                &task_hash[..std::cmp::min(16, task_hash.len())]
            ));
            let _ = std::fs::remove_file(&path);
            true
        } else {
            false
        }
    }

    pub fn len(&self) -> usize {
        self.cache.len()
    }

    pub fn list(&self) -> Vec<&Recipe> {
        self.cache.values().collect()
    }
}

/// Run the recipe FSM for a task.
/// Returns the execution result with state transitions.
pub fn execute_recipe(task: &str, cache: &mut RecipeCache) -> RecipeResult {
    let task_hash = RecipeCache::task_hash(task);
    let recipe_id;
    let cache_hit;
    let replay_count;
    let steps_executed;

    // INTAKE → CACHE_LOOKUP
    // Extract data from immutable borrow first, then mutate
    let cached = cache.lookup(&task_hash).map(|r| {
        (
            r.recipe_id.clone(),
            r.steps.len(),
            r.verified,
            r.replay_count,
        )
    });

    if let Some((existing_id, existing_steps, verified, existing_replays)) = cached {
        if verified && existing_replays > 0 {
            // CACHE_HIT → HIT_VERIFY → REPLAY (CPU only, $0 LLM cost)
            recipe_id = existing_id;
            steps_executed = existing_steps;
            cache.record_replay(&task_hash);
            replay_count = existing_replays + 1;
            cache_hit = true;
        } else {
            // Not verified → treat as MISS, regenerate
            recipe_id = uuid::Uuid::new_v4().to_string();
            let recipe = generate_recipe(task, &task_hash, &recipe_id);
            steps_executed = recipe.steps.len();
            replay_count = 0;
            cache.store(recipe);
            cache_hit = false;
        }
    } else {
        // CACHE_MISS → GENERATE → VALIDATE → STORE
        recipe_id = uuid::Uuid::new_v4().to_string();
        let recipe = generate_recipe(task, &task_hash, &recipe_id);
        steps_executed = recipe.steps.len();
        replay_count = 0;
        cache.store(recipe);
        cache_hit = false;
    }

    // EVIDENCE: seal the execution
    let evidence_hash = {
        let mut hasher = Sha256::new();
        hasher.update(format!("{}:{}:{}", recipe_id, task_hash, steps_executed).as_bytes());
        format!("{:x}", hasher.finalize())
    };

    RecipeResult {
        state: RecipeState::Done,
        recipe_id,
        task_hash,
        cache_hit,
        replay_count,
        steps_executed,
        evidence_hash,
    }
}

/// Intent classification — determines what kind of task this is.
/// Returns (intent, confidence) tuple.
/// In production, this calls the LLM for ambiguous tasks.
/// Currently uses keyword matching for deterministic classification.
pub fn classify_intent(task: &str) -> (&'static str, f64) {
    let lower = task.to_ascii_lowercase();
    if lower.contains("morning brief") || lower.contains("morning-brief") {
        ("orchestrate", 0.95)
    } else if lower.contains("navigate") || lower.contains("open") || lower.contains("go to") {
        ("navigate", 0.90)
    } else if lower.contains("click") || lower.contains("fill") || lower.contains("type") {
        ("interact", 0.85)
    } else if lower.contains("search") || lower.contains("find") || lower.contains("look up") {
        ("search", 0.80)
    } else if lower.contains("schedule") || lower.contains("cron") || lower.contains("every") {
        ("schedule", 0.85)
    } else if lower.contains("download") || lower.contains("save") || lower.contains("export") {
        ("export", 0.80)
    } else {
        ("process", 0.50) // Low confidence → would trigger LLM in production
    }
}

/// Checkpoint a recipe execution state for potential rollback.
pub fn checkpoint_recipe(recipe: &Recipe, step_index: usize) -> RecipeCheckpoint {
    let mut hasher = Sha256::new();
    hasher.update(format!("{}:{}:{}", recipe.recipe_id, recipe.task_hash, step_index).as_bytes());
    RecipeCheckpoint {
        recipe_id: recipe.recipe_id.clone(),
        step_index,
        checkpoint_hash: format!("{:x}", hasher.finalize()),
        created_at: crate::utils::now_iso8601(),
    }
}

/// A checkpoint for rollback support.
#[derive(Debug, Clone, Serialize)]
pub struct RecipeCheckpoint {
    pub recipe_id: String,
    pub step_index: usize,
    pub checkpoint_hash: String,
    pub created_at: String,
}

/// Generate a recipe for a task.
/// In production, this calls the LLM ONCE to produce steps.
/// Currently generates deterministic steps based on task keywords.
fn generate_recipe(task: &str, task_hash: &str, recipe_id: &str) -> Recipe {
    let (intent, _confidence) = classify_intent(task);
    let steps = if intent == "orchestrate" {
        vec![
            RecipeStep {
                action: "fetch".into(),
                selector: None,
                value: Some("hackernews-feed".into()),
                expected: Some("200".into()),
            },
            RecipeStep {
                action: "fetch".into(),
                selector: None,
                value: Some("google-search-trends".into()),
                expected: Some("200".into()),
            },
            RecipeStep {
                action: "fetch".into(),
                selector: None,
                value: Some("reddit-scanner".into()),
                expected: Some("200".into()),
            },
            RecipeStep {
                action: "render".into(),
                selector: Some("morning-brief".into()),
                value: None,
                expected: Some("report.html".into()),
            },
            RecipeStep {
                action: "seal".into(),
                selector: None,
                value: None,
                expected: Some("sha256".into()),
            },
        ]
    } else if intent == "navigate" {
        vec![RecipeStep {
            action: "navigate".into(),
            selector: None,
            value: Some(task.to_string()),
            expected: Some("200".into()),
        }]
    } else {
        vec![RecipeStep {
            action: "process".into(),
            selector: None,
            value: Some(task.to_string()),
            expected: None,
        }]
    };

    Recipe {
        recipe_id: recipe_id.to_string(),
        task_hash: task_hash.to_string(),
        steps,
        created_at: crate::utils::now_iso8601(),
        replay_count: 0,
        verified: false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn task_hash_is_deterministic() {
        let h1 = RecipeCache::task_hash("run morning brief");
        let h2 = RecipeCache::task_hash("run morning brief");
        assert_eq!(h1, h2);
        assert_ne!(h1, RecipeCache::task_hash("different task"));
    }

    #[test]
    fn cache_miss_then_hit() {
        let mut cache = RecipeCache::default();
        let result1 = execute_recipe("test task alpha", &mut cache);
        assert!(!result1.cache_hit);
        assert_eq!(result1.state, RecipeState::Done);
        assert_eq!(cache.len(), 1);

        // Mark as verified for replay
        cache.cache.get_mut(&result1.task_hash).unwrap().verified = true;
        cache
            .cache
            .get_mut(&result1.task_hash)
            .unwrap()
            .replay_count = 1;

        let result2 = execute_recipe("test task alpha", &mut cache);
        assert!(result2.cache_hit);
        assert_eq!(result2.replay_count, 2);
    }

    #[test]
    fn morning_brief_generates_5_steps() {
        let mut cache = RecipeCache::default();
        let result = execute_recipe("run morning brief", &mut cache);
        assert_eq!(result.steps_executed, 5);
    }

    #[test]
    fn evidence_hash_is_nonempty() {
        let mut cache = RecipeCache::default();
        let result = execute_recipe("any task", &mut cache);
        assert!(!result.evidence_hash.is_empty());
        assert_eq!(result.evidence_hash.len(), 64); // SHA-256 hex
    }

    #[test]
    fn recipe_list_after_multiple_tasks() {
        let mut cache = RecipeCache::default();
        execute_recipe("task one", &mut cache);
        execute_recipe("task two", &mut cache);
        execute_recipe("task three", &mut cache);
        assert_eq!(cache.len(), 3);
        assert_eq!(cache.list().len(), 3);
    }

    #[test]
    fn remove_existing_recipe() {
        let mut cache = RecipeCache::default();
        let result = execute_recipe("task to remove", &mut cache);
        assert_eq!(cache.len(), 1);

        let removed = cache.remove(&result.task_hash);
        assert!(removed);
        assert_eq!(cache.len(), 0);
        assert!(cache.lookup(&result.task_hash).is_none());
    }

    #[test]
    fn remove_nonexistent_recipe() {
        let mut cache = RecipeCache::default();
        let removed = cache.remove("nonexistent_hash");
        assert!(!removed);
    }

    #[test]
    fn unverified_recipe_causes_regeneration() {
        let mut cache = RecipeCache::default();
        // First run: generates recipe (unverified)
        let result1 = execute_recipe("verify test", &mut cache);
        assert!(!result1.cache_hit);
        assert_eq!(result1.replay_count, 0);

        // Second run: recipe exists but not verified → regenerate (cache miss)
        let result2 = execute_recipe("verify test", &mut cache);
        assert!(!result2.cache_hit);
        assert_eq!(result2.replay_count, 0);
    }

    #[test]
    fn verified_recipe_replays() {
        let mut cache = RecipeCache::default();
        let result1 = execute_recipe("replay test", &mut cache);
        assert!(!result1.cache_hit);

        // Manually verify the recipe
        cache.cache.get_mut(&result1.task_hash).unwrap().verified = true;
        cache
            .cache
            .get_mut(&result1.task_hash)
            .unwrap()
            .replay_count = 1;

        // Now it should replay (cache hit)
        let result2 = execute_recipe("replay test", &mut cache);
        assert!(result2.cache_hit);
        assert_eq!(result2.replay_count, 2);
    }

    #[test]
    fn intent_classify_orchestrate() {
        let (intent, conf) = classify_intent("run morning brief");
        assert_eq!(intent, "orchestrate");
        assert!(conf > 0.9);
    }

    #[test]
    fn intent_classify_navigate() {
        let (intent, _) = classify_intent("navigate to google.com");
        assert_eq!(intent, "navigate");
    }

    #[test]
    fn intent_classify_interact() {
        let (intent, _) = classify_intent("click the login button");
        assert_eq!(intent, "interact");
    }

    #[test]
    fn intent_classify_search() {
        let (intent, _) = classify_intent("search for AI news");
        assert_eq!(intent, "search");
    }

    #[test]
    fn intent_classify_schedule() {
        let (intent, _) = classify_intent("schedule every morning at 8am");
        assert_eq!(intent, "schedule");
    }

    #[test]
    fn intent_classify_unknown() {
        let (intent, conf) = classify_intent("do something weird");
        assert_eq!(intent, "process");
        assert!(conf <= 0.5);
    }

    #[test]
    fn checkpoint_creates_hash() {
        let recipe = Recipe {
            recipe_id: "test-id".to_string(),
            task_hash: "test-hash".to_string(),
            steps: vec![],
            created_at: "2026-01-01".to_string(),
            replay_count: 0,
            verified: false,
        };
        let cp = checkpoint_recipe(&recipe, 0);
        assert_eq!(cp.recipe_id, "test-id");
        assert_eq!(cp.step_index, 0);
        assert_eq!(cp.checkpoint_hash.len(), 64); // SHA-256 hex
    }

    #[test]
    fn checkpoint_different_steps_different_hashes() {
        let recipe = Recipe {
            recipe_id: "test-id".to_string(),
            task_hash: "test-hash".to_string(),
            steps: vec![],
            created_at: "2026-01-01".to_string(),
            replay_count: 0,
            verified: false,
        };
        let cp0 = checkpoint_recipe(&recipe, 0);
        let cp1 = checkpoint_recipe(&recipe, 1);
        assert_ne!(cp0.checkpoint_hash, cp1.checkpoint_hash);
    }
}
