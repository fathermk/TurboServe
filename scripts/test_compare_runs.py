import unittest

from compare_runs import compare


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
        self.assertIn('environment.server_precision', result['unknown_fields'])

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
