# /distill-verify - Verify Network Artifact

Verify a published artifact's hash, RTC markers, and signature.

## Usage

```
/distill-verify <artifact-id-or-path>
```

## What It Does

1. **Hash Check** - Verify content matches declared hash
2. **Structure Check** - Verify DNA-23, STORY-47, GENOME-79 present
3. **RTC Check** - Verify regeneration markers present
4. **Signature Check** - Verify signature file exists

## Instructions for Claude

When user runs `/distill-verify <id>`:

1. Run the verify.sh script:
   ```bash
   ./network/tools/verify.sh <id>
   ```

2. Show detailed results for each check:
   - Hash: matches or mismatch
   - Structure: which sections found
   - RTC: markers present
   - Signature: valid or missing

3. Show summary:
   - Total passed
   - Total failed
   - Total warnings

## Example

```
User: /distill-verify distill-v1.0

Claude:
=== PM Verify - Full RTC Check ===

Mode: Registry artifact verification
File: network/artifacts/abc123/content.md

1. File Integrity
  ✓ File exists and readable
    Size: 4859 bytes

2. Hash Verification
  ✓ Hash matches (abc123def456...)

3. Structure Verification
  ✓ DNA-23 (core equations) present
  ✓ STORY-47 (axioms) present
  ✓ GENOME-79 (operational rules) present

4. RTC Markers
  ✓ RTC concept referenced
  ✓ MDL concept referenced

5. Invariants
  ✓ Invariants section present

6. Signature
  ✓ Signature file present

=== Verification Summary ===

  Passed:   7
  Failed:   0
  Warnings: 0

✓ VERIFIED: All checks passed
```

## Related Commands

- `/distill` - Create CLAUDE.md from documentation
- `/distill-publish` - Publish artifact to network
- `/distill-list` - List all network artifacts
