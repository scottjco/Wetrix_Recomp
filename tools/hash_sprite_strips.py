"""Audit RT64 v5 capture hashes and derive provable func8004A190 strip hashes."""
import json
import struct
from pathlib import Path
import xxhash
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def positions(meta):
    t = meta['tile']; w = meta['width']; h = meta['height']
    rgba = t['siz'] == 3 and t['fmt'] == 0
    half = rgba or meta['tlut'] != 'None'
    size = 2048 if half else 4096; mask = size - 1
    stride = t['line'] * 8; rowbytes = max(w << (2 if rgba else t['siz']) >> 1, 1)
    start = (t['tmem'] * 8) & mask
    result = []
    def append(base, upper, count, odd):
        if base + count > size:
            result.extend(range(base + upper, size + upper))
            count = min(count - (size - base), base); base = 0
        if odd:
            words, tail = divmod(count, 8)
            result.extend(range(base + upper, base + words * 8 + upper)); base += words * 8
            if tail > 4:
                result.extend(range(base + upper, base + tail - 4 + upper))
                result.extend(range(base + 4 + upper, base + 8 + upper))
            elif tail:
                result.extend(range(base + 4 + upper, base + 4 + tail + upper))
        else:
            result.extend(range(base + upper, base + count + upper))
    for upper in ([0, size] if rgba else [0]):
        if stride > rowbytes:
            for y in range(h): append((start + y * stride) & mask, upper, rowbytes, y & 1)
        else: append(start, upper, stride * (h - 1) + rowbytes, False)
    return result


def digest(memory, meta):
    t = meta['tile']; indices = positions(meta)
    payload = bytes(memory[i] for i in indices)
    tlut = {'None': 0, 'RGBA16': 32768, 'IA16': 49152}[meta['tlut']]
    if tlut:
        ci4 = t['siz'] == 0
        used = set()
        for value in payload:
            used.update([value & 15, value >> 4] if ci4 else [value])
        address = 2048 + (t['palette'] * 128 if ci4 else 0)
        payload += b''.join(memory[address + i * 8:address + i * 8 + 8] for i in sorted(used))
    payload += struct.pack('<HHIHBB', meta['width'], meta['height'], tlut, t['line'], t['siz'], t['fmt'])
    return xxhash.xxh3_64_hexdigest(payload)


def main():
    capture_dir = ROOT / 'work/texture-dump'
    captures = {}
    failures = []
    for path in list(capture_dir.glob('*.v5.tile.json')):
        name = path.name.split('.')[0]; meta = json.loads(path.read_text())
        raw = path.with_name(name + '.v5.tmem').read_bytes()
        actual = digest(raw, meta)
        if actual != name: failures.append((name, actual))
        captures[name] = (raw, meta)
    assert not failures, failures[:10]
    manifest = json.loads((ROOT / 'work/sprite-coverage/manifest.json').read_text())
    entries = sum((manifest.get(key, []) for key in ['entries', 'additional_static_entries', 'dynamic_menu_entries']), [])
    rom = (ROOT / 'Assets/data.z64').read_bytes()
    predictions = []; unresolved = []; capture_matches = 0
    for entry in entries:
        w = entry['width']; h = entry['height']
        native = Image.open(ROOT / 'work/sprite-coverage' / entry['file']).convert('RGBA').tobytes()
        memory = bytearray(4096); known = bytearray(4096)
        for x in range(0, w, 31):
            for y in range(0, h, 31):
                cw = min(32, w - x); ch = min(32, h - y); line = (cw * 2 + 7) // 8
                for yy in range(ch):
                    for xx in range((cw + 1) // 2 * 2):
                        source = ((y + yy) * w + x + xx) * 4
                        rgba = native[source:source + 4]
                        if len(rgba) != 4 and 'compressed_byte_length' not in entry:
                            address = entry['rom_offset'] + source; rgba = rom[address:address + 4]
                        for channel in range(4):
                            address = ((yy * line * 8 + xx * 2 + (channel & 1)) & 2047) ^ (4 if yy & 1 else 0)
                            address |= 2048 if channel >= 2 else 0
                            if len(rgba) == 4: memory[address] = rgba[channel]; known[address] = 1
                            else: known[address] = 0
                meta = {'width': 32, 'height': 32, 'tlut': 'None', 'tile': {'siz': 3, 'fmt': 0, 'line': line, 'tmem': 0, 'palette': 0}}
                base = {'source_id': entry['id'], 'source_file': entry['file'], 'x': x, 'y': y, 'loaded_width': cw, 'loaded_height': ch, 'hash_width': 32, 'hash_height': 32, 'line': line}
                missing = sum(not known[i] for i in positions(meta))
                if missing:
                    unresolved.append(dict(base, unknown_hashed_bytes=missing, reason='TMEM bytes depend on prior sprite draw history or unavailable decompressed allocation padding'))
                    continue
                name = digest(memory, meta)
                matched = name in captures
                if matched:
                    actual, capture_meta = captures[name]
                    assert all(actual[i] == memory[i] for i in positions(meta))
                    capture_matches += 1
                predictions.append(dict(base, rt64_hash=name, captured=matched, proof='Every hashed TMEM byte reconstructed from native source and preceding tiles of this sprite'))
    result = {'verified_capture_hash_count': len(captures), 'source_count': len(entries), 'deterministic_tiles': predictions, 'unresolved_tiles': unresolved, 'captured_deterministic_tile_matches': capture_matches, 'limitation': 'A renderer tail retains TMEM bytes outside its load. Hashes cannot be universal when those bytes depend on earlier sprite draw history. Unresolved tiles are deliberately not assigned hashes.'}
    out = ROOT / 'work/texture-hash/sprite-strip-hashes.json'; out.parent.mkdir(exist_ok=True, parents=True)
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if not isinstance(v, list)}))
    print(f'Deterministic tiles {len(predictions)}; unresolved {len(unresolved)}; {out}')


if __name__ == '__main__': main()
