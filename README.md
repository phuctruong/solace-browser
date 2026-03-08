# Solace Browser

Custom Chromium browser fork with native AI sidebar.

## Build

```bash
# Prerequisites
cd source/src && ./build/install-build-deps.sh

# Configure
cd source/src && gn gen out/Solace --args='is_debug=false chrome_pgo_phase=0 is_component_build=true use_sysroot=true proprietary_codecs=false'

# Build
cd source/src && autoninja -C out/Solace chrome

# Run
./source/src/out/Solace/chrome
```

## License

Source-available under [FSL](https://fsl.software/) — converts to OSS after 4 years.
Chromium source code is licensed under the Chromium BSD license.
