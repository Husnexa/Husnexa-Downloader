# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('gui_liquid', 'gui_liquid'), ('app_icon.ico', '.')]
binaries = []
hiddenimports = []

for pkg in ['imageio_ffmpeg', 'yt_dlp', 'yt_dlp_ejs', 'deno', 'webview', 'pythonnet', 'clr_loader', 'curl_cffi']:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

# pip installs deno.exe into Scripts, outside the package, so collect_all misses it
import deno
binaries.append((deno.find_deno_bin(), 'deno/bin'))

hiddenimports += [
    'downloader',
    'app_glass',
    'updater',
    'single_instance',
    'download_queue',
    'packaging',
    'packaging.version',
]

excludes = [
    'numpy',
    'PIL',
    'tkinter',
    '_tkinter',
    'customtkinter',
    'unittest',
    'pydoc',
    'pdb',
    'doctest',
    'pefile',
]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Browsers talk to this over stdin/stdout, which needs a console-mode exe
helper = Analysis(['native_host.py'], pathex=[], excludes=excludes + ['webview', 'yt_dlp', 'curl_cffi'], noarchive=False)
helper_pyz = PYZ(helper.pure)
helper_exe = EXE(
    helper_pyz,
    helper.scripts,
    [],
    exclude_binaries=True,
    name='Husnexa Helper',
    console=True,
    icon='app_icon.ico',
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Husnexa',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon='app_icon.ico',
)

coll = COLLECT(
    exe,
    helper_exe,
    a.binaries,
    helper.binaries,
    a.datas,
    helper.datas,
    strip=False,
    upx=True,
    upx_exclude=['deno.exe'],
    name='Husnexa',
)
