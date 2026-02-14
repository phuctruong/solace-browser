// Solace Browser - Episode Serializer Implementation
// Auth: 65537 | Phase 2: Episode Recording
//
// Produces deterministic Phase B JSON output with sorted keys.

#include "episode_serializer.h"

#include <algorithm>
#include <iomanip>
#include <map>
#include <sstream>
#include <vector>

// For SHA-256 - when building within Chromium, use boringssl.
// For standalone builds, use a lightweight sha256 implementation.
#ifdef SOLACE_USE_BORINGSSL
#include <openssl/sha.h>
#else
// Minimal SHA-256 for standalone builds
#include <cstdint>
#include <cstring>

namespace {

// SHA-256 constants
static const uint32_t k[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};

inline uint32_t rotr(uint32_t x, uint32_t n) {
  return (x >> n) | (x << (32 - n));
}

void sha256_transform(uint32_t state[8], const uint8_t block[64]) {
  uint32_t w[64];
  for (int i = 0; i < 16; i++) {
    w[i] = (uint32_t(block[i * 4]) << 24) |
           (uint32_t(block[i * 4 + 1]) << 16) |
           (uint32_t(block[i * 4 + 2]) << 8) |
           uint32_t(block[i * 4 + 3]);
  }
  for (int i = 16; i < 64; i++) {
    uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
    uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
    w[i] = w[i - 16] + s0 + w[i - 7] + s1;
  }

  uint32_t a = state[0], b = state[1], c = state[2], d = state[3];
  uint32_t e = state[4], f = state[5], g = state[6], h = state[7];

  for (int i = 0; i < 64; i++) {
    uint32_t S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
    uint32_t ch = (e & f) ^ (~e & g);
    uint32_t temp1 = h + S1 + ch + k[i] + w[i];
    uint32_t S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
    uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
    uint32_t temp2 = S0 + maj;

    h = g; g = f; f = e; e = d + temp1;
    d = c; c = b; b = a; a = temp1 + temp2;
  }

  state[0] += a; state[1] += b; state[2] += c; state[3] += d;
  state[4] += e; state[5] += f; state[6] += g; state[7] += h;
}

std::string sha256_hex(const std::string& input) {
  uint32_t state[8] = {
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
      0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};

  const uint8_t* data = reinterpret_cast<const uint8_t*>(input.data());
  size_t len = input.size();
  size_t processed = 0;

  // Process full blocks
  while (processed + 64 <= len) {
    sha256_transform(state, data + processed);
    processed += 64;
  }

  // Pad and process final block(s)
  uint8_t block[128];
  std::memset(block, 0, 128);
  size_t remaining = len - processed;
  std::memcpy(block, data + processed, remaining);
  block[remaining] = 0x80;

  size_t pad_len = (remaining < 56) ? 64 : 128;
  uint64_t bit_len = uint64_t(len) * 8;
  for (int i = 0; i < 8; i++) {
    block[pad_len - 1 - i] = uint8_t(bit_len >> (i * 8));
  }

  sha256_transform(state, block);
  if (pad_len == 128) {
    sha256_transform(state, block + 64);
  }

  // Convert to hex string
  std::ostringstream oss;
  for (int i = 0; i < 8; i++) {
    oss << std::hex << std::setfill('0') << std::setw(8) << state[i];
  }
  return oss.str();
}

}  // namespace
#endif  // SOLACE_USE_BORINGSSL

