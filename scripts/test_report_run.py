import unittest

from report_run import report


def record():
    return {'status': 'complete', 'requested_measurements': 2,
            'samples': [{'latency_seconds': 0.1}, {'latency_seconds': 0.3}],
            'summary': {'median_seconds': 999}}


class ReportTests(unittest.TestCase):
    def test_recalculates_and_explains_missing_telemetry(self):
        text = report(record())
        self.assertIn('| Median | 200.00 |', text)
        self.assertIn('No GPU samples available', text)

    def test_invalid_metrics_are_not_zero(self):
        data = record()
        data['gpu_telemetry'] = {'samples': [{'devices': [
            {'index': '0', 'power.draw': 'N/A', 'temperature.gpu': 'nan'}]}]}
        text = report(data)
        self.assertIn('| Power draw | unavailable | unavailable | 0/1 |', text)

    def test_devices_are_separate(self):
        data = record()
        data['gpu_telemetry'] = {'samples': [{'devices': [
            {'index': '0', 'memory.used': '100'}, {'index': '1', 'memory.used': '900'}]}]}
        text = report(data)
        self.assertIn('100.00 MiB | 100.00 MiB', text)
        self.assertIn('900.00 MiB | 900.00 MiB', text)

    def test_failed_run_is_rejected(self):
        data = record()
        data['status'] = 'failed'
        with self.assertRaises(ValueError):
            report(data)

    def test_invalid_ttft_is_excluded(self):
        for invalid in (0, -1, True, 'nan', None):
            with self.subTest(invalid=invalid):
                data = record()
                data['samples'][0]['server_ttft_seconds'] = invalid
                data['samples'][1]['server_ttft_seconds'] = 0.02
                self.assertIn('20.00 ms median (1/2 samples)', report(data))


if __name__ == '__main__':
    unittest.main()
