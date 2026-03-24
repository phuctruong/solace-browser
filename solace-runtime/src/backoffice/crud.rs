// Diagram: apps-backoffice-framework
//! Generic CRUD operations for backoffice apps.
//! Validates input against schema, executes SQL, records evidence.

use chrono::Utc;
use rusqlite::{params_from_iter, Connection};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

use super::schema::TableDef;

/// Insert a new record. Returns the record with generated id + timestamps.
pub fn insert(
    conn: &Connection,
    table: &TableDef,
    data: &Value,
    actor: &str,
) -> Result<Value, String> {
    let obj = data.as_object().ok_or("body must be a JSON object")?;

    let id = uuid::Uuid::new_v4().to_string();
    let now = Utc::now().to_rfc3339();

    // Build column list + values
    let mut col_names: Vec<String> = vec![
        "id".into(),
        "created_at".into(),
        "updated_at".into(),
        "created_by".into(),
    ];
    let mut placeholders: Vec<String> = vec!["?1".into(), "?2".into(), "?3".into(), "?4".into()];
    let mut values: Vec<String> = vec![id.clone(), now.clone(), now.clone(), actor.to_string()];

    let mut idx = 5;
    for col_def in &table.columns {
        if let Some(val) = obj.get(&col_def.name) {
            let str_val = match val {
                Value::String(s) => s.clone(),
                Value::Number(n) => n.to_string(),
                Value::Bool(b) => {
                    if *b {
                        "1".to_string()
                    } else {
                        "0".to_string()
                    }
                }
                Value::Null => String::new(),
                other => other.to_string(),
            };

            // Validate required
            if col_def.required && str_val.is_empty() {
                return Err(format!("field '{}' is required", col_def.name));
            }

            // Validate enum
            if col_def.col_type == "enum" && !col_def.values.is_empty() && !str_val.is_empty() {
                if !col_def.values.contains(&str_val) {
                    return Err(format!(
                        "field '{}' must be one of: {:?}",
                        col_def.name, col_def.values
                    ));
                }
            }

            col_names.push(format!("\"{}\"", col_def.name));
            placeholders.push(format!("?{idx}"));
            values.push(str_val);
            idx += 1;
        } else if col_def.required {
            return Err(format!("field '{}' is required", col_def.name));
        }
    }

    // Evidence hash
    let mut hasher = Sha256::new();
    hasher.update(format!("{}:{}:{}", table.name, id, now).as_bytes());
    let evidence_hash = format!("{:x}", hasher.finalize())[..16].to_string();
    col_names.push("evidence_hash".into());
    placeholders.push(format!("?{idx}"));
    values.push(evidence_hash.clone());

    let sql = format!(
        "INSERT INTO \"{}\" ({}) VALUES ({})",
        table.name,
        col_names.join(", "),
        placeholders.join(", ")
    );

    conn.execute(
        &sql,
        params_from_iter(values.iter().map(|v| v as &dyn rusqlite::types::ToSql)),
    )
    .map_err(|e| format!("insert: {e}"))?;

    // Audit record
    let record = json!({
        "id": id,
        "created_at": now,
        "updated_at": now,
        "created_by": actor,
        "evidence_hash": evidence_hash,
    });
    let _ = conn.execute(
        "INSERT INTO _audit (table_name, record_id, action, after, actor, timestamp, evidence_hash) VALUES (?1, ?2, 'create', ?3, ?4, ?5, ?6)",
        rusqlite::params![table.name, id, record.to_string(), actor, now, evidence_hash],
    );

    // Return the full record
    select_one(conn, table, &id)
}

/// Select a single record by ID.
pub fn select_one(conn: &Connection, table: &TableDef, id: &str) -> Result<Value, String> {
    let sql = format!("SELECT * FROM \"{}\" WHERE id = ?1", table.name);
    let mut stmt = conn.prepare(&sql).map_err(|e| format!("prepare: {e}"))?;

    let col_names: Vec<String> = stmt.column_names().iter().map(|s| s.to_string()).collect();

    let row = stmt
        .query_row(rusqlite::params![id], |row| {
            let mut obj = serde_json::Map::new();
            for (i, name) in col_names.iter().enumerate() {
                let val: String = row.get(i).unwrap_or_default();
                obj.insert(name.clone(), Value::String(val));
            }
            Ok(Value::Object(obj))
        })
        .map_err(|e| format!("select: {e}"))?;

    Ok(row)
}

