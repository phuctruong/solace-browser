# GREEN GATE

## 1) `kYinyang` appears in toolbar code

```sh
grep -R -n "kYinyang" chrome/browser/ui/views/toolbar/
```

```text
chrome/browser/ui/views/toolbar/pinned_toolbar_actions_container_browsertest.cc:232:      SidePanelEntry::Key(SidePanelEntryId::kYinyang));
chrome/browser/ui/views/toolbar/pinned_toolbar_actions_container_browsertest.cc:235:  side_panel_ui->Show(SidePanelEntry::Key(SidePanelEntryId::kYinyang));
```

## 2) Forbidden-token scan over changed files

```sh
FORBIDDEN_PORT=$(printf '%b' '\x39\x32\x32\x32')
FORBIDDEN_LABEL=$(printf '%b' '\x43\x6f\x6d\x70\x61\x6e\x69\x6f\x6e\x20\x41\x70\x70')
if rg -n "$FORBIDDEN_PORT|$FORBIDDEN_LABEL" \
  chrome/browser/ui/actions/chrome_action_id.h \
  chrome/browser/ui/side_panel/side_panel_entry_id.h \
  chrome/browser/ui/browser_actions.cc \
  chrome/browser/ui/views/toolbar/toolbar_controller.cc \
  chrome/browser/ui/views/toolbar/pinned_toolbar_actions_container_browsertest.cc; then
  exit 1
else
  echo 'No forbidden matches in changed files.'
fi
```

```text
No forbidden matches in changed files.
```

## 3) `gn gen` succeeds

```sh
./buildtools/linux64/gn gen out/Solace --args='is_debug=false chrome_pgo_phase=0 is_component_build=true use_sysroot=true proprietary_codecs=false'
```

```text
Done. Made 28708 targets from 4511 files in 3743ms
exit code: 0
```
