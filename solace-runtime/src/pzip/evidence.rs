use crate::pzip::Result;
use chrono::Utc;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvidenceEntry {
    pub chain_index: u64,
    pub prev_hash: String,
    pub entry_hash: String,
    pub app_id: String,
    pub run_id: String,
    pub timestamp: String,
    pub report_sha256: String,
    pub alcoa: AlcoaFields,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlcoaFields {
    pub attributable: String,
    pub legible: bool,
    pub contemporaneous: bool,
    pub original: bool,
    pub accurate: bool,
}

#[derive(Debug, Default, Clone, Serialize, Deserialize)]
pub struct EvidenceChain {
    entries: Vec<EvidenceEntry>,
}

impl EvidenceChain {
    pub fn new() -> Self {
        Self {
            entries: Vec::new(),
        }
    }
    pub fn load(path: &Path) -> Result<Self> {
        Ok(if path.exists() {
            serde_json::from_slice(&fs::read(path)?)?
        } else {
            Self::new()
        })
    }
    pub fn append(
        &mut self,
        app_id: &str,
        run_id: &str,
        report_bytes: &[u8],
        user_email: &str,
    ) -> &EvidenceEntry {
        let report_sha256 = hex(report_bytes);
        let prev_hash = self
            .entries
            .last()
            .map(|entry| entry.entry_hash.clone())
            .unwrap_or_default();
        let mut entry = EvidenceEntry {
            chain_index: self.entries.len() as u64,
            prev_hash,
            entry_hash: String::new(),
            app_id: app_id.to_string(),
            run_id: run_id.to_string(),
            timestamp: Utc::now().to_rfc3339(),
            report_sha256,
            alcoa: AlcoaFields {
                attributable: user_email.to_string(),
                legible: true,
                contemporaneous: true,
                original: true,
                accurate: true,
            },
        };
        entry.entry_hash = entry_hash(&entry);
        self.entries.push(entry);
        self.entries.last().expect("entry appended")
    }
    pub fn verify(&self) -> bool {
        self.entries.iter().enumerate().all(|(i, entry)| {
            entry.prev_hash
                == if i == 0 {
                    ""
                } else {
                    self.entries[i - 1].entry_hash.as_str()
                }
                && entry.entry_hash == entry_hash(entry)
                && entry.chain_index == i as u64
        })
    }
    pub fn save(&self, path: &Path) -> Result<()> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(path, serde_json::to_vec_pretty(self)?)?;
        Ok(())
    }
    pub fn compress_bundle(&self) -> Result<Vec<u8>> {
        super::json::compress(&serde_json::to_vec(&self.entries)?)
    }
}

fn entry_hash(entry: &EvidenceEntry) -> String {
    #[derive(Serialize)]
    struct Payload<'a> {
        chain_index: u64,
        prev_hash: &'a str,
        app_id: &'a str,
        run_id: &'a str,
        timestamp: &'a str,
        report_sha256: &'a str,
        alcoa: &'a AlcoaFields,
    }
    let payload = serde_json::to_vec(&Payload {
        chain_index: entry.chain_index,
        prev_hash: &entry.prev_hash,
        app_id: &entry.app_id,
        run_id: &entry.run_id,
        timestamp: &entry.timestamp,
        report_sha256: &entry.report_sha256,
        alcoa: &entry.alcoa,
    })
    .expect("hash payload");
    hex(&payload)
}

fn hex(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

#[cfg(test)]
mod tests {
    use super::EvidenceChain;

    #[test]
    fn appends_and_verifies_chain() {
        let mut chain = EvidenceChain::new();
        chain.append("app", "run-1", b"report", "user@solace.ai");
        chain.append("app", "run-2", b"report-2", "user@solace.ai");
        assert!(chain.verify());
        assert_eq!(&chain.compress_bundle().unwrap()[..4], b"PZJS");
    }
}
