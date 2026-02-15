/**
 * Solace Browser Phase 5: Proof Generation
 *
 * Generates cryptographic proof artifacts for browser episodes and recipes.
 * Each proof provides a verifiable chain linking:
 *   episode -> snapshot hashes -> recipe -> chain hash
 *
 * Proof Artifacts:
 *   1. episode_sha256  - Hash of canonicalized episode JSON
 *   2. recipe_sha256   - Hash of compiled recipe (Phase B2)
 *   3. action_count    - Number of actions (integrity check)
 *   4. chain_hash      - Hash of prev_proof + current artifacts (chain)
 *   5. timestamp       - Proof generation time (ISO 8601)
 *   6. auth_signature  - Signed with auth:65537 (optional)
 *
 * RTC Verification:
 *   encode(decode(episode)) == episode (roundtrip canonicalization)
 *   Deterministic hashing: same input -> identical output
 *
 * Auth: 65537 | Northstar: Phuc Forecast
 * Version: 1.0.0
 */

// Proof format version
const PROOF_VERSION = "1.0.0";

// Auth constant (F4 Fermat Prime)
const AUTH_65537 = 65537;

// Required fields for a valid episode
const REQUIRED_EPISODE_FIELDS = ["session_id", "domain", "actions"];

// Required fields for a valid proof
const REQUIRED_PROOF_FIELDS = [
  "version",
  "proof_id",
  "episode_sha256",
  "recipe_sha256",
  "action_count",
  "chain_hash",
  "timestamp",
  "snapshot_hashes",
];

// ===== Canonical JSON =====

/**
 * Produce canonical JSON bytes for deterministic hashing.
 * Keys sorted alphabetically, minimal whitespace, UTF-8 encoded.
 *
 * @param {any} obj - Object to canonicalize
 * @returns {string} Canonical JSON string
 */
function canonicalJSON(obj) {
  if (obj === null || obj === undefined) {
    return "null";
  }

  if (typeof obj === "boolean") {
    return obj ? "true" : "false";
  }

  if (typeof obj === "number") {
    if (!isFinite(obj)) return "null";
    return String(obj);
  }

  if (typeof obj === "string") {
    return JSON.stringify(obj);
  }

  if (Array.isArray(obj)) {
    const items = obj.map((item) => canonicalJSON(item));
    return "[" + items.join(",") + "]";
  }

  if (typeof obj === "object") {
    const keys = Object.keys(obj).sort();
    const pairs = keys.map((k) => JSON.stringify(k) + ":" + canonicalJSON(obj[k]));
    return "{" + pairs.join(",") + "}";
  }

  return String(obj);
}

/**
 * Produce canonical JSON bytes with trailing newline.
 *
 * @param {any} obj - Object to canonicalize
 * @returns {Uint8Array} UTF-8 encoded canonical JSON bytes
 */
function canonicalJSONBytes(obj) {
  const str = canonicalJSON(obj) + "\n";
  return new TextEncoder().encode(str);
}

// ===== SHA-256 Hashing =====

/**
 * Compute SHA-256 hex digest of a string.
 * Uses Web Crypto API when available, falls back to pure JS.
 *
 * @param {string} input - Input string
 * @returns {string} Hex SHA-256 digest
 */
function sha256Hex(input) {
  const bytes = new TextEncoder().encode(input);
  return sha256HexFromBytes(bytes);
}

/**
 * Compute SHA-256 hex digest of bytes.
 * Pure JavaScript implementation for browser extension compatibility.
 *
 * @param {Uint8Array} bytes - Input bytes
 * @returns {string} Hex SHA-256 digest
 */
