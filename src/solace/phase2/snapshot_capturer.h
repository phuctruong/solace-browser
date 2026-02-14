// Copyright 2025 Solace Browser Authors. All rights reserved.
// Snapshot capturer - renderer process

#ifndef SOLACE_RECORDING_SNAPSHOT_CAPTURER_H_
#define SOLACE_RECORDING_SNAPSHOT_CAPTURER_H_

#include <string>
#include <memory>
#include "episode_schema.h"

namespace blink {
class Document;
}  // namespace blink

namespace solace {
namespace recording {

// Captures and canonicalizes DOM snapshots
class SnapshotCapturer {
 public:
  SnapshotCapturer();
  ~SnapshotCapturer();

  // Capture snapshot of current DOM
  Snapshot CaptureSnapshot(blink::Document* document);

  // Canonicalize snapshot for determinism
  // Removes volatile content (timestamps, random IDs, etc.)
  std::string CanonicalizeSnapshot(const Snapshot& snapshot);

  // Compute deterministic SHA256 hash
  std::string ComputeHash(const std::string& canonical_content);

  // Check if DOM is "settled" (no pending mutations)
  bool IsDOMSettled(blink::Document* document);

  // Wait for DOM to settle (with timeout)
  bool WaitForDOMSettle(blink::Document* document, int timeout_ms);

 private:
  // Serialize document to JSON string
  std::string SerializeDocument(blink::Document* document);

  // Remove volatile elements from serialization
  // - Timestamps (data-timestamp, etc.)
  // - Random IDs (generated class names, etc.)
  // - Counters
  void StripVolatileContent(std::string& content);

  // Sort object keys for determinism
  std::string SortJSONKeys(const std::string& json_str);

  // Normalize whitespace
  std::string NormalizeWhitespace(const std::string& content);

  // Normalize Unicode (NFC normalization)
  std::string NormalizeUnicode(const std::string& content);

  // Track mutation count for settlement detection
  int pending_mutations_ = 0;
};

}  // namespace recording
}  // namespace solace

#endif  // SOLACE_RECORDING_SNAPSHOT_CAPTURER_H_
