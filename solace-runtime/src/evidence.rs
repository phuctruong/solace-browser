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
    pub continuous_chain_valid: bool,
    pub segment_count: usize,
    pub restart_count: usize,
    pub evidence_path: String,
}

#[derive(Serialize)]
pub struct EvidenceRepairReport {
    pub repaired: bool,
    pub backup_path: String,
    pub repaired_records: usize,
    pub skipped_lines: usize,
    pub previous_restart_count: usize,
    pub previous_segment_count: usize,
    pub evidence_path: String,
}

#[derive(Default)]
struct EvidenceValidation {
    record_count: usize,
    chain_valid: bool,
    continuous_chain_valid: bool,
    segment_count: usize,
    restart_count: usize,
}

fn read_evidence_records(path: &Path) -> Vec<EvidenceRecord> {
    let raw = match fs::read_to_string(path) {
        Ok(raw) => raw,
        Err(_) => return Vec::new(),
    };

    raw.lines()
        .filter(|line| !line.trim().is_empty())
        .filter_map(|line| serde_json::from_str::<EvidenceRecord>(line).ok())
        .collect()
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
    let mut records = read_evidence_records(&path);
    records.reverse();
    records.truncate(limit);
    records
}

pub fn part11_status(solace_home: &Path) -> Part11Status {
    let path = solace_home.join("runtime").join("evidence.jsonl");
    let records = read_evidence_records(&path);
    let validation = validate_records(&records);
    Part11Status {
        enabled: true,
        alcoa: [
            "attributable",
            "legible",
            "contemporaneous",
            "original",
            "accurate",
        ],
        record_count: validation.record_count,
        chain_valid: validation.chain_valid,
        continuous_chain_valid: validation.continuous_chain_valid,
        segment_count: validation.segment_count,
        restart_count: validation.restart_count,
        evidence_path: path.display().to_string(),
    }
}

pub fn repair_chain(solace_home: &Path) -> Result<EvidenceRepairReport, String> {
    let runtime_dir = solace_home.join("runtime");
    let evidence_path = runtime_dir.join("evidence.jsonl");
    let raw = fs::read_to_string(&evidence_path).map_err(|error| error.to_string())?;
    let old_records = read_evidence_records(&evidence_path);
    let old_validation = validate_records(&old_records);

    if old_records.is_empty() {
        return Err("no canonical evidence records found to repair".to_string());
    }

    let total_non_empty_lines = raw.lines().filter(|line| !line.trim().is_empty()).count();
    let skipped_lines = total_non_empty_lines.saturating_sub(old_records.len());
    let repaired_at = crate::utils::now_iso8601();
    let backup_path = runtime_dir.join(format!(
        "evidence.legacy-{}.jsonl",
        chrono::Utc::now().format("%Y%m%d-%H%M%S")
    ));

    fs::create_dir_all(&runtime_dir).map_err(|error| error.to_string())?;
    fs::copy(&evidence_path, &backup_path).map_err(|error| error.to_string())?;

    let mut repaired_records = Vec::with_capacity(old_records.len());
    let mut previous_hash = String::new();

    for record in old_records {
        let data = repaired_data(
            record.data,
            &record.previous_hash,
            &record.hash,
            &repaired_at,
        );
        let hash = compute_hash(
            &record.timestamp,
            &record.actor,
            &record.event,
            &data,
            &previous_hash,
        )?;
        repaired_records.push(EvidenceRecord {
            id: record.id,
            timestamp: record.timestamp,
            actor: record.actor,
            event: record.event,
            data,
            previous_hash: previous_hash.clone(),
            hash: hash.clone(),
        });
        previous_hash = hash;
    }

    let mut serialized = repaired_records
        .iter()
        .map(serde_json::to_string)
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| error.to_string())?
        .join("\n");
    serialized.push('\n');
    fs::write(&evidence_path, serialized).map_err(|error| error.to_string())?;

    let repair_event = record_event(
        solace_home,
        "evidence.chain_repaired",
        "runtime",
        json!({
            "backup_path": backup_path.display().to_string(),
            "repaired_records": repaired_records.len(),
            "skipped_lines": skipped_lines,
            "previous_restart_count": old_validation.restart_count,
            "previous_segment_count": old_validation.segment_count,
        }),
    )?;

    Ok(EvidenceRepairReport {
        repaired: true,
        backup_path: backup_path.display().to_string(),
        repaired_records: repaired_records.len() + 1,
        skipped_lines,
        previous_restart_count: old_validation.restart_count,
        previous_segment_count: old_validation.segment_count,
        evidence_path: evidence_path.display().to_string(),
    })
}

fn latest_hash(path: &Path) -> Option<String> {
    let raw = fs::read_to_string(path).ok()?;
    raw.lines().rev().find_map(|line| {
        if line.trim().is_empty() {
            return None;
        }
        serde_json::from_str::<EvidenceRecord>(line)
            .ok()
            .map(|record| record.hash)
    })
}

fn compute_hash(
    timestamp: &str,
    actor: &str,
    event: &str,
    data: &Value,
    previous_hash: &str,
) -> Result<String, String> {
    let seed = serde_json::to_string(&json!({
        "timestamp": timestamp,
        "actor": actor,
        "event": event,
        "data": data,
        "previous_hash": previous_hash,
    }))
    .map_err(|error| error.to_string())?;
    Ok(crate::utils::sha256_hex(&seed))
}

fn repaired_data(
    original: Value,
    legacy_previous_hash: &str,
    legacy_hash: &str,
    repaired_at: &str,
) -> Value {
    match original {
        Value::Object(mut map) => {
            map.insert(
                "_repair".to_string(),
                json!({
                    "legacy_hash": legacy_hash,
                    "legacy_previous_hash": legacy_previous_hash,
                    "repaired_at": repaired_at,
                }),
            );
            Value::Object(map)
        }
        value => json!({
            "value": value,
            "_repair": {
                "legacy_hash": legacy_hash,
                "legacy_previous_hash": legacy_previous_hash,
                "repaired_at": repaired_at,
            }
        }),
    }
}

fn validate_records(records: &[EvidenceRecord]) -> EvidenceValidation {
    let mut previous = String::new();
    let mut chain_valid = true;
    let mut continuous_chain_valid = true;
    let mut segment_count = 0usize;
    let mut restart_count = 0usize;

    for (index, record) in records.iter().enumerate() {
        let seed = match serde_json::to_string(&json!({
            "timestamp": &record.timestamp,
            "actor": &record.actor,
            "event": &record.event,
            "data": &record.data,
            "previous_hash": &record.previous_hash,
        })) {
            Ok(seed) => seed,
            Err(_) => {
                chain_valid = false;
                continuous_chain_valid = false;
                break;
            }
        };

        if crate::utils::sha256_hex(&seed) != record.hash {
            chain_valid = false;
            continuous_chain_valid = false;
            break;
        }

        if index == 0 || record.previous_hash.is_empty() {
            segment_count += 1;
            if index > 0 {
                restart_count += 1;
                continuous_chain_valid = false;
            }
        } else if record.previous_hash != previous {
            chain_valid = false;
            continuous_chain_valid = false;
            break;
        }

        previous = record.hash.clone();
    }

    EvidenceValidation {
        record_count: records.len(),
        chain_valid,
        continuous_chain_valid,
        segment_count,
        restart_count,
    }
}
