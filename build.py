#!/usr/bin/env python3
"""
build.py  —  Build script for Attendance Updater
Packages attendance.py into a standalone executable using PyInstaller.

Usage:
    python build.py            # auto-detects platform
    python build.py --clean    # removes build/ and dist/ before building
    python build.py --help     # shows this help

Output:
    dist/attendance            (Linux / macOS)
    dist/attendance.exe        (Windows)
"""

import os
import sys
import shutil
import platform
import subprocess
import argparse


# ── Config ────────────────────────────────────────────────────────
SCRIPT = "attendance.py"
APP_NAME = "attendance"
ICON_WIN = None   # set to "icon.ico" if you have one
ICON_MAC = None   # set to "icon.icns" if you have one

REQUIRED_DEPS = ["pandas", "prompt_toolkit", "colorama", "pyinstaller"]
OPTIONAL_DEPS = ["chardet"]   # better encoding detection; bundled if present


# ── Helpers ───────────────────────────────────────────────────────
WIDTH = 60


def banner(text):
    print()
    print("╔" + "═" * (WIDTH - 2) + "╗")
    print("║" + text.center(WIDTH - 2) + "║")
    print("╚" + "═" * (WIDTH - 2) + "╝")


def step(n, text):
    print(f"\n[{n}] {text}")
    print("    " + "─" * (WIDTH - 4))


def ok(msg): print(f"    ✔  {msg}")
def warn(msg): print(f"    ⚠  {msg}")
def err(msg): print(f"    ✘  {msg}")


