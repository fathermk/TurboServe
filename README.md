# TurboServe

TurboServe is a portfolio project for measuring and improving large language model inference performance. The project will begin with a normal PyTorch baseline, optimize the same model with NVIDIA TensorRT-LLM, deploy it with Triton Inference Server, and compare latency, time to first token (TTFT), throughput, GPU utilization, VRAM use, and behavior under concurrent requests.

The project is intentionally being built in small, testable milestones. Dependencies and directories will be added only when a milestone needs them.

## Current status

**Milestone 4 — Triton serving (functional test passed)**

The ordinary PyTorch baseline and an isolated NVIDIA TensorRT-LLM 1.2.1 path
both run TinyLlama on the RTX 3060 Ti. On September 8, 2026, the Triton
deployment reached READY and returned generated text through its HTTP API.
See [`docs/milestone-4-triton-serving.md`](docs/milestone-4-triton-serving.md)
for the verified result, launch commands, and remaining limitations.

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

Triton serving is verified. Controlled benchmarking is next. A future
performance investigation assistant will use saved measurements and comparison
tools; it has not been implemented yet.
