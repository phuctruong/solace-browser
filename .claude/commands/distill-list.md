# /distill-list - List Network Artifacts

List all artifacts in the Prime Mermaid Network.

## Usage

```
/distill-list
```

## What It Does

1. **Read Registry** - Parse manifest.json
2. **Format Output** - Display as table
3. **Show Count** - Total artifacts in network

## Instructions for Claude

When user runs `/distill-list`:

1. Run the pm.sh list command:
   ```bash
   ./network/tools/pm.sh list
   ```

2. Show results in table format:
   - ID
   - Type
   - Hash (first 12 chars)
   - Created date

3. Show total count

## Example

```
User: /distill-list

Claude:
=== PM Network Artifacts ===

Total artifacts: 3

ID                              TYPE        HASH
--------------------------------------------------------------
distill-v1.0                    recipe      abc123def456
stillwater-impl-v1.0            knowledge   def456abc123
prime-mermaid-v1.0              knowledge   789xyz123abc

Use 'pm info <id>' for details on a specific artifact.
```

## Related Commands

- `/distill` - Create CLAUDE.md from documentation
- `/distill-publish` - Publish artifact to network
- `/distill-verify` - Verify artifact in network
