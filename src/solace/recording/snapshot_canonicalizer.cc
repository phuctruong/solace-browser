// Solace Browser - Snapshot Canonicalizer Implementation
// Auth: 65537 | Phase 2: Episode Recording
//
// Implements the B1 five-step canonicalization pipeline.

#include "snapshot_canonicalizer.h"
#include "episode_serializer.h"

#include <algorithm>
#include <cctype>
#include <map>
#include <sstream>

namespace solace {
namespace recording {

SnapshotCanonicalizer::SnapshotCanonicalizer() = default;
SnapshotCanonicalizer::~SnapshotCanonicalizer() = default;

const std::set<std::string>& SnapshotCanonicalizer::AllowedAttrs() {
  static const std::set<std::string> allowed = {
      "aria-label", "aria-labelledby", "aria-describedby",
      "data-refid", "href", "id", "name", "placeholder",
      "role", "src", "title", "type", "value"};
  return allowed;
}

const std::set<std::string>& SnapshotCanonicalizer::StripAttrs() {
  static const std::set<std::string> strip = {"class", "style", "tabindex"};
  return strip;
}

CanonicalResult SnapshotCanonicalizer::Canonicalize(const Snapshot& raw) {
  CanonicalResult result;
  result.success = false;

  // Step 0: Validate schema
  std::string error;
  if (!ValidateSchema(raw, error)) {
    result.error_code = "E_SCHEMA";
    result.error_message = error;
    return result;
  }

  // Step 1: Remove volatiles
  DomNode dom = RemoveVolatiles(raw.dom);

  // Step 2: Sort keys
  dom = SortKeys(dom);

  // Step 3: Normalize whitespace
  dom = NormalizeWhitespace(dom);

  // Step 4: Normalize unicode (tag lowercasing)
  dom = NormalizeUnicode(dom);

  // Build canonical snapshot
  Snapshot canonical;
  canonical.version = 1;
  canonical.url = raw.url;
  canonical.viewport = raw.viewport;
  canonical.dom = dom;

  // Step 5: Canonical JSON + SHA-256
  EpisodeSerializer serializer;
  result.canonical_json = serializer.SerializeSnapshot(canonical);
  result.sha256 = EpisodeSerializer::ComputeSHA256(result.canonical_json);

  // Extract landmarks
  result.landmarks = ExtractLandmarks(dom);

  result.success = true;
  return result;
}

bool SnapshotCanonicalizer::ValidateSchema(const Snapshot& snap,
                                            std::string& error) {
  // Validate version
  if (snap.version != 1) {
    error = "E_TYPE: version must be 1";
    return false;
  }

  // Validate viewport
  if (snap.viewport.width < 1 || snap.viewport.height < 1) {
    error = "E_TYPE: viewport dimensions must be >= 1";
    return false;
  }

  // Validate URL
  if (snap.url.empty()) {
    error = "E_TYPE: url must not be empty";
    return false;
  }

  // Validate DOM tree (depth, node count)
  int node_count = 0;
  if (!ValidateNode(snap.dom, 0, node_count, error)) {
    return false;
  }

  return true;
}

bool SnapshotCanonicalizer::ValidateNode(const DomNode& node, int depth,
                                          int& node_count,
                                          std::string& error) {
  if (depth > kMaxDepth) {
    error = "E_DEPTH_LIMIT: depth exceeds 200";
    return false;
  }

  node_count++;
  if (node_count > kMaxNodes) {
    error = "E_NODE_LIMIT: node count exceeds 200000";
    return false;
  }

  // Validate tag is not empty
  if (node.tag.empty()) {
    error = "E_TYPE: node tag must not be empty";
    return false;
  }

  // Validate attrs: check against policy
  for (const auto& [key, val] : node.attrs) {
    if (AllowedAttrs().count(key) == 0 && StripAttrs().count(key) == 0) {
      error = "E_ATTR_FORBIDDEN: forbidden attr: " + key;
      return false;
    }
  }

  // Recurse children
  for (const auto& child : node.children) {
    if (!ValidateNode(child, depth + 1, node_count, error)) {
      return false;
    }
  }

  return true;
}

DomNode SnapshotCanonicalizer::RemoveVolatiles(const DomNode& node) {
  DomNode result;
  result.tag = node.tag;
  result.text = node.text;

  // Keep only allowed attrs, strip class/style/tabindex
  for (const auto& [key, val] : node.attrs) {
    if (AllowedAttrs().count(key) > 0) {
      result.attrs[key] = val;
    }
    // StripAttrs are silently dropped
  }

  // Recurse children
  for (const auto& child : node.children) {
    result.children.push_back(RemoveVolatiles(child));
  }

  return result;
}

DomNode SnapshotCanonicalizer::SortKeys(const DomNode& node) {
  DomNode result;
  result.tag = node.tag;
  result.text = node.text;
  result.attrs = node.attrs;  // attrs will be sorted during serialization

  // Sort children by (tag, id, name, data-refid, text[:32])
  std::vector<DomNode> sorted_children;
  for (const auto& child : node.children) {
    sorted_children.push_back(SortKeys(child));
  }

  std::sort(sorted_children.begin(), sorted_children.end(),
            [](const DomNode& a, const DomNode& b) {
              // Primary: tag
              if (a.tag != b.tag) return a.tag < b.tag;

              // Secondary: id
              auto a_id = a.attrs.count("id") ? a.attrs.at("id") : "";
              auto b_id = b.attrs.count("id") ? b.attrs.at("id") : "";
              if (a_id != b_id) return a_id < b_id;

              // Tertiary: name
              auto a_name = a.attrs.count("name") ? a.attrs.at("name") : "";
              auto b_name = b.attrs.count("name") ? b.attrs.at("name") : "";
              if (a_name != b_name) return a_name < b_name;

              // Quaternary: data-refid
              auto a_ref =
                  a.attrs.count("data-refid") ? a.attrs.at("data-refid") : "";
              auto b_ref =
                  b.attrs.count("data-refid") ? b.attrs.at("data-refid") : "";
              if (a_ref != b_ref) return a_ref < b_ref;

              // Final: text (first 32 chars)
              return a.text.substr(0, 32) < b.text.substr(0, 32);
            });

  result.children = std::move(sorted_children);
  return result;
}

DomNode SnapshotCanonicalizer::NormalizeWhitespace(const DomNode& node) {
  DomNode result;
  result.tag = node.tag;
  result.text = NormalizeText(node.text);
  result.attrs = node.attrs;

  // Normalize attr values
  for (auto& [key, val] : result.attrs) {
    val = NormalizeText(val);
  }

  // Recurse children
  for (const auto& child : node.children) {
    result.children.push_back(NormalizeWhitespace(child));
  }

  return result;
}

DomNode SnapshotCanonicalizer::NormalizeUnicode(const DomNode& node) {
  DomNode result;
  result.tag = ToLower(node.tag);
  result.text = node.text;
  result.attrs = node.attrs;

  // Recurse children
  for (const auto& child : node.children) {
    result.children.push_back(NormalizeUnicode(child));
  }

  return result;
}

std::vector<Landmark> SnapshotCanonicalizer::ExtractLandmarks(
    const DomNode& dom) {
  std::vector<Landmark> landmarks;
  CollectLandmarks(dom, "", landmarks);
  return landmarks;
}

void SnapshotCanonicalizer::CollectLandmarks(
    const DomNode& node, const std::string& path,
    std::vector<Landmark>& out) {
  std::string current_path =
      path.empty() ? node.tag : path + " > " + node.tag;

  auto get_attr = [&node](const std::string& key) -> std::string {
    auto it = node.attrs.find(key);
    return (it != node.attrs.end()) ? it->second : "";
  };

  std::string role = get_attr("role");
  std::string label = get_attr("aria-label");
  if (label.empty()) label = node.text.substr(0, 64);

  // Navigation landmarks
  if (node.tag == "nav" || role == "navigation") {
    out.push_back({"nav", label, role, current_path});
  }

  // Form landmarks
  if (node.tag == "form" || role == "form") {
    out.push_back({"form", label, role, current_path});
  }

  // Heading landmarks
  if (node.tag.size() == 2 && node.tag[0] == 'h' &&
      node.tag[1] >= '1' && node.tag[1] <= '6') {
    out.push_back({"heading", label, role, current_path});
  }

  // Button landmarks
  if (node.tag == "button" || role == "button" ||
      (node.tag == "input" && get_attr("type") == "submit")) {
    out.push_back({"button", label, role, current_path});
  }

  // List landmarks
  if (node.tag == "ul" || node.tag == "ol" || role == "list") {
    out.push_back({"list", label, role, current_path});
  }

  // Recurse
  for (const auto& child : node.children) {
    CollectLandmarks(child, current_path, out);
  }
}

std::string SnapshotCanonicalizer::NormalizeText(const std::string& text) {
  std::string result;
  result.reserve(text.size());

  bool in_whitespace = false;
  for (char c : text) {
    // Replace \r\n and \r with \n
    if (c == '\r') continue;

    if (std::isspace(static_cast<unsigned char>(c))) {
      if (!in_whitespace) {
        result += ' ';
        in_whitespace = true;
      }
    } else {
      result += c;
      in_whitespace = false;
    }
  }

  // Trim leading and trailing whitespace
  size_t start = result.find_first_not_of(' ');
  if (start == std::string::npos) return "";
  size_t end = result.find_last_not_of(' ');
  return result.substr(start, end - start + 1);
}

std::string SnapshotCanonicalizer::ToLower(const std::string& s) {
  std::string result = s;
  std::transform(result.begin(), result.end(), result.begin(),
                 [](unsigned char c) { return std::tolower(c); });
  return result;
}

}  // namespace recording
}  // namespace solace
