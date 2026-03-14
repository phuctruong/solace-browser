// Diagram: 27-prime-wiki-snapshots
// Spec: 41-stillwater-ripple-codecs
//
// Stillwater/Ripple decomposition: detect page type, extract shared structure
// (stillwater) and unique content (ripple). Compress ripple against stillwater
// base for community browsing.
//
// Codec Registry:
//   semantic-html  — <main>/<article> extraction (solaceagi.com, Wikipedia, GitHub)
//   table-html     — <table> dominant, no <main> (HackerNews)
//   json-api       — Content-Type: application/json (Reddit API)
//   rss-xml        — <rss>/<feed> root (Google News RSS)
//   jinja-template — {% extends %} + {{ t() }} (our own templates)
//   spa-shell      — small HTML + large JS (React/Vue SPAs)

use crate::pzip::util::{brotli_compress, brotli_decompress};
use crate::pzip::{PZipError, Result};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

const MAGIC: &[u8; 4] = b"PZSW";
const VERSION: u8 = 0x01;

/// Page type codec identifiers
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Codec {
    SemanticHtml,
    TableHtml,
    JsonApi,
    RssXml,
    JinjaTemplate,
    SpaShell,
}

impl Codec {
    fn id(self) -> u8 {
        match self {
            Codec::SemanticHtml => 0x01,
            Codec::TableHtml => 0x02,
            Codec::JsonApi => 0x03,
            Codec::RssXml => 0x04,
            Codec::JinjaTemplate => 0x05,
            Codec::SpaShell => 0x06,
        }
    }

    fn from_id(id: u8) -> Result<Self> {
        match id {
            0x01 => Ok(Codec::SemanticHtml),
            0x02 => Ok(Codec::TableHtml),
            0x03 => Ok(Codec::JsonApi),
            0x04 => Ok(Codec::RssXml),
            0x05 => Ok(Codec::JinjaTemplate),
            0x06 => Ok(Codec::SpaShell),
            _ => Err(PZipError::Invalid(format!("unknown codec id: {id}"))),
        }
    }

    pub fn name(self) -> &'static str {
        match self {
            Codec::SemanticHtml => "semantic-html",
            Codec::TableHtml => "table-html",
            Codec::JsonApi => "json-api",
            Codec::RssXml => "rss-xml",
            Codec::JinjaTemplate => "jinja-template",
            Codec::SpaShell => "spa-shell",
        }
    }
}

/// Extracted Stillwater (shared structure) + Ripple (unique content)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Decomposition {
    pub codec: Codec,
    pub url: String,
    pub stillwater: Stillwater,
    pub ripple: Ripple,
    pub sha256: String,
}

/// Shared structure that rarely changes (the "generator")
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Stillwater {
    pub headings: Vec<String>,
    pub nav_links: Vec<String>,
    pub css_tokens: Vec<String>,
    pub meta: Vec<(String, String)>,
    pub template_hash: String,
}

/// Unique content per page visit (the "residual")
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Ripple {
    pub title: String,
    pub sections: Vec<Section>,
    pub data_items: Vec<DataItem>,
    pub timestamp: String,
}

/// A semantic section extracted from the page
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Section {
    pub heading: String,
    pub content: String,
    pub level: u8,
}

/// A structured data item (table row, JSON entry, RSS item)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataItem {
    pub fields: Vec<(String, String)>,
}

// ─── Detection ───────────────────────────────────────────────────────

/// Auto-detect the correct codec for a page based on content type and content.
pub fn detect_codec(content: &[u8], content_type: &str) -> Codec {
    if content_type.contains("json") {
        return Codec::JsonApi;
    }
    if content_type.contains("xml") || content.starts_with(b"<?xml") {
        return detect_xml_subtype(content);
    }

    let html = String::from_utf8_lossy(content);
    let html_lower = html.to_ascii_lowercase();

    if html_lower.contains("{% extends") || html_lower.contains("{% block") {
        return Codec::JinjaTemplate;
    }
    if html_lower.contains("<main") || html_lower.contains("<article") {
        return Codec::SemanticHtml;
    }
    if html_lower.contains("<table") && !html_lower.contains("<main") {
        return Codec::TableHtml;
    }
    // SPA detection: small HTML body + large script tags
    if is_spa_shell(&html_lower) {
        return Codec::SpaShell;
    }

    Codec::SemanticHtml // default fallback
}

