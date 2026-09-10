"""Optional device-wide nvidia-smi sampling; no package installation required."""

import csv
from datetime import datetime, timezone
import io
import subprocess
import threading
import time

FIELDS = ['index', 'utilization.gpu', 'memory.used', 'temperature.gpu',
          'clocks.sm', 'clocks.mem', 'power.draw', 'pstate']


def parse_rows(text):
    rows = []
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        if len(row) != len(FIELDS):
            raise ValueError('Unexpected nvidia-smi column count')
        # Preserve N/A and unsupported fields instead of converting them to zero.
        rows.append(dict(zip(FIELDS, (value.strip() for value in row))))
    if not rows:
        raise ValueError('No GPU samples returned')
    return rows


class Sampler:
    def __init__(self):
        self.done = threading.Event()
        self.thread = None
        self.record = {'enabled': True, 'interval_seconds': 0.5,
                       'scope': 'Device-wide local GPU; includes other applications',
                       'units': {'utilization.gpu': 'percent', 'memory.used': 'MiB',
                                 'temperature.gpu': 'C', 'clocks.sm': 'MHz',
                                 'clocks.mem': 'MHz', 'power.draw': 'W'},
                       'samples': [], 'errors': []}

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while not self.done.is_set():
            started = time.perf_counter()
            stamp = datetime.now(timezone.utc).isoformat()
            try:
                result = subprocess.run(['nvidia-smi', '--query-gpu=' + ','.join(FIELDS),
                                         '--format=csv,noheader,nounits'],
                                        capture_output=True, text=True, check=True, timeout=2)
                self.record['samples'].append({'query_started_at_utc': stamp,
                    'query_duration_seconds': time.perf_counter() - started,
                    'devices': parse_rows(result.stdout)})
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                self.record['errors'].append(str(exc))
                break
            self.done.wait(max(0, 0.5 - (time.perf_counter() - started)))

    def stop(self):
        self.done.set()
        if self.thread is not None:
            self.thread.join()
        self.record['status'] = ('partial' if self.record['samples'] else 'unavailable') \
            if self.record['errors'] else ('available' if self.record['samples'] else 'no_samples')
        return self.record
