// Diagram: 05-solace-runtime-architecture
use std::fs;
use std::path::Path;

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

#[derive(Clone, Serialize, Deserialize)]
pub struct EvidenceRecord {
    pub id: String,
    pub timestamp: String,
    pub actor: String,
    pub event: String,
    pub data: Value,
    pub previous_hash: String,
    pub hash: String,
}

#[derive(Serialize)]
pub struct Part11Status {
    pub enabled: bool,
    pub alcoa: [&'static str; 5],
    pub record_count: usize,
    pub chain_valid: bool,
    pub evidence_path: String,
}

pub fn record_event(
    solace_home: &Path,
    event: &str,
    actor: &str,
    data: Value,
) -> Result<EvidenceRecord, String> {
    let evidence_path = solace_home.join("runtime").join("evidence.jsonl");
    let previous_hash = latest_hash(&evidence_path).unwrap_or_default();
    let timestamp = crate::utils::now_iso8601();
    let seed = serde_json::to_string(&json!({
        "timestamp": &timestamp,
        "actor": actor,
        "event": event,
        "data": &data,
        "previous_hash": &previous_hash,
    }))
    .map_err(|error| error.to_string())?;
    let record = EvidenceRecord {
        id: uuid::Uuid::new_v4().to_string(),
        timestamp,
        actor: actor.to_string(),
        event: event.to_string(),
        data,
        previous_hash,
        hash: crate::utils::sha256_hex(&seed),
    };
    crate::persistence::append_evidence_jsonl(solace_home, &record)?;
    Ok(record)
}

pub fn list_evidence(solace_home: &Path, limit: usize) -> Vec<EvidenceRecord> {
    let path = solace_home.join("runtime").join("evidence.jsonl");
    let mut records = crate::persistence::read_jsonl::<EvidenceRecord>(&path).unwrap_or_default();
    records.reverse();
    records.truncate(limit);
    records
}

pub fn part11_status(solace_home: &Path) -> Part11Status {
    let path = solace_home.join("runtime").join("evidence.jsonl");
    let records = crate::persistence::read_jsonl::<EvidenceRecord>(&path).unwrap_or_default();
    let mut previous = String::new();
    let mut valid = true;
    for record in &records {
        if record.previous_hash != previous {
            valid = false;
            break;
        }
        let seed = match serde_json::to_string(&json!({
            "timestamp": &record.timestamp,
            "actor": &record.actor,
            "event": &record.event,
            "data": &record.data,
            "previous_hash": &record.previous_hash,
        })) {
            Ok(seed) => seed,
            Err(_) => {
                valid = false;
                break;
            }
        };
        if crate::utils::sha256_hex(&seed) != record.hash {
            valid = false;
            break;
        }
        previous = record.hash.clone();
    }
    Part11Status {
        enabled: true,
        alcoa: [
            "attributable",
            "legible",
            "contemporaneous",
            "original",
            "accurate",
        ],
        record_count: records.len(),
        chain_valid: valid,
        evidence_path: path.display().to_string(),
    }
}

fn latest_hash(path: &Path) -> Option<String> {
    let raw = fs::read_to_string(path).ok()?;
    let line = raw.lines().rev().find(|line| !line.trim().is_empty())?;
    let record: EvidenceRecord = serde_json::from_str(line).ok()?;
    Some(record.hash)
}
