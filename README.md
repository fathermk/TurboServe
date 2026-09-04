# TurboServe

TurboServe is a portfolio project for measuring and improving large language model inference performance. The project will begin with a normal PyTorch baseline, optimize the same model with NVIDIA TensorRT-LLM, deploy it with Triton Inference Server, and compare latency, time to first token (TTFT), throughput, GPU utilization, VRAM use, and behavior under concurrent requests.

The project is intentionally being built in small, testable milestones. Dependencies and directories will be added only when a milestone needs them.

## Current status

**Milestone 3 — TensorRT-LLM comparison path (complete)**

The ordinary PyTorch baseline and an isolated NVIDIA TensorRT-LLM 1.2.1 path
both run TinyLlama on the RTX 3060 Ti. The first TensorRT-LLM smoke test produced
the same text at about 2.8 times the baseline output-token rate. This is an
initial result; controlled benchmarking remains Milestone 5. See
[`docs/milestone-3-tensorrt-llm.md`](docs/milestone-3-tensorrt-llm.md).

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

Milestone 3 is complete. Triton deployment is next; formal benchmarking,
concurrency testing, and monitoring remain later milestones.
