"""Run the TinyLlama comparison path with NVIDIA TensorRT-LLM."""

from __future__ import annotations

import argparse
import time

import torch
from pynvml import nvmlDeviceGetHandleByIndex, nvmlDeviceGetMemoryInfo, nvmlInit
from tensorrt_llm import LLM, SamplingParams
from tensorrt_llm.llmapi import KvCacheConfig
from transformers import AutoTokenizer


DEFAULT_MODEL = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic text generation with TensorRT-LLM."
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Hugging Face model identifier (default: %(default)s)",
    )
    parser.add_argument(
        "--prompt",
        default="Explain why low latency matters for an LLM inference service.",
        help="User prompt sent to the model.",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=64,
        help="Maximum number of output tokens (default: %(default)s)",
    )
    parser.add_argument(
        "--kv-cache-fraction",
        type=float,
        default=0.30,
        help="Fraction of free GPU memory available to the KV cache (default: %(default)s)",
    )
    return parser.parse_args()


def mib(byte_count: int) -> float:
    return byte_count / (1024**2)


def device_memory_used() -> int:
    # TensorRT-LLM runs inference in a worker process, so PyTorch's allocator
    # counters in this parent process do not include the model. NVML reports
    # device-wide usage and therefore captures the worker's allocation.
    nvmlInit()
    return int(nvmlDeviceGetMemoryInfo(nvmlDeviceGetHandleByIndex(0)).used)


def main() -> None:
    args = parse_args()
    if args.max_new_tokens < 1:
        raise SystemExit("--max-new-tokens must be at least 1")
    if not 0 < args.kv_cache_fraction < 1:
        raise SystemExit("--kv-cache-fraction must be between 0 and 1")
    if not torch.cuda.is_available():
        raise SystemExit(
            "CUDA is unavailable. Run inside the TensorRT-LLM WSL environment."
        )

    torch.manual_seed(0)
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    prompt_token_ids = tokenizer.apply_chat_template(
        [{"role": "user", "content": args.prompt}],
        add_generation_prompt=True,
        tokenize=True,
    )
    input_tokens = len(prompt_token_ids)

    print(f"PyTorch: {torch.__version__}")
    print(f"CUDA runtime: {torch.version.cuda}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Model: {args.model}")
    print("Framework: TensorRT-LLM")
    print("Precision: float16")

    memory_before_load = device_memory_used()
    load_started = time.perf_counter()
    llm = LLM(
        model=args.model,
        dtype="float16",
        kv_cache_config=KvCacheConfig(
            free_gpu_memory_fraction=args.kv_cache_fraction
        ),
    )
    load_seconds = time.perf_counter() - load_started
    memory_after_load = device_memory_used()

    try:
        # Warm up request handling so first-use setup is not in the timed run.
        llm.generate(
            [prompt_token_ids],
            SamplingParams(
                max_tokens=1,
                temperature=0.0,
                seed=0,
                add_special_tokens=False,
                ignore_eos=True,
            ),
            use_tqdm=False,
        )

        generation_started = time.perf_counter()
        outputs = llm.generate(
            [prompt_token_ids],
            SamplingParams(
                max_tokens=args.max_new_tokens,
                temperature=0.0,
                seed=0,
                add_special_tokens=False,
            ),
            use_tqdm=False,
        )
        generation_seconds = time.perf_counter() - generation_started

        completion = outputs[0].outputs[0]
        output_tokens = len(completion.token_ids)
        tokens_per_second = output_tokens / generation_seconds

        print("\n=== Generated text ===")
        print(completion.text.strip())
        print("\n=== TensorRT-LLM measurements ===")
        print(f"Input tokens: {input_tokens}")
        print(f"Output tokens: {output_tokens}")
        print(f"Model/runtime load time: {load_seconds:.3f} s")
        print(f"Generation latency: {generation_seconds:.3f} s")
        print(f"Output throughput: {tokens_per_second:.2f} tokens/s")
        print(f"Device memory before load: {mib(memory_before_load):.1f} MiB")
        print(f"Device memory after load: {mib(memory_after_load):.1f} MiB")
        print(
            "Approximate load-time GPU increase: "
            f"{mib(memory_after_load - memory_before_load):.1f} MiB"
        )
    finally:
        llm.shutdown()


if __name__ == "__main__":
    main()
