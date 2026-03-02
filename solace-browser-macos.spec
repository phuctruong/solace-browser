# -*- mode: python ; coding: utf-8 -*-
# solace-browser-macos.spec — PyInstaller spec for macOS universal binary
# Rung: 641 | Belt: Yellow | Channel: [3]
#
# Build:
#   pyinstaller solace-browser-macos.spec
#
# Produces:
#   dist/solace-browser  (universal binary: x86_64 + arm64)
#
# Upload target:
#   gs://solace-downloads/solace-browser/v1.0.0/solace-browser-macos-universal
#
# Code signing: ad-hoc (codesign_identity='-')
# Bundle ID: com.solaceagi.browser


import platform

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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='universal2',
    codesign_identity='-',
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
