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
        'PySide6.QtWidgets',
        'paho.mqtt.client',
        'ssl'
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

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

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
    icon='icon.png',
    bundle_identifier='com.yylronaldo.copier',
    info_plist={
        'LSUIElement': '1',  # 让应用程序不显示在 Dock 中
        'NSHighResolutionCapable': 'True',
        'CFBundleShortVersionString': '2.1.0',
        'CFBundleVersion': '2.1.0',
        'NSRequiresAquaSystemAppearance': 'False',  # 支持暗色模式
        'LSMinimumSystemVersion': '10.13',  # 最低支持的 macOS 版本
        'NSAppleEventsUsageDescription': 'Copier needs to access clipboard data to provide clipboard history functionality.',
        'NSPasteboardUsageDescription': 'Copier needs to access clipboard data to provide clipboard history functionality.',
        'NSAccessibilityUsageDescription': 'Copier needs accessibility permissions to monitor clipboard changes.',
        'LSApplicationCategoryType': 'public.app-category.utilities',
        'LSRequiresNativeExecution': True,
        'NSSupportsAutomaticGraphicsSwitching': True,
        'CFBundleDisplayName': 'Copier',
        'CFBundleName': 'Copier',
        'CFBundleIdentifier': 'com.yylronaldo.copier',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
    }
)
