# GREEN GATE — TASK-009-launcher

## Step 1 — Shell syntax

a) Commands

```bash
bash -n scripts/launch-yinyang.sh
bash -n scripts/stop-yinyang.sh
bash -n scripts/install.sh
```

b) Output

```text
FINAL_CHECKS=PASS
```

## Step 2 — Stub harness install/start/stop loop

a) What ran

- Installed into a temp `$HOME` with a stub `systemctl`.
- Ran `install.sh` twice to prove idempotent copying and enable flow.
- Ran the installed launcher twice to prove idempotent start behavior.
- Verified the launcher invoked `yinyang-server.py` with the repo root.
- Ran the installed stop script twice to prove idempotent shutdown behavior.

b) Output

```text
systemctl --user daemon-reload
systemctl --user enable yinyang
Installed Yinyang launcher to /tmp/solace-task009-home/.local/lib/solace
Systemd user unit installed at /tmp/solace-task009-home/.config/systemd/user/yinyang.service
systemctl --user daemon-reload
systemctl --user enable yinyang
Installed Yinyang launcher to /tmp/solace-task009-home/.local/lib/solace
Systemd user unit installed at /tmp/solace-task009-home/.config/systemd/user/yinyang.service
Yinyang server healthy on port 8888
Yinyang server healthy on port 8888
Stopped Yinyang server 1394414
Yinyang server is not running
TASK009_STUB_HARNESS=PASS
```

## Step 3 — Real-path launcher attempt in sandbox

a) What ran

- Ran `HOME=/tmp/solace-task009-real ./scripts/launch-yinyang.sh` against the real `yinyang-server.py`.

b) Output

```text
ERROR: Yinyang server process 1394588 exited before passing health check; see /tmp/solace-task009-real/.solace/yinyang.log
Traceback (most recent call last):
  ...
PermissionError: [Errno 1] Operation not permitted
```

c) Result

- The launcher correctly started the real entry point and failed loudly.
- The sandbox blocks opening the local listening socket, so the failure is environmental rather than script syntax or control-flow.

## Step 4 — User unit validation

a) Static fields present

```text
Description=Yinyang AI Server
Type=simple
ExecStart=/bin/sh %h/.local/lib/solace/launch-yinyang.sh
Restart=on-failure
RestartSec=5
WantedBy=default.target
```

b) `systemd-analyze` note

- `systemd-analyze verify scripts/yinyang.service` aborts in this sandbox before unit verification completes.
- The unit file itself is syntactically simple, uses an absolute executable (`/bin/sh`), and installs cleanly through `install.sh`.

## Oracle Sweep

- shell syntax: PASS
- stub harness: PASS
- idempotent install/start/stop: PASS
- banned-term scan on touched files: PASS
- user unit required fields: PASS
- `systemd-analyze` in sandbox: BLOCKED
