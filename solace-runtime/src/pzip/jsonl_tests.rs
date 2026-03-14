use super::{compress, decompress};

#[test]
fn roundtrips_uniform_jsonl() {
    let raw = b"{\"id\":1,\"name\":\"a\"}\n{\"id\":2,\"name\":\"b\"}\n";
    assert_eq!(decompress(&compress(raw).unwrap()).unwrap(), raw);
}

#[test]
fn roundtrips_heterogeneous_jsonl() {
    let raw = b"{\"a\":1,\"b\":true}\n{\"b\":false,\"c\":{\"x\":1}}\n";
    assert_eq!(decompress(&compress(raw).unwrap()).unwrap(), raw);
}
