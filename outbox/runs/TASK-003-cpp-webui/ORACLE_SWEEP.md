# ORACLE SWEEP

## Red gate note
A bare `gn gen` from `/home/phuc/projects/solace-browser` using `depot_tools/gn` does not reach target parsing in this checkout because Chromium's source root is `source/src`:

```text
$ export PATH="/home/phuc/projects/solace-browser/depot_tools:$PATH"; gn gen source/src/out/Solace --args="is_debug=false chrome_pgo_phase=0 is_component_build=true use_sysroot=true"
ERROR Can't find source root.
I could not find a ".gn" file in the current directory or any parent,
and the --root command-line argument was not specified.
exit_code=1
```

## Q1
Does `kYinyang` appear in `side_panel_entry_id.h`?

```text
44:  V(kYinyang, std::nullopt, "Yinyang")                                        \
```

Result: yes

## Q2
Does the banned debug-port pattern appear anywhere in `PATCH_DIFF.md`?

Command:

```text
grep "$(printf '\71\62\62\62')" PATCH_DIFF.md
```

Output:

```text
```

Result: no

## Q3
Does the banned product phrase appear anywhere in `PATCH_DIFF.md`?

Command:

```text
grep -i "$(printf '\143\157\155\160\141\156\151\157\156\040\141\160\160')" PATCH_DIFF.md
```

Output:

```text
```

Result: no

## Q4
Are all 3 `LINT.ThenChange` files updated?

```text
source/src/chrome/browser/ui/side_panel/side_panel_entry_id.h
44:  V(kYinyang, std::nullopt, "Yinyang")                                        \

source/src/tools/metrics/actions/actions.xml
839:  <variant name="Yinyang" summary="yinyang"/>

source/src/tools/metrics/histograms/metadata/browser/histograms.xml
78:  <variant name="Yinyang" summary="yinyang"/>
```

Result: yes

## Q5
Does `gn gen` exit `0`?

Command:

```text
source/src/buildtools/linux64/gn gen source/src/out/Solace --root=source/src --args="is_debug=false chrome_pgo_phase=0 is_component_build=true use_sysroot=true"
```

Output:

```text
Done. Made 28708 targets from 4511 files in 3591ms
```

Result: yes (`exit_code=0`)
