#!/usr/bin/env bash
set -euo pipefail

# Read-only diagnostics. Do not dump environment variables or full Docker inspect.
CONTAINER=turboserve-triton
sudo docker inspect "$CONTAINER" --format \
  'Container={{.Id}} Image={{.Image}} Started={{.State.StartedAt}} Running={{.State.Running}}'
sudo docker exec -i "$CONTAINER" python3 - <<'PY'
import importlib.metadata
import json
import os
from pathlib import Path

import yaml

config_path = Path(os.environ.get('LLM_CONFIG_PATH', '/workspace/TensorRT-LLM/triton_backend/all_models/llmapi/tensorrt_llm/1/model.yaml'))
report = {'package_versions': {}, 'configured_model_yaml': yaml.safe_load(config_path.read_text()),
          'cached_model_candidates': [],
          'limitations': ['Current YAML and cached files do not prove effective loaded state',
                          'No inference or new model loading is performed']}
for package in ['tensorrt-llm', 'torch', 'transformers', 'openai', 'tensorrt']:
    try:
        report['package_versions'][package] = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        report['package_versions'][package] = None

cache = Path('/root/.cache/huggingface/hub/models--TinyLlama--TinyLlama-1.1B-Chat-v1.0')
for snapshot in sorted((cache / 'snapshots').glob('*')):
    config = snapshot / 'config.json'
    if config.is_file():
        data = json.loads(config.read_text())
        report['cached_model_candidates'].append({
            'revision': snapshot.name,
            'model_type': data.get('model_type'),
            'checkpoint_declared_dtype': data.get('dtype', data.get('torch_dtype')),
            'note': 'Checkpoint metadata; not necessarily runtime precision'})
print(json.dumps(report, indent=2))
PY

echo 'Selected startup log evidence (not a live allocator measurement):'
sudo docker logs "$CONTAINER" 2>&1 | \
  grep -E 'starting trtllm engine with args|Allocated .*paged KV cache|Max KV cache blocks per sequence|Model init total|successfully loaded' || {
    echo 'No matching startup lines available, or log retrieval failed.'
  }
