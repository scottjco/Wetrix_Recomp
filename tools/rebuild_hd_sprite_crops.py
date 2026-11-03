"""Rebuild already-proven sprite uploads from reviewed native-oriented masters.

Keep every existing texture hash/path. Integer crop coordinates are encoded in
the authoring filenames; fail rather than guessing an unknown layout.
"""
import json
import re
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
pack=ROOT/'Textures/hd-sprites'
plan=json.loads((ROOT/'work/hd-art-pipeline/redraws.json').read_text())
specs={f"{s.get('folder','sprites')}/{s['id']}":s for s in plan['sprites']}
masters={key:pack/(key+'.png') for key in specs}
database=json.loads((pack/'rt64.json').read_text())
pending={}
records=[]
for entry in database['textures']:
    relative=entry['path']
    if Path(relative).parts[0] not in ('numbers','static','menu'):
        continue
    path=Path(relative)
    if not path.suffix:
        path=path.with_suffix('.png')
    stem=path.with_suffix('').as_posix()
    candidates=[key for key in masters if stem==key or stem.startswith(key+'-')]
    assert candidates,relative
    key=max(candidates,key=len)
    source=Image.open(masters[key]).convert('RGBA')
    old=Image.open(pack/path)
    spec=specs[key]
    scale=spec.get('scale',4)
    assert isinstance(scale,int) and scale>0,(key,scale)
    native=Image.open(ROOT/spec['original'])
    assert source.size==(native.width*scale,native.height*scale),(key,source.size,scale)
    suffix=stem[len(key):]
    if not suffix:
        result=source
        box=None
    else:
        match=re.fullmatch(r'-(?:proven|edge|strip)-(\d+)-(\d+)',suffix)
        if match:
            x,y=map(int,match.groups())
            native_size=spec.get('crop_native_sizes',{}).get(path.as_posix())
            if native_size is None:
                assert scale==4,('Missing native upload size for scaled sprite',relative)
                native_size=[old.width//4,old.height//4]
            w,h=native_size
        else:
            match=re.fullmatch(r'-crop-(\d+)-(\d+)-(\d+)-(\d+)',suffix)
            assert match,relative
            x,y,right,bottom=map(int,match.groups())
            w,h=right-x,bottom-y
        assert old.size in ((w*4,h*4),(w*scale,h*scale)),relative
        box=[x*scale,y*scale,(x+w)*scale,(y+h)*scale]
        result=source.crop(box)
    expected=(source.size if not suffix else (w*scale,h*scale))
    assert result.size==expected,(relative,result.size,expected)
    pending[path]=result
    records.append({'hash':entry['hashes']['rt64'],'path':path.as_posix(),'source':key+'.png','pixel_box':box,'scale':scale})
expected=sum(Path(e['path']).parts[0] in ('numbers','static','menu') for e in database['textures'])
assert len(records)==expected,(len(records),expected)
# All layouts validate before touching any crop. Masters stay unchanged.
for path,image in pending.items():
    if path.with_suffix('').as_posix() not in masters:
        image.save(pack/path,compress_level=9)
report=ROOT/'work/edge-qa/rebuilt-sprite-crops.json'
report.parent.mkdir(parents=True,exist_ok=True)
report.write_text(json.dumps({'mapping_count':len(records),'unique_paths':len(pending),'entries':records},indent=2)+'\n')
print(f'Rebuilt {len(records)} proven texture mappings from {len(masters)} reviewed masters; no hashes changed')
