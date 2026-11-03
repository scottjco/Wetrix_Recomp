"""Derive full-upload billboard hashes from native ROM bytes, verify captures.

No replacement-pack writes. Manifest entries require id,file,width,height,format,
rom_offset (absolute); file paths are relative to the manifest directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image
from hash_sprite_strips import digest, positions, ROOT


def encode(raw, width, height, fmt):
    assert fmt in ('RGBA32', 'IA8'), fmt
    line = (width * (2 if fmt == 'RGBA32' else 1) + 7) // 8
    memory = bytearray(4096); known = set()
    for y in range(height):
        for x in range(width):
            channels = range(4) if fmt == 'RGBA32' else range(1)
            for c in channels:
                relative = y * line * 8 + (x * 2 + (c & 1) if fmt == 'RGBA32' else x)
                address = relative ^ (4 if y & 1 else 0)
                if fmt == 'RGBA32': address = (address & 2047) | (2048 if c >= 2 else 0)
                else: address &= 4095
                memory[address] = raw[(y * width + x) * (4 if fmt == 'RGBA32' else 1) + c]
                known.add(address)
    meta = {'width': width, 'height': height, 'tlut': 'None', 'tile': {'siz': 3 if fmt == 'RGBA32' else 1, 'fmt': 0 if fmt == 'RGBA32' else 3, 'line': line, 'tmem': 0, 'palette': 0}}
    assert all(i in known for i in positions(meta)), 'Upload includes unknown TMEM bytes'
    return memory, meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'work/billboard-inventory/manifest.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'work/texture-hash/billboard-hashes.json')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    entries = manifest['entries']; rom = (ROOT / 'Assets/data.z64').read_bytes()
    assert hashlib.sha256(rom).hexdigest() == manifest['rom_sha256'], 'ROM revision differs from inventory'
    captures = ROOT / 'work/texture-dump'
    rows = []; verified = 0
    for entry in entries:
        fmt = entry['format']; w = entry['width']; h = entry['height']
        if fmt not in ('RGBA32', 'IA8'): continue
        offset = entry['rom_offset']; offset = int(offset, 0) if isinstance(offset, str) else offset
        raw = rom[offset:offset + w * h * (4 if fmt == 'RGBA32' else 1)]
        assert hashlib.sha256(raw).hexdigest() == entry['source_sha256'], entry['id']
        memory, meta = encode(raw, w, h, fmt)
        name = digest(memory, meta); path = captures / f'{name}.v5.tmem'; matched = path.exists()
        if matched:
            actual = path.read_bytes(); observed_meta = json.loads((captures / f'{name}.v5.tile.json').read_text())
            assert digest(actual, observed_meta) == name
            assert all(actual[i] == memory[i] for i in positions(meta)), entry['id']
            verified += 1
        rows.append(dict(entry, rt64_hash=name, captured=matched, native_sha256=hashlib.sha256(raw).hexdigest(), hash_metadata=meta, proof='Complete native upload, no inherited TMEM bytes'))
    result = {'entries': rows, 'source_count': len(rows), 'capture_verified_entries': verified, 'unique_hashes': len({e['rt64_hash'] for e in rows}), 'formats': sorted({e['format'] for e in rows})}
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'entries'}))


if __name__ == '__main__': main()
