# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

ROOT_DIR = os.path.abspath(os.path.join(SPECPATH, '..'))

icon_path = os.path.join(ROOT_DIR, 'ui', 'assets', 'voizy.ico')
logo_path = os.path.join(ROOT_DIR, 'ui', 'assets', 'voizy_logo.png')
entry_script = os.path.join(ROOT_DIR, 'core', 'main.py')

datas = []
if os.path.isfile(icon_path):
    datas.append((icon_path, 'ui/assets'))
    datas.append((icon_path, '.'))

if os.path.isfile(logo_path):
    datas.append((logo_path, 'ui/assets'))
    datas.append((logo_path, '.'))

binaries = []

hiddenimports = [
    'core',
    'core.main',
    'core.config',
    'core.transcriber',
    'core.translator',
    'core.media',
    'core.model_manager',
    'ui',
    'ui.theme',
    'ui.modals',
    'ui.main_window',
    'utils',
    'utils.paths',
    'utils.logger',
    'utils.helpers',
    'huggingface_hub',
    'PIL',
    'deep_translator',
    'ctranslate2',
    'faster_whisper',
    'customtkinter',
    'tkinterdnd2',
    'requests',
]

datas += [
    (os.path.join(ROOT_DIR, 'core'), 'core'),
    (os.path.join(ROOT_DIR, 'ui'), 'ui'),
    (os.path.join(ROOT_DIR, 'utils'), 'utils'),
]

for pkg in ['ctranslate2', 'faster_whisper', 'customtkinter', 'tkinterdnd2']:
    datas += collect_data_files(pkg)
    hiddenimports += collect_submodules(pkg)
    binaries += collect_dynamic_libs(pkg)

a = Analysis(
    [entry_script],
    pathex=[
        ROOT_DIR,
        os.path.join(ROOT_DIR, 'core'),
        os.path.join(ROOT_DIR, 'ui'),
        os.path.join(ROOT_DIR, 'utils'),
    ],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch',
        'torchaudio',
        'torchvision',
        'transformers',
        'tensorflow',
        'tensorboard',
        'unittest',
        'pytest',
        'tkinter.test',
        'matplotlib',
        'IPython',
        'notebook',
        'docutils',
        'edge_tts',
        'pydub',
        'scipy',
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Voizy',
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
    icon=icon_path,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Voizy',
)
