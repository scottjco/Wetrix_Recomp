"""Verify exact native sprite subimages against RT64 captures; never guess hashes."""
import json
from pathlib import Path
from build_hd_sprite_pack import ROOT, read, exact_subimages

coverage = ROOT / 'work/sprite-coverage'
manifest = json.loads((coverage / 'manifest.json').read_text())
entries = sum((manifest.get(key, []) for key in
               ['entries', 'additional_static_entries', 'dynamic_menu_entries']), [])
captures = {p.stem.split('.')[0]: read(p)
            for p in (ROOT / 'work/texture-dump').glob('*.v5.png')}
matches = []
for entry in entries:
    source = read(coverage / entry['file'])
    for hash_value, tile in captures.items():
        boxes = exact_subimages(source, tile)
        if boxes:
            matches.append({'source_id': entry['id'], 'source_file': entry['file'],
                'hash': hash_value, 'capture_size': tile.size, 'boxes': boxes,
                'verification': 'exact RGBA pixels; transparent RGB normalized; native orientation'})
out = ROOT / 'work/hd-art-pipeline/verified-capture-matches.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({'source_count': len(entries), 'capture_count': len(captures),
    'matches': matches}, indent=2) + '\n')
print(f'Verified {len(matches)} source/capture matches across {len(entries)} sources and {len(captures)} captures')
