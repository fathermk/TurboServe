# Milestone 2 PyTorch baseline

Status: complete

## Goal

Establish a normal, reproducible PyTorch LLM inference path before applying any
TensorRT-LLM or Triton optimization. This gives later work an honest comparison
point and proves the complete GPU software path works.

## Verified environment

Verified on 2026-09-02:

- WSL 2.7.12.0 with Linux kernel 6.18.33.2-2
- Ubuntu 24.04.4 LTS on x86-64
- Distribution virtual disk at `M:\WSL\Ubuntu-24.04\ext4.vhdx`
- NVIDIA GeForce RTX 3060 Ti with 8,192 MiB VRAM visible inside WSL
- NVIDIA Windows KMD driver 616.56 and CUDA UMD capability 13.4
- Python 3.12.3 in the `~/.venvs/turboserve` virtual environment
- pip 24.0
- PyTorch 2.13.0+cu130 with CUDA runtime 13.0
- Successful CUDA tensor calculation on the RTX 3060 Ti

The virtual environment lives in the Linux filesystem for correct permissions
and better package performance. The Git working tree remains on the Windows `M:`
drive and appears inside WSL as `/mnt/m/Projects/TurboServe`.

## Baseline model

The baseline uses `TinyLlama/TinyLlama-1.1B-Chat-v1.0`:

- approximately 1.1 billion parameters
- approximately 2.2 GB of BF16 model weights
- Apache-2.0 license
- Llama-family causal language model
- small enough to run in FP16 within the RTX 3060 Ti's 8 GB VRAM

The small model keeps iteration practical while preserving a model architecture
that can be revisited during the TensorRT-LLM milestone.

## Reproduce the environment

Enter Ubuntu from PowerShell:

```powershell
wsl -d Ubuntu-24.04
```

Prepare and activate the Python environment inside Ubuntu:

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv
python3 -m venv ~/.venvs/turboserve
source ~/.venvs/turboserve/bin/activate
cd /mnt/m/Projects/TurboServe
```

Install the pinned CUDA-enabled PyTorch wheel first:

```bash
python -m pip install torch==2.13.0 \
  --index-url https://download.pytorch.org/whl/cu130
```

Install the remaining pinned direct dependencies:

```bash
python -m pip install --requirement requirements.txt
```

The PyTorch wheel supplies the user-space CUDA libraries needed by this
baseline. A system-wide CUDA toolkit is not required.

## Run the baseline

```bash
python src/turboserve/baseline.py
```

Use a custom prompt or output length if desired:

```bash
python src/turboserve/baseline.py \
  --prompt "What makes GPU inference faster than CPU inference?" \
  --max-new-tokens 64
```

The first run downloads the model into the user's Hugging Face cache inside the
Ubuntu virtual disk on `M:`. Model weights and virtual environments are not
committed to Git.

The repository is currently accessed through WSL's `/mnt/m` Windows-drive
mount. A PEP 660 editable package install was deliberately avoided because
setuptools metadata creation encountered an NTFS/WSL permission mismatch there.
Running the source file directly keeps this baseline simple and does not require
unsafe permission changes or a duplicate repository checkout.

## Measurements and limits

The command performs one untimed warm-up generation and then reports:

- model load time
- input and output token counts
- synchronized end-to-end generation latency
- output tokens per second
- current and peak PyTorch-allocated VRAM

Greedy decoding (`do_sample=False`) makes repeated runs comparable. This first
baseline does not yet claim statistically stable benchmark results. Accurate
time to first token requires a streaming measurement path, and concurrency needs
a request-serving layer; both remain later, explicit additions.

## Successful smoke tests

Two successful 32-token runs on 2026-09-02 produced the same deterministic text:

| Run | Input tokens | Output tokens | Cached load | Generation | Output rate | Peak PyTorch VRAM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 29 | 32 | 3.527 s | 0.749 s | 42.75 tokens/s | 2,110.3 MiB |
| 2 | 29 | 32 | 4.322 s | 0.683 s | 46.87 tokens/s | 2,110.3 MiB |

These numbers prove the baseline works, but they are not yet final benchmark
statistics. Multiple controlled runs are needed before drawing performance
conclusions.

`python -m pip check` also reported `No broken requirements found.`