function sha256HexFromBytes(bytes) {
  // SHA-256 constants
  const K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
    0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
    0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ];

  function rightRotate(value, amount) {
    return (value >>> amount) | (value << (32 - amount));
  }

  // Pre-processing: pad message
  const msgLen = bytes.length;
  const bitLen = msgLen * 8;
  const paddedLen = Math.ceil((msgLen + 9) / 64) * 64;
  const padded = new Uint8Array(paddedLen);
  padded.set(bytes);
  padded[msgLen] = 0x80;

  // Append length as 64-bit big-endian
  const view = new DataView(padded.buffer);
  view.setUint32(paddedLen - 4, bitLen, false);

  // Initial hash values
  let h0 = 0x6a09e667;
  let h1 = 0xbb67ae85;
  let h2 = 0x3c6ef372;
  let h3 = 0xa54ff53a;
  let h4 = 0x510e527f;
  let h5 = 0x9b05688c;
  let h6 = 0x1f83d9ab;
  let h7 = 0x5be0cd19;

  // Process each 512-bit block
  for (let offset = 0; offset < paddedLen; offset += 64) {
    const w = new Int32Array(64);

    for (let i = 0; i < 16; i++) {
      w[i] = view.getInt32(offset + i * 4, false);
    }

    for (let i = 16; i < 64; i++) {
      const s0 = rightRotate(w[i - 15], 7) ^ rightRotate(w[i - 15], 18) ^ (w[i - 15] >>> 3);
      const s1 = rightRotate(w[i - 2], 17) ^ rightRotate(w[i - 2], 19) ^ (w[i - 2] >>> 10);
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
    }

    let a = h0, b = h1, c = h2, d = h3;
    let e = h4, f = h5, g = h6, h = h7;

    for (let i = 0; i < 64; i++) {
      const S1 = rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25);
      const ch = (e & f) ^ (~e & g);
      const temp1 = (h + S1 + ch + K[i] + w[i]) | 0;
      const S0 = rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const temp2 = (S0 + maj) | 0;

      h = g;
      g = f;
      f = e;
      e = (d + temp1) | 0;
      d = c;
      c = b;
      b = a;
      a = (temp1 + temp2) | 0;
    }

    h0 = (h0 + a) | 0;
    h1 = (h1 + b) | 0;
    h2 = (h2 + c) | 0;
    h3 = (h3 + d) | 0;
    h4 = (h4 + e) | 0;
    h5 = (h5 + f) | 0;
    h6 = (h6 + g) | 0;
    h7 = (h7 + h) | 0;
  }

  function toHex(n) {
    return ("00000000" + (n >>> 0).toString(16)).slice(-8);
  }

  return toHex(h0) + toHex(h1) + toHex(h2) + toHex(h3) +
         toHex(h4) + toHex(h5) + toHex(h6) + toHex(h7);
}

// ===== Proof Generator =====

class ProofGenerator {
  /**
   * Create a new ProofGenerator.
   *
   * @param {Object} options - Configuration
   * @param {string} options.auth - Auth code (default: "65537")
   * @param {string} options.prev_proof_hash - Previous proof hash for chaining
   */
  constructor(options = {}) {
    this.auth = options.auth || String(AUTH_65537);
    this.prev_proof_hash = options.prev_proof_hash || "";
    this._proof_count = 0;
  }

  /**
   * Canonicalize an episode for deterministic hashing.
   * Removes volatile fields (timestamps on actions), sorts keys.
   *
   * @param {Object} episode - Raw episode object
   * @returns {Object} Canonicalized episode (deep copy, sorted, cleaned)
   */
  canonicalizeEpisode(episode) {
    if (!episode || typeof episode !== "object") {
      throw new Error("Episode must be a non-null object");
    }

    // Deep copy to avoid mutation
    const copy = JSON.parse(JSON.stringify(episode));

    // Remove top-level volatile fields
    delete copy.timestamp;
    delete copy.captured_at;
    delete copy.nonce;
    delete copy.render_timestamp;

    // Normalize action timestamps to step index only
    if (Array.isArray(copy.actions)) {
      copy.actions = copy.actions.map((action, idx) => {
        const cleaned = { ...action };
        // Keep type, data, step - remove volatile timestamp
        delete cleaned.timestamp;
        if (cleaned.step === undefined) {
          cleaned.step = idx;
        }
        return cleaned;
      });
    }

    return copy;
  }

  /**
   * Compute SHA-256 of a canonicalized episode.
   *
   * @param {Object} episode - Episode object
   * @returns {string} Hex SHA-256 digest of canonical episode JSON
   */
  hashEpisode(episode) {
    const canonical = this.canonicalizeEpisode(episode);
    const jsonStr = canonicalJSON(canonical);
    return sha256Hex(jsonStr);
  }

  /**
   * Compute SHA-256 of a compiled recipe.
   * Excludes the 'proof' field to avoid circular dependency.
   *
   * @param {Object} recipe - Recipe IR object
   * @returns {string} Hex SHA-256 digest of canonical recipe JSON
   */
  hashRecipe(recipe) {
    if (!recipe || typeof recipe !== "object") {
      throw new Error("Recipe must be a non-null object");
    }

    // Exclude proof field to avoid circular hash
    const copy = {};
    for (const key of Object.keys(recipe)) {
      if (key !== "proof") {
        copy[key] = recipe[key];
      }
    }

    const jsonStr = canonicalJSON(copy);
    return sha256Hex(jsonStr);
  }

