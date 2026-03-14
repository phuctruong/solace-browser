mod util;

pub mod evidence;
pub mod json;
pub mod jsonl;
pub mod web;

use thiserror::Error;

pub(crate) type Result<T> = std::result::Result<T, PZipError>;

#[derive(Debug, Error)]
pub enum PZipError {
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
    #[error("json: {0}")]
    Json(#[from] serde_json::Error),
    #[error("utf8: {0}")]
    Utf8(#[from] std::str::Utf8Error),
    #[error("invalid pzip: {0}")]
    Invalid(String),
}

pub fn compress(data: &[u8], content_type: &str) -> Result<Vec<u8>> {
    match content_type {
        "application/json" => json::compress(data),
        "application/jsonl" | "application/x-ndjson" => jsonl::compress(data),
        "text/html" | "text/css" | "application/javascript" => web::compress(data, content_type),
        _ => Ok(data.to_vec()),
    }
}

pub fn decompress(data: &[u8]) -> Result<Vec<u8>> {
    if data.len() < 4 {
        return Ok(data.to_vec());
    }
    match &data[..4] {
        b"PZJS" => json::decompress(data),
        b"PZJ0" => jsonl::decompress(data),
        b"PZWB" => web::decompress(data),
        _ => Ok(data.to_vec()),
    }
}
