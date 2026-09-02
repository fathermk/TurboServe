"""Run the ordinary PyTorch text-generation baseline."""

from __future__ import annotations

import argparse
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


DEFAULT_MODEL = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic text generation with the PyTorch baseline."
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
    return parser.parse_args()


def mib(byte_count: int) -> float:
    return byte_count / (1024**2)


def main() -> None:
    args = parse_args()
    if args.max_new_tokens < 1:
        raise SystemExit("--max-new-tokens must be at least 1")
    if not torch.cuda.is_available():
        raise SystemExit(
            "CUDA is unavailable. Run this command inside the verified WSL environment."
        )

    device = torch.device("cuda")
    torch.manual_seed(0)

    print(f"PyTorch: {torch.__version__}")
    print(f"CUDA runtime: {torch.version.cuda}")
    print(f"GPU: {torch.cuda.get_device_name(device)}")
    print(f"Model: {args.model}")
    print("Precision: float16")

    load_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        dtype=torch.float16,
        use_safetensors=True,
    ).to(device)
    model.eval()
    torch.cuda.synchronize(device)
    load_seconds = time.perf_counter() - load_started

    model_inputs = tokenizer.apply_chat_template(
        [{"role": "user", "content": args.prompt}],
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
    ).to(device)
    input_ids = model_inputs["input_ids"]

    generation_args = {
        **model_inputs,
        "do_sample": False,
        # Ignore the model's saved max_length; this CLI uses max_new_tokens only.
        "max_length": None,
        "pad_token_id": tokenizer.eos_token_id,
    }

    # Warm up lazy CUDA kernels so first-use setup is not included in the timed run.
    with torch.inference_mode():
        model.generate(**generation_args, max_new_tokens=1)
    torch.cuda.synchronize(device)
    torch.cuda.reset_peak_memory_stats(device)

    generation_started = time.perf_counter()
    with torch.inference_mode():
        output_ids = model.generate(
            **generation_args,
            max_new_tokens=args.max_new_tokens,
        )
    torch.cuda.synchronize(device)
    generation_seconds = time.perf_counter() - generation_started

    generated_ids = output_ids[0, input_ids.shape[1] :]
    output_tokens = int(generated_ids.numel())
    output_text = tokenizer.decode(generated_ids, skip_special_tokens=True)
    tokens_per_second = output_tokens / generation_seconds

    print("\n=== Generated text ===")
    print(output_text.strip())
    print("\n=== Baseline measurements ===")
    print(f"Input tokens: {input_ids.shape[1]}")
    print(f"Output tokens: {output_tokens}")
    print(f"Model load time: {load_seconds:.3f} s")
    print(f"Generation latency: {generation_seconds:.3f} s")
    print(f"Output throughput: {tokens_per_second:.2f} tokens/s")
    print(f"GPU memory allocated: {mib(torch.cuda.memory_allocated(device)):.1f} MiB")
    print(f"Peak GPU memory allocated: {mib(torch.cuda.max_memory_allocated(device)):.1f} MiB")


if __name__ == "__main__":
    main()
