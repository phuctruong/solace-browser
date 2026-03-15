// Diagram: hub-ux-architecture
// Events API — the universal view. Every action is an event.
// Events are the atoms of the system. Show them and everything is transparent.

use axum::{extract::Query, routing::get, Json, Router};
use serde::Deserialize;
use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new().route("/api/v1/events", get(list_events))
}

#[derive(Deserialize)]
struct EventQuery {
    limit: Option<usize>,
    domain: Option<String>,
    app: Option<String>,
    #[serde(rename = "type")]
    event_type: Option<String>,
}

/// GET /api/v1/events — the heartbeat of the system.
///
/// Scans all app outbox/runs/*/events.jsonl files and returns a unified,
/// time-sorted list of events across all apps and domains.
/// Filterable by domain, app, and event type.
async fn list_events(Query(query): Query<EventQuery>) -> Json<Value> {
    let limit = query.limit.unwrap_or(100);
    let mut all_events: Vec<Value> = Vec::new();

    // Scan all app directories for events.jsonl files
    for app_dir in crate::utils::scan_app_dirs() {
        let manifest = match crate::app_engine::inbox::load_manifest(&app_dir) {
            Ok(m) => m,
            Err(_) => continue,
        };

        // Filter by app if specified
        if let Some(ref app_filter) = query.app {
            if manifest.id != *app_filter {
                continue;
            }
        }

        // Filter by domain if specified
        if let Some(ref domain_filter) = query.domain {
            if manifest.domain != *domain_filter {
                continue;
            }
        }

        let runs_dir = app_dir.join("outbox").join("runs");
        if !runs_dir.is_dir() {
            continue;
        }

        // Read recent run directories (sorted newest first, take last 10)
        let mut run_dirs: Vec<PathBuf> = fs::read_dir(&runs_dir)
            .into_iter()
            .flatten()
            .flatten()
            .map(|e| e.path())
            .filter(|p| p.is_dir())
            .collect();
        run_dirs.sort();
        run_dirs.reverse();
        let recent_runs = &run_dirs[..std::cmp::min(10, run_dirs.len())];

        for run_dir in recent_runs {
            let events_file = run_dir.join("events.jsonl");
            if !events_file.is_file() {
                continue;
            }

            let run_id = run_dir
                .file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("")
                .to_string();

            if let Ok(content) = fs::read_to_string(&events_file) {
                for line in content.lines() {
                    if line.trim().is_empty() {
                        continue;
                    }
                    if let Ok(mut event) = serde_json::from_str::<Value>(line) {
                        // Filter by event type if specified
                        if let Some(ref type_filter) = query.event_type {
                            let et = event
                                .get("event_type")
                                .and_then(|v| v.as_str())
                                .unwrap_or("");
                            if !et.eq_ignore_ascii_case(type_filter) {
                                continue;
                            }
                        }

                        // Enrich event with app/domain/run context
                        if let Some(obj) = event.as_object_mut() {
                            obj.insert("app_id".to_string(), json!(manifest.id));
                            obj.insert("app_name".to_string(), json!(manifest.name));
                            obj.insert("domain".to_string(), json!(manifest.domain));
                            obj.insert("run_id".to_string(), json!(run_id));
                            // Determine L1-L5 level from event type
                            let level = classify_event_level(
                                obj.get("event_type")
                                    .and_then(|v| v.as_str())
                                    .unwrap_or(""),
                            );
                            obj.insert("level".to_string(), json!(level));
                        }

                        all_events.push(event);
                    }
                }
            }
        }
    }

    // Sort by timestamp (newest first)
    all_events.sort_by(|a, b| {
        let ts_a = a.get("timestamp").and_then(|v| v.as_str()).unwrap_or("");
        let ts_b = b.get("timestamp").and_then(|v| v.as_str()).unwrap_or("");
        ts_b.cmp(ts_a)
    });

    // Apply limit
    all_events.truncate(limit);

    Json(json!({
        "events": all_events,
        "count": all_events.len(),
        "limit": limit,
    }))
}

/// Classify event into L1-L5 power level based on event type.
///
/// L1 = CPU only ($0) — no LLM call. Fetch, render, parse, seal.
/// L2 = Haiku/Flash class (~$0.001) — fast, cheap. Classify, extract.
/// L3 = Sonnet/Pro class (~$0.01) — workhorse. Draft, analyze, generate.
/// L4 = Opus/Ultra class (~$0.10) — deep reasoning. Plan, review.
/// L5 = Multi-model consensus (~$1.00) — ABCD harness. Critical decisions.
///
/// The level is determined by what LLM (if any) the action requires,
/// not just the action name. Actions that need no LLM are always L1.
fn classify_event_level(event_type: &str) -> &'static str {
    match event_type.to_uppercase().as_str() {
        // L1: CPU only — deterministic, no LLM call
        "FETCH" | "RENDER" | "SEAL" | "NAVIGATE" | "SCREENSHOT" | "CACHE_HIT" | "REPLAY" => "L1",
        // L2: Haiku/Flash — fast classification, short extraction
        "CLASSIFY" | "EXTRACT" | "TAG" | "FILTER" | "PARSE" => "L2",
        // L3: Sonnet/Pro — the default for any creative/analytical LLM work
        "DRAFT" | "COMPOSE" | "ANALYZE" | "GENERATE" | "SUMMARIZE" | "SYNTHESIZE" => "L3",
        // L4: Opus/Ultra — deep reasoning, multi-step planning
        "REASON" | "PLAN" | "REVIEW" | "AUDIT" | "DIAGNOSE" => "L4",
        // L5: Multi-model consensus (ABCD harness) — irreversible actions
        "SEND" | "SUBMIT" | "DELETE" | "TRANSFER" | "PUBLISH" | "SIGN" => "L5",
        // Default: no LLM = L1
        _ => "L1",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn classify_fetch_is_l1() {
        assert_eq!(classify_event_level("FETCH"), "L1");
        assert_eq!(classify_event_level("fetch"), "L1");
    }

    #[test]
    fn classify_draft_is_l3() {
        assert_eq!(classify_event_level("DRAFT"), "L3");
    }

    #[test]
    fn classify_send_is_l5() {
        assert_eq!(classify_event_level("SEND"), "L5");
    }

    #[test]
    fn classify_unknown_is_l1() {
        assert_eq!(classify_event_level("UNKNOWN_TYPE"), "L1");
    }
}
