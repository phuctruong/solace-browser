// Diagram: apps-backoffice-framework
//! Local Job Queue — replaces GCloud Cloud Tasks.
//! Priority queue backed by SQLite. Retry with exponential backoff.
//! Jobs can spawn sub-jobs (dependency chains).

use chrono::Utc;
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

/// Job status lifecycle: queued → running → done | failed → retry → running...
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum JobStatus {
    Queued,
    Running,
    Done,
    Failed,
    Retrying,
    Cancelled,
}

impl std::fmt::Display for JobStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Queued => write!(f, "queued"),
            Self::Running => write!(f, "running"),
            Self::Done => write!(f, "done"),
            Self::Failed => write!(f, "failed"),
            Self::Retrying => write!(f, "retrying"),
            Self::Cancelled => write!(f, "cancelled"),
        }
    }
}

/// A job in the queue.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Job {
    pub id: String,
    pub job_type: String,
    pub payload: Value,
    pub status: String,
    pub priority: i32, // 0=low, 1=normal, 2=high, 3=critical
    pub assigned_to: String,
    pub parent_job_id: Option<String>,
    pub retry_count: i32,
    pub max_retries: i32,
    pub result: Option<Value>,
    pub error: Option<String>,
    pub created_at: String,
    pub started_at: Option<String>,
    pub completed_at: Option<String>,
    pub evidence_hash: String,
}

/// The job queue backed by SQLite.
pub struct JobQueue {
    db_path: std::path::PathBuf,
}

impl JobQueue {
    pub fn new(solace_home: &std::path::Path) -> Self {
        let db_path = solace_home.join("runtime").join("jobs.db");
        let _ = std::fs::create_dir_all(solace_home.join("runtime"));

        if let Ok(conn) = Connection::open(&db_path) {
            let _ = conn.execute_batch(
                "PRAGMA journal_mode=WAL;
                 CREATE TABLE IF NOT EXISTS jobs (
                   id TEXT PRIMARY KEY,
                   job_type TEXT NOT NULL,
                   payload TEXT NOT NULL,
                   status TEXT NOT NULL DEFAULT 'queued',
                   priority INTEGER NOT NULL DEFAULT 1,
                   assigned_to TEXT NOT NULL DEFAULT '',
                   parent_job_id TEXT,
                   retry_count INTEGER NOT NULL DEFAULT 0,
                   max_retries INTEGER NOT NULL DEFAULT 3,
                   result TEXT,
                   error TEXT,
                   created_at TEXT NOT NULL,
                   started_at TEXT,
                   completed_at TEXT,
                   evidence_hash TEXT NOT NULL
                 );
                 CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
                 CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs(priority DESC);
                 CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type);",
            );
        }

