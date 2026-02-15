# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

cv2_datas, cv2_binaries, cv2_hiddenimports = collect_all('cv2')
numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all('numpy')
pil_datas, pil_binaries, pil_hiddenimports = collect_all('PIL')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=cv2_binaries + numpy_binaries + pil_binaries,
    datas=cv2_datas + numpy_datas + pil_datas,
    hiddenimports=[
        'cv2',
        'numpy',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageOps',
        'PIL.PdfImagePlugin',
    ] + cv2_hiddenimports + numpy_hiddenimports + pil_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TCKimlikDuzenleyici',
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
    icon='app.ico',
    version='version.txt'
)
