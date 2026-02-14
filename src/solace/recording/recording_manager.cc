// Solace Browser - Recording Manager Implementation
// Auth: 65537 | Phase 2: Episode Recording

#include "recording_manager.h"
#include "episode_serializer.h"

#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <sstream>

namespace solace {
namespace recording {

RecordingManager::RecordingManager()
    : recording_(false),
      auto_snapshot_(false),
      serializer_(std::make_unique<EpisodeSerializer>()) {}

RecordingManager::~RecordingManager() {
  if (recording_) {
    StopRecording();
  }
}

void RecordingManager::StartRecording(const std::string& initial_url,
                                      const Viewport& viewport) {
  if (recording_) {
    StopRecording();
  }

  recording_ = true;
  episode_ = Episode{};
  episode_.version = "1.0.0";
  episode_.session_id = GenerateSessionId();
  episode_.start_time = GetCurrentTimestamp();
  episode_.action_count = 0;

  // Extract domain from URL
  size_t start = initial_url.find("://");
  if (start != std::string::npos) {
    start += 3;
    size_t end = initial_url.find('/', start);
    episode_.domain = initial_url.substr(start, end - start);
  } else {
    episode_.domain = "unknown";
  }

  // Record initial navigate action
  RecordNavigate(initial_url);
}

void RecordingManager::StopRecording() {
  if (!recording_) return;

  recording_ = false;
  episode_.end_time = GetCurrentTimestamp();
  episode_.action_count = static_cast<int>(episode_.actions.size());
}

bool RecordingManager::IsRecording() const {
  return recording_;
}

void RecordingManager::RecordNavigate(const std::string& url) {
  if (!recording_) return;

  Action action;
  action.step = static_cast<int>(episode_.actions.size());
  action.type = ActionType::NAVIGATE;
  action.timestamp = GetCurrentTimestamp();
  action.url = url;

  RecordAction(ActionType::NAVIGATE, action);
}

void RecordingManager::RecordClick(const ElementReference& target) {
  if (!recording_) return;

  Action action;
  action.step = static_cast<int>(episode_.actions.size());
  action.type = ActionType::CLICK;
  action.timestamp = GetCurrentTimestamp();
  action.target = target;

  RecordAction(ActionType::CLICK, action);
}

void RecordingManager::RecordType(const ElementReference& target,
                                  const std::string& text) {
  if (!recording_) return;

  Action action;
  action.step = static_cast<int>(episode_.actions.size());
  action.type = ActionType::TYPE;
  action.timestamp = GetCurrentTimestamp();
  action.target = target;
  action.text = text;

  RecordAction(ActionType::TYPE, action);
}

void RecordingManager::RecordSelect(const ElementReference& target,
                                    const std::string& value) {
  if (!recording_) return;

  Action action;
  action.step = static_cast<int>(episode_.actions.size());
  action.type = ActionType::SELECT;
  action.timestamp = GetCurrentTimestamp();
  action.target = target;
  action.value = value;

  RecordAction(ActionType::SELECT, action);
}

void RecordingManager::RecordSubmit(const ElementReference& target) {
  if (!recording_) return;

  Action action;
  action.step = static_cast<int>(episode_.actions.size());
  action.type = ActionType::SUBMIT;
  action.timestamp = GetCurrentTimestamp();
  action.target = target;

  RecordAction(ActionType::SUBMIT, action);
}

void RecordingManager::AttachSnapshot(int step, const Snapshot& snapshot) {
  episode_.snapshots[step] = snapshot;
}

const Episode& RecordingManager::GetCurrentEpisode() const {
  return episode_;
}

int RecordingManager::GetActionCount() const {
  return static_cast<int>(episode_.actions.size());
}

bool RecordingManager::SaveEpisode(const std::string& path) {
  if (recording_) {
    StopRecording();
  }

  std::string json = serializer_->SerializeEpisode(episode_);
  if (json.empty()) return false;

  // Create parent directories
  std::filesystem::path file_path(path);
  std::filesystem::create_directories(file_path.parent_path());

  // Write episode JSON
  std::ofstream out(path);
  if (!out.is_open()) return false;
  out << json;
  out.close();

  // Set file permissions to 600 (owner read/write only)
  std::filesystem::permissions(
      path,
      std::filesystem::perms::owner_read | std::filesystem::perms::owner_write,
      std::filesystem::perm_options::replace);

  return true;
}

bool RecordingManager::SaveEpisodeToDefault() {
  return SaveEpisode(GetDefaultEpisodePath());
}

void RecordingManager::SetSnapshotCallback(SnapshotCallback callback) {
  snapshot_callback_ = std::move(callback);
}

void RecordingManager::SetAutoSnapshot(bool enabled) {
  auto_snapshot_ = enabled;
}

// Private methods

std::string RecordingManager::GenerateSessionId() const {
  auto now = std::chrono::system_clock::now();
  auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                now.time_since_epoch())
                .count();
  std::ostringstream oss;
  oss << "session_" << ms;
  return oss.str();
}

std::string RecordingManager::GetCurrentTimestamp() const {
  auto now = std::chrono::system_clock::now();
  auto time_t = std::chrono::system_clock::to_time_t(now);
  auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                now.time_since_epoch()) %
            1000;

  std::ostringstream oss;
  oss << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%S");
  oss << "." << std::setfill('0') << std::setw(3) << ms.count() << "Z";
  return oss.str();
}

std::string RecordingManager::GetDefaultEpisodePath() const {
  const char* home = std::getenv("HOME");
  std::string base = home ? home : "/tmp";
  std::ostringstream oss;
  oss << base << "/.solace/browser/episodes/"
      << episode_.session_id << ".json";
  return oss.str();
}

void RecordingManager::RecordAction(ActionType type, const Action& action) {
  episode_.actions.push_back(action);

  // Auto-capture snapshot if enabled and callback is set
  if (auto_snapshot_ && snapshot_callback_) {
    Snapshot snap = snapshot_callback_();
    episode_.snapshots[action.step] = snap;
  }
}

}  // namespace recording
}  // namespace solace
