#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="${ROOT_DIR}/tools"
DEST_DIR="${TOOLS_DIR}/codeql"

mkdir -p "${TOOLS_DIR}"

fix_permissions() {
  if [[ -f "${DEST_DIR}/codeql" ]]; then
    chmod +x "${DEST_DIR}/codeql" || true
  fi

  # Zip extraction doesn't preserve unix executable bits via Python's zipfile module.
  # Ensure CodeQL helper scripts and binaries are executable.
  find "${DEST_DIR}" -type f -path "*/bin/*" -exec chmod +x {} + 2>/dev/null || true
  find "${DEST_DIR}" -type f -path "*/tools/linux64/*" -exec chmod +x {} + 2>/dev/null || true
  find "${DEST_DIR}" -type f -name "*.sh" -exec chmod +x {} + 2>/dev/null || true
}

if [[ -x "${DEST_DIR}/codeql" || -x "${DEST_DIR}/codeql.exe" ]]; then
  echo "CodeQL already installed at: ${DEST_DIR}"
  fix_permissions
  "${DEST_DIR}/codeql" version 2>/dev/null || true
  exit 0
fi

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m | tr '[:upper:]' '[:lower:]')"

ASSET=""
case "${OS}" in
  linux)
    ASSET="codeql-linux64.zip"
    ;;
  darwin)
    if [[ "${ARCH}" == "arm64" || "${ARCH}" == "aarch64" ]]; then
      ASSET="codeql-osx-arm64.zip"
    else
      ASSET="codeql-osx64.zip"
    fi
    ;;
  msys*|mingw*|cygwin*)
    ASSET="codeql-win64.zip"
    ;;
  *)
    echo "Unsupported OS for this installer: ${OS}" >&2
    exit 1
    ;;
esac

URL="https://github.com/github/codeql-cli-binaries/releases/latest/download/${ASSET}"

TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "${TMP_DIR}"; }
trap cleanup EXIT

ZIP_PATH="${TMP_DIR}/codeql.zip"
echo "Downloading CodeQL CLI: ${URL}"
curl -L --fail --retry 3 --retry-delay 2 -o "${ZIP_PATH}" "${URL}"

echo "Extracting..."
python3 - "${ZIP_PATH}" "${TMP_DIR}" <<'PY'
import sys
import zipfile

zip_path = sys.argv[1]
out_dir = sys.argv[2]

with zipfile.ZipFile(zip_path, "r") as z:
    z.extractall(out_dir)
PY

SRC_DIR=""
if [[ -d "${TMP_DIR}/codeql" ]]; then
  SRC_DIR="${TMP_DIR}/codeql"
else
  # Fallback: find a directory that contains the codeql binary.
  if [[ "${OS}" == "msys"* || "${OS}" == "mingw"* || "${OS}" == "cygwin"* ]]; then
    BIN_NAME="codeql.exe"
  else
    BIN_NAME="codeql"
  fi
  FOUND="$(find "${TMP_DIR}" -maxdepth 3 -type f -name "${BIN_NAME}" -print -quit || true)"
  if [[ -n "${FOUND}" ]]; then
    SRC_DIR="$(cd "$(dirname "${FOUND}")/.." && pwd)"
  fi
fi

if [[ -z "${SRC_DIR}" || ! -d "${SRC_DIR}" ]]; then
  echo "Failed to locate extracted CodeQL directory." >&2
  exit 1
fi

rm -rf "${DEST_DIR}"
mv "${SRC_DIR}" "${DEST_DIR}"

fix_permissions

echo "Installed CodeQL to: ${DEST_DIR}"
echo "Add to PATH for this shell:"
echo "  export PATH=\"${DEST_DIR}:\$PATH\""
echo "Verify:"
echo "  codeql version"
