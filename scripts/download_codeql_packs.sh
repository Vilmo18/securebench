#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

CODEQL_BIN="${ROOT_DIR}/tools/codeql/codeql"
if [[ ! -x "${CODEQL_BIN}" ]]; then
  CODEQL_BIN="$(command -v codeql || true)"
fi

if [[ -z "${CODEQL_BIN}" || ! -x "${CODEQL_BIN}" ]]; then
  echo "CodeQL CLI not found. Install it first with: bash scripts/install_codeql.sh" >&2
  exit 1
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "GITHUB_TOKEN is not set. Export it in your shell before running this script." >&2
  echo "Example:" >&2
  echo "  export GITHUB_TOKEN=\"<YOUR_TOKEN>\"" >&2
  exit 1
fi

PACKS=("$@")
if [[ ${#PACKS[@]} -eq 0 ]]; then
  PACKS=(
    codeql/python-security-and-quality
    codeql/python-security-extended
    codeql/python-security-experimental
    codeql/python-code-scanning
    codeql/python-queries
    codeql/python-all
  )
fi

echo "Downloading CodeQL packs into the CodeQL package cache..."
echo "Packs:"
for p in "${PACKS[@]}"; do
  echo "  - ${p}"
done

# Avoid passing the token via argv; use stdin instead.
printf '%s' "${GITHUB_TOKEN}" | "${CODEQL_BIN}" pack download --github-auth-stdin -- "${PACKS[@]}"

echo "Done."
