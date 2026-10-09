# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

ROOT = Path(SPECPATH).parent
python_runtime = ROOT / ".local" / "desktop-python"
cpp_runtime = ROOT / ".local" / "toolchains" / "w64devkit"

for required in (
    ROOT / "desktop.py",
    ROOT / "dist" / "index.html",
    ROOT / "packaging" / "GuGuGaGa.ico",
    python_runtime / "python.exe",
    cpp_runtime / "bin" / "g++.exe",
):
    if not required.is_file():
        raise SystemExit(f"Required build input is missing: {required}")

datas = [
    (str(ROOT / "dist"), "dist"),
    (str(python_runtime), "runtime/python"),
    # Keep the whole relocatable toolchain, including its source and license notices.
    (str(cpp_runtime), "runtime/toolchains/w64devkit"),
    (str(ROOT / "packaging" / "GuGuGaGa.ico"), "packaging"),
]
datas += collect_data_files("webview")
for distribution in ("pywebview", "pythonnet", "clr_loader", "cffi", "pycparser", "bottle", "proxy_tools", "typing_extensions"):
    datas += copy_metadata(distribution)
for license_name in ("LICENSE_PYTHON.txt", "LICENSE.txt", "LICENSE"):
    python_license = Path(sys.base_prefix) / license_name
    if python_license.is_file():
        datas.append((str(python_license), "licenses/python-launcher"))
        break
for metadata_path, _ in copy_metadata("pyinstaller"):
    for license_path in Path(metadata_path).rglob("COPYING.txt"):
        datas.append((str(license_path), "licenses/pyinstaller"))

a = Analysis(
    [str(ROOT / "desktop.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=["webview.platforms.winforms", "webview.platforms.edgechromium"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "PySide2", "PySide6", "gi", "gtk", "qtpy", "matplotlib", "numpy", "pandas"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GuGuGaGa",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT / "packaging" / "GuGuGaGa.ico"),
    version=str(ROOT / "packaging" / "version-info.txt"),
    contents_directory="_internal",
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="GuGuGaGa-v2.4.0")
