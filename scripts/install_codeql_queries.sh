#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="${ROOT_DIR}/tools"
DEST_DIR="${TOOLS_DIR}/codeql-repo"

mkdir -p "${TOOLS_DIR}"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required to install CodeQL query packs." >&2
  exit 1
fi

CODEQL_BIN="${ROOT_DIR}/tools/codeql/codeql"
if [[ ! -x "${CODEQL_BIN}" ]]; then
  CODEQL_BIN="$(command -v codeql || true)"
fi

CODEQL_VERSION=""
if [[ -n "${CODEQL_BIN}" && -x "${CODEQL_BIN}" ]]; then
  CODEQL_VERSION="$("${CODEQL_BIN}" version 2>/dev/null | head -n 1 | sed -E 's/.*release ([0-9.]+).*/\1/' | sed -E 's/[.]+$//' || true)"
fi

REF="${CODEQL_QUERIES_REF:-}"
if [[ -z "${REF}" ]]; then
  if [[ -n "${CODEQL_VERSION}" ]]; then
    REF="codeql-cli/v${CODEQL_VERSION}"
  else
    REF="codeql-cli/v2.24.1"
  fi
fi

REPO_URL="${CODEQL_QUERIES_REPO:-https://github.com/github/codeql.git}"

if [[ -d "${DEST_DIR}/.git" ]]; then
  echo "CodeQL query repo already present at: ${DEST_DIR}"
  echo "If you need a different version, delete it and rerun this script."
  exit 0
fi

echo "Cloning CodeQL queries (${REF}) into: ${DEST_DIR}"
git clone --depth 1 --branch "${REF}" --filter=blob:none --sparse "${REPO_URL}" "${DEST_DIR}"

echo "Configuring sparse checkout (python + shared + suite-helpers)..."
git -C "${DEST_DIR}" sparse-checkout set python shared misc/suite-helpers

echo "Installed CodeQL query packs to: ${DEST_DIR}"
echo "You can now point CodeQL to this repo via --search-path or configs.yml:"
echo "  sast:"
echo "    codeql:"
echo "      search_path: tools/codeql-repo"
echo "      queries:"
echo "        - tools/codeql-repo/python/ql/src/codeql-suites/python-security-extended.qls"
