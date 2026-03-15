// Diagram: hub-app-event-log
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

use chrono::Utc;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// Typed event categories for the per-run event log.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EventType {
    Navigate,
    Click,
    Fill,
    Fetch,
    Render,
    Seal,
    Preview,
    SignOff,
}

impl EventType {
    /// Preview and SignOff events are prominent (shown in sidebar).
    pub fn is_prominent(&self) -> bool {
        matches!(self, EventType::Preview | EventType::SignOff)
    }
}

/// A single hash-chained event in the run event log.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Event {
    pub event_type: EventType,
    pub timestamp: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub selector: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub value: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub detail: Option<String>,
    pub sha256: String,
    pub prev_hash: String,
    pub prominent: bool,
}

/// Append-only event log for a single app run, with hash chain integrity.
#[derive(Debug)]
pub struct EventLog {
    pub run_id: String,
    pub app_id: String,
    events: Vec<Event>,
}

impl EventLog {
    pub fn new(app_id: &str, run_id: &str) -> Self {
        Self {
            run_id: run_id.to_string(),
            app_id: app_id.to_string(),
            events: Vec::new(),
        }
    }

    /// Append an event, automatically linking to the previous event's hash.
    pub fn append_event(
        &mut self,
        event_type: EventType,
        url: Option<String>,
        selector: Option<String>,
        value: Option<String>,
        detail: Option<String>,
    ) -> &Event {
        let prev_hash = self
            .events
            .last()
            .map(|e| e.sha256.clone())
            .unwrap_or_default();
        let timestamp = Utc::now().to_rfc3339();
        let prominent = event_type.is_prominent();

        let sha256 = compute_event_hash(
            &event_type,
            &timestamp,
            &prev_hash,
            url.as_deref(),
            selector.as_deref(),
            value.as_deref(),
            detail.as_deref(),
        );

        let event = Event {
            event_type,
            timestamp,
            url,
            selector,
            value,
            detail,
            sha256,
            prev_hash,
            prominent,
        };

        self.events.push(event);
        self.events.last().expect("event appended")
    }

    /// Return a reference to all events.
    pub fn events(&self) -> &[Event] {
        &self.events
    }

    /// Verify the entire hash chain is intact.
    pub fn verify_chain(&self) -> bool {
        self.events.iter().enumerate().all(|(i, event)| {
            let expected_prev = if i == 0 {
                String::new()
            } else {
                self.events[i - 1].sha256.clone()
            };
            if event.prev_hash != expected_prev {
                return false;
            }
            let computed = compute_event_hash(
                &event.event_type,
                &event.timestamp,
                &event.prev_hash,
                event.url.as_deref(),
                event.selector.as_deref(),
                event.value.as_deref(),
                event.detail.as_deref(),
            );
            event.sha256 == computed
        })
    }

    /// Save the event log as JSONL (one JSON object per line) to the run's outbox.
    pub fn save_events(&self, outbox_dir: &Path) -> Result<PathBuf, String> {
        let events_path = outbox_dir.join("events.jsonl");
        let mut file = fs::File::create(&events_path).map_err(|e| e.to_string())?;
        for event in &self.events {
            let line = serde_json::to_string(event).map_err(|e| e.to_string())?;
            writeln!(file, "{}", line).map_err(|e| e.to_string())?;
        }
        Ok(events_path)
    }

    /// Load events from a JSONL file.
    pub fn load_from_file(app_id: &str, run_id: &str, path: &Path) -> Result<Self, String> {
        let content = fs::read_to_string(path).map_err(|e| e.to_string())?;
        let mut events = Vec::new();
        for line in content.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }
            let event: Event = serde_json::from_str(line).map_err(|e| e.to_string())?;
            events.push(event);
        }
        Ok(Self {
            run_id: run_id.to_string(),
            app_id: app_id.to_string(),
            events,
        })
    }
}

/// Compute the SHA-256 hash for an event based on its fields.
fn compute_event_hash(
    event_type: &EventType,
    timestamp: &str,
    prev_hash: &str,
    url: Option<&str>,
    selector: Option<&str>,
    value: Option<&str>,
    detail: Option<&str>,
) -> String {
    #[derive(Serialize)]
    struct HashPayload<'a> {
        event_type: &'a EventType,
        timestamp: &'a str,
        prev_hash: &'a str,
        url: Option<&'a str>,
        selector: Option<&'a str>,
        value: Option<&'a str>,
        detail: Option<&'a str>,
    }
    let payload = serde_json::to_vec(&HashPayload {
        event_type,
        timestamp,
        prev_hash,
        url,
        selector,
        value,
        detail,
    })
    .expect("hash payload serialization");
    let digest = Sha256::digest(&payload);
    format!("{:x}", digest)
}

