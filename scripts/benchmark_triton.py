"""Measure sequential HTTP completion latency; no third-party packages required."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request(path, payload=None, timeout=120):
    data = None if payload is None else json.dumps(payload).encode()
    req = Request('http://127.0.0.1:8000' + path, data=data,
                  headers={'Content-Type': 'application/json'})
    started = time.perf_counter()
    with urlopen(req, timeout=timeout) as response:
        body = response.read()
    elapsed = time.perf_counter() - started
    return elapsed, json.loads(body) if body else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--requests', type=int, default=5)
    parser.add_argument('--warmups', type=int, default=1)
    parser.add_argument('--max-new-tokens', type=int, default=32)
    parser.add_argument('--prompt', default='Low latency is important because')
    args = parser.parse_args()
    if not 1 <= args.requests <= 100 or not 0 <= args.warmups <= 10:
        parser.error('Use 1–100 requests and 0–10 warmups')
    if not 1 <= args.max_new_tokens <= 128 or not args.prompt.strip():
        parser.error('Use 1–128 new tokens and a nonempty prompt')

    stamp = datetime.now(timezone.utc)
    output_dir = Path(__file__).resolve().parents[1] / 'results'
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / (stamp.strftime('triton-%Y%m%dT%H%M%S.%fZ') + '.json')
    payload = {'text_input': args.prompt,
               'sampling_param_max_tokens': args.max_new_tokens,
               'sampling_param_temperature': 0.0,
               'sampling_param_seed': 0}
    record = {
        'schema_version': 1, 'started_at_utc': stamp.isoformat(),
        'status': 'incomplete', 'endpoint': 'http://127.0.0.1:8000',
        'workload': 'sequential_repeated_prompt', 'concurrency': 1,
        'request_payload': payload, 'warmup_count': args.warmups,
        'requested_measurements': args.requests, 'samples': [],
        'measurement': 'HTTP request start through complete response body receipt',
        'limitations': ['No TTFT or actual token counts measured',
                        'Repeated prompts may benefit from server KV cache reuse',
                        'Server model revision, precision and cache settings not captured',
                        'Not comparable to standalone generation-only timings'],
    }
    try:
        request('/v2/models/tensorrt_llm/ready', timeout=10)
        _, record['server_metadata'] = request('/v2', timeout=10)
        for index in range(args.warmups + args.requests):
            elapsed, response = request('/v2/models/tensorrt_llm/generate', payload)
            if not isinstance(response, dict) or not response.get('text_output'):
                raise ValueError('Response does not contain nonempty text_output')
            if index < args.warmups:
                print(f'Warmup {index + 1} complete (excluded)')
                continue
            record['samples'].append({'latency_seconds': elapsed, 'response': response})
            print(f'Request {index - args.warmups + 1}: {elapsed:.3f} s')
        values = [sample['latency_seconds'] for sample in record['samples']]
        record['summary'] = {'count': len(values),
                             'mean_seconds': statistics.mean(values),
                             'median_seconds': statistics.median(values),
                             'min_seconds': min(values), 'max_seconds': max(values)}
        record['status'] = 'complete'
        print(f'Median HTTP completion latency: {statistics.median(values):.3f} s')
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        record['status'] = 'failed'
        record['error'] = str(exc)
        print(f'Run failed: {exc}')
    finally:
        record['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        with output_path.open('x', encoding='utf-8') as handle:
            json.dump(record, handle, indent=2)
            handle.write('\n')
        print(f'Results saved: {output_path}')
    return 0 if record['status'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
