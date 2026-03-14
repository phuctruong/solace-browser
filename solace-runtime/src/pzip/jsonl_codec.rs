use crate::pzip::util::{dec_str, dec_svarint, dec_uvarint};
use crate::pzip::{PZipError, Result};
use serde_json::Value;

pub(super) fn bit(bitmap: &[u8], index: usize) -> bool {
    bitmap[index / 8] & (1 << (index % 8)) != 0
}

pub(super) fn kind(value: &Value) -> u8 {
    match value {
        Value::Bool(_) => 2,
        Value::Number(n) if n.is_i64() || n.is_u64() => 1,
        Value::Number(_) => 5,
        Value::Object(_) => 3,
        Value::Array(_) => 4,
        _ => 0,
    }
}

pub(super) fn val(value: &Value) -> Result<Option<String>> {
    Ok(match value {
        Value::Null => None,
        Value::Bool(v) => Some(v.to_string()),
        Value::Number(v) => Some(v.to_string()),
        Value::String(v) => Some(v.clone()),
        Value::Object(_) | Value::Array(_) => Some(serde_json::to_string(value)?),
    })
}

pub(super) fn render(kind: u8, value: &str) -> Result<String> {
    Ok(if matches!(kind, 1 | 2 | 3 | 4 | 5) {
        value.to_string()
    } else {
        serde_json::to_string(value)?
    })
}

pub(super) fn decode_column(codec: &str, data: &[u8]) -> Result<Vec<String>> {
    let mut offset = 0usize;
    Ok(match codec {
        "RAW" => {
            let count = dec_uvarint(data, &mut offset)?;
            (0..count)
                .map(|_| dec_str(data, &mut offset))
                .collect::<Result<Vec<_>>>()?
        }
        "CONSTANT" => {
            let count = dec_uvarint(data, &mut offset)?;
            vec![dec_str(data, &mut offset)?; count]
        }
        "SEQUENCE_INT" => {
            let count = dec_uvarint(data, &mut offset)?;
            let start = dec_svarint(data, &mut offset)?;
            let step = dec_svarint(data, &mut offset)?;
            (0..count)
                .map(|i| (start + (i as isize * step)).to_string())
                .collect()
        }
        "DICTIONARY" => {
            let count = dec_uvarint(data, &mut offset)?;
            let size = dec_uvarint(data, &mut offset)?;
            let dict = (0..size)
                .map(|_| dec_str(data, &mut offset))
                .collect::<Result<Vec<_>>>()?;
            (0..count)
                .map(|_| Ok(dict[dec_uvarint(data, &mut offset)?].clone()))
                .collect::<Result<Vec<_>>>()?
        }
        "BOOLEAN_BITPACK" => {
            let count = dec_uvarint(data, &mut offset)?;
            let false_val = dec_str(data, &mut offset)?;
            let true_val = dec_str(data, &mut offset)?;
            (0..count)
                .map(|i| {
                    if data[offset + (i >> 3)] & (1 << (7 - (i & 7))) != 0 {
                        true_val.clone()
                    } else {
                        false_val.clone()
                    }
                })
                .collect()
        }
        _ => return Err(PZipError::Invalid("unsupported codec".into())),
    })
}
