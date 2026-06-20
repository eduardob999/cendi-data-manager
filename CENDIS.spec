# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['add_date.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pandas', 'pandas._libs.tslibs.np_datetime', 'pandas._libs.tslibs.nattype', 'pandas._libs.tslibs.timedeltas', 'pandas._libs.skiplist', 'prompt_toolkit', 'prompt_toolkit.completion', 'prompt_toolkit.formatted_text', 'prompt_toolkit.styles', 'colorama', 'unicodedata'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CENDIS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
