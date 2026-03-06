# -*- mode: python ; coding: utf-8 -*-
# solace-browser-macos.spec — PyInstaller spec for macOS native binary
# Rung: 641 | Belt: Yellow | Channel: [3]
#
# Build:
#   pyinstaller solace-browser-macos.spec
#
# Produces:
#   dist/solace-browser  (native binary for runner architecture)
#
# Upload target:
#   gs://solace-downloads/solace-browser/v1.0.0/solace-browser-macos-universal
#
# Code signing: disabled in CI builds
# Bundle ID: com.solaceagi.browser

a = Analysis(
    ['solace_browser_server.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('web', 'web'),
        ('static', 'static'),
        ('data', 'data'),
    ],
    hiddenimports=[
        'competitive_features',
        'history',
        'oauth3',
        'audit',
        'audit.chain',
        'audit.alcoa',
        'audit.retention',
        'browser',
        'sync_client',
        'evidence_upload',
        'llm',
        'llm.claude_code_client',
        'llm.noop_client',
        'yinyang',
        'yinyang.top_rail',
        'yinyang.bottom_rail',
        'yinyang.ws_bridge',
        'yinyang.push_alerts',
        'yinyang.delight_engine',
        'yinyang.state_bridge',
        'yinyang.alert_queue',
        'yinyang.support_bridge',
        'yinyang.highlighter',
        'agents',
        'api',
        'approvals',
        'channels',
        'cli',
        'cross_app',
        'fs_gateway',
        'machine',
        'plugins',
        'profiles',
        'recipes',
        'store_client',
        'voice',
        # web UI dashboard server + its dependencies
        'web',
        'web.server',
        'app_store',
        'app_store.backend',
        'companion',
        'companion.apps',
        'companion.bridge',
        'companion.builtin',
        'companion.scopes',
        'inbox_outbox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'django',
        'django.utils',
        'django.core',
        # Linux-specific modules not needed on macOS
        'systemd',
        'dbus',
        'gi',
        'gi.repository',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='solace-browser',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disabled on macOS to avoid binary corruption issues
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    # Build native to the runner architecture for stable CI output.
    target_arch=None,
    # Unsigned binary for direct download distribution.
    codesign_identity=None,
    entitlements_file=None,
    info_plist={
        'CFBundleName': 'Solace Browser',
        'CFBundleDisplayName': 'Solace Browser',
        'CFBundleIdentifier': 'com.solaceagi.browser',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'LSMinimumSystemVersion': '11.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'CFBundleInfoDictionaryVersion': '6.0',
        'CFBundleExecutable': 'solace-browser',
    },
)
