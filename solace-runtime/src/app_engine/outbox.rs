// Diagram: 13-app-inbox-outbox
use std::fs;
use std::path::PathBuf;

use chrono::Utc;
use serde_json::Value;

use crate::evidence::EvidenceRecord;

pub fn write_run_output(
    app_id: &str,
    html: &str,
    evidence: &EvidenceRecord,
    payload: &Value,
) -> Result<PathBuf, String> {
    let run_id = Utc::now().format("%Y%m%dT%H%M%SZ").to_string();
    let run_dir = crate::utils::solace_home()
        .join("apps")
        .join(app_id)
        .join("outbox")
        .join("runs")
        .join(run_id);
    fs::create_dir_all(&run_dir).map_err(|error| error.to_string())?;
    fs::write(run_dir.join("report.html"), html).map_err(|error| error.to_string())?;
    fs::write(
        run_dir.join("evidence.json"),
        serde_json::to_string_pretty(evidence).map_err(|error| error.to_string())?,
    )
    .map_err(|error| error.to_string())?;
    fs::write(
        run_dir.join("payload.json"),
        serde_json::to_string_pretty(payload).map_err(|error| error.to_string())?,
    )
    .map_err(|error| error.to_string())?;
    Ok(run_dir)
}