/// List records with optional pagination and filtering.
pub fn select_list(
    conn: &Connection,
    table: &TableDef,
    page: u32,
    page_size: u32,
    sort_by: Option<&str>,
    filters: &[(String, String)],
) -> Result<Value, String> {
    let offset = page * page_size;

    // Build WHERE clause from filters
    let mut where_clauses = Vec::new();
    let mut params: Vec<String> = Vec::new();
    for (col, val) in filters {
        // Validate column exists
        let valid = table.columns.iter().any(|c| &c.name == col)
            || ["id", "created_at", "updated_at", "created_by"].contains(&col.as_str());
        if valid {
            where_clauses.push(format!("\"{}\" = ?{}", col, params.len() + 1));
            params.push(val.clone());
        }
    }

    let where_sql = if where_clauses.is_empty() {
        String::new()
    } else {
        format!("WHERE {}", where_clauses.join(" AND "))
    };

    // Sort
    let order_col = sort_by.unwrap_or("created_at");
    let valid_sort = table.columns.iter().any(|c| c.name == order_col)
        || ["id", "created_at", "updated_at"].contains(&order_col);
    let order_sql = if valid_sort {
        format!("ORDER BY \"{}\" DESC", order_col)
    } else {
        "ORDER BY created_at DESC".to_string()
    };

    // Count
    let count_sql = format!("SELECT COUNT(*) FROM \"{}\" {}", table.name, where_sql);
    let total: i64 = if params.is_empty() {
        conn.query_row(&count_sql, [], |r| r.get(0)).unwrap_or(0)
    } else {
        conn.query_row(
            &count_sql,
            params_from_iter(params.iter().map(|v| v as &dyn rusqlite::types::ToSql)),
            |r| r.get(0),
        )
        .unwrap_or(0)
    };

    // Query
    let sql = format!(
        "SELECT * FROM \"{}\" {} {} LIMIT {} OFFSET {}",
        table.name, where_sql, order_sql, page_size, offset
    );

    let mut stmt = conn
        .prepare(&sql)
        .map_err(|e| format!("prepare list: {e}"))?;
    let col_names: Vec<String> = stmt.column_names().iter().map(|s| s.to_string()).collect();

    // Collect results into Vec (avoids type mismatch between query_map branches)
    let mut items: Vec<Value> = Vec::new();
    {
        let col_names_ref = &col_names;
        let mut rows = if params.is_empty() {
            stmt.query([]).map_err(|e| format!("query: {e}"))?
        } else {
            stmt.query(params_from_iter(
                params.iter().map(|v| v as &dyn rusqlite::types::ToSql),
            ))
            .map_err(|e| format!("query: {e}"))?
        };
        while let Some(row) = rows.next().map_err(|e| format!("row: {e}"))? {
            let mut obj = serde_json::Map::new();
            for (i, name) in col_names_ref.iter().enumerate() {
                let val: String = row.get(i).unwrap_or_default();
                obj.insert(name.clone(), Value::String(val));
            }
            items.push(Value::Object(obj));
        }
    }

    Ok(json!({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total as f64 / page_size as f64).ceil() as i64,
    }))
}

