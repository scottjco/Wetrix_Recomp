"""Register reviewed native-oriented billboard redraws without removing other art.

Plan: {"sprites":[{"id":"group-01-lod-0-frame-00",
"redraw":"work/...png"}]}. Every redraw must be RGBA at an integer scale >=2.
Only explicit IDs are registered. No original-image upscale fallback is used.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image
from hash_sprite_strips import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--pack', type=Path, default=ROOT / 'Textures/hd-sprites')
    parser.add_argument('--report', type=Path, default=ROOT / 'work/texture-hash/registered-billboard-art.json')
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    source = json.loads((ROOT / 'work/texture-hash/billboard-hashes.json').read_text())
    sources = {e['id']: e for e in source['entries']}
    database_path = args.pack / 'rt64.json'; database = json.loads(database_path.read_text())
    previous = {e['hashes']['rt64']: e for e in database['textures']}
    previous_count = len(previous)
    pending = {}; assets = {}; report = []
    for spec in plan['sprites']:
        entry = sources[spec['id']]; name = entry['id']; key = entry['rt64_hash']
        redraw = Path(spec['redraw']); redraw = redraw if redraw.is_absolute() else ROOT / redraw
        image = Image.open(redraw).convert('RGBA')
        w = entry['width']; h = entry['height']; scale, remainder = divmod(image.width, w)
        assert scale >= 2 and remainder == 0 and image.height == h * scale, (name, image.size, w, h)
        assert image.getchannel('A').getbbox(), f'Empty art: {name}'
        path = f'billboards/{name}.png'; fingerprint = hashlib.sha256(image.tobytes()).hexdigest()
        if key in pending:
            assert assets[pending[key]['path']][1] == fingerprint, f'Conflicting art for native alias {key}'
            report.append({'id': name, 'hash': key, 'alias_of': pending[key]['path']}); continue
        if key in previous:
            assert previous[key]['path'].startswith('billboards/'), f'Hash belongs to existing unrelated art: {key}'
        pending[key] = {'hashes': {'rt64': key}, 'path': path, 'shift': 'none'}
        assets[path] = (image.copy(), fingerprint)
        report.append({'id': name, 'hash': key, 'path': path, 'native_format': entry['format'], 'size': image.size, 'captured': entry['captured'], 'redraw_source': str(redraw)})
    # Validate the entire batch before changing files or the manifest.
    for relative, (image, _) in assets.items():
        destination = args.pack / relative; destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, compress_level=9)
    previous.update(pending); database['textures'] = list(previous.values())
    database_path.write_text(json.dumps(database, indent=2) + '\n')
    result = {'registered_unique_hashes': len(pending), 'texture_count_before': previous_count, 'texture_count_after': len(database['textures']), 'entries': report}
    args.report.parent.mkdir(parents=True, exist_ok=True); args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(f'Registered {len(pending)} unique billboard hashes; total {len(database["textures"])}')


if __name__ == '__main__': main()
