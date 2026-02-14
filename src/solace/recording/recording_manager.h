// Solace Browser - Recording Manager
// Auth: 65537 | Phase 2: Episode Recording
//
// Manages the lifecycle of episode recording:
// - Start/stop recording sessions
// - Record individual actions (navigate, click, type, select, submit)
// - Capture DOM snapshots at key steps
// - Serialize completed episodes to Phase B JSON format
// - Save episodes to ~/.solace/browser/episodes/

#ifndef SOLACE_RECORDING_RECORDING_MANAGER_H_
#define SOLACE_RECORDING_RECORDING_MANAGER_H_

#include <functional>
#include <memory>
#include <string>

#include "action_types.h"

namespace solace {
namespace recording {

class EpisodeSerializer;

// Callback for snapshot requests (renderer provides DOM state)
using SnapshotCallback = std::function<Snapshot()>;

class RecordingManager {
 public:
  RecordingManager();
  ~RecordingManager();

  // Lifecycle
  void StartRecording(const std::string& initial_url,
                      const Viewport& viewport);
  void StopRecording();
  bool IsRecording() const;

  // Action recording
  void RecordNavigate(const std::string& url);
  void RecordClick(const ElementReference& target);
  void RecordType(const ElementReference& target, const std::string& text);
  void RecordSelect(const ElementReference& target, const std::string& value);
  void RecordSubmit(const ElementReference& target);

  // Snapshot capture
  void AttachSnapshot(int step, const Snapshot& snapshot);

  // Episode access
  const Episode& GetCurrentEpisode() const;
  int GetActionCount() const;

  // Persistence
  bool SaveEpisode(const std::string& path);
  bool SaveEpisodeToDefault();

  // Configuration
  void SetSnapshotCallback(SnapshotCallback callback);
  void SetAutoSnapshot(bool enabled);

 private:
  std::string GenerateSessionId() const;
  std::string GetCurrentTimestamp() const;
  std::string GetDefaultEpisodePath() const;
  void RecordAction(ActionType type, const Action& action);

  Episode episode_;
  bool recording_;
  bool auto_snapshot_;
  SnapshotCallback snapshot_callback_;
  std::unique_ptr<EpisodeSerializer> serializer_;
};

}  // namespace recording
}  // namespace solace

#endif  // SOLACE_RECORDING_RECORDING_MANAGER_H_
