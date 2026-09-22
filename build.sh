#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

APP_NAME="wled-pc"
ENTRY_POINT="main.py"
LOG_FILE="${PROJECT_ROOT}/build_$(date +%Y%m%d_%H%M%S).log"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "[*] wled-pc build script"
echo "[*] project root: $PROJECT_ROOT"
echo "[*] log file: $LOG_FILE"

# linux or no
if [[ "$(uname -s)" != "Linux" ]]; then
    echo "[!] this build script only targets Linux (matches main.py's platform check)."
    echo "[!] building on $(uname -s) is not supported."
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo "[!] python3 not found. install it first."
    exit 1
fi

echo "[*] python: $(python3 --version)"

# deps
echo "[*] ensuring build deps are installed..."
python3 -m pip install --quiet --break-system-packages pyinstaller aiohttp

UPX_FLAG=()
if command -v upx &>/dev/null; then
    echo "[*] upx found ($(upx --version | head -n1)), will compress the binary"
else
    echo "[i] upx not found - binary will be larger than necessary."
    echo "[i] install it for a smaller build: apt install upx-ucl  (or: dnf install upx)"
    UPX_FLAG=(--noupx)
fi

# fuck previous builds
echo "[*] cleaning previous build artifacts..."
rm -rf build dist "${APP_NAME}.spec" "${APP_NAME}"

# build
echo "[*] building optimized binary..."

pyinstaller "$ENTRY_POINT" \
    --name "$APP_NAME" \
    --onefile \
    --strip \
    "${UPX_FLAG[@]}" \
    --clean \
    --noconfirm \
    --console \
    \
    --exclude-module tkinter \
    --exclude-module sqlite3 \
    --exclude-module unittest \
    --exclude-module test \
    --exclude-module lib2to3 \
    --exclude-module multiprocessing \
    --exclude-module curses \
    --exclude-module pydoc_data \
    --exclude-module xmlrpc \
    --exclude-module idlelib \
    --exclude-module turtledemo \
    \
    --hidden-import aiohttp

# report
echo ""
if [[ -f "dist/${APP_NAME}" ]]; then
    SIZE=$(du -h "dist/${APP_NAME}" | cut -f1)
    echo "[+] build complete: dist/${APP_NAME}  (${SIZE})"

    echo "[*] moving binary to project root..."
    mv "dist/${APP_NAME}" "${PROJECT_ROOT}/${APP_NAME}"
    chmod +x "${PROJECT_ROOT}/${APP_NAME}"
else
    echo "[!] build finished but output binary not found - check the log above."
    exit 1
fi

echo "[*] cleaning up build/, dist/ and spec file..."
rm -rf build dist "${APP_NAME}.spec"

echo "[+] done. binary: ${PROJECT_ROOT}/${APP_NAME}"
echo "[+] run it with: ./${APP_NAME}"
echo "[+] build log saved to: ${LOG_FILE}"