"""Package referenced HD textures only, without ROM data or authoring captures."""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path)
args = parser.parse_args()
pack = root / 'Textures/hd-sprites'
database = json.loads((pack / 'rt64.json').read_text())
readme = '''Wetrix N64 Recomp - optional HD Textures pack

Install: extract this ZIP into C:\\recomp\\wetrix_n64 (beside Run Wetrix.cmd).
The resulting manifest must be Textures/hd-sprites/rt64.json.
Restart the game after adding or removing the pack.

Graphics > HD Textures controls the whole pack and defaults to On.
Off restores the native textures. Removing Textures/hd-sprites hides the
option on the next launch. A saved Off preference is remembered.

This preview pack contains AI-assisted redraws of the English menu sprites,
digits and static interface sprites, plus 92 paired font textures. It also
includes all 63 animated main-menu piece icons and visible gameplay sprites:
arrows, water orbs and splashes, fireballs, bombs and explosions, ice, ducks,
rocks, debris, colored orbs, sparks, rings, spikes, arches and gems.
Seven main-menu carousel labels are individually redrawn with their original
custom font at 16x native resolution for 4K, with cleaned transparent edges.
The idle/demo Wetrix plaque uses a new 16x redraw. The clock's ten states and
the English earthquake meter's gray/colored fill variants are included.
The GAME DESIGN STUDIO subtitle under ZED TWO also uses a 16x redraw.
Original frame order, animation timing, transparency and placement are kept.
The copyright text continues using the game's original letter animation.

Experimental land detail: terrain/land-detail.png adds subtle neutral surface
grain and faint grids with two different spacings over the native colored
checker polygons. Original geometry, lighting and colors remain. To remove
this preview, move that PNG outside the pack
and restart. HD Textures Off also disables it along with all other HD art.

Known coverage limits: font glyph 52 retains native artwork pending quality
review. Non-English menu variants
retain their original art. Three intentionally invisible/blinking billboard
texture hashes remain native. Some context-dependent texture uploads may
also fall back to native art. Backgrounds and other 3D materials are not remastered.
The pack is a preview; it is not a complete replacement of every 2D texture.

No ROM, executable, save data or original texture captures are included.
'''
(pack / 'README.txt').write_text(readme)
files = set()
hashes = set()
for entry in database['textures']:
    key = entry['hashes']['rt64']
    assert key not in hashes, key
    hashes.add(key)
    file = pack / entry['path']
    if not file.suffix:
        file = file.with_suffix('.png')
    # The experimental material can be removed independently of this manifest.
    if entry['path']=='terrain/land-detail.png' and not file.is_file():
        continue
    assert file.resolve().is_relative_to(pack.resolve()) and file.is_file(), file
    files.add(file)
args.output.parent.mkdir(parents=True, exist_ok=True)
with ZipFile(args.output, 'w', ZIP_DEFLATED) as archive:
    archive.write(pack / 'rt64.json', 'Textures/hd-sprites/rt64.json')
    archive.writestr('README.txt', readme)
    archive.writestr('Textures/hd-sprites/README.txt', readme)
    rights = pack / 'RIGHTS-AND-AI.txt'
    if rights.is_file():
        archive.write(rights, 'Textures/hd-sprites/RIGHTS-AND-AI.txt')
    for file in sorted(files):
        archive.write(file, file.relative_to(root).as_posix())
with ZipFile(args.output) as archive:
    assert archive.testzip() is None
print(f'{len(hashes)} mappings, {len(files)} referenced PNGs; {args.output.stat().st_size:,} bytes')