fn detect_xml_subtype(content: &[u8]) -> Codec {
    let text = String::from_utf8_lossy(content);
    let lower = text.to_ascii_lowercase();
    if lower.contains("<rss") || lower.contains("<feed") || lower.contains("<channel") {
        Codec::RssXml
    } else {
        Codec::SemanticHtml // treat generic XML as semantic
    }
}

fn is_spa_shell(html: &str) -> bool {
    let body_len = extract_between(html, "<body", "</body>").len();
    let script_len: usize = html
        .match_indices("<script")
        .filter_map(|(start, _)| {
            html[start..]
                .find("</script>")
                .map(|end| end + "</script>".len())
        })
        .sum();
    // SPA = scripts are >60% of body and body text is <500 chars
    body_len < 500 && script_len > 200 && script_len > body_len
}

// ─── Extraction ──────────────────────────────────────────────────────

/// Extract Stillwater + Ripple from page content.
pub fn extract(content: &[u8], content_type: &str, url: &str) -> Result<Decomposition> {
    let codec = detect_codec(content, content_type);
    let (stillwater, ripple) = match codec {
        Codec::SemanticHtml => extract_semantic_html(content)?,
        Codec::TableHtml => extract_table_html(content)?,
        Codec::JsonApi => extract_json_api(content)?,
        Codec::RssXml => extract_rss_xml(content)?,
        Codec::JinjaTemplate => extract_jinja_template(content)?,
        Codec::SpaShell => extract_spa_shell(content)?,
    };

    let sha256 = {
        let mut hasher = Sha256::new();
        hasher.update(content);
        format!("{:x}", hasher.finalize())
    };

    Ok(Decomposition {
        codec,
        url: url.to_string(),
        stillwater,
        ripple,
        sha256,
    })
}

// ─── Semantic HTML Extraction ────────────────────────────────────────

fn extract_semantic_html(content: &[u8]) -> Result<(Stillwater, Ripple)> {
    let html = String::from_utf8_lossy(content);

    let headings = extract_all_tags(&html, "h1")
        .into_iter()
        .chain(extract_all_tags(&html, "h2"))
        .chain(extract_all_tags(&html, "h3"))
        .collect();
    let nav_links = extract_nav_links(&html);
    let css_tokens = extract_css_tokens(&html);
    let meta = extract_meta_tags(&html);
    let template_hash = hash_structure(&html, &["nav", "header", "footer"]);

    let title = extract_tag_content(&html, "title").unwrap_or_default();
    let main_content = extract_between(&html, "<main", "</main>");
    let sections = extract_sections_from_content(&main_content);

    Ok((
        Stillwater {
            headings,
            nav_links,
            css_tokens,
            meta,
            template_hash,
        },
        Ripple {
            title,
            sections,
            data_items: Vec::new(),
            timestamp: chrono::Utc::now().to_rfc3339(),
        },
    ))
}

// ─── Table HTML Extraction (HackerNews) ──────────────────────────────

fn extract_table_html(content: &[u8]) -> Result<(Stillwater, Ripple)> {
    let html = String::from_utf8_lossy(content);

    let headings = extract_all_tags(&html, "th");
    let nav_links = extract_nav_links(&html);
    let css_tokens = extract_css_tokens(&html);
    let meta = extract_meta_tags(&html);
    let template_hash = hash_structure(&html, &["table", "thead"]);

    let title = extract_tag_content(&html, "title").unwrap_or_default();
    let rows = extract_table_rows(&html);

    Ok((
        Stillwater {
            headings,
            nav_links,
            css_tokens,
            meta,
            template_hash,
        },
        Ripple {
            title,
            sections: Vec::new(),
            data_items: rows,
            timestamp: chrono::Utc::now().to_rfc3339(),
        },
    ))
}

// ─── JSON API Extraction (Reddit) ────────────────────────────────────

