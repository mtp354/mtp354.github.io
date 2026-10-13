#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/capture-the-flag/ctf-browser-starter"
exec bash scripts/play.sh "$@"
