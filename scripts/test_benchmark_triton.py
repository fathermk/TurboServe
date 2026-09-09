"""Offline checks of benchmark accounting and failure persistence."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

import benchmark_triton as benchmark


class BenchmarkTests(unittest.TestCase):
    def test_server_ttft_formats(self):
        for arrival, first in [(100, 200), ([100], [200]), ('100', '200')]:
            self.assertAlmostEqual(benchmark.server_ttft(
                {'arrival_time_ns': arrival, 'first_token_time_ns': first}), 1e-7)

    def test_invalid_server_timestamps(self):
        for arrival, first in [(None, 200), (0, 200), (200, 100),
                               (True, 200), (1.5, 200), ([1, 2], 200)]:
            self.assertIsNone(benchmark.server_ttft(
                {'arrival_time_ns': arrival, 'first_token_time_ns': first}))

    def run_case(self, replies):
        with tempfile.TemporaryDirectory() as directory:
            fake_script = str(Path(directory) / 'scripts' / 'benchmark_triton.py')
            with patch.object(benchmark, '__file__', fake_script), \
                 patch('sys.argv', ['benchmark', '--requests', '2']), \
                 patch.object(benchmark, 'request', side_effect=replies), \
                 contextlib.redirect_stdout(io.StringIO()):
                status = benchmark.main()
            files = list((Path(directory) / 'results').glob('*.json'))
            self.assertEqual(len(files), 1)
            return status, json.loads(files[0].read_text())

    def test_warmup_is_excluded(self):
        status, result = self.run_case([
            (0, None), (0, {'version': 'test'}),
            (99, {'text_output': 'warmup'}),
            (1, {'text_output': 'first'}), (3, {'text_output': 'second'})])
        self.assertEqual(status, 0)
        self.assertEqual(result['summary']['median_seconds'], 2)
        self.assertEqual(len(result['samples']), 2)

    def test_failed_request_preserves_partial_results(self):
        status, result = self.run_case([
            (0, None), (0, {}), (1, {'text_output': 'warmup'}),
            (2, {'text_output': 'first'}), URLError('offline')])
        self.assertEqual(status, 1)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(len(result['samples']), 1)
        self.assertNotIn('summary', result)

    def test_bad_response_is_failure(self):
        status, result = self.run_case([(0, None), (0, {}), (1, {'error': 'bad'})])
        self.assertEqual(status, 1)
        self.assertIn('text_output', result['error'])


if __name__ == '__main__':
    unittest.main()
