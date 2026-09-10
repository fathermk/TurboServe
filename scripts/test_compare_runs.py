import unittest

from compare_runs import compare, FIELDS
from copy import deepcopy


def run(values):
    return {'status': 'complete', 'requested_measurements': len(values),
            'samples': [{'latency_seconds': value} for value in values],
            'concurrency': 1}


class ComparisonTests(unittest.TestCase):
    def test_recalculates_medians_and_flags_unknowns(self):
        first, second = run([1, 2, 3]), run([1, 1, 1])
        first['summary'] = {'median_seconds': 999}
        result = compare(first, second)
        self.assertEqual(result['observed_latency_change_percent'], -50)
        self.assertEqual(result['comparison_status'], 'incomplete_context')
        self.assertIn('runtime_snapshot.selected_yaml.dtype', result['unknown_fields'])

    def complete_run(self):
        record = run([1, 2, 3])
        for path in FIELDS:
            parent = record
            parts = path.split('.')
            for part in parts[:-1]:
                parent = parent.setdefault(part, {})
            parent.setdefault(parts[-1], 'test')
        record.update(started_at_utc='2026-09-10T00:00:00Z',
                      finished_at_utc='2026-09-10T00:01:00Z',
                      runtime_verified_at_utc='2026-09-10T00:00:50Z')
        record['runtime_snapshot'] = {
            'captured_at_utc': '2026-09-10T00:00:10Z',
            'container': {'id': 'one', 'running': True, 'image': 'pinned'},
            'triton_config_sha256': 'test', 'packages': {'torch': 'test'},
            'selected_yaml': {'model': '/snapshot/revision', 'dtype': 'float16',
                'backend': 'pytorch', 'tensor_parallel_size': 1, 'pipeline_parallel_size': 1,
                'kv_cache_config': {'free_gpu_memory_fraction': 0.3, 'enable_block_reuse': False}}}
        return record

    def test_matching_settings_allow_different_container_ids(self):
        first = self.complete_run()
        second = deepcopy(first)
        second['runtime_snapshot']['container']['id'] = 'two'
        self.assertEqual(compare(first, second)['comparison_status'], 'recorded_settings_match')

    def test_changed_precision(self):
        first, second = self.complete_run(), self.complete_run()
        second['runtime_snapshot']['selected_yaml']['dtype'] = 'bfloat16'
        self.assertEqual(compare(first, second)['comparison_status'], 'settings_differ')

    def test_stale_snapshot_and_mismatched_fingerprint(self):
        for change in [{'captured_at_utc': '2026-09-09T00:00:00Z'},
                       {'triton_config_sha256': 'wrong'}]:
            first, second = self.complete_run(), self.complete_run()
            second['runtime_snapshot'].update(change)
            self.assertEqual(compare(first, second)['comparison_status'], 'incomplete_context')

    def test_flags_different_concurrency(self):
        first, second = run([1]), run([1])
        second['concurrency'] = 2
        self.assertIn('concurrency', compare(first, second)['different_fields'])

    def test_rejects_bad_samples(self):
        for value in [0, -1, float('nan'), float('inf'), True, '1']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                compare(run([value]), run([1]))

    def test_rejects_failed_or_partial_runs(self):
        for change in [{'status': 'failed'}, {'requested_measurements': 2}]:
            first = run([1])
            first.update(change)
            with self.assertRaises(ValueError):
                compare(first, run([1]))


if __name__ == '__main__':
    unittest.main()
