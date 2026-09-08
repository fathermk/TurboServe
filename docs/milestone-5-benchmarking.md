# Milestone 5: benchmarking (in progress)

The first step measures five sequential HTTP requests after one excluded
warmup. It uses a repeated raw prompt, temperature zero, seed zero, and a
32-new-token limit. The server must already be running.

From a second PowerShell terminal:

```powershell
wsl -d Ubuntu-24.04 -- python3 /mnt/m/Projects/TurboServe/scripts/benchmark_triton.py
```

Each run saves a uniquely named JSON file under `results/` (Git-ignored),
including request settings, server metadata, individual responses, timings,
and any failure. Results may contain prompt and generated text; review before
sharing. No new Python dependencies are needed.

Timing covers HTTP request start through receipt of the entire response body.
It excludes server startup and includes HTTP handling, tokenization, generation,
and response transfer. JSON parsing is outside the timer. Each request uses
a fresh urllib request; this is a simple local client workload.

The report provides mean, median, minimum, and maximum. Five samples are only
an initial measurement, not sufficient for reliable tail-latency claims.
The output limit is not an actual token count. Do not calculate tokens/second
by assuming the model always generates the limit. TTFT is not measured.
Repeated prompts can benefit from KV cache reuse, which is not disabled here.

## First verified run: September 8, 2026

Local record: `results/triton-20260908T222709.300003Z.json`.
Status: complete; Triton metadata reports version 2.71.0. One warmup was
excluded, and all five measured responses contained the same text.

| Metric | HTTP completion latency |
| --- | --- |
| Median | 196.37 ms |
| Mean | 204.62 ms |
| Minimum | 194.70 ms |
| Maximum | 239.28 ms |

Individual times: 239.28, 194.70, 195.21, 197.52, and 196.37 ms.
These describe this small, repeated-prompt workload only. The first measured
request was slower; the record does not establish why. Do not infer a
speedup over the earlier standalone measurements from this run.

Three offline tests passed: warmup exclusion, preserving partial results
when a request fails, and rejecting responses without generated text.
A live attempt with the server stopped also correctly recorded connection
refusal as a failed run before the successful measurement above.

## Remaining work

- Capture model revision, runtime configuration, and hardware metadata.
- Align tokenization, prompts, warmup, decoding and memory measurements for
  cross-backend comparisons. Earlier standalone runs used chat templates;
  this workload currently sends raw text.
- Add actual output-token accounting and a defined TTFT measurement.
- Add controlled concurrency tests and device utilization sampling.
- Review results before publishing performance claims.

The later AI investigation workflow will read validated run records and use
code to calculate comparisons. It should reject incomparable measurements
and report missing information. No agent or MCP integration exists yet.
