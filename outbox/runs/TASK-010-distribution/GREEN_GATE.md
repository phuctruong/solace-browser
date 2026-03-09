# GREEN GATE — TASK-010-distribution

## Step 1 — Shell syntax

a) Commands

```bash
bash -n scripts/build-deb.sh
bash -n scripts/version.sh
```

b) Output

```text
FINAL_CHECKS=PASS
```

## Step 2 — Version and desktop validation

a) Commands

```bash
cat scripts/VERSION
bash scripts/version.sh
desktop-file-validate scripts/solace-browser.desktop
```

b) Output

```text
0.9.0
0.9.0-368
DESKTOP_VALIDATE=PASS
```

## Step 3 — Package tree control generation

a) What ran

- Ran `scripts/build-deb.sh` with the default package root `/tmp/solace-browser-pkg`.
- Verified `/tmp/solace-browser-pkg/DEBIAN/control` exists and contains the requested Debian fields.

b) Output

```text
Package: solace-browser
Version: 0.9.0
Section: web
Priority: optional
Architecture: amd64
Depends: python3 (>=3.10), libgtk-3-0, libx11-xcb1
Maintainer: Solace AI <hello@solaceagi.com>
Description: AI-Native browser with Yinyang sidebar
 AI-Native browser with Yinyang sidebar.
```

## Step 4 — Real `.deb` build

a) What ran

- Built a real package with `bash scripts/build-deb.sh`.
- Verified the output file at `dist/solace-browser_0.9.0_amd64.deb`.
- Listed package contents with `dpkg-deb -c`.

b) Output

```text
dpkg-deb: building package 'solace-browser' in '/home/phuc/projects/solace-browser/dist/solace-browser_0.9.0_amd64.deb'.
/home/phuc/projects/solace-browser/dist/solace-browser_0.9.0_amd64.deb
-rwxr-xr-x ./usr/bin/solace-browser
-rwxr-xr-x ./usr/lib/solace-browser/launch-yinyang.sh
-rwxr-xr-x ./usr/lib/solace-browser/yinyang-server.py
-rw-r--r-- ./usr/lib/systemd/user/yinyang.service
-rw-r--r-- ./usr/share/applications/solace-browser.desktop
```

## Oracle Sweep

- shell syntax: PASS
- `scripts/VERSION` semver: PASS
- `scripts/version.sh` output: PASS
- desktop entry validation: PASS
- default `/tmp/solace-browser-pkg/DEBIAN/control`: PASS
- real `.deb` build: PASS
- banned-term scan on touched files: PASS