/// Update a record by ID.
pub fn update(
    conn: &Connection,
    table: &TableDef,
    id: &str,
    data: &Value,
    actor: &str,
) -> Result<Value, String> {
    let obj = data.as_object().ok_or("body must be a JSON object")?;
    let now = Utc::now().to_rfc3339();

    // Get before state for audit
    let before = select_one(conn, table, id).ok();

    let mut set_clauses = vec!["\"updated_at\" = ?1".to_string()];
    let mut values: Vec<String> = vec![now.clone()];
    let mut idx = 2;

    for col_def in &table.columns {
        if let Some(val) = obj.get(&col_def.name) {
            let str_val = match val {
                Value::String(s) => s.clone(),
                Value::Number(n) => n.to_string(),
                Value::Bool(b) => {
                    if *b {
                        "1".to_string()
                    } else {
                        "0".to_string()
                    }
                }
                Value::Null => String::new(),
                other => other.to_string(),
            };

            // Validate enum
            if col_def.col_type == "enum" && !col_def.values.is_empty() && !str_val.is_empty() {
                if !col_def.values.contains(&str_val) {
                    return Err(format!(
                        "field '{}' must be one of: {:?}",
                        col_def.name, col_def.values
                    ));
                }
            }

            set_clauses.push(format!("\"{}\" = ?{}", col_def.name, idx));
            values.push(str_val);
            idx += 1;
        }
    }

    // Evidence hash
    let mut hasher = Sha256::new();
    hasher.update(format!("{}:{}:{}", table.name, id, now).as_bytes());
    let evidence_hash = format!("{:x}", hasher.finalize())[..16].to_string();
    set_clauses.push(format!("\"evidence_hash\" = ?{}", idx));
    values.push(evidence_hash.clone());
    idx += 1;

    values.push(id.to_string()); // WHERE id = ?N

    let sql = format!(
        "UPDATE \"{}\" SET {} WHERE id = ?{}",
        table.name,
        set_clauses.join(", "),
        idx
    );

    let affected = conn
        .execute(
            &sql,
            params_from_iter(values.iter().map(|v| v as &dyn rusqlite::types::ToSql)),
        )
        .map_err(|e| format!("update: {e}"))?;

    if affected == 0 {
        return Err(format!("record '{}' not found in '{}'", id, table.name));
    }

    // Audit
    let after = select_one(conn, table, id).ok();
    let _ = conn.execute(
        "INSERT INTO _audit (table_name, record_id, action, before, after, actor, timestamp, evidence_hash) VALUES (?1, ?2, 'update', ?3, ?4, ?5, ?6, ?7)",
        rusqlite::params![
            table.name, id,
            before.map(|v| v.to_string()).unwrap_or_default(),
            after.map(|v| v.to_string()).unwrap_or_default(),
            actor, now, evidence_hash
        ],
    );

    select_one(conn, table, id)
}

/// Delete a record by ID.
pub fn delete(conn: &Connection, table: &TableDef, id: &str, actor: &str) -> Result<Value, String> {
    let now = Utc::now().to_rfc3339();

    // Get before state for audit
    let before = select_one(conn, table, id)?;

    let sql = format!("DELETE FROM \"{}\" WHERE id = ?1", table.name);
    let affected = conn
        .execute(&sql, rusqlite::params![id])
        .map_err(|e| format!("delete: {e}"))?;

    if affected == 0 {
        return Err(format!("record '{}' not found in '{}'", id, table.name));
    }

    // Audit
    let mut hasher = Sha256::new();
    hasher.update(format!("delete:{}:{}:{}", table.name, id, now).as_bytes());
    let evidence_hash = format!("{:x}", hasher.finalize())[..16].to_string();

    let _ = conn.execute(
        "INSERT INTO _audit (table_name, record_id, action, before, actor, timestamp, evidence_hash) VALUES (?1, ?2, 'delete', ?3, ?4, ?5, ?6)",
        rusqlite::params![table.name, id, before.to_string(), actor, now, evidence_hash],
    );

    Ok(json!({ "deleted": true, "id": id, "table": table.name }))
}

/// Full-text search using FTS5.
pub fn search(
    conn: &Connection,
    table: &TableDef,
    query: &str,
    limit: u32,
) -> Result<Value, String> {
    if table.search.is_empty() {
        return Err(format!("table '{}' has no search columns", table.name));
    }

    let fts_table = format!("{}_fts", table.name);
    let sql = format!(
        "SELECT t.* FROM \"{}\" t JOIN \"{}\" f ON t.rowid = f.rowid WHERE \"{}\" MATCH ?1 LIMIT ?2",
        table.name, fts_table, fts_table
    );

    let mut stmt = conn
        .prepare(&sql)
        .map_err(|e| format!("fts prepare: {e}"))?;
    let col_names: Vec<String> = stmt.column_names().iter().map(|s| s.to_string()).collect();

    let rows = stmt
        .query_map(rusqlite::params![query, limit], |row| {
            let mut obj = serde_json::Map::new();
            for (i, name) in col_names.iter().enumerate() {
                let val: String = row.get(i).unwrap_or_default();
                obj.insert(name.clone(), Value::String(val));
            }
            Ok(Value::Object(obj))
        })
        .map_err(|e| format!("fts query: {e}"))?;

    let items: Vec<Value> = rows.filter_map(|r| r.ok()).collect();
    Ok(json!({ "items": items, "query": query, "count": items.len() }))
}
