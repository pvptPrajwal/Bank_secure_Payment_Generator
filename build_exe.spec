# build_exe.spec
# Run with: python -m PyInstaller build_exe.spec

block_cipher = None

from PyInstaller.building.build_main import Analysis, PYZ, EXE

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('.env',          '.'),           # Supabase credentials bundled inside exe
        ('resources',     'resources'),   # Logo + icon files
    ],
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
    a.binaries,
    a.datas,
    [],
    name='BankPaymentFileGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                        # No black terminal window
    icon='resources/app_icon.ico',        # TiMoCo logo as .exe icon
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
