"""Smoke-check optional HD pack startup and saved preference, restoring user files."""
import json
from pathlib import Path
import subprocess
import time

root = Path(__file__).resolve().parents[1]
pack = (root / 'Textures/hd-sprites').resolve()
parked = (root / 'Textures/hd-sprites-check-away').resolve()
assert pack.parent == (root / 'Textures').resolve() == parked.parent
assert pack.is_dir() and not parked.exists()
config = root / 'config/user/graphics.json'
original = config.read_bytes()
results = []
try:
    for name, present, preference in [('default-on', True, None), ('saved-off', True, False), ('absent', False, None)]:
        data = json.loads(original)
        data.pop('hd_textures', None)
        if preference is not None:
            data['hd_textures'] = preference
        config.write_text(json.dumps(data, indent=4))
        if not present:
            pack.rename(parked)
        log_path = root / f'work/hd-check-{name}.log'
        with log_path.open('wb') as log:
            process = subprocess.Popen([str(root / 'build/windows/Release/WetrixRuntime.exe'), 'Assets/data.z64'], cwd=root, stdout=log, stderr=log)
            try:
                time.sleep(7)
                assert process.poll() is None, f'{name}: runtime exited {process.returncode}'
            finally:
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=10)
        text = log_path.read_text(errors='replace')
        expected = f"HD Textures: pack {'installed' if present else 'absent'}, option {'visible' if present else 'hidden'}, preference {'off' if preference is False else 'on'}"
        assert expected in text, (name, expected, text[:2000])
        assert ('RT64 sprite texture pack loaded:' in text) == present
        results.append({'case': name, 'passed': True, 'startup': expected})
        if parked.exists():
            parked.rename(pack)
finally:
    config.write_bytes(original)
    if parked.exists():
        parked.rename(pack)
(root / 'work/hd-toggle-validation.json').write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
