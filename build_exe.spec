# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

block_cipher = None

a = Analysis(
    ['colour_picker2.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.ico', '.')],  # Add icon to datas
    hiddenimports=['pystray._win32'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Colour Picker 2.9',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'  # Make sure icon.ico is in the same directory as the spec file
)
