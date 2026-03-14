// Diagram: 14-cron-morning-cycle
use std::time::Duration;

use chrono::{DateTime, Datelike, Timelike, Utc};
use serde::{Deserialize, Serialize};

use crate::state::AppState;

pub async fn run_scheduler(state: AppState) {
    if let Ok(schedules) =
        crate::persistence::read_json::<Vec<crate::state::Schedule>>(&schedules_path())
    {
        *state.schedules.write() = schedules;
    }

    loop {
        let schedules = state.schedules.read().clone();
        let now = Utc::now();
        let mut runs = read_schedule_runs();
        for schedule in &schedules {
            if !schedule.enabled
                || !cron_matches(&schedule.cron, &now)
                || already_ran_this_minute(&runs, &schedule.id, &now)
            {
                continue;
            }

            match crate::app_engine::runner::run_app(&schedule.app_id, &state).await {
                Ok(report_path) => runs.push(ScheduleRunRecord {
                    schedule_id: schedule.id.clone(),
                    app_id: schedule.app_id.clone(),
                    cron: schedule.cron.clone(),
                    ran_at: crate::utils::now_iso8601(),
                    status: "ok".to_string(),
                    report: Some(report_path.display().to_string()),
                    error: None,
                }),
                Err(error) => {
                    tracing::error!(schedule_id = %schedule.id, %error, "schedule dispatch failed");
                    runs.push(ScheduleRunRecord {
                        schedule_id: schedule.id.clone(),
                        app_id: schedule.app_id.clone(),
                        cron: schedule.cron.clone(),
                        ran_at: crate::utils::now_iso8601(),
                        status: "error".to_string(),
                        report: None,
                        error: Some(error),
                    });
                }
            }
        }

        if let Err(error) = crate::persistence::write_json(&schedule_runs_path(), &runs) {
            tracing::error!(%error, "failed to persist schedule runs");
        }

        tokio::time::sleep(Duration::from_secs(60)).await;
    }
}

pub fn validate_cron(expr: &str) -> bool {
    let parts: Vec<&str> = expr.split_whitespace().collect();
    parts.len() == 5
        && field_valid(parts[0], 0, 59)
        && field_valid(parts[1], 0, 23)
        && field_valid(parts[2], 1, 31)
        && field_valid(parts[3], 1, 12)
        && field_valid(parts[4], 0, 7)
}

pub fn cron_matches(expr: &str, now: &DateTime<Utc>) -> bool {
    let fields: Vec<&str> = expr.split_whitespace().collect();
    if fields.len() != 5 {
        return false;
    }
    let cron_weekday = (now.weekday().num_days_from_monday() + 1) % 7;
    let values = [
        now.minute(),
        now.hour(),
        now.day(),
        now.month(),
        cron_weekday,
    ];
    fields
        .iter()
        .zip(values.iter())
        .all(|(field, value)| field_matches(field, *value))
}

fn field_valid(field: &str, min: u32, max: u32) -> bool {
    if field == "*" {
        return true;
    }
    if let Some(step) = field.strip_prefix("*/") {
        return step.parse::<u32>().ok().is_some_and(|value| value > 0);
    }
    if field.contains(',') {
        return field.split(',').all(|part| field_valid(part, min, max));
    }
    if field.contains('-') {
        let parts = field
            .split('-')
            .filter_map(|value| value.parse::<u32>().ok())
            .collect::<Vec<_>>();
        return parts.len() == 2 && parts[0] >= min && parts[1] <= max && parts[0] <= parts[1];
    }
    field
        .parse::<u32>()
        .ok()
        .is_some_and(|value| value >= min && value <= max)
}

pub fn field_matches(field: &str, value: u32) -> bool {
    if field == "*" {
        return true;
    }
    if let Some(step) = field.strip_prefix("*/") {
        let step = step.parse::<u32>().unwrap_or(1);
        return value % step == 0;
    }
    if field.contains('-') {
        let parts = field
            .split('-')
            .filter_map(|segment| segment.parse::<u32>().ok())
            .collect::<Vec<_>>();
        if parts.len() == 2 {
            return value >= parts[0] && value <= parts[1];
        }
    }
    if field.contains(',') {
        return field
            .split(',')
            .filter_map(|segment| segment.parse::<u32>().ok())
            .any(|parsed| parsed == value);
    }
    field.parse::<u32>().map_or(false, |parsed| parsed == value)
}

#[derive(Clone, Serialize, Deserialize)]
struct ScheduleRunRecord {
    schedule_id: String,
    app_id: String,
    cron: String,
    ran_at: String,
    status: String,
    report: Option<String>,
    error: Option<String>,
}

fn schedules_path() -> std::path::PathBuf {
    crate::utils::solace_home()
        .join("daemon")
        .join("schedules.json")
}

fn schedule_runs_path() -> std::path::PathBuf {
    crate::utils::solace_home()
        .join("daemon")
        .join("schedule_runs.json")
}

fn read_schedule_runs() -> Vec<ScheduleRunRecord> {
    crate::persistence::read_json(&schedule_runs_path()).unwrap_or_default()
}

fn already_ran_this_minute(
    runs: &[ScheduleRunRecord],
    schedule_id: &str,
    now: &DateTime<Utc>,
) -> bool {
    runs.iter()
        .rev()
        .find(|run| run.schedule_id == schedule_id)
        .and_then(|run| {
            chrono::DateTime::parse_from_rfc3339(&run.ran_at)
                .ok()
                .map(|time| time.with_timezone(&Utc))
        })
        .is_some_and(|last_run| {
            last_run.year() == now.year()
                && last_run.month() == now.month()
                && last_run.day() == now.day()
                && last_run.hour() == now.hour()
                && last_run.minute() == now.minute()
        })
}

#[cfg(test)]
mod tests {
    use chrono::TimeZone;

    #[test]
    fn validates_simple_cron() {
        assert!(super::validate_cron("* * * * *"));
        assert!(super::validate_cron("*/5 8 * * 1"));
        assert!(!super::validate_cron("bad cron"));
    }

    #[test]
    fn matches_wildcard_cron() {
        let now = chrono::Utc.with_ymd_and_hms(2026, 3, 10, 8, 15, 0).unwrap();
        assert!(super::cron_matches("*/15 8 * * 2", &now));
        assert!(!super::cron_matches("*/7 8 * * 2", &now));
    }

    #[test]
    fn matches_ranges_and_lists() {
        let now = chrono::Utc.with_ymd_and_hms(2026, 3, 10, 8, 15, 0).unwrap();
        assert!(super::cron_matches("15 8 9-11 3 1,2,3", &now));
        assert!(!super::cron_matches("14 8 9-11 3 1,2,3", &now));
    }
}
