// Copyright 2025 Solace Browser Authors. All rights reserved.
// Episode recording schema - Phase B compatible

#ifndef SOLACE_RECORDING_EPISODE_SCHEMA_H_
#define SOLACE_RECORDING_EPISODE_SCHEMA_H_

#include <string>
#include <vector>
#include <map>
#include <cstdint>

namespace solace {
namespace recording {

// Selector types
enum class SelectorType {
  ARIA_LABEL,
  ARIA_DESCRIBEDBY,
  DATA_TESTID,
  DATA_QA,
  PLACEHOLDER,
  ALT_TEXT,
  CSS_SELECTOR,
  XPATH,
  TAG_POSITION,
  URL,
};

// Semantic selector
struct SemanticSelector {
  SelectorType type;
  std::string value;
};

// Structural selector
struct StructuralSelector {
  SelectorType type;
  std::string value;
};

// Target element identification
struct Target {
  SemanticSelector semantic;
  StructuralSelector structural;
};

// Snapshot metadata
struct Snapshot {
  std::string type;  // "DOM_SNAPSHOT"
  std::string hash;  // SHA256 hash of canonical DOM
  int64_t content_length;  // Size in bytes
  std::string root_tag;  // Root HTML tag
};

// Action types
enum class ActionType {
  NAVIGATE,
  CLICK,
  TYPE,
  SELECT,
  SUBMIT,
};

// Single user action
struct Action {
  int64_t index;  // 0-based action index
  ActionType type;
  std::string timestamp;  // ISO 8601 format
  Target target;  // Element identification
  std::string value;  // Action value (text typed, option selected, etc.)
  Snapshot snapshot_before;  // DOM state before action
  Snapshot snapshot_after;   // DOM state after action
};

// Episode metadata
struct Metadata {
  std::string browser_version;  // e.g., "ungoogled-chromium-127.0.0"
  std::string browser_build;    // e.g., "Solace-0.1.0"
  int screen_width;
  int screen_height;
  std::string locale;  // e.g., "en-US"
};

// Complete episode
struct Episode {
  std::string episode_id;  // e.g., "ep_20250214_001"
  std::string recording_start;  // ISO 8601 timestamp
  std::string recording_end;    // ISO 8601 timestamp
  std::string url_start;  // Initial URL
  std::string url_end;    // Final URL
  int64_t action_count;   // Number of actions
  Metadata metadata;
  std::vector<Action> actions;

  // Compute canonical hash of episode
  std::string ComputeHash() const;

  // Convert to Phase B JSON format
  std::string ToJSON() const;

  // Load from Phase B JSON format
  static Episode FromJSON(const std::string& json_str);
};

}  // namespace recording
}  // namespace solace

#endif  // SOLACE_RECORDING_EPISODE_SCHEMA_H_
