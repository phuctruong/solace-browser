// Diagram: apps-backoffice-framework
//! Local Pub/Sub Event Bus — replaces GCloud Pub/Sub.
//! Agents subscribe to topics. Events trigger subscribers.
//! All events are evidence-chained. SQLite-backed for persistence.

use chrono::Utc;
use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use tokio::sync::broadcast;

/// Maximum events kept in memory per topic before flush to SQLite.
const MAX_MEMORY_EVENTS: usize = 1000;

/// A published event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Event {
    pub id: String,
    pub topic: String,
    pub payload: Value,
    pub publisher: String,
    pub timestamp: String,
    pub evidence_hash: String,
}

/// Subscription: who wants to hear about what.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Subscription {
    pub id: String,
    pub topic: String,
    pub subscriber: String,
    /// Filter: only deliver events matching this JSONPath-like filter
    pub filter: Option<String>,
    pub created_at: String,
}

/// The event bus. In-memory broadcast + SQLite persistence.
pub struct EventBus {
    /// Broadcast channels per topic (in-memory, fast delivery).
    senders: RwLock<HashMap<String, broadcast::Sender<Event>>>,
    /// Subscriptions registry.
    subscriptions: RwLock<Vec<Subscription>>,
    /// Recent events per topic (ring buffer for API polling).
    recent_events: RwLock<HashMap<String, Vec<Event>>>,
    /// SQLite path for persistent event log.
    db_path: std::path::PathBuf,
}

impl EventBus {
    pub fn new(solace_home: &std::path::Path) -> Self {
        let db_path = solace_home.join("runtime").join("eventbus.db");

        // Initialize SQLite
        if let Ok(conn) = rusqlite::Connection::open(&db_path) {
            let _ = conn.execute_batch(
                "PRAGMA journal_mode=WAL;
                 CREATE TABLE IF NOT EXISTS events (
                   id TEXT PRIMARY KEY,
                   topic TEXT NOT NULL,
                   payload TEXT NOT NULL,
                   publisher TEXT NOT NULL,
                   timestamp TEXT NOT NULL,
                   evidence_hash TEXT NOT NULL
                 );
                 CREATE INDEX IF NOT EXISTS idx_events_topic ON events(topic);
                 CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp);
                 CREATE TABLE IF NOT EXISTS subscriptions (
                   id TEXT PRIMARY KEY,
                   topic TEXT NOT NULL,
                   subscriber TEXT NOT NULL,
                   filter TEXT,
                   created_at TEXT NOT NULL
                 );",
            );
        }

        Self {
            senders: RwLock::new(HashMap::new()),
            subscriptions: RwLock::new(Vec::new()),
            recent_events: RwLock::new(HashMap::new()),
            db_path,
        }
    }

    /// Publish an event to a topic.
    pub fn publish(&self, topic: &str, payload: Value, publisher: &str) -> Event {
        let id = uuid::Uuid::new_v4().to_string();
        let now = Utc::now().to_rfc3339();

        let mut hasher = Sha256::new();
        hasher.update(format!("{}:{}:{}:{}", topic, publisher, payload, now).as_bytes());
        let evidence_hash = format!("{:x}", hasher.finalize())[..16].to_string();

        let event = Event {
            id: id.clone(),
            topic: topic.to_string(),
            payload,
            publisher: publisher.to_string(),
            timestamp: now,
            evidence_hash,
        };

        // Broadcast to in-memory subscribers
        let senders = self.senders.read();
        if let Some(tx) = senders.get(topic) {
            let _ = tx.send(event.clone());
        }

        // Also broadcast to wildcard subscribers
        if let Some(tx) = senders.get("*") {
            let _ = tx.send(event.clone());
        }

        // Store in recent events (ring buffer)
        {
            let mut recent = self.recent_events.write();
            let events = recent.entry(topic.to_string()).or_default();
            events.push(event.clone());
            if events.len() > MAX_MEMORY_EVENTS {
                events.drain(..events.len() - MAX_MEMORY_EVENTS);
            }
        }

        // Persist to SQLite
        if let Ok(conn) = rusqlite::Connection::open(&self.db_path) {
            let _ = conn.execute(
                "INSERT INTO events (id, topic, payload, publisher, timestamp, evidence_hash) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
                rusqlite::params![
                    event.id, event.topic, event.payload.to_string(),
                    event.publisher, event.timestamp, event.evidence_hash
                ],
            );
        }

        event
    }

    /// Subscribe to a topic. Returns a broadcast receiver.
    pub fn subscribe(&self, topic: &str, subscriber: &str) -> (String, broadcast::Receiver<Event>) {
        let sub_id = uuid::Uuid::new_v4().to_string();
        let now = Utc::now().to_rfc3339();

        // Create or get broadcast channel for this topic
        let mut senders = self.senders.write();
        let tx = senders.entry(topic.to_string()).or_insert_with(|| {
            let (tx, _) = broadcast::channel(256);
            tx
        });
        let rx = tx.subscribe();

        // Register subscription
        let sub = Subscription {
            id: sub_id.clone(),
            topic: topic.to_string(),
            subscriber: subscriber.to_string(),
            filter: None,
            created_at: now.clone(),
        };
        self.subscriptions.write().push(sub.clone());

        // Persist
        if let Ok(conn) = rusqlite::Connection::open(&self.db_path) {
            let _ = conn.execute(
                "INSERT INTO subscriptions (id, topic, subscriber, filter, created_at) VALUES (?1, ?2, ?3, ?4, ?5)",
                rusqlite::params![sub_id, topic, subscriber, Option::<String>::None, now],
            );
        }

        (sub_id, rx)
    }

    /// Get recent events for a topic (polling API).
    pub fn recent(&self, topic: &str, limit: usize) -> Vec<Event> {
        let recent = self.recent_events.read();
        recent
            .get(topic)
            .map(|events| {
                let start = events.len().saturating_sub(limit);
                events[start..].to_vec()
            })
            .unwrap_or_default()
    }

    /// List all topics with event counts.
    pub fn topics(&self) -> Vec<(String, usize)> {
        let recent = self.recent_events.read();
        recent
            .iter()
            .map(|(t, events)| (t.clone(), events.len()))
            .collect()
    }

    /// List active subscriptions.
    pub fn list_subscriptions(&self) -> Vec<Subscription> {
        self.subscriptions.read().clone()
    }
}

/// Well-known topics for the Solace ecosystem.
pub mod topics {
    /// Backoffice events: record created/updated/deleted
    pub const BACKOFFICE_WRITE: &str = "backoffice.write";
    /// App lifecycle: started, completed, failed
    pub const APP_LIFECYCLE: &str = "app.lifecycle";
    /// CLI worker: run started, completed, failed
    pub const CLI_RUN: &str = "cli.run";
    /// Evidence: new entry added to chain
    pub const EVIDENCE_NEW: &str = "evidence.new";
    /// Human action: sign-off, feedback, task assignment
    pub const HUMAN_ACTION: &str = "human.action";
    /// Browser: navigation, page captured, domain detected
    pub const BROWSER_EVENT: &str = "browser.event";
    /// System: heartbeat, boot, shutdown, error
    pub const SYSTEM: &str = "system";
}
