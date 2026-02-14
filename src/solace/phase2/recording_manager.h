// Copyright 2025 Solace Browser Authors. All rights reserved.
// Recording manager - browser process

#ifndef SOLACE_RECORDING_RECORDING_MANAGER_H_
#define SOLACE_RECORDING_RECORDING_MANAGER_H_

#include <string>
#include <memory>
#include "base/files/file_path.h"
#include "episode_schema.h"

namespace solace {
namespace recording {

// Manages episode recording lifecycle
class RecordingManager {
 public:
  RecordingManager();
  ~RecordingManager();

  // Start recording at given URL
  void StartRecording(const std::string& initial_url);

  // Stop recording and return episode
  Episode StopRecording();

  // Get current episode (read-only)
  const Episode& GetCurrentEpisode() const { return current_episode_; }

  // Check if currently recording
  bool IsRecording() const { return is_recording_; }

  // Save episode to file
  bool SaveEpisode(const Episode& episode,
                   const base::FilePath& file_path);

  // Get episode storage directory (~/.solace/browser/episodes/)
  base::FilePath GetEpisodeDirectory();

  // Add action to current episode (called from renderer process via IPC)
  void AddAction(const Action& action);

  // Update episode end URL (called when navigation completes)
  void UpdateEndURL(const std::string& url);

 private:
  Episode current_episode_;
  bool is_recording_ = false;
  int64_t action_count_ = 0;

  // Generate unique episode ID
  std::string GenerateEpisodeID();

  // Get current timestamp in ISO 8601 format
  std::string GetCurrentTimestamp();

  // Ensure storage directory exists
  bool EnsureStorageDirectory();
};

}  // namespace recording
}  // namespace solace

#endif  // SOLACE_RECORDING_RECORDING_MANAGER_H_
