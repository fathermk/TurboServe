#!/usr/bin/env bash
set -euo pipefail

# Run from Ubuntu. The foreground server stops when you press Ctrl+C.
IMAGE='nvcr.io/nvidia/tritonserver@sha256:b097871d05da2e63178d1b91fd1199bc395f653ade4f05ab227c463ea7437007'
SOURCE='/mnt/m/Projects/TensorRT-LLM-v1.2.1'
CACHE='/home/eggcorn/.cache/huggingface'
if [[ ! -f "$SOURCE/triton_backend/all_models/llmapi/tensorrt_llm/1/model.yaml" ]]; then
  echo "Missing NVIDIA model template in $SOURCE" >&2
  exit 1
fi
if [[ ! -d "$CACHE" ]]; then
  echo "Missing Hugging Face cache: $CACHE" >&2
  exit 1
fi

# Loopback-only publishing keeps the endpoints local to this PC.
# The SDK correction is temporary and repeats on each container start.
exec sudo docker run --rm -it --name turboserve-triton \
  --gpus all --shm-size=2g --ulimit memlock=-1 \
  -p 127.0.0.1:8000:8000 \
  -p 127.0.0.1:8001:8001 \
  -p 127.0.0.1:8002:8002 \
  --mount "type=bind,source=$CACHE,target=/root/.cache/huggingface" \
  --mount "type=bind,source=$SOURCE,target=/workspace/TensorRT-LLM,readonly" \
  "$IMAGE" bash -lc '
    python3 -m pip install --no-cache-dir openai==2.53.0 &&
    cd /workspace &&
    exec /opt/tritonserver/bin/tritonserver \
      --model-repository=/workspace/TensorRT-LLM/triton_backend/all_models/llmapi/ \
      --disable-auto-complete-config \
      --backend-config=python,shm-region-prefix-name=prefix0_
  '
