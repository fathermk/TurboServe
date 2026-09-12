"""Print a descriptive Markdown report from one saved benchmark record."""

import argparse
import json
import math
from pathlib import Path
import statistics

from compare_runs import latencies, snapshot_problem


METRICS = {'utilization.gpu': ('GPU utilization', '%'),
           'memory.used': ('Device memory used', 'MiB'),
           'temperature.gpu': ('GPU temperature', 'C'),
           'clocks.sm': ('SM clock', 'MHz'),
           'clocks.mem': ('Memory clock', 'MHz'),
           'power.draw': ('Power draw', 'W')}


def number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (TypeError, ValueError):
        return None


def report(record):
    values = latencies(record)
    lines = ['# TurboServe run report', '',
             f'Measured requests: {len(values)}', '',
             '| HTTP completion metric | Milliseconds |', '| --- | ---: |',
             f'| Median | {statistics.median(values) * 1000:.2f} |',
             f'| Mean | {statistics.mean(values) * 1000:.2f} |',
             f'| Minimum | {min(values) * 1000:.2f} |',
             f'| Maximum | {max(values) * 1000:.2f} |', '']
    ttft = [number(sample.get('server_ttft_seconds')) for sample in record['samples']]
    ttft = [value for value in ttft if value is not None and value > 0]
    lines.append(f'Server TTFT: {statistics.median(ttft) * 1000:.2f} ms median '
                 f'({len(ttft)}/{len(values)} samples).' if ttft else 'Server TTFT: unavailable.')
    problem = snapshot_problem(record)
    lines += ['', 'Runtime evidence: ' + (problem if problem else 'recorded snapshot checks passed.'),
              '', '## GPU observations', '']
    telemetry = record.get('gpu_telemetry') or {}
    samples = telemetry.get('samples') or []
    devices = {}
    for sample in samples:
        for device in sample.get('devices', []):
            # Each GPU is summarized separately; never mix devices into one range.
            index = device.get('index', 'unknown')
            devices.setdefault(str(index), []).append(device)
    if not devices:
        lines.append('No GPU samples available; missing telemetry does not mean zero activity.')
    for ordinal, (_, rows) in enumerate(sorted(devices.items()), 1):
        lines += [f'### Device group {ordinal}', '',
                  '| Signal | Minimum | Maximum | Valid observations |', '| --- | ---: | ---: | ---: |']
        for field, (label, unit) in METRICS.items():
            valid = [number(row.get(field)) for row in rows]
            valid = [value for value in valid if value is not None]
            low, high = ((f'{min(valid):.2f} {unit}', f'{max(valid):.2f} {unit}')
                         if valid else ('unavailable', 'unavailable'))
            lines.append(f'| {label} | {low} | {high} | {len(valid)}/{len(rows)} |')
        lines.append('')
    if telemetry.get('errors'):
        lines.append(f"Telemetry collection errors: {len(telemetry['errors'])}; consult the raw record.")
    lines += ['', '## Interpretation limits', '',
              '- These are observations, not a causal diagnosis or speedup claim.',
              '- GPU signals are device-wide and include other applications.',
              '- Sparse polling can miss spikes and adds measurement overhead.',
              '- Server TTFT is not client-observed streaming latency.',
              '- Statistics are recalculated from samples; no token throughput is inferred.']
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record', type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.record.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('Expected a JSON object')
        print(report(data), end='')
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        parser.exit(1, f'Cannot report run: {exc}\n')


if __name__ == '__main__':
    main()
