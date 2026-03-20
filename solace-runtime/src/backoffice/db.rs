// Diagram: apps-backoffice-framework
//! Database manager: one SQLite connection per app, WAL mode, lazy initialization.

use parking_lot::Mutex;
use rusqlite::Connection;
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;

use super::schema::{self, WorkspaceConfig};

/// Manages SQLite connections for backoffice apps (one DB per app).
pub struct DbManager {
    connections: Mutex<HashMap<String, Arc<Mutex<Connection>>>>,
    base_dir: PathBuf,
}

impl DbManager {
    pub fn new(base_dir: PathBuf) -> Self {
        Self {
            connections: Mutex::new(HashMap::new()),
            base_dir,
        }
    }

    /// Get or create a connection for a backoffice app.
    /// Lazily initializes the database on first access.
    pub fn get_connection(
        &self,
        app_id: &str,
        config: &WorkspaceConfig,
    ) -> Result<Arc<Mutex<Connection>>, String> {
        let mut conns = self.connections.lock();

        if let Some(conn) = conns.get(app_id) {
            return Ok(Arc::clone(conn));
        }

        // Create database directory
        let db_dir = self.base_dir.join(app_id);
        std::fs::create_dir_all(&db_dir).map_err(|e| format!("mkdir: {e}"))?;
        let db_path = db_dir.join("workspace.db");

        // Open connection with WAL mode
        let conn =
            Connection::open(&db_path).map_err(|e| format!("sqlite open {}: {e}", db_path.display()))?;

        conn.execute_batch(
            "PRAGMA journal_mode=WAL;
             PRAGMA synchronous=NORMAL;
             PRAGMA foreign_keys=ON;
             PRAGMA busy_timeout=5000;",
        )
        .map_err(|e| format!("pragma: {e}"))?;

        // Initialize schema
        self.init_schema(&conn, app_id, config)?;

        let conn = Arc::new(Mutex::new(conn));
        conns.insert(app_id.to_string(), Arc::clone(&conn));
        Ok(conn)
    }

    /// Create tables from workspace config if they don't exist.
    fn init_schema(
        &self,
        conn: &Connection,
        app_id: &str,
        config: &WorkspaceConfig,
    ) -> Result<(), String> {
        // Meta + audit tables
        conn.execute_batch(schema::generate_meta_ddl())
            .map_err(|e| format!("meta ddl: {e}"))?;
        conn.execute_batch(schema::generate_audit_ddl())
            .map_err(|e| format!("audit ddl: {e}"))?;

        // App tables
        for table in &config.tables {
            let ddl = schema::generate_ddl(table);
            conn.execute_batch(&ddl)
                .map_err(|e| format!("table '{}': {e}", table.name))?;

            // FTS5 for searchable tables
            if let Some(fts_ddl) = schema::generate_fts_ddl(table) {
                // FTS5 may fail if already exists with different columns — that's OK
                let _ = conn.execute_batch(&fts_ddl);
            }
        }

        // Store config hash for migration detection
        let hash = config.config_hash();
        conn.execute(
            "INSERT OR REPLACE INTO _meta (key, value) VALUES ('schema_hash', ?1)",
            rusqlite::params![hash],
        )
        .map_err(|e| format!("meta insert: {e}"))?;

        conn.execute(
            "INSERT OR REPLACE INTO _meta (key, value) VALUES ('app_id', ?1)",
            rusqlite::params![app_id],
        )
        .map_err(|e| format!("meta insert: {e}"))?;

        Ok(())
    }

    /// List all initialized backoffice app IDs.
    pub fn app_ids(&self) -> Vec<String> {
        self.connections.lock().keys().cloned().collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::backoffice::schema::{ColumnDef, TableDef};

    #[test]
    fn test_create_and_connect() {
        let tmp = tempfile::tempdir().unwrap();
        let mgr = DbManager::new(tmp.path().to_path_buf());

        let config = WorkspaceConfig {
            tables: vec![TableDef {
                name: "contacts".into(),
                columns: vec![ColumnDef {
                    name: "name".into(),
                    col_type: "text".into(),
                    required: true,
                    unique: false,
                    values: vec![],
                }],
                display: None,
                search: vec![],
            }],
            views: vec![],
        };

        let conn = mgr.get_connection("test-crm", &config).unwrap();
        let c = conn.lock();

        // Verify table exists
        let count: i64 = c
            .query_row(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='contacts'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(count, 1);

        // Verify meta
        let hash: String = c
            .query_row("SELECT value FROM _meta WHERE key='schema_hash'", [], |row| {
                row.get(0)
            })
            .unwrap();
        assert!(!hash.is_empty());
    }
}
