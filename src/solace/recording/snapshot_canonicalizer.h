// Solace Browser - Snapshot Canonicalizer
// Auth: 65537 | Phase 2: Episode Recording
//
// Implements the B1 five-step canonicalization pipeline:
// 1. Validate schema
// 2. Remove volatiles (strip class, style, tabindex; reject unknowns)
// 3. Sort keys (recursive alphabetical, children by tag/id/name)
// 4. Normalize whitespace (collapse, trim, \r\n -> \n)
// 5. Normalize unicode (NFC, tag lowercasing)
// 6. Canonical JSON + SHA-256 hash

#ifndef SOLACE_RECORDING_SNAPSHOT_CANONICALIZER_H_
#define SOLACE_RECORDING_SNAPSHOT_CANONICALIZER_H_

#include <set>
#include <string>
#include <vector>

#include "action_types.h"

namespace solace {
namespace recording {

// Landmark types extracted from DOM
struct Landmark {
  std::string type;     // "nav", "form", "heading", "button", "list"
  std::string label;    // Semantic label (aria-label, text content)
  std::string role;     // ARIA role
  std::string selector; // Minimal CSS selector path
};

// Canonicalization result
struct CanonicalResult {
  bool success;
  std::string error_code;
  std::string error_message;
  std::string canonical_json;   // Deterministic JSON bytes
  std::string sha256;           // SHA-256 of canonical_json
  std::vector<Landmark> landmarks;
};

class SnapshotCanonicalizer {
 public:
  SnapshotCanonicalizer();
  ~SnapshotCanonicalizer();

  // Main entry point: canonicalize a raw snapshot
  CanonicalResult Canonicalize(const Snapshot& raw);

  // Individual pipeline steps (for testing)
  bool ValidateSchema(const Snapshot& snap, std::string& error);
  DomNode RemoveVolatiles(const DomNode& node);
  DomNode SortKeys(const DomNode& node);
  DomNode NormalizeWhitespace(const DomNode& node);
  DomNode NormalizeUnicode(const DomNode& node);

  // Landmark extraction
  std::vector<Landmark> ExtractLandmarks(const DomNode& dom);

 private:
  // Attribute policies from B1 design
  static const std::set<std::string>& AllowedAttrs();
  static const std::set<std::string>& StripAttrs();

  // Recursive helpers
  DomNode ProcessNode(const DomNode& node,
                      DomNode (SnapshotCanonicalizer::*step)(const DomNode&));
  void CollectLandmarks(const DomNode& node, const std::string& path,
                        std::vector<Landmark>& out);

  // Validation limits
  static constexpr int kMaxDepth = 200;
  static constexpr int kMaxNodes = 200000;
  bool ValidateNode(const DomNode& node, int depth, int& node_count,
                    std::string& error);

  std::string NormalizeText(const std::string& text);
  std::string ToLower(const std::string& s);
};

}  // namespace recording
}  // namespace solace

#endif  // SOLACE_RECORDING_SNAPSHOT_CANONICALIZER_H_
