use std::time::Duration;

use chrono::{DateTime, Datelike, Timelike, Utc};

use crate::state::AppState;

pub async fn run_scheduler(state: AppState) {
    loop {
        tokio::time::sleep(Duration::from_secs(60)).await;
        let schedules = state.schedules.read().clone();
        let now = Utc::now();
        for schedule in &schedules {
            if schedule.enabled && cron_matches(&schedule.cron, &now) {
                if let Err(error) =
                    crate::app_engine::runner::run_app(&schedule.app_id, &state).await
                {
                    tracing::error!(schedule_id = %schedule.id, %error, "schedule dispatch failed");
                }
            }
        }
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
    let parts: Vec<&str> = expr.split_whitespace().collect();
    if parts.len() != 5 {
        return false;
    }

    field_matches(parts[0], now.minute(), 59)
        && field_matches(parts[1], now.hour(), 23)
        && field_matches(parts[2], now.day(), 31)
        && field_matches(parts[3], now.month(), 12)
        && field_matches(parts[4], now.weekday().num_days_from_sunday(), 7)
}

fn field_valid(field: &str, min: u32, max: u32) -> bool {
    if field == "*" {
        return true;
    }
    for part in field.split(',') {
        if let Some(step) = part.strip_prefix("*/") {
            if step
                .parse::<u32>()
                .ok()
                .filter(|value| *value > 0)
                .is_none()
            {
                return false;
            }
            continue;
        }
        if part
            .parse::<u32>()
            .ok()
            .filter(|value| *value >= min && *value <= max)
            .is_none()
        {
            return false;
        }
    }
    true
}

fn field_matches(field: &str, value: u32, ceiling: u32) -> bool {
    if field == "*" {
        return true;
    }
    field.split(',').any(|part| {
        if let Some(step) = part.strip_prefix("*/") {
            return step
                .parse::<u32>()
                .ok()
                .filter(|step| *step > 0)
                .is_some_and(|step| value % step == 0);
        }
        part.parse::<u32>().ok().is_some_and(|parsed| {
            if value == 0 && parsed == ceiling {
                true
            } else {
                parsed == value
            }
        })
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
}