/// Read events.jsonl for a given app_id and run_id from the outbox directory tree.
pub fn load_run_events(app_id: &str, run_id: &str) -> Result<Vec<Event>, String> {
    let app_dir =
        crate::utils::find_app_dir(app_id).ok_or_else(|| format!("app not found: {app_id}"))?;
    let events_path = app_dir
        .join("outbox")
        .join("runs")
        .join(run_id)
        .join("events.jsonl");
    if !events_path.exists() {
        return Err(format!(
            "events.jsonl not found for {app_id} run {run_id}"
        ));
    }
    let log = EventLog::load_from_file(app_id, run_id, &events_path)?;
    Ok(log.events().to_vec())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn append_event_creates_hash_chain() {
        let mut log = EventLog::new("test-app", "run-001");
        log.append_event(
            EventType::Fetch,
            Some("https://api.example.com/data".to_string()),
            None,
            None,
            Some("fetched 42 items".to_string()),
        );
        log.append_event(EventType::Render, None, None, None, Some("template rendered".to_string()));
        log.append_event(EventType::Seal, None, None, None, Some("evidence sealed".to_string()));

        assert_eq!(log.events().len(), 3);
        // First event prev_hash is empty
        assert_eq!(log.events()[0].prev_hash, "");
        // Second event links to first
        assert_eq!(log.events()[1].prev_hash, log.events()[0].sha256);
        // Third event links to second
        assert_eq!(log.events()[2].prev_hash, log.events()[1].sha256);
        // All hashes are non-empty hex strings
        for event in log.events() {
            assert!(!event.sha256.is_empty());
            assert_eq!(event.sha256.len(), 64); // SHA-256 hex = 64 chars
        }
    }

    #[test]
    fn verify_chain_passes_for_valid_log() {
        let mut log = EventLog::new("test-app", "run-002");
        log.append_event(EventType::Navigate, Some("https://example.com".to_string()), None, None, None);
        log.append_event(EventType::Click, None, Some("#submit".to_string()), None, None);
        log.append_event(EventType::Fill, None, Some("#email".to_string()), Some("user@test.com".to_string()), None);
        assert!(log.verify_chain());
    }

    #[test]
    fn verify_chain_fails_on_tampered_event() {
        let mut log = EventLog::new("test-app", "run-003");
        log.append_event(EventType::Fetch, Some("https://api.example.com".to_string()), None, None, None);
        log.append_event(EventType::Render, None, None, None, None);

        // Tamper with the first event's URL
        log.events[0].url = Some("https://evil.com".to_string());
        assert!(!log.verify_chain());
    }

    #[test]
    fn prominent_flag_set_for_preview_and_signoff() {
        let mut log = EventLog::new("test-app", "run-004");
        log.append_event(EventType::Fetch, None, None, None, None);
        log.append_event(EventType::Preview, None, None, None, Some("proposed action".to_string()));
        log.append_event(EventType::SignOff, None, None, None, Some("user approved".to_string()));
        log.append_event(EventType::Render, None, None, None, None);

        assert!(!log.events()[0].prominent); // Fetch
        assert!(log.events()[1].prominent);  // Preview
        assert!(log.events()[2].prominent);  // SignOff
        assert!(!log.events()[3].prominent); // Render
    }

    #[test]
    fn save_and_load_roundtrip() {
        let dir = std::env::temp_dir().join(format!("event-log-test-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&dir).unwrap();

        let mut log = EventLog::new("test-app", "run-005");
        log.append_event(EventType::Fetch, Some("https://api.example.com".to_string()), None, None, Some("fetched".to_string()));
        log.append_event(EventType::Render, None, None, None, Some("rendered".to_string()));
        log.append_event(EventType::Seal, None, None, None, Some("sealed".to_string()));

        let path = log.save_events(&dir).unwrap();
        assert!(path.exists());

        let loaded = EventLog::load_from_file("test-app", "run-005", &path).unwrap();
        assert_eq!(loaded.events().len(), 3);
        assert_eq!(loaded.events()[0].event_type, EventType::Fetch);
        assert_eq!(loaded.events()[1].event_type, EventType::Render);
        assert_eq!(loaded.events()[2].event_type, EventType::Seal);
        assert!(loaded.verify_chain());

        // Cleanup
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn empty_log_verifies() {
        let log = EventLog::new("test-app", "run-006");
        assert!(log.verify_chain());
        assert_eq!(log.events().len(), 0);
    }

    #[test]
    fn event_type_serialization() {
        let event_type = EventType::SignOff;
        let json = serde_json::to_string(&event_type).unwrap();
        assert_eq!(json, "\"SIGN_OFF\"");

        let parsed: EventType = serde_json::from_str("\"FETCH\"").unwrap();
        assert_eq!(parsed, EventType::Fetch);
    }
}
