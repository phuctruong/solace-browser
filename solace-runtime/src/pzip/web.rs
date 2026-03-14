use crate::pzip::util::{
    brotli_compress, brotli_decompress, dec_uvarint, enc_uvarint, xz_decompress,
};
use crate::pzip::{PZipError, Result};

const MAGIC: &[u8; 4] = b"PZWB";
const VERSION_LZMA: u8 = 0x01;
const VERSION_BROTLI: u8 = 0x02;
const HTML: u8 = 0x01;
const CSS: u8 = 0x02;
const JS: u8 = 0x03;

pub fn compress(data: &[u8], content_type: &str) -> Result<Vec<u8>> {
    if data.is_empty() {
        return Err(PZipError::Invalid("ERROR:EMPTY_INPUT".into()));
    }
    let subtype = match content_type {
        "text/html" => HTML,
        "text/css" => CSS,
        _ => JS,
    };
    let mut blob = Vec::new();
    for _ in 0..stream_count(subtype) {
        enc_uvarint(0, &mut blob);
    }
    enc_uvarint(data.len(), &mut blob);
    blob.extend_from_slice(data);
    let mut out = Vec::new();
    out.extend_from_slice(MAGIC);
    out.push(VERSION_BROTLI);
    out.push(subtype);
    out.extend_from_slice(&brotli_compress(&blob)?);
    Ok(out)
}

pub fn decompress(data: &[u8]) -> Result<Vec<u8>> {
    if data.len() < 6 || &data[..4] != MAGIC {
        return Err(PZipError::Invalid("ERROR:INVALID_PZWB".into()));
    }
    let blob = match data[4] {
        VERSION_BROTLI => brotli_decompress(&data[6..])?,
        VERSION_LZMA => xz_decompress(&data[6..])?,
        _ => return Err(PZipError::Invalid("ERROR:INVALID_PZWB".into())),
    };
    let mut offset = 0usize;
    match data[5] {
        HTML => {
            for _ in 0..dec_uvarint(&blob, &mut offset)? {
                offset += dec_uvarint(&blob, &mut offset)?;
            }
            for _ in 0..dec_uvarint(&blob, &mut offset)? {
                offset += dec_uvarint(&blob, &mut offset)?;
            }
            for _ in 0..5 {
                offset += dec_uvarint(&blob, &mut offset)?;
            }
        }
        CSS => {
            for _ in 0..dec_uvarint(&blob, &mut offset)? {
                offset += dec_uvarint(&blob, &mut offset)?;
            }
            for _ in 0..dec_uvarint(&blob, &mut offset)? {
                offset += dec_uvarint(&blob, &mut offset)?;
            }
            for _ in 0..2 {
                offset += dec_uvarint(&blob, &mut offset)?;
            }
        }
        JS => {
            for _ in 0..4 {
                offset += dec_uvarint(&blob, &mut offset)?;
            }
        }
        _ => return Err(PZipError::Invalid("ERROR:UNKNOWN_SUBTYPE".into())),
    }
    let len = dec_uvarint(&blob, &mut offset)?;
    Ok(blob
        .get(offset..offset + len)
        .ok_or_else(|| PZipError::Invalid("truncated original".into()))?
        .to_vec())
}

fn stream_count(subtype: u8) -> usize {
    match subtype {
        HTML => 7,
        CSS => 4,
        JS => 4,
        _ => 0,
    }
}

#[cfg(test)]
mod tests {
    use super::{compress, decompress, CSS, HTML, JS};

    #[test]
    fn roundtrips_html() {
        let raw = b"<!doctype html><html><body><h1>hi</h1></body></html>";
        let packed = compress(raw, "text/html").unwrap();
        assert_eq!(packed[5], HTML);
        assert_eq!(decompress(&packed).unwrap(), raw);
    }

    #[test]
    fn roundtrips_css_and_js() {
        assert_eq!(compress(b"body{color:red}", "text/css").unwrap()[5], CSS);
        assert_eq!(
            compress(b"const x=1;", "application/javascript").unwrap()[5],
            JS
        );
    }
}
