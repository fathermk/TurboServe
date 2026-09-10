# Milestone 4: local Triton serving

## Verified result

On September 8, 2026, the user ran the repository launch and smoke-test
scripts on Ubuntu 24.04 under WSL2. Triton reported `tensorrt_llm` version 1
as READY and the HTTP generation endpoint returned:

```json
{"model_name":"tensorrt_llm","model_version":"1","text_output":"Low latency is important because it allows for real-time communication between the server and the client. This means that the server can respond to user requests quickly and accurately, which is essential"}
```

The request prompt was `Low latency is important because`, with a maximum
of 32 new tokens. The readiness check succeeded with an empty response body.
This proves functional serving; it does not establish latency, TTFT,
throughput, or concurrent-request performance. Clean shutdown has been
instructed but has not yet been confirmed in supplied output.

## Environment and dependencies

- NVIDIA RTX 3060 Ti, 8192 MiB VRAM, Windows driver 616.56.
- Ubuntu distribution stored at `M:\WSL\Ubuntu-24.04`; Docker data is inside it.
- Docker Engine 29.8.0 and NVIDIA Container Toolkit 1.20.0 were installed
  using the setup scripts. They are one-time system setup, not launch steps.
- Image: `nvcr.io/nvidia/tritonserver:26.07-trtllm-python-py3`.
- Verified image digest: `sha256:b097871d05da2e63178d1b91fd1199bc395f653ade4f05ab227c463ea7437007`.
- Triton 2.71.0; TensorRT-LLM 1.2.1 using its PyTorch backend.
- Model: `TinyLlama/TinyLlama-1.1B-Chat-v1.0`.
- NVIDIA template checkout: tag `v1.2.1`, commit
  `376f7e1bd8ed543f75014309e3fd4b237e9b0e73`, at
  `/mnt/m/Projects/TensorRT-LLM-v1.2.1`.
- Existing model cache: `/home/eggcorn/.cache/huggingface`.

The original deployment used these machine-specific paths. The launch script
now defaults to the current Ubuntu user's Hugging Face cache and the NVIDIA
checkout alongside this repository. Set `TURBOSERVE_HF_CACHE` and
`TURBOSERVE_TRTLLM_SOURCE` to override these paths (see README). The
template is an external checkout, mounted read-only; it is not vendored
into TurboServe. On another machine, obtain the same tag and adjust paths.
The container image is pinned by digest, but model revision and all
transitive Python dependencies are not pinned, so this is not yet a fully
reproducible benchmark environment.

## Run from two PowerShell terminals

Terminal 1:

```powershell
wsl -d Ubuntu-24.04 -- bash /mnt/m/Projects/TurboServe/scripts/start-triton-wsl.sh
```

Enter the Ubuntu sudo password locally. Wait for model READY and HTTP startup.
Terminal 2:

```powershell
wsl -d Ubuntu-24.04 -- bash /mnt/m/Projects/TurboServe/scripts/test-triton-wsl.sh
```

The test uses curl to check model readiness, then requests text generation.
HTTP errors and timeouts produce a failing exit status. It prints the response
for human inspection; it does not yet validate response content automatically.

Stop with Ctrl+C in Terminal 1. Docker's `--rm` removes the temporary container;
the image and model cache persist. Confirm shutdown in Terminal 2 with:

```powershell
wsl -d Ubuntu-24.04 -- sudo docker ps --filter name=turboserve-triton
```

There should be no running container row. Do not launch a second instance
while the named container is already running.

## How serving works

The client sends HTTP to port 8000. Triton passes the input to its Python
backend, which runs TensorRT-LLM and TinyLlama on the GPU. Generated text is
returned as JSON. The Python backend's CPU instance label does not mean
model computation is confined to the CPU. The model stays loaded between requests.

Host ports 8000 (HTTP), 8001 (gRPC), and 8002 (metrics) are published on
127.0.0.1 only. The container logs show 0.0.0.0 internally; Docker limits
the host-side published addresses. There is no web chat UI or authentication.

## Issues encountered

1. Image pulls failed twice with `tls: bad record MAC`. A subsequent pull
   succeeded after download-concurrency tuning was proposed. The logs do
   not establish the underlying TLS failure cause. The tuning script
   changes Docker configuration and restarts the daemon; do not rerun it
   during serving.
2. NVIDIA's launcher uses `subprocess.Popen` and exits. Used as the main
   Docker process, it let the container stop. The project script runs
   Triton in the foreground with `exec`.
3. The image bundled OpenAI SDK 1.107.3, which lacked `PartReasoningText`
   required by this TensorRT-LLM import path. Installing `openai==2.53.0`
   inside the temporary container allowed model initialization and the
   verified request. This repeats each launch and requires network access.
   It does not send the inference request to OpenAI.
4. Pip still reports missing `opencv-python-headless`; ModelOpt reports a
   Transformers compatibility warning. Startup also logs a CUDA helper
   error and attention/cache warnings. They did not prevent this smoke
   test, but are not evidence of a dependency-clean or production-ready image.

## Next milestone

Build controlled measurements with matching inputs, generation settings,
warmup, and timing definitions. Save structured run records before adding
the proposed performance investigation assistant. That assistant can later
use comparison tools and MCP to explain recorded evidence. No agent, MCP
server, or formal benchmark is implemented by this milestone.
