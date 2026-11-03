"""Find libultra symbol candidates by matching SSSV instruction shapes.

Candidates only: masking relocatable immediates cannot establish identity.
"""
import csv
import json
import struct
import tomllib
from pathlib import Path
from project import ROOT, verify

_, wetrix = verify()
reference = Path(r'C:\recomp\sssv')
sssv = (reference / 'sssv.us.z64').read_bytes()
syms = tomllib.loads((reference / 'SSSVRecompSyms/sssv.us.syms.toml').read_text())

def shape(data):
    words = list(struct.unpack('>' + 'I' * (len(data) // 4), data))
    while words and words[-1] == 0:
        words.pop()
    result = []
    for word in words:
        op = word >> 26
        if op in (2, 3):
            word &= 0xFC000000
        elif op in (8, 9, 10, 11, 12, 13, 14, 15) or op >= 32:
            word &= 0xFFFF0000
        result.append(word)
    return tuple(result)

refs = {}
for section in syms['section']:
    for func in section.get('functions', []):
        if not func['name'].startswith(('os', '__os', 'gu', 'al', 'bcopy', 'bzero', 'mem', 'str')):
            continue
        offset = section['rom'] + func['vram'] - section['vram']
        key = shape(sssv[offset:offset + func['size']])
        refs.setdefault(key, []).append(func['name'])
matches = []
for row in csv.DictReader((ROOT / 'work/cpu-functions.csv').open()):
    offset, size = int(row['vrom'], 16), int(row['length'], 16)
    key = shape(wetrix[offset:offset + size])
    if key in refs:
        matches.append({'address': row['address'], 'size': row['length'], 'candidates': refs[key], 'instructions': len(key)})
(ROOT / 'work/reference-candidates.json').write_text(json.dumps(matches, indent=2))
print(json.dumps(matches, indent=2))
