// Diagram: 05-solace-runtime-architecture
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;

use serde::de::DeserializeOwned;
use serde::Serialize;

pub fn read_json<T: DeserializeOwned>(path: &Path) -> Result<T, String> {
    let raw = fs::read_to_string(path).map_err(|error| error.to_string())?;
    serde_json::from_str(&raw).map_err(|error| error.to_string())
}

pub fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    let raw = serde_json::to_string_pretty(value).map_err(|error| error.to_string())?;
    fs::write(path, raw).map_err(|error| error.to_string())
}

pub fn write_port_lock(solace_home: &Path, port: u16, token_hash: &str) -> Result<(), String> {
    let path = solace_home.join("port.lock");
    let payload = serde_json::json!({
        "port": port,
        "token_hash": token_hash,
        "pid": std::process::id(),
        "started_at": crate::utils::now_iso8601(),
    });
    write_json(&path, &payload)
}

pub fn remove_port_lock(solace_home: &Path) -> Result<(), String> {
    let path = solace_home.join("port.lock");
    match fs::remove_file(path) {
        Ok(_) => Ok(()),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(error.to_string()),
    }
}

pub fn append_evidence_jsonl(solace_home: &Path, value: &impl Serialize) -> Result<(), String> {
    let path = solace_home.join("runtime").join("evidence.jsonl");
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    let line = serde_json::to_string(value).map_err(|error| error.to_string())?;
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .map_err(|error| error.to_string())?;
    writeln!(file, "{line}").map_err(|error| error.to_string())
}

pub fn read_jsonl<T: DeserializeOwned>(path: &Path) -> Result<Vec<T>, String> {
    let raw = fs::read_to_string(path).map_err(|error| error.to_string())?;
    raw.lines()
        .filter(|line| !line.trim().is_empty())
        .map(|line| serde_json::from_str(line).map_err(|error| error.to_string()))
        .collect()
}
