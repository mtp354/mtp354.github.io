#!/usr/bin/env bash
# Ubuntu/Linux launcher. Installs only inside this project, never with sudo.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."
ctf_open=1
ctf_lan=0
export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-2567}"
for ctf_arg in "$@"; do
  case "$ctf_arg" in
    --no-open) ctf_open=0 ;;
    --lan) export HOST=0.0.0.0; ctf_lan=1 ;;
    --help) echo 'Usage: ./play-ctf.sh [--lan] [--no-open]'; exit 0 ;;
    *) echo "Unknown option: $ctf_arg" >&2; exit 1 ;;
  esac
done
mkdir -p .runtime
if ! command -v node >/dev/null || ! node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 22 ? 0 : 1)' 2>/dev/null; then
  if [ ! -x .runtime/node/bin/node ]; then
    case "$(uname -sm)" in
      'Linux x86_64') ctf_arch=x64 ;;
      'Linux aarch64') ctf_arch=arm64 ;;
      *) echo 'Install Node.js 22 or newer, then run this launcher again.' >&2; exit 1 ;;
    esac
    command -v curl >/dev/null || { echo 'curl is required to download Node.js.' >&2; exit 1; }
    ctf_node_version=v22.23.2
    ctf_archive="node-${ctf_node_version}-linux-${ctf_arch}.tar.xz"
    echo 'Installing a private Node.js runtime into .runtime/node (first launch only)...'
    curl --fail --location --retry 2 "https://nodejs.org/dist/${ctf_node_version}/${ctf_archive}" -o ".runtime/${ctf_archive}"
    curl --fail --location --retry 2 "https://nodejs.org/dist/${ctf_node_version}/SHASUMS256.txt" -o .runtime/SHASUMS256.txt
    (cd .runtime; awk -v file="$ctf_archive" '$2 == file {print}' SHASUMS256.txt | sha256sum --check --status)
    mkdir -p .runtime/node
    tar -xJf ".runtime/${ctf_archive}" --strip-components=1 -C .runtime/node
    rm ".runtime/${ctf_archive}"
  fi
  export PATH="$PWD/.runtime/node/bin:$PATH"
fi
export VITE_BASE_PATH="${VITE_BASE_PATH:-${CTF_BASE_PATH:-/}}"
export CTF_BASE_PATH="${CTF_BASE_PATH:-$VITE_BASE_PATH}"
ctf_origin="http://localhost:${PORT}"
ctf_path="/${CTF_BASE_PATH#/}"
ctf_url="${ctf_origin}${ctf_path%/}/"
if node --input-type=module -e 'const r=await fetch(process.argv[1]+"/health",{signal:AbortSignal.timeout(1500)}); const j=await r.json(); process.exit(j.service==="ctf"?0:1)' "$ctf_origin" >/dev/null 2>&1; then
  if [ "$ctf_lan" = 1 ]; then
    echo 'A game is already running. To restart in LAN mode, stop its terminal with Ctrl+C, then run ./play-ctf.sh --lan again.'
    exit 1
  fi
  echo "Your game is already running: $ctf_url"
  if [ "$ctf_open" = 1 ] && command -v xdg-open >/dev/null; then xdg-open "$ctf_url" >/dev/null 2>&1 || true; fi
  exit 0
fi
ctf_lock_hash="$(sha256sum package-lock.json | cut -d ' ' -f 1)"
if [ ! -d node_modules ] || [ ! -f .runtime/installed-lock ] || [ "$(cat .runtime/installed-lock)" != "$ctf_lock_hash" ]; then
  echo 'Installing locked game dependencies (first launch or dependency update)...'
  npm ci --cache .npm-cache --no-fund --no-audit
  echo "$ctf_lock_hash" > .runtime/installed-lock
fi
echo 'Building Capture the Flag...'
npm run build
if [ "$ctf_open" = 1 ] && command -v xdg-open >/dev/null; then
  (
    for ctf_attempt in {1..60}; do
      if node --input-type=module -e 'const r=await fetch(process.argv[1]+"/health",{signal:AbortSignal.timeout(1500)}); process.exit(r.ok?0:1)' "$ctf_origin" >/dev/null 2>&1; then
        xdg-open "$ctf_url" >/dev/null 2>&1 || true
        exit 0
      fi
      sleep 0.5
    done
  ) &
fi
echo "Open $ctf_url and select Play practice, or create a room and share its link."
echo 'Keep this terminal open. Press Ctrl+C to stop the game.'
exec node apps/server/dist/index.js
