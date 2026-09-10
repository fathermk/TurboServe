#!/usr/bin/env bash
set -euo pipefail
PROJECT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
# Authenticate locally; Python's Docker diagnostics use noninteractive sudo.
sudo -v
exec python3 "$PROJECT/scripts/benchmark_triton.py" --capture-runtime "$@"
