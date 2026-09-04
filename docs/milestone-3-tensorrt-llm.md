# Milestone 3 TensorRT-LLM comparison path

Status: complete

## Goal

Run the same TinyLlama model through NVIDIA TensorRT-LLM on the RTX 3060 Ti,
without changing or replacing the verified ordinary PyTorch baseline. This
milestone establishes the optimized inference path; controlled multi-run and
concurrency benchmarks remain Milestone 5.

## Important architecture note

TensorRT-LLM 1.2 removed its older serialized TensorRT engine backend. The
current `LLM` API uses TensorRT-LLM's PyTorch backend and loads Hugging Face
checkpoints directly. It still adds NVIDIA's LLM-specific runtime, custom GPU
kernels, paged KV cache, scheduling, and other inference optimizations, but
there is no separate `trtllm-build` engine-build step in this release.

This means TurboServe now compares:

- ordinary Hugging Face Transformers generation on PyTorch; and
- the same model through NVIDIA's optimized TensorRT-LLM runtime.

This behavior is documented in NVIDIA's
[TensorRT backend removal guide](https://nvidia.github.io/TensorRT-LLM/latest/legacy/tensorrt-backend-removal.html).

## Compatibility decision

Verified on 2026-09-03:

- NVIDIA GeForce RTX 3060 Ti, 8,192 MiB VRAM, compute capability 8.6 (SM86)
- Ubuntu 24.04.4 LTS under WSL2
- NVIDIA Windows KMD driver 616.56; GPU access works inside WSL
- Python 3.12.3
- CUDA Toolkit 13.0.88 at `/usr/local/cuda-13.0`
- Open MPI 4.1.6
- TensorRT-LLM 1.2.1
- TensorRT 10.14.1.48.post1
- PyTorch 2.9.1+cu130
- Transformers 4.57.3
- successful TensorRT-LLM import and CUDA tensor calculation

NVIDIA's [support matrix](https://nvidia.github.io/TensorRT-LLM/reference/support-matrix.html)
lists Ampere SM86 as supported. TinyLlama is also the model used in NVIDIA's
[LLM API introduction](https://nvidia.github.io/TensorRT-LLM/llm-api/index.html).

Stable TensorRT-LLM 1.2.1 was selected instead of a 1.3 release candidate. A
separate virtual environment protects the completed baseline because this
release requires older PyTorch and Transformers versions than Milestone 2.

## Storage layout

The Ubuntu distribution is stored at
`M:\WSL\Ubuntu-24.04\ext4.vhdx`. Therefore, these Linux paths consume space on
the Windows `M:` drive:

- `~/.venvs/turboserve-trtllm`: approximately 14 GB
- `/usr/local/cuda-13.0`: approximately 4.9 GB
- `~/.cache/pip`: approximately 7.5 GB after installation
- the existing Hugging Face cache, shared with the PyTorch baseline

The pip cache is intentionally retained because it contains expensive package
downloads that would otherwise be needed again. A verified 787 MiB partial
file left by an interrupted dry run was removed from `/tmp`.

## Reproduce the environment

Enter Ubuntu and install Open MPI:

```powershell
wsl -d Ubuntu-24.04
```

```bash
sudo apt update
sudo apt install -y libopenmpi-dev
```

Install only the CUDA Toolkit inside WSL. Do not install a Linux NVIDIA driver;
WSL uses the driver provided by Windows.

```bash
cd /tmp
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install -y cuda-toolkit-13-0
```

Create the isolated environment and install the pinned stack:

```bash
python3 -m venv ~/.venvs/turboserve-trtllm
source ~/.venvs/turboserve-trtllm/bin/activate
cd /mnt/m/Projects/TurboServe
python -m pip install --upgrade pip "setuptools<80" wheel
python -m pip install --requirement requirements-tensorrt-llm.txt
```

NVIDIA's [CUDA on WSL guidance](https://docs.nvidia.com/cuda/wsl-user-guide/)
explains why the Windows driver and Linux toolkit are separate components.

## Run the TensorRT-LLM path

In each new Ubuntu shell, activate the isolated environment and identify the
CUDA Toolkit before running the script:

```bash
source ~/.venvs/turboserve-trtllm/bin/activate
export CUDA_HOME=/usr/local/cuda-13.0
export PATH="$CUDA_HOME/bin:$PATH"
cd /mnt/m/Projects/TurboServe
python src/turboserve/tensorrt_llm_baseline.py --max-new-tokens 32
```

The script uses FP16 and limits TensorRT-LLM's paged KV cache to 30% of free
GPU memory by default. That conservative setting leaves room for the model,
runtime workspaces, and the Windows desktop on an 8 GB card. Override it only
when deliberately testing memory behavior:

```bash
python src/turboserve/tensorrt_llm_baseline.py \
  --max-new-tokens 64 \
  --kv-cache-fraction 0.30
```

## Verified smoke-test result

A 32-token run on 2026-09-03 produced the same generated text as the ordinary
PyTorch baseline:

> Low latency is a critical factor for an LLM inference service because it
> refers to the time it takes for the LLM to process a request and provide

| Measurement | PyTorch baseline (best recorded run) | TensorRT-LLM smoke test |
| --- | ---: | ---: |
| Input tokens | 29 | 30 |
| Output tokens | 32 | 32 |
| Model/runtime load | 4.322 s | 32.712 s |
| Generation latency | 0.683 s | 0.242 s |
| Output throughput | 46.87 tokens/s | 132.44 tokens/s |
| Reported memory | 2,110.3 MiB peak PyTorch allocation | 4,107.2 MiB approximate device increase |

For this single smoke test, TensorRT-LLM generated tokens about 2.8 times as
fast and reduced generation latency by about 2.8 times. This is promising
evidence, not yet a final benchmark claim. Runtime startup is substantially
slower because TensorRT-LLM loads its worker, initializes the paged KV cache,
and compiles or auto-tunes kernels.

## Measurement limitations and warnings

- Required Transformers versions tokenize the TinyLlama chat boundary
  differently. Transformers 4.57.3 inserts one zero-width SentencePiece spacing
  token that Transformers 5.16.1 omits. The output text was identical, but
  Milestone 5 must use shared pre-tokenized inputs for a strict comparison.
- The baseline memory number comes from PyTorch's allocator. TensorRT-LLM uses
  a worker process, so its script uses NVML device-wide memory before and after
  load. These two memory figures are not directly equivalent; Milestone 5 will
  use one measurement method for both paths.
- NVIDIA ModelOpt 0.37 recommends Transformers `<4.57`, while TensorRT-LLM 1.2.1
  pins Transformers 4.57.3. The official pinned TensorRT-LLM version was
  preserved. The warning did not prevent model loading or generation.
- TensorRT-LLM emitted non-fatal startup warnings while resizing attention
  workspaces and warming the KV cache. Generation completed successfully.
- `python -m pip check` reported `No broken requirements found.`

No Triton server, load generator, Prometheus, Grafana, or formal concurrency
test was added in this milestone.
