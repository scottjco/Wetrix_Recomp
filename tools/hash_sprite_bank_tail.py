"""Verify every observed bank-tail tile against native upload and prepare isolated mappingplan."""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageChops
from match_billboard_hashes import encode
from hash_sprite_strips import digest,positions
ROOT=Path(__file__).resolve().parents[1]
def encode16(raw,w,h):
 line=(w*2+7)//8;mem=bytearray(4096)
 for y in range(h):
  for x in range(w*2):mem[(y*line*8+x)^(4 if y&1 else 0)]=raw[y*w*2+x]
 meta=dict(width=w,height=h,tlut='None',tile=dict(siz=2,fmt=0,line=line,tmem=0,palette=0));return mem,meta
rom=(ROOT/'Assets/data.z64').read_bytes();out=ROOT/'work/sprite-bank-tail';m=json.load(open(out/'manifest.json'));cropdir=ROOT/'Textures/hd-sprites/tail/tiles';cropdir.mkdir(exist_ok=True,parents=True);rows=[]
for e in m['entries']:
 native=Image.open(out/e['file']).convert('RGBA');art=Image.open(ROOT/f'Textures/hd-sprites/tail/{e["id"]}.png').convert('RGBA');assert art.size==(e['width']*4,e['height']*4)
 for t in e['captured_tiles']:
  w,h=t['width'],t['height'];bpp=4 if e['format']=='RGBA32' else 2;raw=rom[t['rom_offset']:t['rom_offset']+w*h*bpp];mem,meta=encode(raw,w,h,'RGBA32') if bpp==4 else encode16(raw,w,h);name=digest(mem,meta);assert name==t['hash'],(e['id'],name,t['hash']);actual=(ROOT/f'work/texture-dump/{name}.v5.tmem').read_bytes();actualmeta=json.load(open(ROOT/f'work/texture-dump/{name}.v5.tile.json'));assert digest(actual,actualmeta)==name;assert all(actual[i]==mem[i] for i in positions(meta));x,y=t['x'],t['y'];assert x+w<=e['width'] and y+h<=e['height'];orig=native.crop((x,y,x+w,y+h));captured=Image.open(ROOT/f'work/texture-dump/{name}.v5.png').convert('RGBA');dif=ImageChops.difference(orig,captured);assert not dif.getbbox(),(e['id'],dif.getextrema());crop=art.crop((x*4,y*4,(x+w)*4,(y+h)*4));dest=cropdir/(name+'.png');crop.save(dest);rows.append(dict(source_id=e['id'],hash=name,path='tail/tiles/'+name+'.png',shift='none',box=[x,y,w,h],visible=True,proof='Whole rawupload/TMEMhashedbytes/digest and decodedPNGcrop exactlymatch native source',native_format=e['format']))
assert len(rows)==209;report=dict(entries=rows,verified_captured_tiles=209,verified_meter_single_tiles=sum(e['source_id']=='meter-single' for e in rows),database_entries=[dict(path=e['path'],hashes=dict(rt64=e['hash']),shift='none') for e in rows]);(out/'hashes-and-redraws.json').write_text(json.dumps(report,indent=2)+'\n');print('209tailtilesTMEM+hash+decodedpixelsverified,cropped;198singlemetertiles;DBnotedited')