fn extract_json_api(content: &[u8]) -> Result<(Stillwater, Ripple)> {
    let value: serde_json::Value = serde_json::from_slice(content)
        .map_err(|e| PZipError::Invalid(format!("json parse: {e}")))?;

    let keys = collect_all_keys(&value);
    let template_hash = {
        let mut hasher = Sha256::new();
        for k in &keys {
            hasher.update(k.as_bytes());
        }
        format!("{:x}", hasher.finalize())
    };

    let data_items = extract_json_items(&value);

    Ok((
        Stillwater {
            headings: keys,
            nav_links: Vec::new(),
            css_tokens: Vec::new(),
            meta: Vec::new(),
            template_hash,
        },
        Ripple {
            title: String::new(),
            sections: Vec::new(),
            data_items,
            timestamp: chrono::Utc::now().to_rfc3339(),
        },
    ))
}

// ─── RSS/XML Extraction (Google News) ────────────────────────────────

fn extract_rss_xml(content: &[u8]) -> Result<(Stillwater, Ripple)> {
    let xml = String::from_utf8_lossy(content);

    let channel_title = extract_tag_content(&xml, "title").unwrap_or_default();
    let channel_link = extract_tag_content(&xml, "link").unwrap_or_default();
    let channel_desc = extract_tag_content(&xml, "description").unwrap_or_default();
    let template_hash = hash_structure(&xml, &["channel", "generator"]);

    let items = extract_rss_items(&xml);

    Ok((
        Stillwater {
            headings: vec![channel_title.clone()],
            nav_links: vec![channel_link],
            css_tokens: Vec::new(),
            meta: vec![("description".to_string(), channel_desc)],
            template_hash,
        },
        Ripple {
            title: channel_title,
            sections: Vec::new(),
            data_items: items,
            timestamp: chrono::Utc::now().to_rfc3339(),
        },
    ))
}

// ─── Jinja Template Extraction ───────────────────────────────────────

fn extract_jinja_template(content: &[u8]) -> Result<(Stillwater, Ripple)> {
    let html = String::from_utf8_lossy(content);

    let extends = extract_jinja_extends(&html);
    let blocks = extract_jinja_blocks(&html);
    let i18n_keys = extract_i18n_keys(&html);
    let css_tokens = extract_css_tokens(&html);
    let template_hash = {
        let mut hasher = Sha256::new();
        hasher.update(extends.as_bytes());
        for block in &blocks {
            hasher.update(block.as_bytes());
        }
        format!("{:x}", hasher.finalize())
    };

    Ok((
        Stillwater {
            headings: blocks,
            nav_links: Vec::new(),
            css_tokens,
            meta: i18n_keys,
            template_hash,
        },
        Ripple {
            title: extends,
            sections: Vec::new(),
            data_items: Vec::new(),
            timestamp: chrono::Utc::now().to_rfc3339(),
        },
    ))
}

// ─── SPA Shell Extraction ────────────────────────────────────────────

fn extract_spa_shell(content: &[u8]) -> Result<(Stillwater, Ripple)> {
    let html = String::from_utf8_lossy(content);

    let meta = extract_meta_tags(&html);
    let css_tokens = extract_css_tokens(&html);
    let script_srcs = extract_script_srcs(&html);
    let template_hash = hash_structure(&html, &["head", "script"]);

    let title = extract_tag_content(&html, "title").unwrap_or_default();

    Ok((
        Stillwater {
            headings: Vec::new(),
            nav_links: script_srcs,
            css_tokens,
            meta,
            template_hash,
        },
        Ripple {
            title,
            sections: Vec::new(),
            data_items: Vec::new(),
            timestamp: chrono::Utc::now().to_rfc3339(),
        },
    ))
}

// ─── Compression (Stillwater + Ripple → PZSW) ───────────────────────

/// Compress a Decomposition into a PZSW binary blob.
pub fn compress_decomposition(decomp: &Decomposition) -> Result<Vec<u8>> {
    let json = serde_json::to_vec(decomp)?;
    let payload = brotli_compress(&json)?;

    let mut out = Vec::with_capacity(6 + payload.len());
    out.extend_from_slice(MAGIC);
    out.push(VERSION);
    out.push(decomp.codec.id());
    out.extend_from_slice(&payload);
    Ok(out)
}