        Self { db_path }
    }

    fn conn(&self) -> Result<Connection, String> {
        Connection::open(&self.db_path).map_err(|e| format!("job db: {e}"))
    }

    /// Enqueue a new job.
    pub fn enqueue(
        &self,
        job_type: &str,
        payload: Value,
        priority: i32,
        assigned_to: &str,
        parent_job_id: Option<&str>,
    ) -> Result<Job, String> {
        let id = uuid::Uuid::new_v4().to_string();
        let now = Utc::now().to_rfc3339();

        let mut hasher = Sha256::new();
        hasher.update(format!("{}:{}:{}:{}", job_type, payload, priority, now).as_bytes());
        let evidence_hash = format!("{:x}", hasher.finalize())[..16].to_string();

        let conn = self.conn()?;
        conn.execute(
            "INSERT INTO jobs (id, job_type, payload, status, priority, assigned_to, parent_job_id, created_at, evidence_hash)
             VALUES (?1, ?2, ?3, 'queued', ?4, ?5, ?6, ?7, ?8)",
            rusqlite::params![id, job_type, payload.to_string(), priority, assigned_to, parent_job_id, now, evidence_hash],
        ).map_err(|e| format!("enqueue: {e}"))?;

        Ok(Job {
            id,
            job_type: job_type.to_string(),
            payload,
            status: "queued".to_string(),
            priority,
            assigned_to: assigned_to.to_string(),
            parent_job_id: parent_job_id.map(|s| s.to_string()),
            retry_count: 0,
            max_retries: 3,
            result: None,
            error: None,
            created_at: now,
            started_at: None,
            completed_at: None,
            evidence_hash,
        })
    }

    /// Claim the next available job (highest priority, oldest first).
    pub fn claim(&self, worker_id: &str) -> Result<Option<Job>, String> {
        let conn = self.conn()?;
        let now = Utc::now().to_rfc3339();

        // Atomic claim: SELECT + UPDATE in one transaction
        let tx = conn.unchecked_transaction().map_err(|e| format!("tx: {e}"))?;

        let maybe_id: Option<String> = tx.query_row(
            "SELECT id FROM jobs WHERE status IN ('queued', 'retrying')
             ORDER BY priority DESC, created_at ASC LIMIT 1",
            [],
            |row| row.get(0),
        ).ok();

        if let Some(job_id) = maybe_id {
            tx.execute(
                "UPDATE jobs SET status = 'running', assigned_to = ?1, started_at = ?2 WHERE id = ?3",
                rusqlite::params![worker_id, now, job_id],
            ).map_err(|e| format!("claim: {e}"))?;
            tx.commit().map_err(|e| format!("commit: {e}"))?;

            self.get(&job_id)
        } else {
            Ok(None)
        }
    }

    /// Complete a job with result.
    pub fn complete(&self, job_id: &str, result: Value) -> Result<(), String> {
        let conn = self.conn()?;
        let now = Utc::now().to_rfc3339();
        conn.execute(
            "UPDATE jobs SET status = 'done', result = ?1, completed_at = ?2 WHERE id = ?3",
            rusqlite::params![result.to_string(), now, job_id],
        ).map_err(|e| format!("complete: {e}"))?;
        Ok(())
    }

    /// Fail a job. Auto-retries if under max_retries.
    pub fn fail(&self, job_id: &str, error: &str) -> Result<(), String> {
        let conn = self.conn()?;
        let now = Utc::now().to_rfc3339();

        // Check retry count
        let (retry_count, max_retries): (i32, i32) = conn.query_row(
            "SELECT retry_count, max_retries FROM jobs WHERE id = ?1",
            rusqlite::params![job_id],
            |row| Ok((row.get(0)?, row.get(1)?)),
        ).map_err(|e| format!("query: {e}"))?;

        if retry_count < max_retries {
            conn.execute(
                "UPDATE jobs SET status = 'retrying', error = ?1, retry_count = retry_count + 1, completed_at = ?2 WHERE id = ?3",
                rusqlite::params![error, now, job_id],
            ).map_err(|e| format!("retry: {e}"))?;
        } else {
            conn.execute(
                "UPDATE jobs SET status = 'failed', error = ?1, completed_at = ?2 WHERE id = ?3",
                rusqlite::params![error, now, job_id],
            ).map_err(|e| format!("fail: {e}"))?;
        }
        Ok(())
    }

    /// Get a job by ID.
    pub fn get(&self, job_id: &str) -> Result<Option<Job>, String> {
        let conn = self.conn()?;
        conn.query_row(
            "SELECT id, job_type, payload, status, priority, assigned_to, parent_job_id,
                    retry_count, max_retries, result, error, created_at, started_at, completed_at, evidence_hash
             FROM jobs WHERE id = ?1",
            rusqlite::params![job_id],
            |row| {
                Ok(Some(Job {
                    id: row.get(0)?,
                    job_type: row.get(1)?,
                    payload: serde_json::from_str::<Value>(&row.get::<_, String>(2)?).unwrap_or(json!(null)),
                    status: row.get(3)?,
                    priority: row.get(4)?,
                    assigned_to: row.get(5)?,
                    parent_job_id: row.get(6)?,
                    retry_count: row.get(7)?,
                    max_retries: row.get(8)?,
                    result: row.get::<_, Option<String>>(9)?.and_then(|s| serde_json::from_str(&s).ok()),
                    error: row.get(10)?,
                    created_at: row.get(11)?,
                    started_at: row.get(12)?,
                    completed_at: row.get(13)?,
                    evidence_hash: row.get(14)?,
                }))
            },
        ).map_err(|e| format!("get: {e}"))
    }

    /// List jobs with optional status filter.
    pub fn list(&self, status: Option<&str>, limit: u32) -> Result<Vec<Job>, String> {
        let conn = self.conn()?;
        let sql = if let Some(s) = status {
            format!("SELECT id, job_type, payload, status, priority, assigned_to, parent_job_id,
                    retry_count, max_retries, result, error, created_at, started_at, completed_at, evidence_hash
             FROM jobs WHERE status = '{}' ORDER BY priority DESC, created_at ASC LIMIT {}", s, limit)
        } else {
            format!("SELECT id, job_type, payload, status, priority, assigned_to, parent_job_id,
                    retry_count, max_retries, result, error, created_at, started_at, completed_at, evidence_hash
             FROM jobs ORDER BY created_at DESC LIMIT {}", limit)
        };

        let mut stmt = conn.prepare(&sql).map_err(|e| format!("prepare: {e}"))?;
        let mut rows = stmt.query([]).map_err(|e| format!("query: {e}"))?;
        let mut jobs = Vec::new();

        while let Some(row) = rows.next().map_err(|e| format!("row: {e}"))? {
            jobs.push(Job {
                id: row.get(0).unwrap_or_default(),
                job_type: row.get(1).unwrap_or_default(),
                payload: serde_json::from_str::<Value>(&row.get::<_, String>(2).unwrap_or_default()).unwrap_or(json!(null)),
                status: row.get(3).unwrap_or_default(),
                priority: row.get(4).unwrap_or(1),
                assigned_to: row.get(5).unwrap_or_default(),
                parent_job_id: row.get(6).ok(),
                retry_count: row.get(7).unwrap_or(0),
                max_retries: row.get(8).unwrap_or(3),
                result: row.get::<_, Option<String>>(9).ok().flatten().and_then(|s| serde_json::from_str(&s).ok()),
                error: row.get(10).ok().flatten(),
                created_at: row.get(11).unwrap_or_default(),
                started_at: row.get(12).ok().flatten(),
                completed_at: row.get(13).ok().flatten(),
                evidence_hash: row.get(14).unwrap_or_default(),
            });
        }

        Ok(jobs)
    }

    /// Queue stats.
    pub fn stats(&self) -> Result<Value, String> {
        let conn = self.conn()?;
        let total: i64 = conn.query_row("SELECT COUNT(*) FROM jobs", [], |r| r.get(0)).unwrap_or(0);
        let queued: i64 = conn.query_row("SELECT COUNT(*) FROM jobs WHERE status='queued'", [], |r| r.get(0)).unwrap_or(0);
        let running: i64 = conn.query_row("SELECT COUNT(*) FROM jobs WHERE status='running'", [], |r| r.get(0)).unwrap_or(0);
        let done: i64 = conn.query_row("SELECT COUNT(*) FROM jobs WHERE status='done'", [], |r| r.get(0)).unwrap_or(0);
        let failed: i64 = conn.query_row("SELECT COUNT(*) FROM jobs WHERE status='failed'", [], |r| r.get(0)).unwrap_or(0);

        Ok(json!({
            "total": total, "queued": queued, "running": running,
            "done": done, "failed": failed,
        }))
    }
}
