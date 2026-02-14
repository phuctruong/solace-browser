# /distill-publish - Publish to PM Network

Publish a CLAUDE.md artifact to the Prime Mermaid Network.

## Usage

```
/distill-publish <path>
```

## What It Does

1. **Verify** - Check artifact structure (DNA-23, STORY-47, GENOME-79)
2. **Hash** - Compute BLAKE3/SHA256 content hash
3. **Sign** - Sign artifact (placeholder for now)
4. **Register** - Add to network registry
5. **Store** - Copy to content-addressed storage

## Instructions for Claude

When user runs `/distill-publish <path>`:

1. Verify the file exists and is a valid CLAUDE.md:
   - Has DNA-23 (core equations)
   - Has STORY-47 (axioms)
   - Has GENOME-79 (operational rules)
   - Has Invariants section

2. Run the pm.sh publish command:
   ```bash
   ./network/tools/pm.sh publish <path>
   ```

3. Show the result:
   - Artifact ID
   - Hash (first 12 chars)
   - Type detected
   - Storage path

4. Verify the published artifact:
   ```bash
   ./network/tools/verify.sh <artifact-id>
   ```

## Example

```
User: /distill-publish docs/prime-mermaid-recipes/implementation/CLAUDE.md

Claude:
=== PM Publish ===

Step 1: Hashing content...
  Hash: abc123def456...

Step 2: Generating metadata...
  ID: stillwater-implementation-canon-v1.0
  Type: knowledge

Step 3: Creating artifact storage...

Step 4: Updating registry...

=== Published ===
  ID:     stillwater-implementation-canon-v1.0
  Hash:   abc123def456
  Type:   knowledge
  Path:   network/artifacts/abc123def456/

✓ Artifact published to network

=== Verification ===
✓ Hash verified
✓ RTC markers present
✓ Signature present

VERIFIED: All checks passed
```

## Related Commands

- `/distill` - Create CLAUDE.md from documentation
- `/distill-verify` - Verify artifact in network
- `/distill-list` - List all network artifacts
