// Diagram: apps-backoffice-framework
//! Schema engine: parse YAML config → generate SQLite DDL → create/migrate tables.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// A complete backoffice workspace definition from manifest.yaml
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct WorkspaceConfig {
    #[serde(default)]
    pub tables: Vec<TableDef>,
    #[serde(default)]
    pub views: Vec<ViewDef>,
}

/// A table definition with columns, display hints, and search config
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TableDef {
    pub name: String,
    #[serde(default)]
    pub columns: Vec<ColumnDef>,
    #[serde(default)]
    pub display: Option<DisplayHints>,
    #[serde(default)]
    pub search: Vec<String>,
}

/// A column definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ColumnDef {
    pub name: String,
    /// Type: text, integer, real, boolean, datetime, enum, ref:<table>, tags, json
    #[serde(rename = "type")]
    pub col_type: String,
    #[serde(default)]
    pub required: bool,
    #[serde(default)]
    pub unique: bool,
    /// For enum type: allowed values
    #[serde(default)]
    pub values: Vec<String>,
}

/// Display hints for UI rendering
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DisplayHints {
    pub title: Option<String>,
    pub subtitle: Option<String>,
    pub badge: Option<String>,
}

/// A view definition (table, kanban, timeline, chart)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ViewDef {
    pub name: String,
    pub table: String,
    #[serde(rename = "type", default = "default_view_type")]
    pub view_type: String,
    pub group_by: Option<String>,
    pub order_by: Option<String>,
}

fn default_view_type() -> String {
    "table".to_string()
}

impl WorkspaceConfig {
    /// Compute SHA-256 hash of the config for migration detection
    pub fn config_hash(&self) -> String {
        let json = serde_json::to_string(self).unwrap_or_default();
        let mut hasher = Sha256::new();
        hasher.update(json.as_bytes());
        format!("{:x}", hasher.finalize())
    }
}

impl ColumnDef {
    /// Generate SQLite column DDL
    pub fn to_ddl(&self) -> String {
        let sql_type = match self.col_type.as_str() {
            "text" | "tags" | "json" | "datetime" => "TEXT",
            "integer" | "boolean" => "INTEGER",
            "real" => "REAL",
            t if t.starts_with("ref:") => "TEXT", // FK as text UUID
            t if t.starts_with("enum") => "TEXT",
            _ => "TEXT",
        };

        let mut parts = vec![format!("\"{}\" {}", self.name, sql_type)];

        if self.required {
            parts.push("NOT NULL".to_string());
        }

        if self.unique {
            parts.push("UNIQUE".to_string());
        }

        // Default values
        match self.col_type.as_str() {
            "text" | "tags" | "json" | "datetime" => {
                if !self.required {
                    parts.push("DEFAULT ''".to_string());
                }
            }
            "integer" | "boolean" => {
                parts.push("DEFAULT 0".to_string());
            }
            "real" => {
                parts.push("DEFAULT 0.0".to_string());
            }
            _ => {}
        }

        // Enum check constraint
        if self.col_type == "enum" && !self.values.is_empty() {
            let vals: Vec<String> = self.values.iter().map(|v| format!("'{}'", v)).collect();
            parts.push(format!("CHECK(\"{}\" IN ({}))", self.name, vals.join(", ")));
        }

        parts.join(" ")
    }
}

/// Generate CREATE TABLE DDL for a table definition.
/// Every table auto-gets: id, created_at, updated_at, created_by, evidence_hash.
pub fn generate_ddl(table: &TableDef) -> String {
    let mut columns = vec!["\"id\" TEXT PRIMARY KEY".to_string()];

    for col in &table.columns {
        columns.push(col.to_ddl());
    }

    // Auto-columns
    columns.push("\"created_at\" TEXT NOT NULL DEFAULT ''".to_string());
    columns.push("\"updated_at\" TEXT NOT NULL DEFAULT ''".to_string());
    columns.push("\"created_by\" TEXT NOT NULL DEFAULT ''".to_string());
    columns.push("\"evidence_hash\" TEXT NOT NULL DEFAULT ''".to_string());

    format!(
        "CREATE TABLE IF NOT EXISTS \"{}\" (\n  {}\n);",
        table.name,
        columns.join(",\n  ")
    )
}

/// Generate the _audit table DDL (tracks all changes)
pub fn generate_audit_ddl() -> &'static str {
    "CREATE TABLE IF NOT EXISTS \"_audit\" (
  \"id\" INTEGER PRIMARY KEY AUTOINCREMENT,
  \"table_name\" TEXT NOT NULL,
  \"record_id\" TEXT NOT NULL,
  \"action\" TEXT NOT NULL,
  \"before\" TEXT,
  \"after\" TEXT,
  \"actor\" TEXT NOT NULL DEFAULT '',
  \"timestamp\" TEXT NOT NULL,
  \"evidence_hash\" TEXT NOT NULL DEFAULT ''
);"
}

/// Generate the _meta table DDL (tracks schema version)
pub fn generate_meta_ddl() -> &'static str {
    "CREATE TABLE IF NOT EXISTS \"_meta\" (
  \"key\" TEXT PRIMARY KEY,
  \"value\" TEXT NOT NULL
);"
}

/// Generate FTS5 virtual table for full-text search
pub fn generate_fts_ddl(table: &TableDef) -> Option<String> {
    if table.search.is_empty() {
        return None;
    }
    let cols = table.search.join(", ");
    Some(format!(
        "CREATE VIRTUAL TABLE IF NOT EXISTS \"{}_fts\" USING fts5({}, content=\"{}\", content_rowid=\"rowid\");",
        table.name, cols, table.name
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_column_ddl_text() {
        let col = ColumnDef {
            name: "name".to_string(),
            col_type: "text".to_string(),
            required: true,
            unique: false,
            values: vec![],
        };
        assert_eq!(col.to_ddl(), "\"name\" TEXT NOT NULL");
    }

    #[test]
    fn test_column_ddl_enum() {
        let col = ColumnDef {
            name: "stage".to_string(),
            col_type: "enum".to_string(),
            required: false,
            unique: false,
            values: vec!["lead".into(), "won".into(), "lost".into()],
        };
        let ddl = col.to_ddl();
        assert!(ddl.contains("CHECK"));
        assert!(ddl.contains("'lead'"));
    }

    #[test]
    fn test_generate_table_ddl() {
        let table = TableDef {
            name: "contacts".to_string(),
            columns: vec![
                ColumnDef {
                    name: "name".into(),
                    col_type: "text".into(),
                    required: true,
                    unique: false,
                    values: vec![],
                },
                ColumnDef {
                    name: "email".into(),
                    col_type: "text".into(),
                    required: false,
                    unique: true,
                    values: vec![],
                },
            ],
            display: None,
            search: vec!["name".into()],
        };
        let ddl = generate_ddl(&table);
        assert!(ddl.contains("CREATE TABLE"));
        assert!(ddl.contains("\"id\" TEXT PRIMARY KEY"));
        assert!(ddl.contains("\"name\" TEXT NOT NULL"));
        assert!(ddl.contains("\"email\" TEXT UNIQUE"));
        assert!(ddl.contains("\"evidence_hash\""));
    }

    #[test]
    fn test_fts_ddl() {
        let table = TableDef {
            name: "contacts".into(),
            columns: vec![],
            display: None,
            search: vec!["name".into(), "email".into()],
        };
        let fts = generate_fts_ddl(&table).unwrap();
        assert!(fts.contains("fts5(name, email"));
    }
}
