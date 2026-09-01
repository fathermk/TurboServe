# Milestone 1 environment assessment

Assessment date: 2026-09-01

## Scope and evidence boundary

The active Codex shell is running on a MacBook Air, not on the target Windows 11 development PC. The target PC cannot be inspected remotely from this shell. Results below are therefore labeled **verified on attached host**, **reported by project owner**, or **pending direct verification**.

## Target development PC

| Check | Current result | How it will be verified |
| --- | --- | --- |
| Windows version and architecture | Windows 11 reported; exact edition, build, and architecture pending | PowerShell/CIM output |
| NVIDIA GPU | RTX 3060 Ti with 8 GB VRAM reported; exact detection pending | Windows device inventory and `nvidia-smi` |
| NVIDIA driver | Pending | `nvidia-smi` on Windows |
| WSL2 | Pending | `wsl --status`, `wsl --version`, and `wsl --list --verbose` |
| Ubuntu distribution | Pending | WSL distribution list and `/etc/os-release` |
| NVIDIA GPU access from WSL2 | Pending | `nvidia-smi` inside each WSL distribution |
| Python and pip | Pending | Version and command-path checks on Windows and inside WSL |
| Git installation/configuration | Pending | Version and presence of global identity settings |
| Docker/Docker Desktop | Pending | CLI, daemon, application, and WSL-side checks |
| CUDA-related tooling | Pending | `nvidia-smi`, `nvcc`, and command-path checks |

Run `scripts/assess-environment.ps1` in PowerShell on the target PC to replace the pending entries with evidence. The script is read-only.

## Attached Codex host (verified)

These facts describe the machine hosting this Codex task. They do **not** establish readiness of the target PC:

- macOS 26.6.2 on ARM64
- Apple M4 MacBook Air with 16 GB unified memory and integrated Apple GPU
- Python 3.14.3 and pip 26.0
- Git 2.33.0; global name and email are configured
- Docker CLI 29.2.1 and Docker Desktop application are present, but the Docker daemon is not running
- No `nvidia-smi`, `nvcc`, WSL, PowerShell, or NVIDIA/CUDA hardware tooling was found

The Mac cannot validate the NVIDIA deployment path because it has neither the RTX GPU nor Windows/WSL. It can still be useful later for documentation and CPU-only repository work.

## What the tools are for

- **NVIDIA driver:** lets Windows and WSL communicate with the RTX GPU. A sufficiently recent Windows driver is the foundation for GPU compute in WSL2.
- **WSL2:** runs a real Linux kernel alongside Windows. TensorRT-LLM and Triton are most naturally used in their Linux/container ecosystem.
- **Ubuntu:** provides the Linux user space, shell, package manager, and libraries used by the project.
- **`nvidia-smi`:** reports whether the NVIDIA driver can see the GPU and shows driver version, VRAM usage, utilization, and running GPU processes. It is also a quick WSL GPU-pass-through test.
- **Python:** will hold the baseline inference and benchmarking code. We will choose a supported version rather than automatically using whatever is newest.
- **pip:** installs Python packages into an isolated environment. No project packages are being installed in Milestone 1.
- **Git:** records small, explainable changes so each milestone can be reviewed, reverted, and presented on GitHub.
- **Docker Desktop:** provides the container engine on Windows and integrates it with WSL2. Containers will later help make Triton and TensorRT-LLM environments repeatable.
- **CUDA toolkit / `nvcc`:** CUDA is NVIDIA's GPU-computing platform, and `nvcc` is its compiler. The full Windows toolkit may not be needed because containers can carry user-space CUDA libraries; driver capability matters first. We will decide after collecting evidence.

## Decisions deliberately deferred

Milestone 1 does not install CUDA, PyTorch, TensorRT-LLM, Triton, model weights, monitoring tools, or benchmark frameworks. Version choices must be made together later because GPU architecture, 8 GB VRAM, driver compatibility, framework support, and container support all constrain one another.