def run(cmd, *, check=True):
    """Run a shell command, stream output, and return the exit code."""
    print(f"    $ {' '.join(cmd)}\n")
    result = subprocess.run(cmd, check=False)
    if check and result.returncode != 0:
        err(f"Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    return result.returncode


def pip_install(packages, optional=False):
    for pkg in packages:
        try:
            rc = run([sys.executable, "-m", "pip",
                     "install", pkg], check=False)
            if rc != 0:
                if optional:
                    warn(f"{pkg} could not be installed (optional — skipping).")
                else:
                    err(f"Failed to install required package: {pkg}")
                    sys.exit(1)
            else:
                ok(f"{pkg} installed / up-to-date.")
        except Exception as e:
            if optional:
                warn(f"{pkg} skipped: {e}")
            else:
                raise


def is_installed(package):
    import importlib.util
    return importlib.util.find_spec(package) is not None


# ── Main build logic ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Build attendance.py into a standalone executable.",
        add_help=True,
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="Remove build/ and dist/ directories before building."
    )
    parser.add_argument(
        "--no-install", action="store_true",
        help="Skip pip install steps (assume deps already present)."
    )
    args = parser.parse_args()

    os_name = platform.system()          # Windows / Linux / Darwin
    exe_name = APP_NAME + (".exe" if os_name == "Windows" else "")
    dist_exe = os.path.join("dist", exe_name)

    banner(f"ATTENDANCE UPDATER — BUILD SCRIPT  ({os_name})")

    # ── 0. Sanity checks ──────────────────────────────────────────
    step(0, "Pre-flight checks")

    py_ver = sys.version_info
    if py_ver < (3, 8):
        err(f"Python 3.8+ required. You have {py_ver.major}.{py_ver.minor}.")
        sys.exit(1)
    ok(f"Python {py_ver.major}.{py_ver.minor}.{py_ver.micro}")

    if not os.path.isfile(SCRIPT):
        err(f"{SCRIPT} not found in the current directory.")
        err(f"Run this script from the same folder as {SCRIPT}.")
        sys.exit(1)
    ok(f"{SCRIPT} found.")

    # ── 1. Optional clean ─────────────────────────────────────────
    if args.clean:
        step(1, "Cleaning previous build artefacts")
        for folder in ("build", "dist", f"{APP_NAME}.spec"):
            if os.path.isdir(folder):
                shutil.rmtree(folder)
                ok(f"Removed {folder}/")
            elif os.path.isfile(folder):
                os.remove(folder)
                ok(f"Removed {folder}")
    else:
        step(1, "Skipping clean  (pass --clean to wipe build/ and dist/)")
        ok("Skipped.")

    # ── 2. Install dependencies ───────────────────────────────────
    if not args.no_install:
        step(2, "Installing required dependencies")
        pip_install(REQUIRED_DEPS)

        step(3, "Installing optional dependencies")
        pip_install(OPTIONAL_DEPS, optional=True)
    else:
        step(2, "Skipping dependency installation  (--no-install)")
        missing = [p for p in REQUIRED_DEPS if not is_installed(
            p.replace("-", "_"))]
        if missing:
            err(f"Missing required packages: {', '.join(missing)}")
            err("Run without --no-install to install them automatically.")
            sys.exit(1)
        ok("All required packages present.")

    # ── 3. Write requirements.txt ─────────────────────────────────
    step(4, "Writing requirements.txt")
    req_lines = REQUIRED_DEPS + OPTIONAL_DEPS
    with open("requirements.txt", "w") as f:
        f.write("# Generated by build.py\n")
        for pkg in req_lines:
            f.write(pkg + "\n")
    ok("requirements.txt written.")

    # ── 4. Build with PyInstaller ─────────────────────────────────
    step(5, f"Packaging {SCRIPT} with PyInstaller")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--clean",
        f"--name={APP_NAME}",
        # Hidden imports that PyInstaller may miss with pandas / prompt_toolkit
        "--hidden-import=pandas",
        "--hidden-import=pandas._libs.tslibs.np_datetime",
        "--hidden-import=pandas._libs.tslibs.nattype",
        "--hidden-import=pandas._libs.tslibs.timedeltas",
        "--hidden-import=pandas._libs.skiplist",
        "--hidden-import=prompt_toolkit",
        "--hidden-import=prompt_toolkit.completion",
        "--hidden-import=prompt_toolkit.formatted_text",
        "--hidden-import=prompt_toolkit.styles",
        "--hidden-import=colorama",
        "--hidden-import=unicodedata",
    ]

    # Optional: chardet hidden import if installed
    if is_installed("chardet"):
        cmd.append("--hidden-import=chardet")
        ok("chardet detected — will be bundled.")

    # Platform icon
    if os_name == "Windows" and ICON_WIN and os.path.isfile(ICON_WIN):
        cmd += [f"--icon={ICON_WIN}"]
        ok(f"Icon: {ICON_WIN}")
    elif os_name == "Darwin" and ICON_MAC and os.path.isfile(ICON_MAC):
        cmd += [f"--icon={ICON_MAC}"]
        ok(f"Icon: {ICON_MAC}")

    # Disable the console window on Windows only if explicitly wanted
    # (keep console open since this is a CLI app)
    # cmd.append("--noconsole")  # ← uncomment only for GUI apps

    cmd.append(SCRIPT)
    run(cmd)

    # ── 5. Verify output ──────────────────────────────────────────
    step(6, "Verifying output")

    if os.path.isfile(dist_exe):
        size_mb = os.path.getsize(dist_exe) / 1_048_576
        ok(f"Executable created:  {dist_exe}  ({size_mb:.1f} MB)")
    else:
        err(f"Expected executable not found at: {dist_exe}")
        err("Check PyInstaller output above for errors.")
        sys.exit(1)

    # ── 6. Assemble distribution folder ──────────────────────────
    step(7, "Assembling distribution package")

    dist_pkg = os.path.join("dist", "attendance_package")
    os.makedirs(dist_pkg, exist_ok=True)

    # Copy executable
    shutil.copy2(dist_exe, dist_pkg)
    ok(f"Copied {exe_name} → {dist_pkg}/")

    # Create a placeholder nomina.csv if one doesn't exist in dist yet
    nomina_src = "nomina.csv"
    nomina_dst = os.path.join(dist_pkg, "nomina.csv")
    if os.path.isfile(nomina_src):
        shutil.copy2(nomina_src, nomina_dst)
        ok(f"Copied nomina.csv → {dist_pkg}/")
    else:
        with open(nomina_dst, "w", encoding="utf-8-sig") as f:
            f.write("CÉDULA,APELLIDOS,NOMBRES\n")
        warn(
            f"nomina.csv not found in project root — a blank template was created at {nomina_dst}")

    # ── 7. Summary ────────────────────────────────────────────────
    banner("BUILD COMPLETE")
    print()
    print(f"  Executable : dist/{exe_name}")
    print(f"  Package    : {dist_pkg}/")
    print()
    print("  Deliver to the user:")
    print(f"    • {exe_name}")
    print(f"    • nomina.csv  (or their existing file)")
    print()
    if os_name == "Windows":
        print("  User runs:  double-click attendance.exe")
    else:
        print("  User runs:  ./attendance   (or double-click in file manager)")
    print()


if __name__ == "__main__":
    main()
