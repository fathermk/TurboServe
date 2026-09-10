"""Describe two local benchmark records without asserting causation or speedup."""

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import statistics


FIELDS = [
    'schema_version', 'measurement', 'workload', 'concurrency',
    'warmup_count', 'request_payload', 'server_metadata.version',
    'environment.benchmark_sha256', 'environment.client_python',
    'environment.local_gpu_inventory.value', 'model_configuration.sha256',
]

RUNTIME_FIELDS = [
    'runtime_snapshot.container.image',
    'runtime_snapshot.selected_yaml.model',
    'runtime_snapshot.selected_yaml.dtype',
    'runtime_snapshot.selected_yaml.backend',
    'runtime_snapshot.selected_yaml.tensor_parallel_size',
    'runtime_snapshot.selected_yaml.pipeline_parallel_size',
    'runtime_snapshot.selected_yaml.kv_cache_config.free_gpu_memory_fraction',
    'runtime_snapshot.selected_yaml.kv_cache_config.enable_block_reuse',
    'runtime_snapshot.selected_yaml', 'runtime_snapshot.packages',
]


def snapshot_problem(record):
    """Check recorded verification evidence, not the current live server."""
    try:
        def date(path):
            value = datetime.fromisoformat(get(record, path))
            if value.utcoffset() is None:
                raise ValueError('Timestamp has no timezone')
            return value
        start = date('started_at_utc')
        captured = date('runtime_snapshot.captured_at_utc')
        verified = date('runtime_verified_at_utc')
        end = date('finished_at_utc')
        if not start <= captured <= verified <= end:
            return 'Snapshot verification timestamps fall outside the run or are reversed'
    except (TypeError, ValueError):
        return 'Missing or invalid runtime verification timestamps'
    if get(record, 'runtime_snapshot.container.running') is not True:
        return 'Snapshot does not report a running container'
    if not get(record, 'runtime_snapshot.container.id'):
        return 'Missing container identity'
    fingerprint = get(record, 'runtime_snapshot.triton_config_sha256')
    if not fingerprint or fingerprint != get(record, 'model_configuration.sha256'):
        return 'Snapshot model configuration fingerprint is missing or inconsistent'
    return None


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
    evidence_problems = {'first': snapshot_problem(first), 'second': snapshot_problem(second)}
    for field in FIELDS + RUNTIME_FIELDS:
        a, b = get(first, field), get(second, field)
        if a is None or b is None:
            unknown.append(field)
        elif a != b:
            different.append(field)
    for label, problem in evidence_problems.items():
        if problem:
            unknown.append(f'{label}.runtime_verification')
    a, b = statistics.median(left), statistics.median(right)
    return {
        'comparison_status': 'incomplete_context' if unknown else (
            'settings_differ' if different else 'recorded_settings_match'),
        'unknown_fields': unknown, 'different_fields': different,
        'runtime_evidence_problems': evidence_problems,
        'comparison_scope': 'Recorded workload and declared server settings; not loaded-tensor introspection',
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
