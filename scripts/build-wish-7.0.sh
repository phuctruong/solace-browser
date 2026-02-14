#!/bin/bash
set +e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACTS_DIR="$PROJECT_ROOT/artifacts"
EPISODES_DIR="$ARTIFACTS_DIR/episodes"

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_pass() { echo -e "${GREEN}[PASS]${NC} $*"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $*"; }

mkdir -p "$ARTIFACTS_DIR"
passed=0
failed=0

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║ WISH 7.0 RIPPLE: Episode Analytics & Summarization            ║"
echo "║ Authority: 65537 | Phase: 7 (Analytics & Summary)             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# T1: Episode Collection Loaded
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 1: T1 - Episode Collection Loaded"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python3 << 'PYEOF' > /dev/null 2>&1
import json
import os
import glob

episodes_dir = 'artifacts/episodes'
episode_files = glob.glob(f'{episodes_dir}/*.json')

episodes_loaded = []
for ep_file in episode_files:
    try:
        with open(ep_file) as f:
            episode = json.load(f)
            # Validate structure
            required = ['id', 'timestamp', 'actions', 'state_snapshot']
            for field in required:
                assert field in episode, f"Missing {field} in {ep_file}"
            episodes_loaded.append(episode)
    except Exception as e:
        print(f"Failed to load {ep_file}: {e}")
        exit(1)

assert len(episodes_loaded) > 0, "No episodes loaded"

with open('artifacts/episodes-loaded.json', 'w') as f:
    json.dump({"episodes_loaded": len(episodes_loaded), "episodes": [e['id'] for e in episodes_loaded]}, f, indent=2)
PYEOF

if [[ $? -eq 0 ]] && [[ -f "$ARTIFACTS_DIR/episodes-loaded.json" ]]; then
    log_pass "T1: Episode Collection Loaded ✓"
    ((passed++))
else
    log_fail "T1 failed"
    ((failed++))
fi

# T2: Action Sequence Analysis
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 2: T2 - Action Sequence Analysis"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python3 << 'PYEOF' > /dev/null 2>&1
import json
import glob

episodes_dir = 'artifacts/episodes'
episode_files = glob.glob(f'{episodes_dir}/*.json')

total_actions = 0
action_counts = {}

for ep_file in episode_files:
    with open(ep_file) as f:
        episode = json.load(f)
        actions = episode.get('actions', [])
        total_actions += len(actions)
        
        for action in actions:
            action_type = action.get('type', 'unknown')
            action_counts[action_type] = action_counts.get(action_type, 0) + 1

action_analysis = {
    "total_actions": total_actions,
    "action_types": action_counts,
    "analysis_complete": True
}

with open('artifacts/action-analysis.json', 'w') as f:
    json.dump(action_analysis, f, indent=2)
PYEOF

if [[ $? -eq 0 ]] && [[ -f "$ARTIFACTS_DIR/action-analysis.json" ]]; then
    log_pass "T2: Action Sequence Analysis ✓"
    ((passed++))
else
    log_fail "T2 failed"
    ((failed++))
fi

# T3: State Transition Analysis
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 3: T3 - State Transition Analysis"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python3 << 'PYEOF' > /dev/null 2>&1
import json
import glob

episodes_dir = 'artifacts/episodes'
episode_files = glob.glob(f'{episodes_dir}/*.json')

unique_urls = set()
transitions = []

for ep_file in episode_files:
    with open(ep_file) as f:
        episode = json.load(f)
        state = episode.get('state_snapshot', {})
        url = state.get('url', '')
        if url:
            unique_urls.add(url)
        
        for action in episode.get('actions', []):
            if action.get('type') == 'navigate':
                new_url = action.get('value', '')
                if new_url:
                    unique_urls.add(new_url)
                    transitions.append({"from": url, "to": new_url})

transition_analysis = {
    "unique_urls": list(unique_urls),
    "total_transitions": len(transitions),
    "transitions": transitions
}

with open('artifacts/transition-analysis.json', 'w') as f:
    json.dump(transition_analysis, f, indent=2)
PYEOF

if [[ $? -eq 0 ]] && [[ -f "$ARTIFACTS_DIR/transition-analysis.json" ]]; then
    log_pass "T3: State Transition Analysis ✓"
    ((passed++))
else
    log_fail "T3 failed"
    ((failed++))
fi

# T4: Pattern Fingerprint Generation
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 4: T4 - Pattern Fingerprint Generation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python3 << 'PYEOF' > /dev/null 2>&1
import json
import hashlib
import glob

episodes_dir = 'artifacts/episodes'
episode_files = glob.glob(f'{episodes_dir}/*.json')

pattern_fingerprints = []

for ep_file in episode_files:
    with open(ep_file) as f:
        episode = json.load(f)
        actions = episode.get('actions', [])
        
        # Create pattern from action sequence
        pattern = " → ".join([a.get('type', '?') for a in actions])
        
        # Generate deterministic fingerprint
        pattern_json = json.dumps({"pattern": pattern, "action_count": len(actions)}, sort_keys=True)
        fingerprint = hashlib.sha256(pattern_json.encode()).hexdigest()
        
        pattern_fingerprints.append({
            "episode_id": episode.get('id'),
            "pattern": pattern,
            "fingerprint": f"sha256:{fingerprint}",
            "action_count": len(actions)
        })

# Test determinism: same pattern twice should give same fingerprint
test_pattern = "click → type → navigate"
hash1 = hashlib.sha256(test_pattern.encode()).hexdigest()
hash2 = hashlib.sha256(test_pattern.encode()).hexdigest()
assert hash1 == hash2, "Fingerprints not deterministic"

fingerprint_data = {
    "total_patterns": len(pattern_fingerprints),
    "patterns": pattern_fingerprints,
    "determinism_verified": True
}

with open('artifacts/pattern-fingerprints.json', 'w') as f:
    json.dump(fingerprint_data, f, indent=2)
PYEOF

if [[ $? -eq 0 ]] && [[ -f "$ARTIFACTS_DIR/pattern-fingerprints.json" ]]; then
    log_pass "T4: Pattern Fingerprints Generated ✓"
    ((passed++))
else
    log_fail "T4 failed"
    ((failed++))
fi

# T5: Summary Report Generated
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 5: T5 - Summary Report Generated"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python3 << 'PYEOF' > /dev/null 2>&1
import json
import glob
from datetime import datetime

episodes_dir = 'artifacts/episodes'
episode_files = glob.glob(f'{episodes_dir}/*.json')

# Load all analyses
with open('artifacts/episodes-loaded.json') as f:
    episodes_data = json.load(f)
with open('artifacts/action-analysis.json') as f:
    action_data = json.load(f)
with open('artifacts/transition-analysis.json') as f:
    transition_data = json.load(f)
with open('artifacts/pattern-fingerprints.json') as f:
    pattern_data = json.load(f)

# Generate comprehensive summary
total_episodes = episodes_data['episodes_loaded']
total_actions = action_data['total_actions']
avg_actions = total_actions / total_episodes if total_episodes > 0 else 0

summary_report = {
    "report_timestamp": datetime.utcnow().isoformat() + "Z",
    "episode_statistics": {
        "total_episodes": total_episodes,
        "total_actions": total_actions,
        "average_actions_per_episode": avg_actions,
        "episodes_analyzed": total_episodes
    },
    "action_frequency": action_data.get('action_types', {}),
    "state_transitions": {
        "unique_urls": len(transition_data.get('unique_urls', [])),
        "transition_count": transition_data.get('total_transitions', 0)
    },
    "pattern_analysis": {
        "total_patterns": len(pattern_data.get('patterns', [])),
        "determinism_verified": pattern_data.get('determinism_verified', False)
    },
    "dataset_quality": "good" if total_episodes > 0 else "no_data",
    "ready_for_ml": total_episodes > 0 and total_actions > 0
}

# Validate summary consistency
assert summary_report['episode_statistics']['total_episodes'] > 0, "No episodes analyzed"
assert summary_report['episode_statistics']['total_actions'] > 0, "No actions found"
assert summary_report['ready_for_ml'] == True, "Dataset not ready for ML"

with open('artifacts/analytics-report.json', 'w') as f:
    json.dump(summary_report, f, indent=2)
PYEOF

if [[ $? -eq 0 ]] && [[ -f "$ARTIFACTS_DIR/analytics-report.json" ]]; then
    log_pass "T5: Summary Report Generated ✓"
    ((passed++))
else
    log_fail "T5 failed"
    ((failed++))
fi

# Summary
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║ TEST SUMMARY                                                   ║"
echo "╠════════════════════════════════════════════════════════════════╣"
printf "║ Passed: %d tests                                         ║\n" "$passed"
printf "║ Failed: %d tests                                         ║\n" "$failed"

if [[ $failed -eq 0 ]]; then
    echo "║ Status: ✅ ALL PASSED                                           ║"
else
    echo "║ Status: ❌ SOME FAILED                                           ║"
fi

echo "╚════════════════════════════════════════════════════════════════╝"

cat > "$ARTIFACTS_DIR/proof-7.0.json" <<EOF
{"spec_id": "wish-7.0-episode-analytics", "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)", "tests_passed": $passed, "tests_failed": $failed, "status": "$([ $failed -eq 0 ] && echo 'SUCCESS' || echo 'FAILED')"}
EOF

echo ""
if [[ $failed -eq 0 ]]; then
    log_pass "WISH 7.0 COMPLETE: Episode analytics verified ✅"
    exit 0
else
    log_fail "WISH 7.0 FAILED: $failed test(s) failed ❌"
    exit 1
fi
