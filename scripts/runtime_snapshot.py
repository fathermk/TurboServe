"""Read-only Docker evidence for the local Triton benchmark."""

from datetime import datetime, timezone
import hashlib
import json
import subprocess


CONTAINER = 'turboserve-triton'


def docker(*args, input=None):
    return subprocess.run(['sudo', '-n', 'docker', *args], input=input,
                          capture_output=True, text=True, timeout=30,
                          check=True).stdout


def identity():
    template = ('{"id":{{json .Id}},"image":{{json .Image}},'
                '"started_at":{{json .State.StartedAt}},'
                '"running":{{json .State.Running}},'
                '"restarts":{{json .RestartCount}},'
                '"ports":{{json .NetworkSettings.Ports}}}')
    result = json.loads(docker('inspect', CONTAINER, '--format', template))
    if result.get('running') is not True:
        raise ValueError('Triton container is not running')
    bindings = (result.get('ports') or {}).get('8000/tcp') or []
    if {'HostIp': '127.0.0.1', 'HostPort': '8000'} not in bindings:
        raise ValueError('Container does not publish expected local HTTP endpoint')
    return result


def capture(expected_config_hash):
    before = identity()
    code = '''
import hashlib, importlib.metadata, json, os
from pathlib import Path
from urllib.request import urlopen
import yaml
p = Path(os.environ.get('LLM_CONFIG_PATH', '/workspace/turboserve-model.yaml'))
raw = p.read_bytes()
with urlopen('http://127.0.0.1:8000/v2/models/tensorrt_llm/config', timeout=10) as r:
    triton = json.load(r)
print(json.dumps({'selected_yaml': yaml.safe_load(raw),
                  'yaml_sha256': hashlib.sha256(raw).hexdigest(),
                  'triton_config_sha256': hashlib.sha256(json.dumps(triton, sort_keys=True).encode()).hexdigest(),
                  'packages': {p: importlib.metadata.version(p) for p in
                    ['tensorrt-llm', 'torch', 'transformers', 'openai']}}))
'''
    evidence = json.loads(docker('exec', '-i', CONTAINER, 'python3', '-', input=code))
    if not expected_config_hash or evidence['triton_config_sha256'] != expected_config_hash:
        raise ValueError('Container and benchmark HTTP model configurations differ')
    if identity() != before:
        raise ValueError('Container changed during evidence capture')
    return {'captured_at_utc': datetime.now(timezone.utc).isoformat(),
            'container': before, **evidence,
            'provenance': 'Docker inspection and current selected YAML inside container',
            'limitation': 'Selected YAML is declared configuration, not introspection of loaded tensors'}


def verify(snapshot):
    """Detect restarts, replacements and configuration edits during a run."""
    after = capture(snapshot['triton_config_sha256'])
    for field in ['container', 'yaml_sha256', 'packages']:
        if after[field] != snapshot[field]:
            raise ValueError(f'Runtime evidence changed during benchmark: {field}')
    return after['captured_at_utc']
