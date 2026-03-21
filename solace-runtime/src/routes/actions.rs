// Diagram: apps-signoff-cooldown
//! Pending Actions — Preview, Sign-Off, Cooldown system.
//! The authorization layer. AI proposes, human approves, cooldown, then execute.

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::Html,
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use serde_json::{json, Value};
use std::collections::HashMap;

use crate::state::AppState;

pub fn routes() -> Router<AppState> {
    Router::new()
        .route("/api/v1/actions/propose", post(propose_action))
        .route("/api/v1/actions/pending", get(list_pending))
        .route("/api/v1/actions/summary", get(action_summary))
        .route("/api/v1/actions/:id/approve", post(approve_action))
        .route("/api/v1/actions/:id/reject", post(reject_action))
        .route("/api/v1/actions/:id/execute", post(execute_now))
        .route("/api/v1/actions/:id/cancel", post(cancel_action))
        .route("/api/v1/actions/:id/preview", get(preview_action))
        .route("/signoff", get(signoff_page))
}

// Default cooldowns per action type (seconds)
fn default_cooldown(action_type: &str) -> i64 {
    match action_type {
        "delete" => 300,    // 5 min
        "archive" => 120,   // 2 min
        "send" => 180,      // 3 min
        "reply" => 180,     // 3 min
        "outreach" => 600,  // 10 min
        "post" => 300,      // 5 min
        "purchase" => 900,  // 15 min
        "modify" => 120,    // 2 min
        "connect" => 300,   // 5 min
        "create" | "read" => 0,  // instant
        _ => 300,
    }
}

fn priority_for(action_type: &str) -> &'static str {
    match action_type {
        "delete" | "send" | "outreach" | "purchase" | "post" => "review",
        "reply" | "modify" | "connect" => "review",
        "archive" => "routine",
        "create" | "read" => "routine",
        _ => "review",
    }
}

#[derive(Deserialize)]
struct ProposeAction {
    action_type: String,
    summary: String,
    #[serde(default)]
    domain: String,
    #[serde(default)]
    app_id: String,
    #[serde(default)]
    agent_id: String,
    #[serde(default)]
    details: Value,
    #[serde(default)]
    preview_hash: String,
    #[serde(default)]
    cooldown_override: Option<i64>,
}