namespace solace {
namespace recording {

EpisodeSerializer::EpisodeSerializer() = default;
EpisodeSerializer::~EpisodeSerializer() = default;

std::string EpisodeSerializer::SerializeEpisode(const Episode& episode) {
  std::ostringstream out;

  // Phase B episode JSON with sorted keys (deterministic)
  out << "{\n";
  out << "  \"action_count\": " << episode.action_count << ",\n";

  // Actions array
  out << "  \"actions\": [\n";
  for (size_t i = 0; i < episode.actions.size(); i++) {
    out << "    " << SerializeAction(episode.actions[i]);
    if (i + 1 < episode.actions.size()) out << ",";
    out << "\n";
  }
  out << "  ],\n";

  out << "  \"domain\": " << EscapeJson(episode.domain) << ",\n";
  out << "  \"end_time\": " << EscapeJson(episode.end_time) << ",\n";
  out << "  \"session_id\": " << EscapeJson(episode.session_id) << ",\n";

  // Snapshots (sorted by step)
  out << "  \"snapshots\": {\n";
  std::map<int, Snapshot> sorted_snaps(episode.snapshots.begin(),
                                        episode.snapshots.end());
  size_t snap_idx = 0;
  for (const auto& [step, snapshot] : sorted_snaps) {
    out << "    \"" << step << "\": " << SerializeSnapshot(snapshot);
    if (++snap_idx < sorted_snaps.size()) out << ",";
    out << "\n";
  }
  out << "  },\n";

  out << "  \"start_time\": " << EscapeJson(episode.start_time) << ",\n";
  out << "  \"version\": " << EscapeJson(episode.version) << "\n";
  out << "}";

  return out.str();
}

std::string EpisodeSerializer::SerializeAction(const Action& action) {
  std::ostringstream out;
  out << "{";

  // Sorted keys: data, step, timestamp, type
  out << "\"data\": {";
  switch (action.type) {
    case ActionType::NAVIGATE:
      out << "\"url\": " << EscapeJson(action.url);
      break;

    case ActionType::CLICK:
      if (!action.target.reference.empty()) {
        out << "\"reference\": " << EscapeJson(action.target.reference) << ", ";
      }
      out << "\"selector\": " << EscapeJson(action.target.selector);
      break;

    case ActionType::TYPE:
      if (!action.target.reference.empty()) {
        out << "\"reference\": " << EscapeJson(action.target.reference) << ", ";
      }
      out << "\"selector\": " << EscapeJson(action.target.selector)
          << ", \"text\": " << EscapeJson(action.text);
      break;

    case ActionType::SELECT:
      if (!action.target.reference.empty()) {
        out << "\"reference\": " << EscapeJson(action.target.reference) << ", ";
      }
      out << "\"selector\": " << EscapeJson(action.target.selector)
          << ", \"value\": " << EscapeJson(action.value);
      break;

    case ActionType::SUBMIT:
      if (!action.target.reference.empty()) {
        out << "\"reference\": " << EscapeJson(action.target.reference) << ", ";
      }
      out << "\"selector\": " << EscapeJson(action.target.selector);
      break;

    case ActionType::SNAPSHOT:
      // No additional data for snapshot actions
      break;
  }
  out << "}, ";

  out << "\"step\": " << action.step << ", ";
  out << "\"timestamp\": " << EscapeJson(action.timestamp) << ", ";
  out << "\"type\": " << EscapeJson(ActionTypeToString(action.type));
  out << "}";

  return out.str();
}

std::string EpisodeSerializer::SerializeDomNode(const DomNode& node,
                                                 int depth) {
  std::ostringstream out;
  std::string ind = Indent(depth);
  std::string ind2 = Indent(depth + 1);

  out << "{\n";

  // Sorted keys: attrs, children, tag, text
  // Attrs (sorted by key)
  out << ind2 << "\"attrs\": {";
  std::map<std::string, std::string> sorted_attrs(node.attrs.begin(),
                                                    node.attrs.end());
  size_t attr_idx = 0;
  for (const auto& [key, val] : sorted_attrs) {
    out << EscapeJson(key) << ": " << EscapeJson(val);
    if (++attr_idx < sorted_attrs.size()) out << ", ";
  }
  out << "},\n";

  // Children
  out << ind2 << "\"children\": [";
  if (!node.children.empty()) {
    out << "\n";
    for (size_t i = 0; i < node.children.size(); i++) {
      out << Indent(depth + 2)
          << SerializeDomNode(node.children[i], depth + 2);
      if (i + 1 < node.children.size()) out << ",";
      out << "\n";
    }
    out << ind2;
  }
  out << "],\n";

  out << ind2 << "\"tag\": " << EscapeJson(node.tag) << ",\n";
  out << ind2 << "\"text\": " << EscapeJson(node.text) << "\n";

  out << ind << "}";

  return out.str();
}

std::string EpisodeSerializer::SerializeSnapshot(const Snapshot& snapshot) {
  std::ostringstream out;

  out << "{";
  out << "\"dom\": " << SerializeDomNode(snapshot.dom) << ", ";
  out << "\"meta\": {";
  out << "\"url\": " << EscapeJson(snapshot.url) << ", ";
  out << "\"viewport\": {\"h\": " << snapshot.viewport.height
      << ", \"w\": " << snapshot.viewport.width << "}";
  out << "}, ";
  out << "\"v\": " << snapshot.version;
  out << "}";

  return out.str();
}

std::string EpisodeSerializer::ComputeSHA256(const std::string& input) {
#ifdef SOLACE_USE_BORINGSSL
  uint8_t hash[SHA256_DIGEST_LENGTH];
  SHA256(reinterpret_cast<const uint8_t*>(input.data()), input.size(), hash);
  std::ostringstream oss;
  for (int i = 0; i < SHA256_DIGEST_LENGTH; i++) {
    oss << std::hex << std::setfill('0') << std::setw(2) << int(hash[i]);
  }
  return oss.str();
#else
  return sha256_hex(input);
#endif
}

// Static helpers

std::string EpisodeSerializer::EscapeJson(const std::string& s) {
  std::ostringstream out;
  out << '"';
  for (char c : s) {
    switch (c) {
      case '"':  out << "\\\""; break;
      case '\\': out << "\\\\"; break;
      case '\b': out << "\\b";  break;
      case '\f': out << "\\f";  break;
      case '\n': out << "\\n";  break;
      case '\r': out << "\\r";  break;
      case '\t': out << "\\t";  break;
      default:
        if (static_cast<unsigned char>(c) < 0x20) {
          out << "\\u" << std::hex << std::setfill('0') << std::setw(4)
              << static_cast<int>(c);
        } else {
          out << c;
        }
    }
  }
  out << '"';
  return out.str();
}

std::string EpisodeSerializer::Indent(int depth) {
  return std::string(depth * 2, ' ');
}

}  // namespace recording
}  // namespace solace
