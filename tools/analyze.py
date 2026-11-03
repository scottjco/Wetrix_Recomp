"""Draft CPU map from the inspected ROM. Requires the analysis requirements."""
import csv
from pathlib import Path
import subprocess
import sys
from project import ROOT, verify

verify()
work = ROOT / 'work'
work.mkdir(exist_ok=True)
subprocess.run([sys.executable, '-m', 'spimdisasm', 'singleFileDisasm',
    str(ROOT / 'Assets/data.z64'), str(work / 'cpu'),
    '--start', '0x10DC0', '--end', '0x648FC', '--vram', '0x800101C0',
    '--compiler', 'KMC', '--function-info', str(work / 'cpu-functions.csv'),
    '--save-context', str(work / 'cpu-context.csv'), '--quiet'], check=True)
rows = list(csv.DictReader((work / 'cpu-functions.csv').open()))
text = '''# ANALYSIS DRAFT: function boundaries require validation.
# ROM offset 0x1000 maps to RAM 0x80000400; startup clears BSS at 0x8007C380.
[[section]]
name = ".main"
rom = 0x1000
vram = 0x80000400
size = 0x7BF80
functions = [
    {name = "recomp_entrypoint", vram = 0x80000400, size = 0x3C},
'''
for row in rows:
    text += f'    {{name = "{row["name"]}", vram = {row["address"]}, size = {row["length"]}}},\n'
(work / 'wetrix.draft.syms.toml').write_text(text + ']\n')
print(f'Draft map: {len(rows) + 1} functions, including entrypoint')
