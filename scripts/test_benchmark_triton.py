"""Offline checks of benchmark accounting and failure persistence."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import URLError

import benchmark_triton as benchmark


class BenchmarkTests(unittest.TestCase):
    def test_concurrent_requests_overlap_and_preserve_order(self):
        barrier = threading.Barrier(2)
        def reply(*args, **kwargs):
            barrier.wait(timeout=5)
            return 0.1, {'text_output': 'ok'}
        result = {'samples': []}
        with patch.object(benchmark, 'request', side_effect=reply), \
             contextlib.redirect_stdout(io.StringIO()):
            benchmark.measure(result, {}, 4, 2)
        self.assertEqual([s['request_index'] for s in result['samples']], [1, 2, 3, 4])
        self.assertGreater(result['measurement_wall_seconds'], 0)

    def test_concurrent_failure_drains_and_preserves_successes(self):
        def sample(payload, index):
            if index == 2:
                raise URLError('offline')
            return {'request_index': index, 'latency_seconds': 0.1}
        result = {'samples': []}
        with patch.object(benchmark, 'generate_sample', side_effect=sample), \
             contextlib.redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
            benchmark.measure(result, {}, 4, 2)
        self.assertEqual([s['request_index'] for s in result['samples']], [1, 3, 4])
        self.assertEqual(result['request_errors'][0]['request_index'], 2)

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
                 patch.object(benchmark, 'collect_environment', return_value={'test': True}), \
                 patch.object(benchmark, 'collect_model_config', return_value={'status': 'unavailable'}), \
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

    def test_missing_diagnostic_tool(self):
        with patch.object(benchmark.subprocess, 'run', side_effect=FileNotFoundError('missing')):
            self.assertEqual(benchmark.command_snapshot(['missing'])['status'], 'unavailable')

    def test_model_config_unavailable(self):
        with patch.object(benchmark, 'request', side_effect=URLError('offline')):
            self.assertEqual(benchmark.collect_model_config()['status'], 'unavailable')

    def test_config_fingerprint_ignores_key_order(self):
        with patch.object(benchmark, 'request', side_effect=[
                (0, {'name': 'test', 'backend': 'python'}),
                (0, {'backend': 'python', 'name': 'test'})]):
            self.assertEqual(benchmark.collect_model_config()['sha256'],
                             benchmark.collect_model_config()['sha256'])


if __name__ == '__main__':
    unittest.main()
