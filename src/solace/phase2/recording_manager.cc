// Copyright 2025 Solace Browser Authors. All rights reserved.
// Recording manager implementation

#include "recording_manager.h"
#include "base/files/file_util.h"
#include "base/files/file_path.h"
#include "base/path_service.h"
#include "base/time/time.h"
#include "base/json/json_writer.h"

namespace solace {
namespace recording {

RecordingManager::RecordingManager() {}

RecordingManager::~RecordingManager() {}

void RecordingManager::StartRecording(const std::string& initial_url) {
  is_recording_ = true;
  action_count_ = 0;

  current_episode_.episode_id = GenerateEpisodeID();
  current_episode_.recording_start = GetCurrentTimestamp();
  current_episode_.url_start = initial_url;
  current_episode_.url_end = initial_url;
  current_episode_.action_count = 0;
  current_episode_.metadata.browser_version = "ungoogled-chromium-127.0.0";
  current_episode_.metadata.browser_build = "Solace-0.1.0";
  current_episode_.metadata.screen_width = 1920;
  current_episode_.metadata.screen_height = 1080;
  current_episode_.metadata.locale = "en-US";
  current_episode_.actions.clear();

  EnsureStorageDirectory();
}

Episode RecordingManager::StopRecording() {
  is_recording_ = false;
  current_episode_.recording_end = GetCurrentTimestamp();
  current_episode_.action_count = action_count_;

  // Save episode to disk
  base::FilePath episode_path = GetEpisodeDirectory().AppendASCII(
      current_episode_.episode_id + ".json");
  SaveEpisode(current_episode_, episode_path);

  return current_episode_;
}

bool RecordingManager::SaveEpisode(const Episode& episode,
                                   const base::FilePath& file_path) {
  std::string json_str = episode.ToJSON();

  // Write to file
  int bytes_written = base::WriteFile(file_path, json_str.c_str(), json_str.length());
  return bytes_written == static_cast<int>(json_str.length());
}

base::FilePath RecordingManager::GetEpisodeDirectory() {
  base::FilePath home_dir;
  base::PathService::Get(base::DIR_HOME, &home_dir);

  base::FilePath solace_dir = home_dir.AppendASCII(".solace");
  base::FilePath browser_dir = solace_dir.AppendASCII("browser");
  base::FilePath episodes_dir = browser_dir.AppendASCII("episodes");

  return episodes_dir;
}

void RecordingManager::AddAction(const Action& action) {
  if (!is_recording_) return;

  current_episode_.actions.push_back(action);
  action_count_++;
}

void RecordingManager::UpdateEndURL(const std::string& url) {
  if (is_recording_) {
    current_episode_.url_end = url;
  }
}

std::string RecordingManager::GenerateEpisodeID() {
  // Generate episode ID in format: ep_YYYYMMDD_NNN
  base::Time now = base::Time::Now();
  base::Time::Exploded exploded;
  now.LocalExplode(&exploded);

  char id_buffer[32];
  snprintf(id_buffer, sizeof(id_buffer), "ep_%04d%02d%02d_%03d",
           exploded.year, exploded.month, exploded.day_of_month,
           static_cast<int>(now.ToJsTime()) % 1000);

  return std::string(id_buffer);
}

std::string RecordingManager::GetCurrentTimestamp() {
  // Return ISO 8601 timestamp
  base::Time now = base::Time::Now();
  return now.ToStringWithoutLocalOffset() + "Z";
}

bool RecordingManager::EnsureStorageDirectory() {
  base::FilePath episodes_dir = GetEpisodeDirectory();
  return base::CreateDirectory(episodes_dir);
}

}  // namespace recording
}  // namespace solace
