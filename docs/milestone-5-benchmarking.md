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

The request also asks Triton for its performance fields. When the server
returns valid arrival and first-token timestamps, the record derives server TTFT
as `first_token_time_ns - arrival_time_ns`; otherwise TTFT is recorded as
unavailable. This measures executor-side timing, not client-observed streaming
TTFT. Schema version 2 uses `server_ttft_seconds` and records the number of
valid timing samples. Scalar or single-element-array timestamps are accepted;
missing, zero, or reversed timestamps are unavailable, not zero-latency samples.
The report provides mean, median, minimum, and maximum. Five samples are only
an initial measurement, not sufficient for reliable tail-latency claims.
The output limit is not an actual token count. Do not calculate tokens/second
by assuming the model always generates the limit. Client streaming TTFT is not measured.
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

### Verified server timing extension

Run `triton-20260909T033645.980965Z.json` (September 8 local Eastern time)
completed with five valid server timestamp pairs after one excluded warmup.
Median executor-side TTFT was 19.89 ms; median full HTTP completion latency
was approximately 226 ms. The timestamps come from the pinned NVIDIA
template's executor timing metrics. This is not client-observed first-token
latency, because the endpoint still returns a complete non-streaming response.
All five offline tests passed, including scalar/array timestamp parsing and
rejection of missing, zero, reversed, boolean, and non-integer timestamps.
The request now enables performance metadata, so it also differs from the
initial measurement's request settings. No regression or improvement claim
is made between those two small runs.

- Capture model revision, runtime configuration, and hardware metadata.
- Align tokenization, prompts, warmup, decoding and memory measurements for
  cross-backend comparisons. Earlier standalone runs used chat templates;
  this workload currently sends raw text.
- Add actual output-token accounting and validate Triton’s returned timing
  fields against a streamed response.
- Add controlled concurrency tests and device utilization sampling.
- Review results before publishing performance claims.

The later AI investigation workflow will read validated run records and use
code to calculate comparisons. It should reject incomparable measurements
and report missing information. No agent or MCP integration exists yet.
