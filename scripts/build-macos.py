"""Build and verify a native macOS app, then create a drag-to-install DMG.

Run with Python 3.13 on the target Mac architecture; see build-macos.sh.
The independent code interpreter is copied after PyInstaller so its relative
library paths are preserved, then every Mach-O image and the app are signed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = ROOT / ".local" / "macos"
PYTHON_RELEASE = "20251014"
PYTHON_VERSION = "3.13.9"
RUNTIMES = {
    "arm64": ("aarch64", "52721745b0fa3196e4d0381fa5c06dda1d54343b90d49d90c3bba52d1171bd98"),
    "x86_64": ("x86_64", "7c33b153a69c6255e6f2659cf39738f316b03969d6230d7bc47c73b7fde9a0d4"),
}
MACHO_MAGIC = {b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"}


def run(*command, timeout=1200, env=None):
    print("+ " + " ".join(map(str, command)), flush=True)
    return subprocess.run(list(map(str, command)), cwd=ROOT, check=True, timeout=timeout, env=env)


def clean_build_directory(path):
    """Only delete generated descendants of this project's macOS build root."""
    path = Path(path)
    resolved = path.resolve()
    if path.is_symlink() or not resolved.is_relative_to(BUILD_ROOT.resolve()) or resolved == BUILD_ROOT.resolve():
        raise RuntimeError(f"Unsafe build cleanup path: {path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download_runtime(architecture):
    triple, expected = RUNTIMES[architecture]
    filename = f"cpython-{PYTHON_VERSION}+{PYTHON_RELEASE}-{triple}-apple-darwin-install_only_stripped.tar.gz"
    archive = BUILD_ROOT / filename
    if not archive.is_file() or sha256(archive) != expected:
        url = f"https://github.com/astral-sh/python-build-standalone/releases/download/{PYTHON_RELEASE}/{filename.replace('+', '%2B')}"
        temporary = archive.with_suffix(".download")
        request = urllib.request.Request(url, headers={"User-Agent": "GuGuGaGa-build"})
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as target:
            shutil.copyfileobj(response, target)
        if sha256(temporary) != expected:
            temporary.unlink()
            raise RuntimeError("Python runtime checksum mismatch")
        temporary.replace(archive)
    extracted = BUILD_ROOT / f"python-{architecture}"
    clean_build_directory(extracted)
    with tarfile.open(archive, "r:gz") as source:
        source.extractall(extracted, filter="data")
    python_root = extracted / "python"
    run(python_root / "bin/python3", "-I", "-X", "utf8", "-c", "import json, sqlite3, ssl; print('Bundled Python ready')")
    return python_root


def build_icon():
    iconset = BUILD_ROOT / "GuGuGaGa.iconset"
    clean_build_directory(iconset)
    source = ROOT / "public/gugugaga-icon.png"
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            suffix = "@2x" if scale == 2 else ""
            run("sips", "-z", size * scale, size * scale, source, "--out", iconset / f"icon_{size}x{size}{suffix}.png")
    run("iconutil", "-c", "icns", iconset, "-o", BUILD_ROOT / "GuGuGaGa.icns")


def sign_runtime(app):
    runtime = app / "Contents/Resources/runtime/python"
    for path in sorted(runtime.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb") as stream:
            is_binary = stream.read(4) in MACHO_MAGIC
        if is_binary:
            run("codesign", "--force", "--sign", "-", path)
    run("codesign", "--force", "--deep", "--sign", "-", app)
    run("codesign", "--verify", "--deep", "--strict", "--verbose=2", app)


def verify_app(app, reports):
    executable = app / "Contents/MacOS/GuGuGaGa"
    reports.mkdir(parents=True, exist_ok=True)
    # Relocate the application before tests: absolute build paths must not leak
    # into either PyInstaller's launcher or the independent code interpreter.
    relocated_root = BUILD_ROOT / "relocation test"
    clean_build_directory(relocated_root)
    relocated = relocated_root / "GuGuGaGa.app"
    run("ditto", app, relocated)
    executable = relocated / "Contents/MacOS/GuGuGaGa"
    run(executable, "--self-test", reports / "frozen-self-test.json", timeout=180)
    run(executable, "--data-dir", reports / "gui-data", "--gui-smoke-test", reports / "native-gui.json", timeout=100)
    for name in ("frozen-self-test.json", "native-gui.json"):
        result = json.loads((reports / name).read_text(encoding="utf-8"))
        if not result.get("passed"):
            raise RuntimeError(f"App verification failed: {name}")


def package(app, release, name):
    stage = BUILD_ROOT / "dmg-stage"
    clean_build_directory(stage)
    run("ditto", app, stage / "GuGuGaGa.app")
    (stage / "Applications").symlink_to("/Applications", target_is_directory=True)
    (stage / "安装说明.txt").write_text(
        "GuGuGaGa\n\n将 GuGuGaGa.app 拖入 Applications 文件夹，然后在应用程序中打开。\n"
        "学习记录保存在当前用户的资源库中，更新应用会保留进度。\n"
        "Python 已随应用提供。运行 C++ 需要安装 Xcode Command Line Tools：\n"
        "在终端运行 xcode-select --install 并完成安装。\n"
        "若 macOS 提示无法验证开发者，可在系统设置 → 隐私与安全性中点击“仍要打开”。\n",
        encoding="utf-8",
    )
    dmg = release / f"{name}.dmg"
    run("hdiutil", "create", "-volname", "GuGuGaGa", "-srcfolder", stage, "-format", "UDZO", "-ov", dmg)
    run("hdiutil", "verify", dmg)
    archive = release / f"{name}.zip"
    # ditto preserves executable bits and PyInstaller's framework symlinks.
    run("ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", app, archive)
    (release / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in (dmg, archive)), encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-install", action="store_true", help="Reuse the macOS packaging venv")
    parser.add_argument("--skip-frontend", action="store_true", help="Use the existing dist directory")
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("A native macOS machine is required; use the macOS GitHub Actions workflow from Windows.")
    if sys.version_info < (3, 13):
        parser.error("Python 3.13 or later is required to build.")
    architecture = platform.machine()
    if architecture not in RUNTIMES:
        parser.error(f"Unsupported Mac architecture: {architecture}")
    version = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise RuntimeError("Expected a three-part numeric application version")
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    venv = BUILD_ROOT / "package-env"
    python = venv / "bin/python"
    if not python.is_file():
        run(sys.executable, "-m", "venv", venv)
    if not args.skip_install:
        run(python, "-m", "pip", "install", "--disable-pip-version-check", "-r", ROOT / "requirements-macos.txt")
    if not args.skip_frontend:
        run("npm", "ci")
        run("npm", "run", "build")
    runtime = download_runtime(architecture)
    build_icon()
    output = BUILD_ROOT / "dist"
    clean_build_directory(output)
    environment = dict(os.environ)
    environment.update(GUGUGAGA_MACOS_ARCH=architecture, PYINSTALLER_CONFIG_DIR=str(BUILD_ROOT / "cache"), MACOSX_DEPLOYMENT_TARGET="14.0")
    run(python, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", output,
        "--workpath", BUILD_ROOT / "pyinstaller", ROOT / "packaging/GuGuGaGa-macos.spec", env=environment)
    app = output / "GuGuGaGa.app"
    resources = app / "Contents/Resources"
    shutil.copytree(runtime, resources / "runtime/python", symlinks=True)
    (app / "Contents/Frameworks/runtime").symlink_to("../Resources/runtime", target_is_directory=True)
    shutil.copy2(ROOT / "README.md", resources / "README.md")
    shutil.copy2(ROOT / "packaging/THIRD-PARTY-MACOS.txt", resources / "THIRD-PARTY-NOTICES.txt")
    run(python, ROOT / "scripts/collect-frontend-licenses.py", "--output", resources / "THIRD-PARTY-FRONTEND.txt")
    sign_runtime(app)
    reports = BUILD_ROOT / "reports"
    verify_app(app, reports)
    name = f"GuGuGaGa-v{version}-macos-{architecture}"
    release = ROOT / "release" / name
    release.mkdir(parents=True, exist_ok=True)
    package(app, release, name)
    manifest = {
        "version": version, "architecture": architecture, "minimumMacOS": "14.0",
        "buildMacOS": platform.mac_ver()[0], "pythonRuntime": PYTHON_VERSION,
        "signature": "ad-hoc", "notarized": False, "verified": True,
        "sourceCommit": os.environ.get("GITHUB_SHA"),
    }
    (release / "build-info.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Verified macOS packages: {release}", flush=True)


if __name__ == "__main__":
    main()
