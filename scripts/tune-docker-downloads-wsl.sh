#!/usr/bin/env bash
set -euo pipefail

# Reduce parallel layer downloads for unreliable WSL/network transfers.
# Preserve the NVIDIA runtime settings written by nvidia-ctk.
CONFIG=/etc/docker/daemon.json
BACKUP="${CONFIG}.before-turboserve-download-tuning"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or is not on PATH." >&2
  exit 1
fi

running_containers=$(sudo docker ps -q)
if [[ -n "$running_containers" ]]; then
  echo "Stop running containers deliberately before restarting Docker." >&2
  exit 1
fi

if sudo test -f "$CONFIG" && ! sudo test -f "$BACKUP"; then
  sudo cp "$CONFIG" "$BACKUP"
fi

sudo python3 - "$CONFIG" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
try:
    data = json.loads(path.read_text()) if path.exists() else {}
except json.JSONDecodeError as exc:
    raise SystemExit(f"Cannot parse {path}: {exc}")
data["max-concurrent-downloads"] = 1
path.write_text(json.dumps(data, indent=2) + "\n")
PY

sudo systemctl restart docker
echo "Docker download concurrency set to 1. Existing image layers will be reused."