/// Decompress a PZSW blob back to a Decomposition.
pub fn decompress_decomposition(data: &[u8]) -> Result<Decomposition> {
    if data.len() < 6 || &data[..4] != MAGIC || data[4] != VERSION {
        return Err(PZipError::Invalid("invalid PZSW".into()));
    }
    let _codec = Codec::from_id(data[5])?;
    let json = brotli_decompress(&data[6..])?;
    let decomp: Decomposition = serde_json::from_slice(&json)?;
    Ok(decomp)
}

/// Compress only the ripple against a known stillwater base.
/// Returns a smaller payload when stillwater hasn't changed.
pub fn compress_ripple_only(ripple: &Ripple) -> Result<Vec<u8>> {
    let json = serde_json::to_vec(ripple)?;
    brotli_compress(&json)
}

/// Decompress a ripple-only payload.
pub fn decompress_ripple(data: &[u8]) -> Result<Ripple> {
    let json = brotli_decompress(data)?;
    let ripple: Ripple = serde_json::from_slice(&json)?;
    Ok(ripple)
}

// ─── Helper: HTML Tag Extraction (no dependency on html5ever) ────────

fn extract_tag_content(html: &str, tag: &str) -> Option<String> {
    let open = format!("<{}", tag);
    let close = format!("</{}>", tag);
    let start = html.find(&open)?;
    let after_open = html[start..].find('>')? + start + 1;
    let end = html[after_open..].find(&close)? + after_open;
    Some(strip_tags(&html[after_open..end]).trim().to_string())
}

fn extract_all_tags(html: &str, tag: &str) -> Vec<String> {
    let open = format!("<{}", tag);
    let close = format!("</{}>", tag);
    let mut results = Vec::new();
    let mut search_from = 0;
    while let Some(pos) = html[search_from..].find(&open) {
        let abs = search_from + pos;
        if let Some(gt) = html[abs..].find('>') {
            let start = abs + gt + 1;
            if let Some(end) = html[start..].find(&close) {
                let text = strip_tags(&html[start..start + end]).trim().to_string();
                if !text.is_empty() {
                    results.push(text);
                }
                search_from = start + end + close.len();
            } else {
                break;
            }
        } else {
            break;
        }
    }
    results
}

fn extract_between(html: &str, open_tag: &str, close_tag: &str) -> String {
    let lower = html.to_ascii_lowercase();
    if let Some(start) = lower.find(open_tag) {
        if let Some(gt) = html[start..].find('>') {
            let content_start = start + gt + 1;
            if let Some(end) = lower[content_start..].find(close_tag) {
                return html[content_start..content_start + end].to_string();
            }
        }
    }
    String::new()
}

fn extract_nav_links(html: &str) -> Vec<String> {
    let nav = extract_between(html, "<nav", "</nav>");
    extract_href_values(&nav)
}

fn extract_href_values(html: &str) -> Vec<String> {
    let mut links = Vec::new();
    let mut search_from = 0;
    while let Some(pos) = html[search_from..].find("href=\"") {
        let start = search_from + pos + 6;
        if let Some(end) = html[start..].find('"') {
            links.push(html[start..start + end].to_string());
            search_from = start + end + 1;
        } else {
            break;
        }
    }
    links
}

fn extract_css_tokens(html: &str) -> Vec<String> {
    let mut tokens = Vec::new();
    let mut search_from = 0;
    while let Some(pos) = html[search_from..].find("var(--") {
        let start = search_from + pos + 4;
        if let Some(end) = html[start..].find(')') {
            let token = html[start..start + end].to_string();
            if !tokens.contains(&token) {
                tokens.push(token);
            }
            search_from = start + end + 1;
        } else {
            break;
        }
    }
    tokens
}

