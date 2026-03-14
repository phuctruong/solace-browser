#[path = "jsonl_codec.rs"]
mod jsonl_codec;
#[cfg(test)]
#[path = "jsonl_tests.rs"]
mod jsonl_tests;
use crate::pzip::util::{dec_str, dec_uvarint, enc_str, enc_uvarint, xz_compress, xz_decompress};
use crate::pzip::{PZipError, Result};
use jsonl_codec::{bit, decode_column, kind, render, val};
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};

const MAGIC: &[u8; 4] = b"PZJ0";
const V2: u8 = 0x02;
const V3: u8 = 0x03;

pub fn compress(data: &[u8]) -> Result<Vec<u8>> {
    let text = std::str::from_utf8(data)?;
    let mut rows: Vec<(BTreeMap<String, Option<String>>, Vec<String>)> = Vec::new();
    let mut key_order = Vec::<String>::new();
    let mut types = BTreeMap::<String, u8>::new();
    for raw in text
        .split('\n')
        .map(|line| line.trim_end_matches('\r'))
        .filter(|line| !line.is_empty())
    {
        let value: Value =
            serde_json::from_str(raw).map_err(|_| PZipError::Invalid("invalid jsonl".into()))?;
        let obj = value
            .as_object()
            .ok_or_else(|| PZipError::Invalid("jsonl rows must be objects".into()))?;
        if serde_json::to_string(&value)? != raw {
            return Ok(data.to_vec());
        }
        let mut row = BTreeMap::new();
        let mut order = Vec::new();
        for (key, value) in obj {
            if !key_order.iter().any(|k| k == key) {
                key_order.push(key.clone());
                types.insert(key.clone(), kind(value));
            }
            row.insert(key.clone(), val(value)?);
            order.push(key.clone());
        }
        rows.push((row, order));
    }
    if rows.is_empty() {
        return Ok([MAGIC.as_slice(), &[V2, 0x00]].concat());
    }
    let sorted = BTreeSet::from_iter(key_order.iter().cloned())
        .into_iter()
        .collect::<Vec<_>>();
    let index = sorted
        .iter()
        .enumerate()
        .map(|(i, key)| (key.as_str(), i))
        .collect::<BTreeMap<_, _>>();
    let needs_v3 = rows.iter().any(|(_, order)| {
        order.iter().cloned().collect::<Vec<_>>()
            != key_order
                .iter()
                .filter(|key| order.contains(key))
                .cloned()
                .collect::<Vec<_>>()
    });
    let mut body = Vec::new();
    enc_uvarint(rows.len(), &mut body);
    enc_uvarint(sorted.len(), &mut body);
    for key in &sorted {
        enc_str(key, &mut body);
    }
    enc_uvarint(key_order.len(), &mut body);
    for key in &key_order {
        enc_uvarint(*index.get(key.as_str()).unwrap(), &mut body);
    }
    if needs_v3 {
        for (_, order) in &rows {
            enc_uvarint(order.len(), &mut body);
            for key in order {
                enc_uvarint(*index.get(key.as_str()).unwrap(), &mut body);
            }
        }
    }
    for key in &sorted {
        body.push(*types.get(key).unwrap_or(&0));
    }
    let bitmap_len = rows.len().div_ceil(8);
    for key in &sorted {
        let mut present = vec![0u8; bitmap_len];
        let mut nulls = vec![0u8; bitmap_len];
        let mut values = Vec::new();
        for (i, (row, _)) in rows.iter().enumerate() {
            match row.get(key) {
                Some(None) => {
                    present[i / 8] |= 1 << (i % 8);
                    nulls[i / 8] |= 1 << (i % 8);
                    values.push(String::new());
                }
                Some(Some(value)) => {
                    present[i / 8] |= 1 << (i % 8);
                    values.push(value.clone());
                }
                None => values.push(String::new()),
            }
        }
        enc_uvarint(bitmap_len, &mut body);
        body.extend_from_slice(&present);
        enc_uvarint(bitmap_len, &mut body);
        body.extend_from_slice(&nulls);
        enc_str("RAW", &mut body);
        let mut payload = Vec::new();
        enc_uvarint(values.len(), &mut payload);
        for value in values {
            enc_str(&value, &mut payload);
        }
        enc_uvarint(payload.len(), &mut body);
        body.extend_from_slice(&payload);
    }
    let mut out = Vec::new();
    out.extend_from_slice(MAGIC);
    out.push(if needs_v3 { V3 } else { V2 });
    out.push(0x01);
    out.extend_from_slice(&xz_compress(&body)?);
    Ok(out)
}

pub fn decompress(data: &[u8]) -> Result<Vec<u8>> {
    if data.len() < 6 || &data[..4] != MAGIC {
        return Err(PZipError::Invalid("invalid pzj0".into()));
    }
    let version = data[4];
    if data[5] == 0 {
        return Ok(Vec::new());
    }
    let body = xz_decompress(&data[6..])?;
    let mut offset = 0usize;
    let row_count = dec_uvarint(&body, &mut offset)?;
    let keys = (0..dec_uvarint(&body, &mut offset)?)
        .map(|_| dec_str(&body, &mut offset))
        .collect::<Result<Vec<_>>>()?;
    let global = (0..dec_uvarint(&body, &mut offset)?)
        .map(|_| dec_uvarint(&body, &mut offset))
        .collect::<Result<Vec<_>>>()?;
    let orders = if version == V3 {
        (0..row_count)
            .map(|_| {
                (0..dec_uvarint(&body, &mut offset)?)
                    .map(|_| dec_uvarint(&body, &mut offset))
                    .collect::<Result<Vec<_>>>()
            })
            .collect::<Result<Vec<_>>>()?
    } else {
        Vec::new()
    };
    let mut types = BTreeMap::new();
    for key in &keys {
        let kind = *body
            .get(offset)
            .ok_or_else(|| PZipError::Invalid("truncated types".into()))?;
        types.insert(key.clone(), kind);
        offset += 1;
    }
    let mut columns = BTreeMap::new();
    let mut present = BTreeMap::new();
    let mut nulls = BTreeMap::new();
    for key in &keys {
        let p_len = dec_uvarint(&body, &mut offset)?;
        let p = body[offset..offset + p_len].to_vec();
        offset += p_len;
        let n_len = dec_uvarint(&body, &mut offset)?;
        let n = body[offset..offset + n_len].to_vec();
        offset += n_len;
        let codec = dec_str(&body, &mut offset)?;
        let payload_len = dec_uvarint(&body, &mut offset)?;
        let payload_end = offset + payload_len;
        let vals = decode_column(&codec, &body[offset..payload_end])?;
        offset = payload_end;
        columns.insert(key.clone(), vals);
        present.insert(key.clone(), p);
        nulls.insert(key.clone(), n);
    }
    let mut lines = Vec::new();
    for row in 0..row_count {
        let order = if version == V3 { &orders[row] } else { &global };
        let mut pairs = Vec::new();
        for idx in order {
            let key = &keys[*idx];
            if bit(&present[key], row) {
                let value = if bit(&nulls[key], row) {
                    "null".into()
                } else {
                    render(types[key], &columns[key][row])?
                };
                pairs.push(format!("{}:{}", serde_json::to_string(key)?, value));
            }
        }
        lines.push(format!("{{{}}}", pairs.join(",")));
    }
    Ok(format!("{}\n", lines.join("\n")).into_bytes())
}
