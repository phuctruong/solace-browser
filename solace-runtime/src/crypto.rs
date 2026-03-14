use std::collections::BTreeMap;
use std::fs;
use std::path::PathBuf;

use aes_gcm::aead::Aead;
use aes_gcm::{Aes256Gcm, KeyInit, Nonce};
use rand::RngCore;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};

pub const VAULT_FILENAME: &str = "oauth3-vault.enc";
const DEFAULT_VAULT_SALT: &[u8] = b"solace-oauth3-vault:v1";

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct OAuthToken {
    #[serde(default)]
    pub token_id: String,
    #[serde(default)]
    pub agent_name: Option<String>,
    #[serde(default)]
    pub service: Option<String>,
    #[serde(default)]
    pub scope: Option<String>,
    #[serde(default)]
    pub scopes: Vec<String>,
    #[serde(default)]
    pub expires_at: Option<i64>,
    #[serde(default)]
    pub created_at: Option<i64>,
    #[serde(default)]
    pub revoked: bool,
    #[serde(flatten)]
    pub extra: BTreeMap<String, Value>,
}

pub fn derive_key(secret: &str, salt: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(secret.as_bytes());
    hasher.update(salt);
    hasher.finalize().into()
}

pub fn encrypt(plaintext: &[u8], key: &[u8; 32]) -> Result<Vec<u8>, String> {
    let cipher = Aes256Gcm::new_from_slice(key).map_err(|error| format!("cipher init failed: {error}"))?;
    let mut nonce_bytes = [0u8; 12];
    rand::thread_rng().fill_bytes(&mut nonce_bytes);
    let nonce = Nonce::from_slice(&nonce_bytes);
    let ciphertext = cipher
        .encrypt(nonce, plaintext)
        .map_err(|error| format!("encrypt failed: {error}"))?;
    let mut result = nonce_bytes.to_vec();
    result.extend(ciphertext);
    Ok(result)
}

pub fn decrypt(data: &[u8], key: &[u8; 32]) -> Result<Vec<u8>, String> {
    if data.len() < 12 {
        return Err("data too short".to_string());
    }
    let (nonce_bytes, ciphertext) = data.split_at(12);
    let cipher = Aes256Gcm::new_from_slice(key).map_err(|error| format!("cipher init failed: {error}"))?;
    let nonce = Nonce::from_slice(nonce_bytes);
    cipher
        .decrypt(nonce, ciphertext)
        .map_err(|error| format!("decrypt failed: {error}"))
}

pub fn save_vault(tokens: &[OAuthToken], secret: &str) -> Result<PathBuf, String> {
    let raw = serde_json::to_vec(tokens).map_err(|error| format!("vault encode failed: {error}"))?;
    let encrypted = encrypt(&raw, &key_from_secret(secret))?;
    let path = vault_path();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    fs::write(&path, encrypted).map_err(|error| error.to_string())?;
    Ok(path)
}

pub fn load_vault(secret: &str) -> Result<Vec<OAuthToken>, String> {
    let path = vault_path();
    if !path.exists() {
        return Ok(Vec::new());
    }
    let encrypted = fs::read(&path).map_err(|error| error.to_string())?;
    let decrypted = decrypt(&encrypted, &key_from_secret(secret))?;
    serde_json::from_slice(&decrypted).map_err(|error| format!("vault decode failed: {error}"))
}

pub fn vault_path() -> PathBuf {
    crate::utils::solace_home().join(VAULT_FILENAME)
}

fn key_from_secret(secret: &str) -> [u8; 32] {
    decode_hex_key(secret).unwrap_or_else(|| derive_key(secret, DEFAULT_VAULT_SALT))
}

fn decode_hex_key(secret: &str) -> Option<[u8; 32]> {
    if secret.len() != 64 {
        return None;
    }
    let mut key = [0u8; 32];
    for (index, chunk) in secret.as_bytes().chunks_exact(2).enumerate() {
        let high = hex_nibble(chunk[0])?;
        let low = hex_nibble(chunk[1])?;
        key[index] = (high << 4) | low;
    }
    Some(key)
}

fn hex_nibble(value: u8) -> Option<u8> {
    match value {
        b'0'..=b'9' => Some(value - b'0'),
        b'a'..=b'f' => Some(10 + value - b'a'),
        b'A'..=b'F' => Some(10 + value - b'A'),
        _ => None,
    }
}
