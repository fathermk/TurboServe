import subprocess
import unittest
from unittest.mock import patch

from gpu_telemetry import Sampler, parse_rows


class TelemetryTests(unittest.TestCase):
    def test_preserves_unsupported_fields(self):
        self.assertEqual(parse_rows('0, 10, 2000, 40, N/A, 5000, 20, P8')[0]['clocks.sm'], 'N/A')

    def test_rejects_bad_rows(self):
        for value in ['', '0, 10']:
            with self.assertRaises(ValueError):
                parse_rows(value)

    def test_missing_tool_stops_cleanly(self):
        sampler = Sampler()
        with patch('gpu_telemetry.subprocess.run', side_effect=FileNotFoundError('missing')):
            sampler.start()
            sampler.thread.join(timeout=3)
            record = sampler.stop()
        self.assertEqual(record['status'], 'unavailable')
        self.assertEqual(len(record['errors']), 1)