  /**
   * Extract ordered snapshot hashes from a recipe.
   *
   * @param {Object} recipe - Recipe IR with snapshots field
   * @returns {string[]} Ordered list of snapshot SHA-256 hashes
   */
  extractSnapshotHashes(recipe) {
    const snapshots = recipe.snapshots || {};
    const keys = Object.keys(snapshots).sort((a, b) => {
      const na = parseInt(a, 10);
      const nb = parseInt(b, 10);
      if (!isNaN(na) && !isNaN(nb)) return na - nb;
      return a.localeCompare(b);
    });

    return keys
      .map((k) => {
        const snap = snapshots[k];
        if (snap && typeof snap === "object" && snap.sha256) {
          return snap.sha256;
        }
        return "";
      })
      .filter((h) => h.length > 0);
  }

  /**
   * Compute the chain hash linking previous proof to current artifacts.
   *
   * chain_hash = SHA-256(prev_proof_hash + episode_sha256 + recipe_sha256 + snapshot_hashes_joined)
   *
   * @param {string} episodeHash - SHA-256 of episode
   * @param {string} recipeHash - SHA-256 of recipe
   * @param {string[]} snapshotHashes - Ordered snapshot hashes
   * @returns {string} Chain hash hex digest
   */
  computeChainHash(episodeHash, recipeHash, snapshotHashes) {
    const prev = this.prev_proof_hash || "0".repeat(64);
    const snapshotConcat = snapshotHashes.join("");
    const input = prev + episodeHash + recipeHash + snapshotConcat;
    return sha256Hex(input);
  }

  /**
   * Generate an auth signature for the proof.
   * Uses HMAC-like construction: SHA-256(auth + ":" + chain_hash)
   *
   * @param {string} chainHash - Chain hash to sign
   * @returns {string} Auth signature hex digest
   */
  signProof(chainHash) {
    const input = this.auth + ":" + chainHash;
    return sha256Hex(input);
  }

  /**
   * Generate a unique proof ID from episode and sequence.
   *
   * @param {string} episodeHash - Episode SHA-256
   * @param {number} seq - Proof sequence number
   * @returns {string} Proof ID string
   */
  generateProofId(episodeHash, seq) {
    const input = `proof:${episodeHash}:${seq}`;
    const hash = sha256Hex(input);
    return "proof_" + hash.substring(0, 16);
  }

  /**
   * Generate a complete proof artifact for an episode and its compiled recipe.
   *
   * @param {Object} episode - Raw episode object
   * @param {Object} recipe - Compiled recipe IR from Phase B2
   * @returns {Object} Complete proof artifact
   */
  generateProof(episode, recipe) {
    // Validate inputs
    if (!episode || typeof episode !== "object") {
      throw new Error("Episode must be a non-null object");
    }
    if (!recipe || typeof recipe !== "object") {
      throw new Error("Recipe must be a non-null object");
    }

    // Validate required episode fields
    for (const field of REQUIRED_EPISODE_FIELDS) {
      if (!(field in episode)) {
        throw new Error(`Episode missing required field: ${field}`);
      }
    }

    if (!Array.isArray(episode.actions) || episode.actions.length === 0) {
      throw new Error("Episode must have at least one action");
    }

    // Compute hashes
    const episodeHash = this.hashEpisode(episode);
    const recipeHash = this.hashRecipe(recipe);
    const snapshotHashes = this.extractSnapshotHashes(recipe);
    const actionCount = (episode.actions || []).length;

    // Compute chain hash
    const chainHash = this.computeChainHash(episodeHash, recipeHash, snapshotHashes);

    // Generate proof ID
    this._proof_count++;
    const proofId = this.generateProofId(episodeHash, this._proof_count);

    // Build proof artifact
    const proof = {
      version: PROOF_VERSION,
      proof_id: proofId,
      episode_sha256: episodeHash,
      recipe_sha256: recipeHash,
      action_count: actionCount,
      chain_hash: chainHash,
      timestamp: new Date().toISOString(),
      snapshot_hashes: snapshotHashes,
      domain: episode.domain || "unknown",
      session_id: episode.session_id || "",
      prev_proof_hash: this.prev_proof_hash || null,
      auth_signature: this.signProof(chainHash),
    };

    // Update chain for next proof
    this.prev_proof_hash = sha256Hex(canonicalJSON(proof));

    return proof;
  }

