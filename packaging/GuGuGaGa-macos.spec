# -*- mode: python ; coding: utf-8 -*-
import json
import os
from pathlib import Path
import sys
import certifi

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

ROOT = Path(SPECPATH).parent
VERSION = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
ICON = ROOT / ".local" / "macos" / "GuGuGaGa.icns"
if sys.platform != "darwin":
    raise SystemExit("Build this specification on macOS.")
for required in (ROOT / "desktop.py", ROOT / "dist/index.html", ICON):
    if not required.is_file():
        raise SystemExit(f"Missing build input: {required}. Run scripts/build-macos.sh.")

datas = [(str(ROOT / "dist"), "dist"), (str(ICON), "packaging"), (certifi.where(), "packaging")]
datas += collect_data_files("webview")
for distribution in (
    "pywebview", "proxy_tools", "bottle", "typing_extensions", "pyobjc-core", "certifi",
    "pyobjc-framework-Cocoa", "pyobjc-framework-Quartz", "pyobjc-framework-WebKit",
    "pyobjc-framework-Security", "pyobjc-framework-UniformTypeIdentifiers",
):
    datas += copy_metadata(distribution)
for metadata_path, _ in copy_metadata("pyinstaller"):
    for license_path in Path(metadata_path).rglob("COPYING.txt"):
        datas.append((str(license_path), "licenses/pyinstaller"))
for license_name in ("LICENSE_PYTHON.txt", "LICENSE.txt", "LICENSE"):
    python_license = Path(sys.base_prefix) / license_name
    if python_license.is_file():
        datas.append((str(python_license), "licenses/python-launcher"))
        break

a = Analysis(
    [str(ROOT / "desktop.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=["webview.platforms.cocoa", "WebKit", "Foundation", "AppKit", "objc"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "PySide2", "PySide6", "gi", "gtk", "qtpy", "matplotlib", "numpy", "pandas"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="GuGuGaGa",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=os.environ["GUGUGAGA_MACOS_ARCH"],
    codesign_identity=None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="GuGuGaGa")
app = BUNDLE(
    coll,
    name="GuGuGaGa.app",
    icon=str(ICON),
    bundle_identifier="io.github.k0s0k.GuGuGaGa",
    version=VERSION,
    info_plist={
        "CFBundleDisplayName": "GuGuGaGa",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSMinimumSystemVersion": "14.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
        "NSAppTransportSecurity": {"NSAllowsLocalNetworking": True},
        "NSHumanReadableCopyright": "GuGuGaGa contributors",
    },
)
