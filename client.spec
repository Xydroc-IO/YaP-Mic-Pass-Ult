# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['client/client_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icons', 'icons'),
        ('client/client.py', 'client'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'pyaudio',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'pystray',
        'numpy',
        'struct',
        'socket',
        'threading',
        'queue',
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
    name='yap-mic-pass-ult-client',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
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
    upx=False,
    upx_exclude=[],
    name='yap-mic-pass-ult-client',
)
