// Solace Browser - Action Type Definitions
// Auth: 65537 | Phase 2: Episode Recording
//
// Defines the core data structures for episode recording:
// - ActionType enum (NAVIGATE, CLICK, TYPE, SELECT, SUBMIT)
// - Action struct (single user interaction)
// - Snapshot struct (DOM state at a point in time)
// - Episode struct (sequence of actions + snapshots)

#ifndef SOLACE_RECORDING_ACTION_TYPES_H_
#define SOLACE_RECORDING_ACTION_TYPES_H_

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace solace {
namespace recording {

// Phase B action types
enum class ActionType {
  NAVIGATE = 0,
  CLICK = 1,
  TYPE = 2,
  SELECT = 3,
  SUBMIT = 4,
  SNAPSHOT = 5,
};

// Convert ActionType to Phase B string representation
inline const char* ActionTypeToString(ActionType type) {
  switch (type) {
    case ActionType::NAVIGATE: return "navigate";
    case ActionType::CLICK:    return "click";
    case ActionType::TYPE:     return "type";
    case ActionType::SELECT:   return "select";
    case ActionType::SUBMIT:   return "submit";
    case ActionType::SNAPSHOT: return "snapshot";
  }
  return "unknown";
}

// Parse Phase B string to ActionType
inline ActionType StringToActionType(const std::string& s) {
  if (s == "navigate") return ActionType::NAVIGATE;
  if (s == "click")    return ActionType::CLICK;
  if (s == "type")     return ActionType::TYPE;
  if (s == "select")   return ActionType::SELECT;
  if (s == "submit")   return ActionType::SUBMIT;
  if (s == "snapshot") return ActionType::SNAPSHOT;
  return ActionType::NAVIGATE;  // fallback
}

// Element reference (semantic + structural selectors)
struct ElementReference {
  std::string selector;     // CSS selector or XPath
  std::string reference;    // Semantic label (aria-label, text content)
  std::string tag;          // HTML tag name
  std::string id;           // Element ID attribute
  std::string role;         // ARIA role
};

// Single action in an episode
struct Action {
  int step;                 // Sequential step number (0-indexed)
  ActionType type;          // Action type
  std::string timestamp;    // ISO 8601 timestamp

  // Action-specific data
  std::string url;          // For NAVIGATE
  std::string text;         // For TYPE
  std::string value;        // For SELECT
  ElementReference target;  // For CLICK, TYPE, SELECT, SUBMIT
};

// DOM node for structured snapshot
struct DomNode {
  std::string tag;
  std::string text;
  std::unordered_map<std::string, std::string> attrs;
  std::vector<DomNode> children;
};

// Viewport dimensions
struct Viewport {
  int width;
  int height;
};

// Snapshot: DOM state at a point in time
struct Snapshot {
  int version;              // Schema version (1)
  std::string url;          // Page URL
  Viewport viewport;        // Viewport dimensions
  DomNode dom;              // Root DOM node
  std::string sha256;       // Content hash (computed after canonicalization)
};

// Complete episode: sequence of actions with snapshots
struct Episode {
  std::string version;      // "1.0.0"
  std::string session_id;   // Unique session identifier
  std::string domain;       // Primary domain
  std::string start_time;   // ISO 8601
  std::string end_time;     // ISO 8601
  std::vector<Action> actions;
  std::unordered_map<int, Snapshot> snapshots;  // step -> snapshot
  int action_count;         // Must equal actions.size()
};

}  // namespace recording
}  // namespace solace

#endif  // SOLACE_RECORDING_ACTION_TYPES_H_
