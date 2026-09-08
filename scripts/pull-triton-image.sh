#!/usr/bin/env bash
set -euo pipefail

# Milestone 4 pins the Triton image to the release carrying TensorRT-LLM 1.2.1,
# matching the host runner documented in Milestone 3.
IMAGE="nvcr.io/nvidia/tritonserver:26.07-trtllm-python-py3"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or is not on PATH." >&2
  exit 1
fi

echo "Pulling $IMAGE (approximately 14.2 GB; stored in Docker's WSL data root)..."
sudo docker pull "$IMAGE"

echo
echo "Image pulled successfully. Exact local image reference:"
sudo docker image inspect "$IMAGE" --format '{{.Id}}'