fn extract_meta_tags(html: &str) -> Vec<(String, String)> {
    let mut metas = Vec::new();
    let mut search_from = 0;
    while let Some(pos) = html[search_from..].find("<meta ") {
        let abs = search_from + pos;
        if let Some(end) = html[abs..].find('>') {
            let tag = &html[abs..abs + end + 1];
            let name = extract_attr(tag, "name")
                .or_else(|| extract_attr(tag, "property"))
                .unwrap_or_default();
            let content = extract_attr(tag, "content").unwrap_or_default();
            if !name.is_empty() && !content.is_empty() {
                metas.push((name, content));
            }
            search_from = abs + end + 1;
        } else {
            break;
        }
    }
    metas
}

fn extract_attr(tag: &str, attr: &str) -> Option<String> {
    let pattern = format!("{}=\"", attr);
    let pos = tag.find(&pattern)?;
    let start = pos + pattern.len();
    let end = tag[start..].find('"')?;
    Some(tag[start..start + end].to_string())
}

fn extract_script_srcs(html: &str) -> Vec<String> {
    let mut srcs = Vec::new();
    let mut search_from = 0;
    while let Some(pos) = html[search_from..].find("<script") {
        let abs = search_from + pos;
        if let Some(end) = html[abs..].find('>') {
            let tag = &html[abs..abs + end + 1];
            if let Some(src) = extract_attr(tag, "src") {
                srcs.push(src);
            }
            search_from = abs + end + 1;
        } else {
            break;
        }
    }
    srcs
}

fn strip_tags(text: &str) -> String {
    let mut result = String::with_capacity(text.len());
    let mut in_tag = false;
    for ch in text.chars() {
        if ch == '<' {
            in_tag = true;
        } else if ch == '>' {
            in_tag = false;
        } else if !in_tag {
            result.push(ch);
        }
    }
    result
}

fn extract_sections_from_content(content: &str) -> Vec<Section> {
    let mut sections = Vec::new();
    for level in 1..=6u8 {
        let close = format!("</h{level}>");
        let mut search_from = 0;
        let lower = content.to_ascii_lowercase();
        while let Some(pos) = lower[search_from..].find(&format!("<h{level}")) {
            let abs = search_from + pos;
            if let Some(gt) = content[abs..].find('>') {
                let heading_start = abs + gt + 1;
                if let Some(heading_end) = lower[heading_start..].find(&close) {
                    let heading = strip_tags(&content[heading_start..heading_start + heading_end])
                        .trim()
                        .to_string();
                    // Content after heading until next heading or end
                    let after = heading_start + heading_end + close.len();
                    let next_h = lower[after..]
                        .find("<h")
                        .map(|p| after + p)
                        .unwrap_or(content.len());
                    let body = strip_tags(&content[after..next_h]).trim().to_string();
                    if !heading.is_empty() {
                        sections.push(Section {
                            heading,
                            content: truncate(&body, 2000),
                            level,
                        });
                    }
                    search_from = next_h;
                } else {
                    break;
                }
            } else {
                break;
            }
        }
    }
    sections
}

fn extract_table_rows(html: &str) -> Vec<DataItem> {
    let mut items = Vec::new();
    let headers = extract_all_tags(html, "th");
    let lower = html.to_ascii_lowercase();
    let mut search_from = 0;

    while let Some(pos) = lower[search_from..].find("<tr") {
        let abs = search_from + pos;
        if let Some(end) = lower[abs..].find("</tr>") {
            let row_html = &html[abs..abs + end + 5];
            let cells = extract_all_tags(row_html, "td");
            if !cells.is_empty() {
                let fields: Vec<(String, String)> = cells
                    .into_iter()
                    .enumerate()
                    .map(|(i, val)| {
                        let key = headers
                            .get(i)
                            .cloned()
                            .unwrap_or_else(|| format!("col_{i}"));
                        (key, val)
                    })
                    .collect();
                items.push(DataItem { fields });
            }
            search_from = abs + end + 5;
        } else {
            break;
        }
    }
    items
}

