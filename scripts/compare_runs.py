"""Describe two local benchmark records without asserting causation or speedup."""

import argparse
import json
import math
from pathlib import Path
import statistics


FIELDS = [
    'schema_version', 'measurement', 'workload', 'concurrency',
    'warmup_count', 'request_payload', 'server_metadata.version',
    'environment.benchmark_sha256', 'environment.client_python',
    'environment.local_gpu_inventory.value', 'model_configuration.sha256',
    'environment.server_model_weight_revision', 'environment.server_precision',
    'environment.server_kv_cache_settings',
]


def get(record, path):
    for key in path.split('.'):
        if not isinstance(record, dict) or key not in record:
            return None
        record = record[key]
    return record


def latencies(record):
    if record.get('status') != 'complete':
        raise ValueError('Only complete runs can be compared')
    samples = record.get('samples')
    if not isinstance(samples, list) or not samples:
        raise ValueError('Missing measured samples')
    if len(samples) != record.get('requested_measurements'):
        raise ValueError('Measured sample count does not match requested count')
    values = [sample.get('latency_seconds') if isinstance(sample, dict) else None
              for sample in samples]
    if any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0
           for value in values):
        raise ValueError('Latency samples must be finite positive numbers')
    return values


def compare(first, second):
    left, right = latencies(first), latencies(second)
    unknown, different = [], []
    for field in FIELDS:
        a, b = get(first, field), get(second, field)
        if a is None or b is None:
            unknown.append(field)
        elif a != b:
            different.append(field)
    a, b = statistics.median(left), statistics.median(right)
    return {
        'comparison_status': 'incomplete_context' if unknown else (
            'settings_differ' if different else 'recorded_settings_match'),
        'unknown_fields': unknown, 'different_fields': different,
        'first_sample_count': len(left), 'second_sample_count': len(right),
        'first_median_seconds': a, 'second_median_seconds': b,
        'observed_latency_change_percent': (b - a) / a * 100,
        'interpretation': 'Descriptive change only; negative means lower latency in the second run.',
        'limitations': ['No statistical significance or causal speedup established',
                        'Actual token counts and server GPU assignment are not verified',
                        'Recorded settings are not independently authenticated'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('first', type=Path)
    parser.add_argument('second', type=Path)
    args = parser.parse_args()
    try:
        records = [json.loads(path.read_text(encoding='utf-8'))
                   for path in (args.first, args.second)]
        if any(not isinstance(record, dict) for record in records):
            raise ValueError('Each record must be a JSON object')
        report = compare(*records)
        report['source_files'] = [str(args.first), str(args.second)]
        print(json.dumps(report, indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Cannot compare runs: {exc}\n')


if __name__ == '__main__':
    main()
