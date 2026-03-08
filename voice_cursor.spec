# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for voice_cursor
# Build command: pyinstaller voice_cursor.spec
#
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# ---------- data files ----------
datas = [
    # Bundled whisper-medium model (local, no download needed at runtime)
    ("resources/whisper-medium", "resources/whisper-medium"),
    # Qt DPI config
    ("qt.conf", "."),
]

# Collect faster-whisper package data (tokenizer assets, etc.)
datas += collect_data_files("faster_whisper")

# ---------- hidden imports ----------
hiddenimports = [
    # Audio
    "sounddevice",
    "soundfile",
    "cffi",
    "_cffi_backend",
    # Numpy / scipy internals that are sometimes missed
    "numpy",
    "numpy.core._multiarray_umath",
    # CTranslate2 / faster-whisper
    "ctranslate2",
    "faster_whisper",
    "faster_whisper.transcribe",
    "faster_whisper.audio",
    "faster_whisper.feature_extractor",
    "faster_whisper.tokenizer",
    "faster_whisper.vad",
    # Tokenizer / HF
    "tokenizers",
    "huggingface_hub",
    "huggingface_hub.utils",
    # Automation
    "pyautogui",
    "pyperclip",
    "pynput",
    "pynput.keyboard",
    "pynput.mouse",
    # PySide6 extras that may not be auto-detected
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtNetwork",
    # OpenAI client
    "openai",
    "httpx",
    "anyio",
]

# ---------- Analysis ----------
a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={
        "matplotlib": {"backends": "no"},
    },
    runtime_hooks=[],
    excludes=[
        # 排除另一套 Qt 绑定，避免 PyInstaller "multiple Qt bindings" 报错
        "PyQt5",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        # 不需要的大型库
        "matplotlib",
        "tkinter",
        "_tkinter",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "unittest",
        "tensorflow",
        "keras",
    ],
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
    name="voice_cursor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # 不显示控制台黑窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # 可替换为 ico 路径，例如 "resources/icon.ico"
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=["vcruntime140.dll", "python*.dll"],
    name="voice_cursor",
)
