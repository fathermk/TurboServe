# TurboServe

TurboServe is a portfolio project for measuring and improving large language model inference performance. The project will begin with a normal PyTorch baseline, optimize the same model with NVIDIA TensorRT-LLM, deploy it with Triton Inference Server, and compare latency, time to first token (TTFT), throughput, GPU utilization, VRAM use, and behavior under concurrent requests.

The project is intentionally being built in small, testable milestones. Dependencies and directories will be added only when a milestone needs them.

## Current status

**Milestone 1 — Environment assessment and repository foundation**

The target Windows 11 / RTX 3060 Ti development PC has been assessed directly. The GPU and NVIDIA driver are working on Windows, while WSL2, Ubuntu, Windows/WSL Python, Docker, and WSL GPU access are not yet available or verifiable. See [`docs/milestone-1-environment.md`](docs/milestone-1-environment.md) for the evidence, explanations, and deliberately deferred setup decisions.

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

Only Milestone 1 is in scope today.
