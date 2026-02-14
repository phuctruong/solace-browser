// Solace Browser - Episode Serializer
// Auth: 65537 | Phase 2: Episode Recording
//
// Serializes Episode objects to Phase B JSON format.
// Produces deterministic output (sorted keys, canonical whitespace).
// Computes SHA-256 hashes for episodes and snapshots.

#ifndef SOLACE_RECORDING_EPISODE_SERIALIZER_H_
#define SOLACE_RECORDING_EPISODE_SERIALIZER_H_

#include <string>

#include "action_types.h"

namespace solace {
namespace recording {

class EpisodeSerializer {
 public:
  EpisodeSerializer();
  ~EpisodeSerializer();

  // Serialize complete episode to Phase B JSON
  std::string SerializeEpisode(const Episode& episode);

  // Serialize individual action to JSON object string
  std::string SerializeAction(const Action& action);

  // Serialize DOM node to JSON (recursive)
  std::string SerializeDomNode(const DomNode& node, int depth = 0);

  // Serialize snapshot to Phase B JSON
  std::string SerializeSnapshot(const Snapshot& snapshot);

  // Compute SHA-256 hash of a string
  static std::string ComputeSHA256(const std::string& input);

 private:
  // JSON encoding helpers
  static std::string EscapeJson(const std::string& s);
  static std::string Indent(int depth);
};

}  // namespace recording
}  // namespace solace

#endif  // SOLACE_RECORDING_EPISODE_SERIALIZER_H_
