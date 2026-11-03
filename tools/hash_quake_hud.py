"""Prove complete English earthquake fill-slice hashes, preserve native shake renderer."""
from pathlib import Path
import json,hashlib
from PIL import Image
from hash_sprite_strips import digest,positions
ROOT=Path(__file__).resolve().parents[1]
def encode16(raw,w,h):
 line=(w*2+7)//8;memory=bytearray(4096)
 for y in range(h):
  for x in range(w*2):memory[(y*line*8+x)^(4 if y&1 else 0)]=raw[y*w*2+x]
 return memory,dict(width=w,height=h,tlut='None',tile=dict(siz=2,fmt=0,line=line,tmem=0,palette=0))
def main():
 rom=(ROOT/'Assets/data.z64').read_bytes();audit=ROOT/'work/quake-hud-audit';source=json.load(open(audit/'manifest.json'));entries=[e for e in source['entries'] if e['language']==0];folder=ROOT/'Textures/hd-sprites/quake/tiles';folder.mkdir(parents=True,exist_ok=True);rows=[];proofs=[]
 for e in entries:
  art=Image.open(ROOT/f'Textures/hd-sprites/quake/{e["id"]}.png').convert('RGBA');w=e['width'];half=e['height']//2;assert art.size==(w*4,e['height']*4)
  for state in ['gray','color']:
   for h in range(1,half):
    y=0 if state=='gray' else e['height']-h;off=e['rom_offset']+y*w*2;raw=rom[off:off+w*h*2];memory,meta=encode16(raw,w,h);name=digest(memory,meta);cap=ROOT/f'work/texture-dump/{name}.v5.tmem';observed=cap.exists()
    if observed:
     actual=cap.read_bytes();actualmeta=json.load(open(cap.with_suffix('.tile.json')));assert digest(actual,actualmeta)==name;assert all(actual[i]==memory[i] for i in positions(meta));proofs.append(name)
    crop=art.crop((0,y*4,w*4,(y+h)*4));dest=folder/(name+'.png');crop.save(dest);rows.append(dict(source_id=e['id'],state=state,rows=h,source_y=y,rom_offset=off,source_sha256=hashlib.sha256(raw).hexdigest(),hash=name,captured=observed,path='quake/tiles/'+name+'.png',box=[0,y,w,h],hash_metadata=meta,proof='NativeRGBA16 full knownupload; no inheritedTMEMbytes; allcapturedhashbytes exact'))
 known={t['hash'] for e in entries for t in e['captured_tiles']};assert known==set(proofs),(len(known),len(set(proofs)),known-set(proofs));assert len(rows)==296
 result=dict(entries=rows,total_tiles=296,captured_hashes_byte_verified=len(set(proofs)),single_tiles=198,multiplayer_tiles=98,scope='Englishallnativeclampedfillpositions; singlewidth16 heights1..99, multiplayerwidth8 heights1..49; sourcegrayy0/colorfromtail, noROMoverread',database_entries=[dict(path=e['path'],hashes=dict(rt64=e['hash']),shift='none') for e in rows]);(audit/'hashes-and-redraws-english.json').write_text(json.dumps(result,indent=2)+'\n');print('296Englishquakefilltiles prepared;90capturedhashes+TMEMbyteverified;DBnotedited')
if __name__=='__main__':main()
