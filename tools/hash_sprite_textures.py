"""Prove native RGBA32 font hashes against captures before mapping all glyphs.

Specialized to the observed 36x16, line=9, tmem=0, no-TLUT font layout.
Mirrors RT64 v5 TMEMHasher and inverts shared/rt64_texture_decoder.h.
Does not modify the replacement pack or the source mapping.
"""
import argparse
import json
from pathlib import Path
import struct

from PIL import Image
import xxhash


def encode_tmem(image):
    assert image.size == (36, 16)
    memory = bytearray(4096)
    for y in range(16):
        for x in range(36):
            rgba = image.getpixel((x, y))
            for channel, value in enumerate(rgba):
                relative = y * 72 + x * 2 + (channel & 1)
                # RT64 implLoadTMEM swaps adjacent 32-bit words on odd rows.
                row, offset = divmod(relative, 72)
                address = row * 72 + (offset ^ (4 if y & 1 else 0))
                address = (address & 2047) | (2048 if channel >= 2 else 0)
                memory[address] = value
    return bytes(memory)


def digest(memory):
    # Full rows: 36*2 == line*8. RG and BA halves are hashed consecutively.
    payload = memory[:1152] + memory[2048:3200]
    payload += struct.pack('<HHIHBB', 36, 16, 0, 9, 3, 0)
    return xxhash.xxh3_64_hexdigest(payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=Path('work/copyright-assets'))
    parser.add_argument('--captures', type=Path, default=Path('work/texture-dump'))
    parser.add_argument('--output', type=Path, default=Path('work/texture-hash/font-hashes.json'))
    args = parser.parse_args()
    mapping = json.loads((args.assets / 'mapping.json').read_text())
    results = []
    verified = 0
    for glyph in mapping['glyphs']:
        native = args.assets / 'native' / f"glyph-{glyph['glyph_id']:03d}-ascii-{glyph['ascii']:03d}.png"
        memory = encode_tmem(Image.open(native).convert('RGBA'))
        computed = digest(memory)
        for captured in glyph['captured_rt64_hashes']:
            metadata = json.loads((args.captures / f'{captured}.v5.tile.json').read_text())
            tile = metadata['tile']
            assert (metadata['width'], metadata['height'], tile['line'], tile['tmem'], tile['siz'], tile['fmt'], metadata['tlut']) == (36, 16, 9, 0, 3, 0, 'None')
            original = (args.captures / f'{captured}.v5.tmem').read_bytes()
            assert digest(original) == captured, f'capture hashing failure: {captured}'
            assert memory[:1152] == original[:1152] and memory[2048:3200] == original[2048:3200], f'TMEM layout failure: {native}'
            assert computed == captured, f'hash mismatch: {native}'
            verified += 1
        results.append({'glyph_id': glyph['glyph_id'], 'character': glyph['character'], 'ascii': glyph['ascii'], 'rt64_hash': computed, 'captured': bool(glyph['captured_rt64_hashes'])})
    assert verified >= 43, f'Insufficient capture proof: {verified}'
    assert len(results) == 93
    report = {'hash_version': 5, 'verified_capture_hashes': verified, 'glyph_count': len(results), 'proof': 'All captured glyphs match the reconstructed RG/BA TMEM bytes and XXH3 v5 hash exactly.', 'glyphs': results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(f'Verified {verified} captures byte-for-byte; computed {len(results)} glyph hashes: {args.output}')


if __name__ == '__main__':
    main()