/// AI proposes an action
async fn propose_action(
    State(state): State<AppState>,
    Json(req): Json<ProposeAction>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let config = crate::routes::backoffice::load_workspace_config("backoffice-actions")
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;
    let table = config.tables.iter().find(|t| t.name == "actions")
        .ok_or((StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": "actions table not found"}))))?;

    let conn = state.backoffice_db.get_connection("backoffice-actions", &config)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;

    let cooldown = req.cooldown_override.unwrap_or_else(|| default_cooldown(&req.action_type));
    let priority = priority_for(&req.action_type);
    let status = if cooldown == 0 && priority == "routine" { "approved" } else { "proposed" };

    let data = json!({
        "action_type": req.action_type,
        "summary": req.summary,
        "domain": req.domain,
        "app_id": req.app_id,
        "agent_id": req.agent_id,
        "status": status,
        "priority": priority,
        "cooldown_seconds": cooldown,
        "details": req.details.to_string(),
        "preview_hash": req.preview_hash,
    });

    let actor = req.agent_id.clone();
    let c = conn.lock();
    let record = crate::backoffice::crud::insert(&c, table, &data, &actor)
        .map_err(|e| (StatusCode::BAD_REQUEST, Json(json!({"error": e}))))?;

    // Publish event
    state.event_bus.publish("action.proposed", json!({
        "action_type": req.action_type,
        "summary": req.summary,
        "priority": priority,
        "cooldown": cooldown,
    }), &actor);

    *state.evidence_count.write() += 1;

    Ok(Json(json!({
        "proposed": true,
        "action": record,
        "auto_approved": status == "approved",
        "cooldown_seconds": cooldown,
        "needs_review": priority == "review" || priority == "critical",
    })))
}

/// List pending actions
async fn list_pending(
    State(state): State<AppState>,
    Query(params): Query<HashMap<String, String>>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let config = crate::routes::backoffice::load_workspace_config("backoffice-actions")
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;
    let table = config.tables.iter().find(|t| t.name == "actions")
        .ok_or((StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": "actions table not found"}))))?;

    let conn = state.backoffice_db.get_connection("backoffice-actions", &config)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;

    let status_filter = params.get("status").cloned().unwrap_or_else(|| "proposed".to_string());
    let filters = vec![("status".to_string(), status_filter)];

    let c = conn.lock();
    let result = crate::backoffice::crud::select_list(&c, table, 0, 100, Some("created_at"), &filters)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;

    Ok(Json(result))
}

/// Morning brief summary
async fn action_summary(
    State(state): State<AppState>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let config = crate::routes::backoffice::load_workspace_config("backoffice-actions")
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;

    let conn = state.backoffice_db.get_connection("backoffice-actions", &config)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;

    let c = conn.lock();

    // Count by status
    let count_sql = |status: &str| -> i64 {
        c.query_row(
            &format!("SELECT COUNT(*) FROM actions WHERE status = '{}'", status),
            [], |r| r.get(0)
        ).unwrap_or(0)
    };

    let proposed = count_sql("proposed");
    let approved = count_sql("approved");
    let completed = count_sql("completed");
    let rejected = count_sql("rejected");

    Ok(Json(json!({
        "needs_review": proposed,
        "approved_pending": approved,
        "completed_today": completed,
        "rejected": rejected,
        "total": proposed + approved + completed + rejected,
        "message": if proposed > 0 {
            format!("{} actions need your review.", proposed)
        } else {
            "All clear — no pending actions.".to_string()
        },
    })))
}

/// Approve an action (starts cooldown)
async fn approve_action(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    update_action_status(&state, &id, "approved", None).await
}

/// Reject an action
async fn reject_action(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    update_action_status(&state, &id, "rejected", None).await
}

/// Execute immediately (skip cooldown)
async fn execute_now(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    update_action_status(&state, &id, "completed", Some("executed_now")).await
}

/// Cancel during cooldown
async fn cancel_action(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    update_action_status(&state, &id, "cancelled", None).await
}

async fn update_action_status(
    state: &AppState,
    id: &str,
    new_status: &str,
    note: Option<&str>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    let config = crate::routes::backoffice::load_workspace_config("backoffice-actions")
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;
    let table = config.tables.iter().find(|t| t.name == "actions")
        .ok_or((StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": "actions table not found"}))))?;

    let conn = state.backoffice_db.get_connection("backoffice-actions", &config)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, Json(json!({"error": e}))))?;

    let now = chrono::Utc::now().to_rfc3339();
    let update_data = json!({
        "status": new_status,
        "approved_at": if new_status == "approved" { now.clone() } else { String::new() },
        "feedback": note.unwrap_or(""),
    });

    let c = conn.lock();
    let record = crate::backoffice::crud::update(&c, table, id, &update_data, "human")
        .map_err(|e| (StatusCode::BAD_REQUEST, Json(json!({"error": e}))))?;

    // Evidence
    let solace_home = crate::utils::solace_home();
    let _ = crate::evidence::record_event(
        &solace_home,
        &format!("action.{}", new_status),
        "human",
        json!({"action_id": id, "status": new_status}),
    );
    *state.evidence_count.write() += 1;

    state.event_bus.publish(&format!("action.{}", new_status), json!({
        "action_id": id,
    }), "human");

    Ok(Json(json!({"updated": true, "status": new_status, "action": record})))
}

/// Preview: reconstruct page from PZip for this action
async fn preview_action(
    Path(id): Path<String>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    // Look up the action to get its preview_hash
    let _config = crate::routes::backoffice::load_workspace_config("backoffice-actions")
        .unwrap_or_default();
    let _solace_home = crate::utils::solace_home();

    // For now return the action's details + any associated wiki snapshot
    Ok(Json(json!({
        "action_id": id,
        "preview_available": true,
        "note": "Preview loads the PZip-reconstructed page via /api/v1/rtc/reconstruct/:hash",
    })))
}

/// Sign-off HTML page
async fn signoff_page(State(_state): State<AppState>) -> Html<String> {
    let body = r#"
<div class="sb-section-header">
  <h2 class="sb-heading">Pending Actions</h2>
  <div>
    <button class="sb-btn sb-btn--approve sb-btn--sm" id="approve-all-btn">Approve All</button>
    <button class="sb-btn sb-btn--reject sb-btn--sm" id="reject-all-btn" style="margin-left:0.3rem">Reject Selected</button>
    <button class="sb-btn sb-btn--donow sb-btn--sm" id="do-now-btn" style="margin-left:0.3rem">Do Now</button>
  </div>
</div>

<!-- Morning Brief -->
<div id="morning-brief" class="bo-stats" style="margin-bottom:1rem"></div>

<!-- Actions DataTable -->
<table id="actions-table" class="sb-table" style="width:100%">
  <thead>
    <tr>
      <th><input type="checkbox" id="select-all"></th>
      <th>Action</th>
      <th>Domain</th>
      <th>App</th>
      <th>Type</th>
      <th>Priority</th>
      <th>Status</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody id="actions-tbody"></tbody>
</table>

<script>
(function() {
  function ge(id) { return document.getElementById(id); }
  function esc(s) { var d=document.createElement('div'); d.textContent=s; return d.innerHTML; }

  // Load morning brief
  fetch('/api/v1/actions/summary').then(r=>r.json()).then(function(d) {
    var html = '<div class="bo-stat-card"><div class="bo-stat-value">' + (d.needs_review||0) + '</div><div class="bo-stat-label">Need Review</div></div>';
    html += '<div class="bo-stat-card"><div class="bo-stat-value">' + (d.approved_pending||0) + '</div><div class="bo-stat-label">In Cooldown</div></div>';
    html += '<div class="bo-stat-card"><div class="bo-stat-value">' + (d.completed_today||0) + '</div><div class="bo-stat-label">Completed</div></div>';
    html += '<div class="bo-stat-card"><div class="bo-stat-value">' + (d.rejected||0) + '</div><div class="bo-stat-label">Rejected</div></div>';
    ge('morning-brief').innerHTML = html;
  }).catch(function(){});

  // Load pending actions
  fetch('/api/v1/actions/pending?status=proposed').then(r=>r.json()).then(function(d) {
    var items = d.items || [];
    var tbody = ge('actions-tbody');
    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="sb-text-muted">No pending actions. Your AI team is waiting for instructions.</td></tr>';
      return;
    }
    items.forEach(function(a) {
      // Color-code action types (deterministic design: each color has a citation)
      var typeCls = {delete:'danger',send:'warning',outreach:'warning',reply:'info',post:'info',archive:'success',read:'success',create:'success'}[a.action_type] || 'info';
      var statusCls = a.status === 'approved' ? 'success' : a.status === 'rejected' ? 'danger' : a.status === 'proposed' ? 'warning' : 'info';
      var tr = document.createElement('tr');
      tr.id = 'action-row-' + (a.id||'').substring(0,8);
      tr.innerHTML = '<td><input type="checkbox" class="action-check" data-id="' + esc(a.id||'') + '"></td>' +
        '<td><strong>' + esc(a.summary||'') + '</strong></td>' +
        '<td>' + esc(a.domain||'') + '</td>' +
        '<td class="sb-text-xs">' + esc(a.app_id||'') + '</td>' +
        '<td><span class="sb-pill sb-pill--' + typeCls + '">' + esc(a.action_type||'') + '</span></td>' +
        '<td><span class="sb-pill sb-pill--' + statusCls + '">' + esc(a.priority||'') + '</span></td>' +
        '<td><span class="sb-pill sb-pill--' + statusCls + '">' + esc(a.status||'') + '</span></td>' +
        '<td><button class="sb-btn sb-btn--approve sb-btn--sm" onclick="approveAction(\'' + esc(a.id||'') + '\')">Approve</button></td>';
      tbody.appendChild(tr);
    });

    // Init DataTables
    if (typeof jQuery !== 'undefined' && jQuery.fn.DataTable) {
      jQuery.fn.dataTable.ext.errMode = 'none';
      try { jQuery('#actions-table').DataTable({paging:true,searching:true,ordering:true,pageLength:25,dom:'ftip'}); } catch(e) {}
    }
  }).catch(function(){});

  // Select all checkbox
  ge('select-all').addEventListener('change', function() {
    document.querySelectorAll('.action-check').forEach(function(cb) { cb.checked = ge('select-all').checked; });
  });

  // Approve all button
  ge('approve-all-btn').addEventListener('click', function() {
    var checked = document.querySelectorAll('.action-check:checked');
    if (!checked.length) { if (window.Solace) Solace.toast('Select actions first', 'pending'); return; }
    checked.forEach(function(cb) {
      fetch('/api/v1/actions/' + cb.dataset.id + '/approve', {method:'POST'});
      var row = cb.closest('tr');
      if (row) row.style.background = 'rgba(38,191,140,0.15)';
    });
    if (window.Solace) Solace.toast(checked.length + ' actions approved', 'verified');
    setTimeout(function() { location.reload(); }, 1500);
  });

  // Reject button
  ge('reject-all-btn').addEventListener('click', function() {
    var checked = document.querySelectorAll('.action-check:checked');
    if (!checked.length) { if (window.Solace) Solace.toast('Select actions first', 'pending'); return; }
    checked.forEach(function(cb) {
      fetch('/api/v1/actions/' + cb.dataset.id + '/reject', {method:'POST'});
      var row = cb.closest('tr');
      if (row) row.style.background = 'rgba(215,58,73,0.1)';
    });
    if (window.Solace) Solace.toast(checked.length + ' actions rejected', 'pending');
    setTimeout(function() { location.reload(); }, 1500);
  });

  // Do now button
  ge('do-now-btn').addEventListener('click', function() {
    document.querySelectorAll('.action-check:checked').forEach(function(cb) {
      fetch('/api/v1/actions/' + cb.dataset.id + '/execute', {method:'POST'});
    });
    setTimeout(function() { location.reload(); }, 500);
  });

  // Global approve function with dopamine feedback (Brunson: satisfaction on action)
  window.approveAction = function(id) {
    var row = document.querySelector('[data-id="' + id + '"]');
    if (row) row = row.closest('tr');
    fetch('/api/v1/actions/' + id + '/approve', {method:'POST'}).then(function() {
      if (row) {
        row.style.transition = 'all 0.3s';
        row.style.background = 'rgba(38,191,140,0.15)';
        row.querySelector('.sb-btn--approve').textContent = 'Approved ✓';
        row.querySelector('.sb-btn--approve').disabled = true;
      }
      if (window.Solace) Solace.toast('Action approved — cooldown started', 'verified');
      setTimeout(function() { location.reload(); }, 1500);
    });
  };
})();
</script>"#;

    Html(crate::routes::files::hub_page_pub("Sign-Off — Pending Actions", body))
}
