use crate::pzip::util::{
    brotli_compress, brotli_decompress, dec_str, dec_uvarint, enc_str, enc_uvarint,
};
use crate::pzip::{PZipError, Result};
use serde_json::{Map, Value};
use std::collections::BTreeSet;

const MAGIC: &[u8; 4] = b"PZJS";
const VERSION: u8 = 0x01;
const SHAPE_ARRAY: u8 = 0x01;
const SHAPE_OBJECT: u8 = 0x02;
const SHAPE_OTHER: u8 = 0x03;

pub fn compress(data: &[u8]) -> Result<Vec<u8>> {
    let parsed: Value = serde_json::from_slice(data)?;
    let rows = match parsed {
        Value::Array(rows) if rows.iter().all(Value::is_object) && !rows.is_empty() => rows,
        _ => return Ok(data.to_vec()),
    };
    let mut keys = BTreeSet::new();
    for row in &rows {
        collect_keys(row, &mut keys);
    }
    if keys.is_empty() {
        return Ok(data.to_vec());
    }
    let dict: Vec<String> = keys.into_iter().collect();
    let index: std::collections::BTreeMap<&str, usize> = dict
        .iter()
        .enumerate()
        .map(|(i, key)| (key.as_str(), i))
        .collect();
    let mut columns = Vec::new();
    if let Some(Value::Object(first)) = rows.first() {
        for key in first.keys() {
            columns.push(key.clone());
        }
    }
    for row in &rows {
        if let Value::Object(obj) = row {
            for key in obj.keys() {
                if !columns.iter().any(|k| k == key) {
                    columns.push(key.clone());
                }
            }
        }
    }
    let mut blob = Vec::new();
    enc_uvarint(dict.len(), &mut blob);
    for key in &dict {
        enc_str(key, &mut blob);
    }
    enc_uvarint(rows.len(), &mut blob);
    enc_uvarint(columns.len(), &mut blob);
    for key in &columns {
        enc_uvarint(
            *index
                .get(key.as_str())
                .ok_or_else(|| PZipError::Invalid("missing key".into()))?,
            &mut blob,
        );
    }
    for key in &columns {
        enc_uvarint(rows.len(), &mut blob);
        for row in &rows {
            let text = row.get(key).map(canon).transpose()?.unwrap_or_default();
            enc_str(&text, &mut blob);
        }
    }
    let payload = brotli_compress(&blob)?;
    let mut out = Vec::with_capacity(10 + payload.len());
    out.extend_from_slice(MAGIC);
    out.push(VERSION);
    out.push(SHAPE_ARRAY);
    out.extend_from_slice(&(canon_bytes(&Value::Array(rows))?.len() as u32).to_le_bytes());
    out.extend_from_slice(&payload);
    Ok(out)
}

pub fn decompress(data: &[u8]) -> Result<Vec<u8>> {
    if data.len() < 10 || &data[..4] != MAGIC || data[4] != VERSION {
        return Err(PZipError::Invalid("invalid pzjs".into()));
    }
    match data[5] {
        SHAPE_ARRAY => dec_array(&brotli_decompress(&data[10..])?),
        SHAPE_OBJECT => Ok(b"{}".to_vec()),
        SHAPE_OTHER => Err(PZipError::Invalid(
            "cannot reconstruct non-array JSON".into(),
        )),
        _ => Err(PZipError::Invalid("unknown json shape".into())),
    }
}

fn dec_array(blob: &[u8]) -> Result<Vec<u8>> {
    let mut offset = 0usize;
    let keys = (0..dec_uvarint(blob, &mut offset)?)
        .map(|_| dec_str(blob, &mut offset))
        .collect::<Result<Vec<_>>>()?;
    let rows = dec_uvarint(blob, &mut offset)?;
    let cols = (0..dec_uvarint(blob, &mut offset)?)
        .map(|_| dec_uvarint(blob, &mut offset))
        .collect::<Result<Vec<_>>>()?;
    let mut values = Vec::new();
    for _ in 0..cols.len() {
        let count = dec_uvarint(blob, &mut offset)?;
        values.push(
            (0..count)
                .map(|_| dec_str(blob, &mut offset))
                .collect::<Result<Vec<_>>>()?,
        );
    }
    let mut out = Vec::new();
    for row_idx in 0..rows {
        let mut row = Map::new();
        for (col_idx, key_idx) in cols.iter().enumerate() {
            let value = values
                .get(col_idx)
                .and_then(|column| column.get(row_idx))
                .filter(|v| !v.is_empty());
            if let Some(text) = value {
                row.insert(
                    keys[*key_idx].clone(),
                    serde_json::from_str(text).unwrap_or_else(|_| Value::String(text.clone())),
                );
            }
        }
        out.push(Value::Object(row));
    }
    canon_bytes(&Value::Array(out))
}

fn collect_keys(value: &Value, keys: &mut BTreeSet<String>) {
    match value {
        Value::Object(map) => {
            for (key, value) in map {
                keys.insert(key.clone());
                collect_keys(value, keys);
            }
        }
        Value::Array(items) => {
            for item in items {
                collect_keys(item, keys);
            }
        }
        _ => {}
    }
}

fn canon(value: &Value) -> Result<String> {
    Ok(String::from_utf8(canon_bytes(value)?).map_err(|e| PZipError::Invalid(e.to_string()))?)
}

fn canon_bytes(value: &Value) -> Result<Vec<u8>> {
    Ok(serde_json::to_vec(value)?)
}

#[cfg(test)]
mod tests {
    use super::{compress, decompress};

    #[test]
    fn roundtrips_array_objects() {
        let raw = br#"[{"id":1,"name":"a"},{"id":2,"name":"b","ok":true}]"#;
        let packed = compress(raw).unwrap();
        assert_eq!(&packed[..4], b"PZJS");
        assert_eq!(
            decompress(&packed).unwrap(),
            br#"[{"id":1,"name":"a"},{"id":2,"name":"b","ok":true}]"#
        );
    }

    #[test]
    fn passthroughs_non_array_json() {
        let raw = br#"{"a":1}"#;
        assert_eq!(compress(raw).unwrap(), raw);
    }
}
