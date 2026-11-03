"""Align authored animation atlas frames to verified native canvases."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--atlas', type=Path, required=True)
p.add_argument('--group', type=int, required=True)
p.add_argument('--columns', type=int, default=4)
p.add_argument('--rows', type=int, default=2)
p.add_argument('--cycle', type=int, help='Native cycle length when some slots are intentionally hidden')
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
atlas = Image.open(a.atlas).convert('RGBA')
a.out.mkdir(parents=True, exist_ok=True)
source = json.loads((ROOT/'work/billboard-inventory/manifest.json').read_text())
entries = [e for e in source['entries'] if e.get('group') == a.group]
specs, canonical = [], {}
preview = Image.new('RGB', (16*136, 156), (30,30,35))
draw = ImageDraw.Draw(preview)
for entry in entries:
    if a.cycle and entry['frame'] % a.cycle >= a.columns*a.rows:
        continue
    f = entry['frame'] % (a.columns*a.rows)
    col,row = f%a.columns, f//a.columns
    cell = atlas.crop((round(col*atlas.width/a.columns), round(row*atlas.height/a.rows),
                       round((col+1)*atlas.width/a.columns), round((row+1)*atlas.height/a.rows)))
    bounds = cell.getchannel('A').point(lambda x:255 if x>16 else 0).getbbox()
    assert bounds, entry['id']
    art = cell.crop(bounds)
    native = Image.open(ROOT/'work/billboard-inventory'/entry['file']).convert('RGBA')
    # Native exports contain invisible alpha-1 residue far from the sprite.
    # Align visible ink, otherwise edge-on arrows become full-height blocks.
    bbox = native.getchannel('A').point(lambda x:255 if x>8 else 0).getbbox()
    if not bbox:
        # Fully invisible native slots intentionally have no replacement.
        continue
    identity = (entry['source_sha256'], entry['width'], entry['height'],entry['format'])
    if identity in canonical:
        output = canonical[identity]
    else:
        output = Image.new('RGBA',(native.width*4,native.height*4))
        art = art.resize(((bbox[2]-bbox[0])*4,(bbox[3]-bbox[1])*4), Image.Resampling.LANCZOS)
        opacity = native.getchannel('A').getextrema()[1]
        if opacity < 255:
            art.putalpha(art.getchannel('A').point(lambda x:round(x*opacity/255)))
        output.paste(art,(bbox[0]*4,bbox[1]*4))
        canonical[identity] = output
    file = a.out/f"{entry['id']}.png"
    output.save(file)
    specs.append({'id':entry['id'],'redraw':str(file.resolve())})
    if entry['lod']==0:
        x=entry['frame']*136
        preview.paste(output,(x,20),output)
        draw.text((x,0),str(entry['frame']),fill='white')
(a.out/'registration.json').write_text(json.dumps({'sprites':specs},indent=2))
preview.save(a.out/'contact.png')
print(f'{len(specs)} frames; {len(canonical)} distinct native sources')
