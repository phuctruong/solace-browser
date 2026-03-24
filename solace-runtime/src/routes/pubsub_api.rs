// Diagram: apps-backoffice-framework
//! Pub/Sub + Job Queue REST API endpoints.

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use serde_json::{json, Value};
use std::collections::HashMap;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        // Pub/Sub
        .route("/api/v1/events/publish", post(publish_event))
        .route("/api/v1/events/subscribe", post(subscribe_topic))
        .route("/api/v1/events/topics", get(list_topics))
        .route("/api/v1/events/topic/:topic", get(get_topic_events))
        .route("/api/v1/events/subscriptions", get(list_subscriptions))
        // Job Queue
        .route("/api/v1/jobs", get(list_jobs))
        .route("/api/v1/jobs/enqueue", post(enqueue_job))
        .route("/api/v1/jobs/claim", post(claim_job))
        .route("/api/v1/jobs/:job_id", get(get_job))
        .route("/api/v1/jobs/:job_id/complete", post(complete_job))
        .route("/api/v1/jobs/:job_id/fail", post(fail_job))
        .route("/api/v1/jobs/stats", get(job_stats))
}

// ── Pub/Sub ──

#[derive(Deserialize)]
struct PublishRequest {
    topic: String,
    payload: Value,
    #[serde(default = "default_publisher")]
    publisher: String,
}
fn default_publisher() -> String {
    "system".to_string()
}

async fn publish_event(
    State(state): State<AppState>,
    Json(req): Json<PublishRequest>,
) -> Json<Value> {
    let event = state
        .event_bus
        .publish(&req.topic, req.payload, &req.publisher);
    Json(json!({
        "published": true,
        "event_id": event.id,
        "topic": event.topic,
        "evidence_hash": event.evidence_hash,
    }))
}

#[derive(Deserialize)]
struct SubscribeRequest {
    topic: String,
    subscriber: String,
}

async fn subscribe_topic(
    State(state): State<AppState>,
    Json(req): Json<SubscribeRequest>,
) -> Json<Value> {
    let (sub_id, _rx) = state.event_bus.subscribe(&req.topic, &req.subscriber);
    Json(json!({
        "subscribed": true,
        "subscription_id": sub_id,
        "topic": req.topic,
        "subscriber": req.subscriber,
    }))
}

async fn list_topics(State(state): State<AppState>) -> Json<Value> {
    let topics = state.event_bus.topics();
    Json(json!({
        "topics": topics.iter().map(|(t, c)| json!({"topic": t, "event_count": c})).collect::<Vec<_>>(),
        "total": topics.len(),
    }))
}

async fn get_topic_events(
    State(state): State<AppState>,
    Path(topic): Path<String>,
    Query(params): Query<HashMap<String, String>>,
) -> Json<Value> {
    let limit: usize = params
        .get("limit")
        .and_then(|l| l.parse().ok())
        .unwrap_or(50);
    let events = state.event_bus.recent(&topic, limit);
    Json(json!({
        "topic": topic,
        "events": events,
        "count": events.len(),
    }))
}

async fn list_subscriptions(State(state): State<AppState>) -> Json<Value> {
    let subs = state.event_bus.list_subscriptions();
    Json(json!({ "subscriptions": subs, "count": subs.len() }))
}

// ── Job Queue ──

#[derive(Deserialize)]
struct EnqueueRequest {
    job_type: String,
    payload: Value,
    #[serde(default = "default_priority")]
    priority: i32,
    #[serde(default)]
    assigned_to: String,
    parent_job_id: Option<String>,
}
fn default_priority() -> i32 {
    1
}

async fn enqueue_job(
    State(state): State<AppState>,
    Json(req): Json<EnqueueRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let job = state
        .job_queue
        .enqueue(
            &req.job_type,
            req.payload,
            req.priority,
            &req.assigned_to,
            req.parent_job_id.as_deref(),
        )
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;

    // Publish event
    state.event_bus.publish(
        "job.enqueued",
        json!({"job_id": job.id, "type": job.job_type}),
        "job_queue",
    );

    Ok(Json(json!({"enqueued": true, "job": job})))
}

async fn claim_job(
    State(state): State<AppState>,
    Json(body): Json<Value>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let worker_id = body
        .get("worker_id")
        .and_then(|v| v.as_str())
        .unwrap_or("default");

    let job = state
        .job_queue
        .claim(worker_id)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;

    match job {
        Some(j) => {
            state.event_bus.publish(
                "job.claimed",
                json!({"job_id": j.id, "worker": worker_id}),
                "job_queue",
            );
            Ok(Json(json!({"claimed": true, "job": j})))
        }
        None => Ok(Json(
            json!({"claimed": false, "message": "no jobs available"}),
        )),
    }
}

async fn get_job(
    State(state): State<AppState>,
    Path(job_id): Path<String>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let job = state
        .job_queue
        .get(&job_id)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?
        .ok_or_else(|| {
            (
                StatusCode::NOT_FOUND,
                Json(json!({"error": "job not found"})),
            )
        })?;
    Ok(Json(json!({"job": job})))
}

#[derive(Deserialize)]
struct CompleteRequest {
    result: Value,
}

async fn complete_job(
    State(state): State<AppState>,
    Path(job_id): Path<String>,
    Json(req): Json<CompleteRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    state
        .job_queue
        .complete(&job_id, req.result)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;
    state
        .event_bus
        .publish("job.completed", json!({"job_id": job_id}), "job_queue");
    Ok(Json(json!({"completed": true, "job_id": job_id})))
}

#[derive(Deserialize)]
struct FailRequest {
    error: String,
}

async fn fail_job(
    State(state): State<AppState>,
    Path(job_id): Path<String>,
    Json(req): Json<FailRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    state
        .job_queue
        .fail(&job_id, &req.error)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;
    state.event_bus.publish(
        "job.failed",
        json!({"job_id": job_id, "error": req.error}),
        "job_queue",
    );
    Ok(Json(json!({"failed": true, "job_id": job_id})))
}

async fn list_jobs(
    State(state): State<AppState>,
    Query(params): Query<HashMap<String, String>>,
) -> Json<Value> {
    let status = params.get("status").map(|s| s.as_str());
    let limit: u32 = params
        .get("limit")
        .and_then(|l| l.parse().ok())
        .unwrap_or(50);

    let jobs = state.job_queue.list(status, limit).unwrap_or_default();
    Json(json!({"jobs": jobs, "count": jobs.len()}))
}

async fn job_stats(State(state): State<AppState>) -> Json<Value> {
    let stats = state.job_queue.stats().unwrap_or_default();
    Json(stats)
}
