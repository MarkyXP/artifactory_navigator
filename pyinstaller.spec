# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/', 'assets/'),
        ('app/core/config.json', 'app/core/config.json'),
        (app/services/DSTFile', 'app/services/DSTFile'),
        ('app/services/email_body.html'l', 'app/services/email_body.html'),
        ('.env', '.')
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LBSArtifactoryNavigator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['Assets/LBS_AF_Logo.ico'],
)