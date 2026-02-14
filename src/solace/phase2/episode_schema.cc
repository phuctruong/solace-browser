// Copyright 2025 Solace Browser Authors. All rights reserved.
// Episode recording schema implementation

#include "episode_schema.h"
#include "base/sha1.h"
#include "base/json/json_writer.h"
#include "base/values.h"
#include "base/time/time.h"

namespace solace {
namespace recording {

std::string Episode::ComputeHash() const {
  // Compute SHA256 hash of JSON representation
  std::string json_str = ToJSON();

  // In real implementation, use crypto::SHA256Hash()
  // For now, placeholder
  return "sha256_" + std::to_string(json_str.length());
}

std::string Episode::ToJSON() const {
  base::Value episode_dict(base::Value::Type::DICTIONARY);

  episode_dict.SetStringKey("episode_id", episode_id);
  episode_dict.SetStringKey("recording_start", recording_start);
  episode_dict.SetStringKey("recording_end", recording_end);
  episode_dict.SetStringKey("url_start", url_start);
  episode_dict.SetStringKey("url_end", url_end);
  episode_dict.SetIntKey("action_count", action_count);

  // Metadata
  base::Value metadata_dict(base::Value::Type::DICTIONARY);
  metadata_dict.SetStringKey("browser_version", metadata.browser_version);
  metadata_dict.SetStringKey("browser_build", metadata.browser_build);
  metadata_dict.SetIntKey("screen_width", metadata.screen_width);
  metadata_dict.SetIntKey("screen_height", metadata.screen_height);
  metadata_dict.SetStringKey("locale", metadata.locale);
  episode_dict.SetKey("metadata", std::move(metadata_dict));

  // Actions array
  base::Value actions_list(base::Value::Type::LIST);
  for (const auto& action : actions) {
    base::Value action_dict(base::Value::Type::DICTIONARY);
    action_dict.SetIntKey("index", action.index);
    action_dict.SetStringKey("type", ActionTypeToString(action.type));
    action_dict.SetStringKey("timestamp", action.timestamp);
    action_dict.SetStringKey("value", action.value);

    // Target (semantic + structural)
    base::Value target_dict(base::Value::Type::DICTIONARY);
    base::Value semantic_dict(base::Value::Type::DICTIONARY);
    semantic_dict.SetStringKey("type", SelectorTypeToString(action.target.semantic.type));
    semantic_dict.SetStringKey("value", action.target.semantic.value);
    target_dict.SetKey("semantic", std::move(semantic_dict));

    base::Value structural_dict(base::Value::Type::DICTIONARY);
    structural_dict.SetStringKey("type", SelectorTypeToString(action.target.structural.type));
    structural_dict.SetStringKey("value", action.target.structural.value);
    target_dict.SetKey("structural", std::move(structural_dict));
    action_dict.SetKey("target", std::move(target_dict));

    // Snapshots
    base::Value snap_before(base::Value::Type::DICTIONARY);
    snap_before.SetStringKey("type", action.snapshot_before.type);
    snap_before.SetStringKey("hash", action.snapshot_before.hash);
    snap_before.SetIntKey("content_length", action.snapshot_before.content_length);
    snap_before.SetStringKey("root_tag", action.snapshot_before.root_tag);
    action_dict.SetKey("snapshot_before", std::move(snap_before));

    base::Value snap_after(base::Value::Type::DICTIONARY);
    snap_after.SetStringKey("type", action.snapshot_after.type);
    snap_after.SetStringKey("hash", action.snapshot_after.hash);
    snap_after.SetIntKey("content_length", action.snapshot_after.content_length);
    snap_after.SetStringKey("root_tag", action.snapshot_after.root_tag);
    action_dict.SetKey("snapshot_after", std::move(snap_after));

    actions_list.Append(std::move(action_dict));
  }
  episode_dict.SetKey("actions", std::move(actions_list));

  std::string json_str;
  base::JSONWriter::WriteWithOptions(
      episode_dict,
      base::JSONWriter::OPTIONS_PRETTY_PRINT,
      &json_str);
  return json_str;
}

Episode Episode::FromJSON(const std::string& json_str) {
  // In real implementation, parse JSON and reconstruct episode
  // For now, placeholder
  Episode episode;
  episode.episode_id = "ep_placeholder";
  return episode;
}

std::string ActionTypeToString(ActionType type) {
  switch (type) {
    case ActionType::NAVIGATE: return "NAVIGATE";
    case ActionType::CLICK: return "CLICK";
    case ActionType::TYPE: return "TYPE";
    case ActionType::SELECT: return "SELECT";
    case ActionType::SUBMIT: return "SUBMIT";
  }
  return "UNKNOWN";
}

std::string SelectorTypeToString(SelectorType type) {
  switch (type) {
    case SelectorType::ARIA_LABEL: return "ARIA_LABEL";
    case SelectorType::ARIA_DESCRIBEDBY: return "ARIA_DESCRIBEDBY";
    case SelectorType::DATA_TESTID: return "DATA_TESTID";
    case SelectorType::DATA_QA: return "DATA_QA";
    case SelectorType::PLACEHOLDER: return "PLACEHOLDER";
    case SelectorType::ALT_TEXT: return "ALT_TEXT";
    case SelectorType::CSS_SELECTOR: return "CSS_SELECTOR";
    case SelectorType::XPATH: return "XPATH";
    case SelectorType::TAG_POSITION: return "TAG_POSITION";
    case SelectorType::URL: return "URL";
  }
  return "UNKNOWN";
}

}  // namespace recording
}  // namespace solace