fn extract_rss_items(xml: &str) -> Vec<DataItem> {
    let mut items = Vec::new();
    let lower = xml.to_ascii_lowercase();
    let mut search_from = 0;

    while let Some(pos) = lower[search_from..].find("<item") {
        let abs = search_from + pos;
        if let Some(end) = lower[abs..].find("</item>") {
            let item_xml = &xml[abs..abs + end + 7];
            let mut fields = Vec::new();
            for tag in &["title", "link", "description", "pubDate", "guid"] {
                if let Some(val) = extract_tag_content(item_xml, tag) {
                    fields.push((tag.to_string(), truncate(&val, 500)));
                }
            }
            if !fields.is_empty() {
                items.push(DataItem { fields });
            }
            search_from = abs + end + 7;
        } else {
            break;
        }
    }
    items
}

fn extract_json_items(value: &serde_json::Value) -> Vec<DataItem> {
    match value {
        serde_json::Value::Array(arr) => arr
            .iter()
            .take(100)
            .filter_map(|v| {
                if let serde_json::Value::Object(obj) = v {
                    let fields: Vec<(String, String)> = obj
                        .iter()
                        .map(|(k, v)| (k.clone(), truncate(&format_json_value(v), 500)))
                        .collect();
                    Some(DataItem { fields })
                } else {
                    None
                }
            })
            .collect(),
        serde_json::Value::Object(obj) => {
            // Look for nested arrays (e.g., Reddit's data.children)
            for (_key, val) in obj {
                if let serde_json::Value::Array(_) = val {
                    let items = extract_json_items(val);
                    if !items.is_empty() {
                        return items;
                    }
                }
            }
            // Single object = single item
            let fields: Vec<(String, String)> = obj
                .iter()
                .map(|(k, v)| (k.clone(), truncate(&format_json_value(v), 500)))
                .collect();
            if fields.is_empty() {
                Vec::new()
            } else {
                vec![DataItem { fields }]
            }
        }
        _ => Vec::new(),
    }
}

fn collect_all_keys(value: &serde_json::Value) -> Vec<String> {
    let mut keys = Vec::new();
    collect_keys_recursive(value, &mut keys);
    keys.sort();
    keys.dedup();
    keys
}

fn collect_keys_recursive(value: &serde_json::Value, keys: &mut Vec<String>) {
    match value {
        serde_json::Value::Object(obj) => {
            for (k, v) in obj {
                if !keys.contains(k) {
                    keys.push(k.clone());
                }
                collect_keys_recursive(v, keys);
            }
        }
        serde_json::Value::Array(arr) => {
            for v in arr.iter().take(10) {
                collect_keys_recursive(v, keys);
            }
        }
        _ => {}
    }
}

fn format_json_value(v: &serde_json::Value) -> String {
    match v {
        serde_json::Value::String(s) => s.clone(),
        serde_json::Value::Number(n) => n.to_string(),
        serde_json::Value::Bool(b) => b.to_string(),
        serde_json::Value::Null => "null".to_string(),
        _ => serde_json::to_string(v).unwrap_or_default(),
    }
}

fn extract_jinja_extends(html: &str) -> String {
    if let Some(pos) = html.find("{% extends") {
        if let Some(start) = html[pos..].find('"') {
            let s = pos + start + 1;
            if let Some(end) = html[s..].find('"') {
                return html[s..s + end].to_string();
            }
        }
    }
    String::new()
}

fn extract_jinja_blocks(html: &str) -> Vec<String> {
    let mut blocks = Vec::new();
    let mut search_from = 0;
    while let Some(pos) = html[search_from..].find("{% block ") {
        let start = search_from + pos + 9;
        if let Some(end) = html[start..].find(' ') {
            let name = html[start..start + end].trim_end_matches('%').to_string();
            if !blocks.contains(&name) {
                blocks.push(name);
            }
            search_from = start + end;
        } else if let Some(end) = html[start..].find('%') {
            let name = html[start..start + end].trim().to_string();
            if !blocks.contains(&name) {
                blocks.push(name);
            }
            search_from = start + end;
        } else {
            break;
        }
    }
    blocks
}

