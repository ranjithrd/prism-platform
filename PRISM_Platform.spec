# -*- mode: python ; coding: utf-8 -*-

# from PyInstaller.utils.hooks import collect_data_files

# # --- List of Python modules to EXCLUDE ---
# # (This is still good practice to reduce app size)
# excluded_modules = [
#     'PySide6.Qt3DAnimation',
#     'PySide6.Qt3DCore',
#     'PySide6.Qt3DExtras',
#     'PySide6.Qt3DInput',
#     'PySide6.Qt3DLogic',
#     'PySide6.Qt3DRender',
#     'PySide6.QtWebEngineCore',
#     'PySide6.QtWebEngineQuick',
#     'PySide6.QtWebEngineWidgets',
#     'PySide6.QtCharts',
#     'PySide6.QtNetworkAuth',
#     'PySide6.QtQuick3D',
#     'PySide6.QtTest',
#     'PySide6.QtBluetooth',
#     'PySide6.QtConcurrent',
#     'PySide6.QtMultimedia',
#     'PySide6.QtPositioning',
#     'PySide6.QtSensors',
#     'PySide6.QtSerialPort',
#     'PySide6.QtNfc',
#     'PySide6.QtSql',
#     'PySide6.QtSvg',
#     'PySide6.QtWebSockets',
#     'PySide6.QtWebChannel',
#     'PySide6.QtTextToSpeech',
#     'PySide6.QtQuick',
#     'PySide6.QtQml',
# ]


# # --- List of binary/framework NAMES to EXCLUDE ---
# # This is the "nuke from orbit" list.
# excluded_binaries = [
#     'Qt3D',
#     'QtWebEngine',
#     'QtCharts',
#     'QtQuick3D',
#     'QtNetworkAuth',
#     'QtBluetooth',
#     'QtConcurrent',
#     'QtMultimedia',
#     'QtPositioning',
#     'QtSensors',
#     'QtSerialPort',
#     'QtNfc',
#     'QtQuick',
#     'QtQml',
#     'QtSql',
#     'QtSvg',
#     'QtWebSockets',
#     'QtWebChannel',
#     'QtTextToSpeech',
# ]


# # --- THE REAL FIX: Manually filter the greedy hook ---
# # 1. Get ALL files from the hook
# all_datas = collect_data_files('PySide6')

# # 2. Filter them to remove the ones we don't want
# filtered_datas = []
# for item in all_datas:
#     # item[0] is the full path. We check if any "excluded" name is in it.
#     if not any(excluded in item[0] for excluded in excluded_binaries):
#         filtered_datas.append(item)


# # --- Now the Analysis uses our SMALLER, filtered lists ---
# a = Analysis(
#     ['run_gui.py'],
#     pathex=[],
#     binaries=[],  # <-- This is now empty.
#     datas=filtered_datas,    # <-- Use our new filtered list
#     hiddenimports=[],
#     hookspath=[],
#     hooksconfig={},
#     runtime_hooks=[],
#     excludes=excluded_modules, # <-- Still good to keep this
#     noarchive=False,
#     optimize=0,
# )
# pyz = PYZ(a.pure)

# exe = EXE(
#     pyz,
#     a.scripts,
#     [],
#     exclude_binaries=True,
#     name='PRISM_Platform',
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     console=False,
#     disable_windowed_traceback=False,
#     argv_emulation=False,
#     target_arch=None,
#     codesign_identity=None,
#     entitlements_file=None,
# )

# import os
# filtered_binaries = []
# for item in a.binaries:
#     src = item[0] if isinstance(item, tuple) else item
#     # Skip framework symlinks
#     if isinstance(src, str) and os.path.islink(src) and 'Versions/Current' in src:
#         continue
#     filtered_binaries.append(item)

# coll = COLLECT(
#     exe,
#     filtered_binaries,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='PRISM_Platform',
#     copy_dependent_files=True
# )
# app = BUNDLE(
#     coll,
#     name='PRISM_Platform.app',
#     icon=None,
#     bundle_identifier=None,
# )

block_cipher = None


a = Analysis(
    ["run_gui.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    name="PRISM Platform",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PRISM Platform",
)
app = BUNDLE(coll, name="PRISM Platform.app", icon=None, bundle_identifier=None)
