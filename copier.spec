# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Copier',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Copier'
)

app = BUNDLE(
    coll,
    name='Copier.app',
    icon=None,
    bundle_identifier='com.yylronaldo.copier',
    info_plist={
        'NSHighResolutionCapable': True,
        'NSAppleEventsUsageDescription': 'Copier needs to access clipboard data to provide clipboard history functionality.',
        'NSPasteboardUsageDescription': 'Copier needs to access clipboard data to provide clipboard history functionality.',
        'NSAccessibilityUsageDescription': 'Copier needs accessibility permissions to monitor clipboard changes.',
        'LSMinimumSystemVersion': '10.13',
        'CFBundleDisplayName': 'Copier',
        'CFBundleName': 'Copier',
        'CFBundleIdentifier': 'com.yylronaldo.copier',
        'CFBundleVersion': '2.1.0',
        'CFBundleShortVersionString': '2.1.0',
    }
)