fn extract_i18n_keys(html: &str) -> Vec<(String, String)> {
    let mut keys = Vec::new();
    let mut search_from = 0;
    while let Some(pos) = html[search_from..].find("{{ copy.") {
        let start = search_from + pos + 8;
        if let Some(end) = html[start..].find(' ') {
            let key = html[start..start + end]
                .trim_end_matches('}')
                .to_string();
            if !keys.iter().any(|(k, _)| k == &key) {
                keys.push((key, "i18n".to_string()));
            }
            search_from = start + end;
        } else {
            break;
        }
    }
    keys
}

fn hash_structure(html: &str, tags: &[&str]) -> String {
    let mut hasher = Sha256::new();
    for tag in tags {
        let content = extract_between(html, &format!("<{tag}"), &format!("</{tag}>"));
        // Hash structure only — strip text content, keep tag skeleton
        let skeleton = strip_text_keep_tags(&content);
        hasher.update(skeleton.as_bytes());
    }
    format!("{:x}", hasher.finalize())
}

fn strip_text_keep_tags(html: &str) -> String {
    let mut result = String::new();
    let mut in_tag = false;
    for ch in html.chars() {
        if ch == '<' {
            in_tag = true;
            result.push(ch);
        } else if ch == '>' {
            in_tag = false;
            result.push(ch);
        } else if in_tag {
            result.push(ch);
        }
    }
    result
}

fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max {
        s.to_string()
    } else {
        format!("{}...", &s[..max])
    }
}

