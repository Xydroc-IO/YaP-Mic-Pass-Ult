# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

# Get the base directory (where the spec file is located)
# In PyInstaller, SPEC variable contains the path to this spec file
basedir = os.path.dirname(os.path.abspath(SPEC))

# Define data files
datas = [
    (os.path.join(basedir, 'server', 'server.py'), 'server'),
    (os.path.join(basedir, 'icons', 'icon.png'), 'icons'),
]

# Find and include audio libraries if needed
binaries = []

a = Analysis(
    [os.path.join(basedir, 'server', 'server_gui.py')],
    pathex=[basedir],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinter.font',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL._tkinter_finder',
        'pystray',
        'pystray._base',
        'pystray._win32',
        'pystray._darwin',
        'pystray._xorg',
        'numpy',
        'queue',
        'threading',
        'subprocess',
        'socket',
        'signal',
        'tempfile',
        'platform',
        'time',
        'os',
        'sys',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'pandas'],
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
    name='yap-mic-pass-ult-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed mode
    disable_windowed_traceback=False,
    argv_emulation=False,
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
    name='yap-mic-pass-ult-server',
)

