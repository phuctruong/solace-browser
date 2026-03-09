Command:
```bash
export PATH="/home/phuc/projects/solace-browser/depot_tools:$PATH"
gn_binary="source/src/buildtools/linux64/gn"
$gn_binary gen source/src/out/Solace --root=source/src --args="is_debug=false chrome_pgo_phase=0 is_component_build=true use_sysroot=true"
```

Exit code: 0

Output:
```text
Done. Made 28708 targets from 4511 files in 2996ms
```