  /**
   * Verify a proof artifact against its episode and recipe.
   *
   * Checks:
   *   1. Episode hash matches
   *   2. Recipe hash matches
   *   3. Action count matches
   *   4. Chain hash is correct
   *   5. Auth signature is valid
   *   6. Required fields present
   *
   * @param {Object} proof - Proof artifact to verify
   * @param {Object} episode - Original episode
   * @param {Object} recipe - Compiled recipe
   * @returns {Object} Verification result {valid: bool, errors: string[]}
   */
  verifyProof(proof, episode, recipe) {
    const errors = [];

    // Check required fields
    for (const field of REQUIRED_PROOF_FIELDS) {
      if (!(field in proof)) {
        errors.push(`Missing required field: ${field}`);
      }
    }

    if (errors.length > 0) {
      return { valid: false, errors };
    }

    // Check version
    if (proof.version !== PROOF_VERSION) {
      errors.push(`Version mismatch: expected ${PROOF_VERSION}, got ${proof.version}`);
    }

    // Check episode hash
    const expectedEpisodeHash = this.hashEpisode(episode);
    if (proof.episode_sha256 !== expectedEpisodeHash) {
      errors.push("Episode hash mismatch");
    }

    // Check recipe hash
    const expectedRecipeHash = this.hashRecipe(recipe);
    if (proof.recipe_sha256 !== expectedRecipeHash) {
      errors.push("Recipe hash mismatch");
    }

    // Check action count
    const expectedActionCount = (episode.actions || []).length;
    if (proof.action_count !== expectedActionCount) {
      errors.push(`Action count mismatch: expected ${expectedActionCount}, got ${proof.action_count}`);
    }

    // Check chain hash
    const snapshotHashes = proof.snapshot_hashes || [];
    const prevHash = proof.prev_proof_hash || "";

    // Temporarily set prev_proof_hash for chain verification
    const savedPrev = this.prev_proof_hash;
    this.prev_proof_hash = prevHash;
    const expectedChainHash = this.computeChainHash(
      proof.episode_sha256,
      proof.recipe_sha256,
      snapshotHashes
    );
    this.prev_proof_hash = savedPrev;

    if (proof.chain_hash !== expectedChainHash) {
      errors.push("Chain hash mismatch");
    }

    // Check auth signature
    const savedAuth = this.auth;
    const expectedSig = this.signProof(proof.chain_hash);
    this.auth = savedAuth;

    if (proof.auth_signature !== expectedSig) {
      errors.push("Auth signature mismatch");
    }

    return { valid: errors.length === 0, errors };
  }

  /**
   * Verify RTC (Roundtrip Canonicalization) for an episode.
   * encode(decode(episode)) must produce identical bytes.
   *
   * @param {Object} episode - Episode to verify RTC
   * @returns {Object} {rtc_valid: bool, hash1: string, hash2: string}
   */
  verifyRTC(episode) {
    // First pass: canonicalize and hash
    const hash1 = this.hashEpisode(episode);

    // Round-trip: serialize canonical form, parse, re-hash
    const canonical = this.canonicalizeEpisode(episode);
    const serialized = canonicalJSON(canonical);
    const parsed = JSON.parse(serialized);
    const recanonical = this.canonicalizeEpisode(parsed);
    const rehash = canonicalJSON(recanonical);
    const hash2 = sha256Hex(rehash);

    return {
      rtc_valid: hash1 === hash2,
      hash1,
      hash2,
    };
  }

  /**
   * Generate a proof chain for multiple episodes.
   * Each proof links to the previous via chain_hash.
   *
   * @param {Array<{episode: Object, recipe: Object}>} pairs - Episode/recipe pairs
   * @returns {Object[]} Array of proof artifacts
   */
  generateProofChain(pairs) {
    if (!Array.isArray(pairs) || pairs.length === 0) {
      throw new Error("Pairs must be a non-empty array");
    }

    const proofs = [];
    for (const pair of pairs) {
      const proof = this.generateProof(pair.episode, pair.recipe);
      proofs.push(proof);
    }
    return proofs;
  }

