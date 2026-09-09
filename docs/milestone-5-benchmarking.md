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

### Explicit server configuration (restart and request verified)

`configs/triton-model.yaml` now selects cached snapshot
`fe8a4ea1ffedaf415f4da2f062534de366a451e6`, requests float16, allocates
30% of free GPU memory to the KV cache, and disables cross-request block reuse.
The allocation fraction is not 30% of total VRAM. The launch script mounts
this file read-only and selects it through NVIDIA's `LLM_CONFIG_PATH` setting.
Shell syntax checks passed. Startup evidence at 2026-09-09 03:58:28 UTC
shows the exact snapshot path, `dtype='float16'`,
`free_gpu_memory_fraction=0.3`, and `enable_block_reuse=False` in the engine
arguments. The model reached READY at 03:59:07 UTC, and the user's smoke
test returned generated text successfully. Startup reported a final KV-cache
allocation of 1.26 GiB (60064 tokens), following an initial 1.34 GiB stage;
these values are not summed or interpreted as total GPU usage.

The inspection script reads the selected `LLM_CONFIG_PATH` when present and
reports package versions, cached snapshot candidates and selected startup
logs. Checkpoint metadata is labeled separately from runtime configuration.
Existing benchmark JSON records still contain unknown runtime fields; linking
verified configuration evidence to each new run remains future work. No
performance benchmark has yet been recorded for this new configuration.

These settings define a new workload configuration. Do not apply them
retroactively to saved runs. The checkpoint metadata declaring bfloat16 does
not override the requested runtime float16 conversion. Disabling block reuse
does not disable within-request KV caching during generation.

### Deterministic comparison tool

Run `scripts/compare_runs.py FIRST.json SECOND.json` with Python 3.
It reads saved records only, recalculates medians from individual samples,
and reports the observed percentage change. It rejects failed/incomplete
runs and invalid latency values. Required recorded settings are checked
for differences and missing values; two missing values are not a match.
Matching recorded settings does not establish statistical significance,
causation, or independently verified server state.

Four offline tests passed. Comparing `triton-20260909T033645.980965Z.json`
against `triton-20260909T034034.305216Z.json` reported `incomplete_context`,
a schema difference and seven missing comparison fields. The observed median
increase was 16.42%, but the report makes no regression claim. This tool
provides deterministic calculations for a future AI explanation workflow;
it is not yet an agent or MCP server.

Capturing the actual loaded model-weight revision, precision and KV-cache
settings remains outstanding. The current NVIDIA model YAML relies on runtime
defaults and does not establish those effective values by itself.

### Run metadata (schema version 3)

Each run now records client Python, kernel and architecture, benchmark file
SHA-256, client Git commit and working-tree status, and local GPU name,
driver and total memory. The client GPU inventory is not proof of server
GPU assignment. No serial numbers or environment variables are collected.
Read-only subprocess diagnostics have a ten-second timeout and record
unavailable tools explicitly. All metadata collection occurs before warmup,
outside the request timers.

The running server's `/v2/models/tensorrt_llm/config` response is saved with
a SHA-256 fingerprint of sorted-key JSON. Its configuration is distinct
from TensorRT-LLM's model YAML: model-weight revision, precision and KV-cache
settings remain null until verified through another source. Matching
fingerprints alone are therefore insufficient to establish comparable runs.

Live verification: `triton-20260909T034034.305216Z.json` completed five requests
and captured configuration plus RTX 3060 Ti / driver 616.56 / 8192 MiB.
Median server TTFT was 20.83 ms and HTTP completion latency approximately
263 ms. Eight offline tests passed. The benchmark source was modified during
this run; its file fingerprint and working-tree status record that fact.
Git status may differ between Windows and WSL because of platform settings.

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
