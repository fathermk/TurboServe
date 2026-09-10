import json
import unittest
from unittest.mock import patch

import runtime_snapshot as runtime


class RuntimeTests(unittest.TestCase):
    def test_wrong_http_config_is_rejected(self):
        with patch.object(runtime, 'identity', return_value={'id': 'a'}), \
             patch.object(runtime, 'docker', return_value=json.dumps({'triton_config_sha256': 'wrong'})):
            with self.assertRaises(ValueError):
                runtime.capture('expected')

    def test_replaced_container_is_rejected(self):
        with patch.object(runtime, 'identity', side_effect=[{'id': 'a'}, {'id': 'b'}]), \
             patch.object(runtime, 'docker', return_value=json.dumps({'triton_config_sha256': 'same'})):
            with self.assertRaises(ValueError):
                runtime.capture('same')

    def test_edits_during_run_are_rejected(self):
        original = {'triton_config_sha256': 'a', 'container': {},
                    'yaml_sha256': 'before', 'packages': {}}
        with patch.object(runtime, 'capture', return_value={**original, 'yaml_sha256': 'after'}):
            with self.assertRaises(ValueError):
                runtime.verify(original)

    def test_matching_capture(self):
        with patch.object(runtime, 'identity', return_value={'id': 'a'}), \
             patch.object(runtime, 'docker', return_value=json.dumps({'triton_config_sha256': 'same'})):
            self.assertEqual(runtime.capture('same')['container']['id'], 'a')


if __name__ == '__main__':
    unittest.main()
