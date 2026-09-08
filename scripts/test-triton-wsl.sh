#!/usr/bin/env bash
set -euo pipefail

# A functional smoke test, not a benchmark. HTTP failures produce a nonzero exit.
echo 'Checking TinyLlama model readiness...'
curl --fail-with-body --silent --show-error --max-time 10 \
  http://127.0.0.1:8000/v2/models/tensorrt_llm/ready
echo
echo 'Requesting up to 32 new tokens...'
curl --fail-with-body --silent --show-error --max-time 120 \
  http://127.0.0.1:8000/v2/models/tensorrt_llm/generate \
  -H 'Content-Type: application/json' \
  -d '{"text_input":"Low latency is important because","sampling_param_max_tokens":32}'
echo
