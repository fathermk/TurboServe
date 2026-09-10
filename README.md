# TurboServe

TurboServe is a Python portfolio project for serving a local language model and measuring its inference performance. It runs TinyLlama on an 8 GB NVIDIA RTX 3060 Ti through ordinary PyTorch, NVIDIA TensorRT-LLM, and Triton Inference Server. The goal is to make performance comparisons reproducible and explainable on a constrained consumer GPU.

The project is intentionally being built in small, testable milestones. Dependencies and directories will be added only when a milestone needs them.

## Current status

**Milestone 5 — benchmarking and results analysis (in progress)**

The ordinary PyTorch baseline and an isolated NVIDIA TensorRT-LLM 1.2.1 path
both run TinyLlama on the RTX 3060 Ti. On September 8, 2026, the Triton
deployment reached READY and returned generated text through its HTTP API.
See [`docs/milestone-4-triton-serving.md`](docs/milestone-4-triton-serving.md)
for the verified result, launch commands, and remaining limitations.

The project now includes sequential HTTP benchmarking, server-side time to
first token (TTFT), saved JSON run records, container configuration snapshots,
and a comparison tool that flags missing or mismatched evidence.
See [`docs/milestone-5-benchmarking.md`](docs/milestone-5-benchmarking.md).

## How it works

The client sends a prompt to Triton over local HTTP. Triton's Python backend
invokes TensorRT-LLM, which runs TinyLlama on the GPU and returns generated text.
The benchmark records individual response timings, then checks that the
container and selected configuration stayed consistent during the run.
The comparison tool reads saved results without making new inference requests.

## Run on the configured development machine

These commands target Windows PowerShell and the existing Ubuntu-24.04 WSL
installation. Setup is machine-specific: the repository is on M:, NVIDIA's
v1.2.1 template checkout is alongside it, and the model cache belongs to the
Ubuntu user `eggcorn`. New users should read the milestone documents before
running setup scripts; they install system packages and configure Docker.

Terminal 1 starts the server; leave it open and wait for `READY`:

```powershell
wsl -d Ubuntu-24.04 -- bash /mnt/m/Projects/TurboServe/scripts/start-triton-wsl.sh
```

Terminal 2 checks generation, or runs a short benchmark with container evidence:

```powershell
wsl -d Ubuntu-24.04 -- bash /mnt/m/Projects/TurboServe/scripts/test-triton-wsl.sh
wsl -d Ubuntu-24.04 -- bash /mnt/m/Projects/TurboServe/scripts/benchmark-with-runtime-wsl.sh
```

The benchmark uses one warmup and five measured requests by default. Results
are saved under `results/`, which is excluded from Git. Prompts and responses
are included in these files; review them before sharing. Stop the server with
Ctrl+C in Terminal 1. HTTP, gRPC and metrics ports are published on loopback only.

Compare two saved records inside Ubuntu (replace FIRST.json and SECOND.json):

```bash
python3 /mnt/m/Projects/TurboServe/scripts/compare_runs.py FIRST.json SECOND.json
```

Run offline tests from PowerShell without loading a model:

```powershell
wsl -d Ubuntu-24.04 -- python3 -m unittest discover -s /mnt/m/Projects/TurboServe/scripts -p 'test_*.py'
```

## Evidence and limitations

Two five-request runs with matching recorded settings had median HTTP completion
times of 199.46 ms and 631.64 ms, with server-side TTFT of 18.42 ms and 30.81 ms.
This variation is unresolved; it is not a demonstrated optimization result.
The records do not include GPU utilization, clocks, temperature, or concurrent
desktop activity during measurement. Full HTTP completion time and server-side
TTFT are different measurements; client-observed streaming TTFT is not measured.

The selected configuration pins a cached TinyLlama snapshot, requests float16,
uses a 30% free-memory KV-cache budget, and disables cross-request block reuse.
Container inspection records declared settings, not loaded-tensor introspection.
Actual output-token accounting, controlled cross-backend comparisons and
concurrency testing remain incomplete. The startup script also applies a pinned
OpenAI SDK correction inside each temporary container; it needs network access.

## Project map

- `src/turboserve/`: standalone PyTorch and TensorRT-LLM runners.
- `configs/triton-model.yaml`: explicit Triton LLM configuration.
- `scripts/`: setup, serving, benchmarking, evidence capture, comparisons and tests.
- `docs/`: milestone decisions, verified results and known limitations.

Future work includes a performance investigation assistant that calls these
comparison tools and explains their evidence. MCP and agent integration are
planned extensions, not implemented features.

## Run the Windows/WSL assessment

Open PowerShell on the Windows development PC, change to this repository, and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\assess-environment.ps1
```

`Set-ExecutionPolicy -Scope Process Bypass` applies only to that PowerShell window. The assessment script does not install or configure anything; it prints system and tool information so we can decide what Milestone 2 actually needs.

Review the output before sharing it publicly. The script avoids intentionally collecting serial numbers, product keys, environment variables, or credentials.

## Milestones

1. Environment assessment and repository foundation
2. Reproducible PyTorch inference baseline
3. TensorRT-LLM optimization of the same model
4. Triton Inference Server deployment
5. Benchmarking, concurrency testing, and results analysis

Triton serving is verified. Benchmarking is underway. A future
performance investigation assistant will use saved measurements and comparison
tools; it has not been implemented yet.
