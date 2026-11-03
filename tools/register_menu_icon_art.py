"""Register the 63 authored menu-icon frames with exact captured CI8 tile IDs."""
import json
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
pack=ROOT/'Textures/hd-sprites'
source=json.loads((ROOT/'work/main-menu-texture-audit/piece-icons-manifest.json').read_text())
dbpath=pack/'rt64.json'
db=json.loads(dbpath.read_text())
index={e['hashes']['rt64']:e for e in db['textures']}
pending={}
for entry in source['entries']:
    full=pack/'main-menu'/f"piece-group-{entry['group']}-frame-{entry['frame']}.png"
    assert full.is_file(), full
    art=Image.open(full).convert('RGBA')
    assert art.size==(entry['width']*4,entry['height']*4)
    for part,strip in enumerate(entry['strips']):
        assert strip['maximum_channel_difference']==0
        key=strip['hash']
        relative=f"main-menu/piece-group-{entry['group']}-frame-{entry['frame']}-part-{part}.png"
        x,y,w,h=strip['box']
        tile=art.crop((x*4,y*4,(x+w)*4,(y+h)*4))
        if key in pending:
            assert pending[key][1].tobytes()==tile.tobytes()
            continue
        assert key not in index or index[key]['path'].startswith('main-menu/'),key
        pending[key]=(relative,tile)
for key,(relative,tile) in pending.items():
    tile.save(pack/relative)
    index[key]={'hashes':{'rt64':key},'path':relative,'shift':'none'}
db['textures']=list(index.values())
dbpath.write_text(json.dumps(db,indent=2)+'\n')
print(f'{len(source["entries"])} main-menu frames; {len(pending)} exact captured tile mappings; {len(index)} pack mappings')
