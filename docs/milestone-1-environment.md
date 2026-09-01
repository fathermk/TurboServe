# Milestone 1 environment assessment

Assessment date: 2026-09-01

## Scope and evidence

This assessment was run directly on the target Windows development PC from the
TurboServe repository. The commands were read-only: they inspected operating
system metadata, command availability, installed-tool locations, and GPU status.
No software was installed and no system settings were changed.

The main evidence came from `scripts/assess-environment.ps1`, run by the project
owner in a normal PowerShell window and collected at
`2026-09-01T15:58:02-04:00`. A few additional read-only PowerShell checks were
used to confirm command paths, installed-tool locations, and release metadata.

## Verified results

| Check | Verified result | Evidence and interpretation |
| --- | --- | --- |
| Windows version | Microsoft Windows 11 Pro, release 25H2, version 10.0.26200, build 26200.9278 | The assessment's CIM query directly identified Windows 11 Pro and build 26200. Additional registry evidence supplied release 25H2 and update build revision (UBR) 9278. |
| Architecture | 64-bit Windows on an x64-based PC | The assessment's CIM query reported `OSArchitecture: 64-bit` and `SystemType: x64-based PC`; runtime evidence also reported AMD64. |
| NVIDIA GPU | NVIDIA GeForce RTX 3060 Ti, 8,192 MiB VRAM, compute capability 8.6 | Both Windows CIM inventory and `nvidia-smi` detected the GPU. It used the WDDM driver model and was driving a display. |
| NVIDIA driver | Installed and working; NVIDIA-SMI/KMD 616.56, Windows inventory version 32.0.16.1656 | `C:\Windows\System32\nvidia-smi.exe` ran successfully and reported CUDA UMD capability 13.4. The displayed CUDA value is the driver's supported CUDA level, not proof that a CUDA toolkit is installed. |
| WSL2 | Not installed/configured | `wsl.exe --status`, `--version`, and `--list --verbose` all reported that Windows Subsystem for Linux is not installed. The executable's presence alone does not mean WSL is configured. |
| Ubuntu/Linux | Not installed as a WSL distribution | WSL reported no distributions. An all-users Appx inventory check was access-denied, but the authoritative WSL distribution list was empty. |
| NVIDIA GPU inside WSL2 | Not testable yet | There is no working WSL installation or Linux distribution in which to run `nvidia-smi`. Windows GPU detection does not by itself prove WSL GPU pass-through. |
| Windows Python and pip | Not usable from the command line | `py.exe`, `python.exe`, `python3`, `pip.exe`, and `pip3` were not found on `PATH`. The uninstall registry contains `Python Launcher 3.13.150.0`, but its command is not resolvable; this does not establish a usable Python interpreter or pip installation. |
| WSL Python and pip | Not testable yet | No WSL distribution exists. |
| Git | Ready: Git 2.48.1 for Windows | `C:\Program Files\Git\cmd\git.exe` ran successfully. Global `user.name` and `user.email` are both configured; their values were intentionally not recorded. |
| Docker / Docker Desktop | Not found; daemon therefore unavailable | `docker.exe` was not on `PATH`, standard Docker Desktop executable paths were absent, no Docker service was found, and no matching installed-program registry entry was found. |
| CUDA-related tooling | NVIDIA driver tooling only | `nvidia-smi.exe` is available. `nvcc.exe`, the usual CUDA toolkit directory, and CUDA toolkit registry entries were not found. No standalone CUDA toolkit was verified. |

The first WSL-unavailable run exposed a script edge case: error text from
`wsl.exe --list --quiet` could be mistaken for distribution names, leading to
repeated interactive installation prompts. No installation occurred; the prompts
were aborted. The script now checks `wsl.exe --status` and skips later WSL
commands when WSL is not ready, preserving its read-only, non-interactive intent.

## What the tools are for

- **NVIDIA driver:** lets Windows communicate with the RTX GPU and provides the
  host-side foundation for GPU access from WSL2. The working Windows driver is a
  strong starting point, but WSL GPU access still needs its own test after WSL is
  installed.
- **WSL2:** runs a Linux kernel alongside Windows. TensorRT-LLM and Triton are
  designed primarily for Linux and container workflows, so TurboServe will use
  WSL2 rather than trying to force the whole stack into native Windows.
- **Ubuntu:** supplies the Linux command line, package manager, and libraries in
  which the project's GPU and container work can run.
- **`nvidia-smi`:** confirms that the NVIDIA driver sees the GPU. It also reports
  driver version, VRAM use, utilization, temperature, and GPU processes. Later,
  running it inside WSL will verify GPU pass-through.
- **Python:** will run the PyTorch baseline, benchmark harness, and supporting
  scripts. Milestone 2 should choose a version supported by the selected PyTorch
  stack rather than installing an arbitrary latest release.
- **pip:** installs Python packages into an isolated virtual environment. It is
  absent today because no TurboServe Python environment has been created yet.
- **Git:** records each small, reviewable milestone. This makes the project easy
  to explain, reproduce, compare, and safely revise.
- **Docker Desktop / Docker Engine:** runs reproducible containers and integrates
  them with WSL2. Containers are likely to simplify later TensorRT-LLM and Triton
  compatibility, but Docker is not required to document Milestone 1.
- **CUDA toolkit / `nvcc`:** CUDA is NVIDIA's GPU-computing platform and `nvcc`
  compiles CUDA code. A local toolkit is not automatically required: supported
  containers can provide user-space CUDA libraries while relying on the Windows
  NVIDIA driver. Its need and exact version are deliberately deferred.

## Readiness and problems discovered

The Windows GPU and Git foundation are healthy. The main blocker for Linux/NVIDIA
development is that WSL2 is not installed. As a consequence, Ubuntu, WSL-side
Python, WSL-side Docker, and GPU pass-through cannot yet be checked. Native
Windows also lacks a usable Python/pip command, Docker Desktop, and a standalone
CUDA toolkit.

These are findings, not installation instructions. Before Milestone 2 begins,
the next environment-preparation proposal should be reviewed in this order:

1. Enable/install WSL2 and an Ubuntu distribution, then restart if Windows asks.
2. Verify the distribution is using WSL version 2 and run `nvidia-smi` inside it.
3. Choose a supported Linux Python version and isolated-environment approach for
   the PyTorch baseline.
4. Decide whether Docker Desktop is needed immediately or can wait until the
   TensorRT-LLM/Triton container milestones.
5. Install a standalone CUDA toolkit only if the chosen, documented workflow
   actually requires it.

## Decisions deliberately deferred

Milestone 1 does not install or configure WSL, Ubuntu, Python, pip, Docker, CUDA,
PyTorch, TensorRT-LLM, Triton, model weights, monitoring tools, or benchmark
frameworks. Version choices must be made together later because the RTX 3060 Ti's
compute capability and 8 GB VRAM, driver compatibility, framework support, model
size, and container support constrain one another.

Milestone 2 will establish a reproducible, ordinary PyTorch inference baseline
for one deliberately small model and record initial correctness and performance
measurements. It will begin only after the Linux/Python execution environment is
agreed upon and verified.
