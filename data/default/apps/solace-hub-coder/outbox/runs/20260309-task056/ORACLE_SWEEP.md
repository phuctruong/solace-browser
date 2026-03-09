# Oracle Sweep

- `HQ-001` PASS — changes stay in `solace-browser`.
- `HQ-002` PASS — new exception handling uses typed exceptions only.
- `HQ-004` PASS — Prime Wiki route behavior is covered by snapshot tests.
- `HQ-007` PASS — tests avoid the live Hub port by using an ephemeral server port.
- `HQ-010` PASS — targeted and broader Prime Wiki tests pass after the patch.
- `HQ-020` PASS — outbox includes diff, red/green logs, oracle sweep, and evidence JSON.
- `HQ-029` PASS — modified code keeps Hub traffic on the single allowed port.
- `HQ-030` PASS — scope stays under five files; this task changes two files.
- `HQ-031` PASS — work stays in the server lane and does not depend on blocked Tauri build work.
- `HQ-032` PASS — diff touches the active server surface only.
- `HQ-043` PASS — no broad exception handlers, no banned remote-debugging port, evidence bundle present.