// ─── Tests ───────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detect_semantic_html() {
        let html = b"<html><body><main><h1>Hello</h1></main></body></html>";
        assert_eq!(detect_codec(html, "text/html"), Codec::SemanticHtml);
    }

    #[test]
    fn detect_table_html() {
        let html = b"<html><body><table><tr><td>data</td></tr></table></body></html>";
        assert_eq!(detect_codec(html, "text/html"), Codec::TableHtml);
    }

    #[test]
    fn detect_json_api() {
        let json = br#"{"data": [{"id": 1}]}"#;
        assert_eq!(detect_codec(json, "application/json"), Codec::JsonApi);
    }

    #[test]
    fn detect_rss_xml() {
        let rss = b"<?xml version=\"1.0\"?><rss version=\"2.0\"><channel></channel></rss>";
        assert_eq!(detect_codec(rss, "application/xml"), Codec::RssXml);
    }

    #[test]
    fn detect_jinja_template() {
        let jinja = b"{% extends \"base.html\" %}{% block content %}Hello{% endblock %}";
        assert_eq!(detect_codec(jinja, "text/html"), Codec::JinjaTemplate);
    }

    #[test]
    fn extract_semantic_html_decomposition() {
        let html = br#"<html><head><title>Test Page</title><meta name="description" content="A test"></head><body><nav><a href="/about">About</a></nav><main><h1>Welcome</h1><p>Content here</p><h2>Section 2</h2><p>More content</p></main><footer>Footer</footer></body></html>"#;
        let decomp = extract(html, "text/html", "https://example.com/test").unwrap();
        assert_eq!(decomp.codec, Codec::SemanticHtml);
        assert_eq!(decomp.ripple.title, "Test Page");
        assert!(!decomp.ripple.sections.is_empty());
        assert!(!decomp.stillwater.nav_links.is_empty());
        assert!(!decomp.sha256.is_empty());
    }

    #[test]
    fn extract_table_html_decomposition() {
        let html = br#"<html><head><title>HN</title></head><body><table><thead><tr><th>Rank</th><th>Title</th></tr></thead><tbody><tr><td>1</td><td>Rust is great</td></tr><tr><td>2</td><td>PZip 66:1</td></tr></tbody></table></body></html>"#;
        let decomp = extract(html, "text/html", "https://news.ycombinator.com").unwrap();
        assert_eq!(decomp.codec, Codec::TableHtml);
        assert_eq!(decomp.ripple.data_items.len(), 2);
        assert_eq!(decomp.ripple.data_items[0].fields[0].0, "Rank");
        assert_eq!(decomp.ripple.data_items[0].fields[1].1, "Rust is great");
    }

    #[test]
    fn extract_json_api_decomposition() {
        let json = br#"[{"id":1,"title":"Hello","score":100},{"id":2,"title":"World","score":200}]"#;
        let decomp = extract(json, "application/json", "https://api.reddit.com/r/rust").unwrap();
        assert_eq!(decomp.codec, Codec::JsonApi);
        assert_eq!(decomp.ripple.data_items.len(), 2);
        assert!(decomp.stillwater.headings.contains(&"id".to_string()));
        assert!(decomp.stillwater.headings.contains(&"title".to_string()));
    }

    #[test]
    fn extract_rss_xml_decomposition() {
        let rss = br#"<?xml version="1.0"?><rss version="2.0"><channel><title>Tech News</title><link>https://example.com</link><description>Latest tech</description><item><title>Rust 2026</title><link>https://example.com/rust</link><description>New release</description></item><item><title>PZip Launch</title><link>https://example.com/pzip</link></item></channel></rss>"#;
        let decomp = extract(rss, "application/xml", "https://example.com/rss").unwrap();
        assert_eq!(decomp.codec, Codec::RssXml);
        assert_eq!(decomp.ripple.data_items.len(), 2);
        assert_eq!(decomp.ripple.title, "Tech News");
    }

    #[test]
    fn extract_jinja_template_decomposition() {
        let jinja = br#"{% extends "base.html" %}{% block title %}Home{% endblock %}{% block content %}<h1>{{ copy.welcome }}</h1><p>{{ copy.intro }}</p>{% endblock %}"#;
        let decomp = extract(jinja, "text/html", "https://solaceagi.com/").unwrap();
        assert_eq!(decomp.codec, Codec::JinjaTemplate);
        assert_eq!(decomp.ripple.title, "base.html");
        assert!(decomp.stillwater.headings.contains(&"title".to_string()));
        assert!(decomp.stillwater.headings.contains(&"content".to_string()));
    }

    #[test]
    fn compress_decompress_roundtrip() {
        let html = br#"<html><head><title>RTC Test</title></head><body><main><h1>Test</h1><p>Content</p></main></body></html>"#;
        let decomp = extract(html, "text/html", "https://example.com").unwrap();
        let compressed = compress_decomposition(&decomp).unwrap();
        assert_eq!(&compressed[..4], b"PZSW");
        let restored = decompress_decomposition(&compressed).unwrap();
        assert_eq!(restored.codec, decomp.codec);
        assert_eq!(restored.url, decomp.url);
        assert_eq!(restored.sha256, decomp.sha256);
        assert_eq!(restored.ripple.title, decomp.ripple.title);
    }

    #[test]
    fn ripple_only_compression() {
        let html = br#"<html><body><main><h1>Title</h1><p>Body</p></main></body></html>"#;
        let decomp = extract(html, "text/html", "https://example.com").unwrap();
        let compressed = compress_ripple_only(&decomp.ripple).unwrap();
        let restored = decompress_ripple(&compressed).unwrap();
        assert_eq!(restored.title, decomp.ripple.title);
        assert_eq!(restored.sections.len(), decomp.ripple.sections.len());
    }

    #[test]
    fn solaceagi_base_template_detection() {
        // Simulates our own base.html
        let html = br#"{% extends "base.html" %}{% block title %}Solace AGI{% endblock %}{% block content %}<main id="main-content"><h1>{{ copy.hero_title }}</h1></main>{% endblock %}"#;
        assert_eq!(detect_codec(html, "text/html"), Codec::JinjaTemplate);
    }

    #[test]
    fn empty_input_handled() {
        let decomp = extract(b"<html></html>", "text/html", "https://example.com").unwrap();
        assert_eq!(decomp.codec, Codec::SemanticHtml);
        assert!(decomp.ripple.sections.is_empty());
    }

    #[test]
    fn css_token_extraction() {
        let html = br#"<style>body { color: var(--sa-text-primary); background: var(--sa-bg-primary); }</style>"#;
        let decomp = extract(html, "text/html", "https://example.com").unwrap();
        assert!(decomp.stillwater.css_tokens.contains(&"--sa-text-primary".to_string()));
        assert!(decomp.stillwater.css_tokens.contains(&"--sa-bg-primary".to_string()));
    }
}
