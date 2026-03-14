// Diagram: 16-evidence-chain
use crate::pzip::{PZipError, Result};
use brotli::{CompressorWriter, Decompressor};
use std::io::{Read, Write};
use std::process::{Command, Stdio};

pub(crate) fn enc_uvarint(mut value: usize, out: &mut Vec<u8>) {
    loop {
        let mut byte = (value & 0x7f) as u8;
        value >>= 7;
        if value != 0 {
            byte |= 0x80;
        }
        out.push(byte);
        if value == 0 {
            break;
        }
    }
}

pub(crate) fn dec_uvarint(data: &[u8], offset: &mut usize) -> Result<usize> {
    let mut value = 0usize;
    let mut shift = 0usize;
    let start = *offset;
    loop {
        let byte = *data
            .get(*offset)
            .ok_or_else(|| PZipError::Invalid("truncated varint".into()))?;
        value |= usize::from(byte & 0x7f) << shift;
        *offset += 1;
        shift += 7;
        if byte & 0x80 == 0 {
            let mut check = Vec::new();
            enc_uvarint(value, &mut check);
            if check != data[start..*offset] {
                return Err(PZipError::Invalid("non-minimal varint".into()));
            }
            return Ok(value);
        }
    }
}

pub(crate) fn dec_svarint(data: &[u8], offset: &mut usize) -> Result<isize> {
    let value = dec_uvarint(data, offset)?;
    Ok(if value & 1 == 1 {
        -(((value + 1) >> 1) as isize)
    } else {
        (value >> 1) as isize
    })
}

pub(crate) fn enc_str(value: &str, out: &mut Vec<u8>) {
    enc_uvarint(value.len(), out);
    out.extend_from_slice(value.as_bytes());
}

pub(crate) fn dec_str(data: &[u8], offset: &mut usize) -> Result<String> {
    let len = dec_uvarint(data, offset)?;
    let end = offset
        .checked_add(len)
        .ok_or_else(|| PZipError::Invalid("overflow".into()))?;
    let bytes = data
        .get(*offset..end)
        .ok_or_else(|| PZipError::Invalid("truncated string".into()))?;
    *offset = end;
    Ok(std::str::from_utf8(bytes)?.to_string())
}

pub(crate) fn brotli_compress(data: &[u8]) -> Result<Vec<u8>> {
    let mut out = Vec::new();
    let mut writer = CompressorWriter::new(&mut out, 4096, 11, 22);
    writer.write_all(data)?;
    drop(writer);
    Ok(out)
}

pub(crate) fn brotli_decompress(data: &[u8]) -> Result<Vec<u8>> {
    let mut out = Vec::new();
    Decompressor::new(data, 4096).read_to_end(&mut out)?;
    Ok(out)
}

fn xz_pipe(args: &[&str], data: &[u8]) -> Result<Vec<u8>> {
    let mut child = Command::new("xz")
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;
    child
        .stdin
        .take()
        .ok_or_else(|| PZipError::Invalid("missing stdin".into()))?
        .write_all(data)?;
    let out = child.wait_with_output()?;
    if out.status.success() {
        Ok(out.stdout)
    } else {
        Err(PZipError::Invalid(
            String::from_utf8_lossy(&out.stderr).trim().to_string(),
        ))
    }
}

pub(crate) fn xz_compress(data: &[u8]) -> Result<Vec<u8>> {
    xz_pipe(&["-z", "-c"], data)
}

pub(crate) fn xz_decompress(data: &[u8]) -> Result<Vec<u8>> {
    xz_pipe(&["-d", "-c"], data)
}