  /**
   * Verify an entire proof chain.
   * Checks each proof individually and verifies chain linkage.
   *
   * @param {Object[]} proofs - Array of proof artifacts
   * @param {Array<{episode: Object, recipe: Object}>} pairs - Corresponding episode/recipe pairs
   * @returns {Object} {valid: bool, errors: string[], verified_count: number}
   */
  verifyProofChain(proofs, pairs) {
    if (proofs.length !== pairs.length) {
      return {
        valid: false,
        errors: ["Proof count does not match pair count"],
        verified_count: 0,
      };
    }

    const errors = [];
    let verifiedCount = 0;

    // Save and reset prev_proof_hash for chain verification
    const savedPrev = this.prev_proof_hash;
    this.prev_proof_hash = "";

    for (let i = 0; i < proofs.length; i++) {
      const result = this.verifyProof(proofs[i], pairs[i].episode, pairs[i].recipe);
      if (result.valid) {
        verifiedCount++;
      } else {
        errors.push(`Proof ${i}: ${result.errors.join(", ")}`);
      }

      // Verify chain linkage
      if (i > 0) {
        const prevProofHash = sha256Hex(canonicalJSON(proofs[i - 1]));
        if (proofs[i].prev_proof_hash !== prevProofHash) {
          errors.push(`Proof ${i}: chain link broken (prev_proof_hash mismatch)`);
        }
      }

      // Update prev for next iteration
      this.prev_proof_hash = sha256Hex(canonicalJSON(proofs[i]));
    }

    // Restore state
    this.prev_proof_hash = savedPrev;

    return {
      valid: errors.length === 0,
      errors,
      verified_count: verifiedCount,
    };
  }
}

// ===== Static Validation =====

/**
 * Validate a proof artifact has correct structure.
 *
 * @param {Object} proof - Proof to validate
 * @returns {string[]} List of validation issues (empty = valid)
 */
function validateProofSchema(proof) {
  const issues = [];

  if (!proof || typeof proof !== "object") {
    issues.push("Proof must be a non-null object");
    return issues;
  }

  // Required fields
  for (const field of REQUIRED_PROOF_FIELDS) {
    if (!(field in proof)) {
      issues.push(`Missing required field: ${field}`);
    }
  }

  // Type checks
  if (typeof proof.version !== "string") {
    issues.push("version must be a string");
  }
  if (typeof proof.proof_id !== "string") {
    issues.push("proof_id must be a string");
  }
  if (typeof proof.episode_sha256 !== "string" || proof.episode_sha256.length !== 64) {
    issues.push("episode_sha256 must be a 64-char hex string");
  }
  if (typeof proof.recipe_sha256 !== "string" || proof.recipe_sha256.length !== 64) {
    issues.push("recipe_sha256 must be a 64-char hex string");
  }
  if (typeof proof.action_count !== "number" || !Number.isInteger(proof.action_count) || proof.action_count < 0) {
    issues.push("action_count must be a non-negative integer");
  }
  if (typeof proof.chain_hash !== "string" || proof.chain_hash.length !== 64) {
    issues.push("chain_hash must be a 64-char hex string");
  }
  if (typeof proof.timestamp !== "string") {
    issues.push("timestamp must be a string");
  }
  if (!Array.isArray(proof.snapshot_hashes)) {
    issues.push("snapshot_hashes must be an array");
  } else {
    for (let i = 0; i < proof.snapshot_hashes.length; i++) {
      const h = proof.snapshot_hashes[i];
      if (typeof h !== "string" || h.length !== 64) {
        issues.push(`snapshot_hashes[${i}] must be a 64-char hex string`);
      }
    }
  }

  // Proof ID format
  if (proof.proof_id && !proof.proof_id.startsWith("proof_")) {
    issues.push("proof_id must start with 'proof_'");
  }

  // Hex validation for hash fields
  const hexPattern = /^[0-9a-f]{64}$/;
  for (const field of ["episode_sha256", "recipe_sha256", "chain_hash"]) {
    if (typeof proof[field] === "string" && !hexPattern.test(proof[field])) {
      issues.push(`${field} must be lowercase hex`);
    }
  }

  return issues;
}

/**
 * Store a proof artifact to the artifacts directory.
 *
 * @param {Object} proof - Proof artifact
 * @param {string} episodeId - Episode identifier for filename
 * @returns {Object} {path: string, bytes: number}
 */
function serializeProof(proof) {
  const jsonStr = canonicalJSON(proof) + "\n";
  return {
    json: jsonStr,
    bytes: new TextEncoder().encode(jsonStr).length,
    sha256: sha256Hex(canonicalJSON(proof)),
  };
}

// Export for Node.js / test environments
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    ProofGenerator,
    canonicalJSON,
    canonicalJSONBytes,
    sha256Hex,
    sha256HexFromBytes,
    validateProofSchema,
    serializeProof,
    PROOF_VERSION,
    AUTH_65537,
    REQUIRED_EPISODE_FIELDS,
    REQUIRED_PROOF_FIELDS,
  };
}
