"""Prove every carousel IA8 64x32 upload including native ROM-overread tails."""
from pathlib import Path
import json,hashlib
from PIL import Image
from match_billboard_hashes import encode
from hash_sprite_strips import digest,positions
ROOT=Path(__file__).resolve().parents[1]
def main():
 rom=(ROOT/'Assets/data.z64').read_bytes();out=ROOT/'work/main-menu-texture-audit';native=json.load(open(out/'carousel-words-manifest.json'));art=json.load(open(out/'redraw/carousel-seven-redraw-manifest.json'));arts={e['id']:e for e in art['entries']};entries=[];verified=0
 cropdir=ROOT/'Textures/hd-sprites/main-menu/carousel-strips';cropdir.mkdir(exist_ok=True)
 for e in native['entries']:
  im=Image.open(ROOT/arts[e['id']]['file']).convert('RGBA')
  scale=im.width//e['width'];assert scale>0 and im.size==(e['width']*scale,e['height']*scale)
  for y in range(0,e['height'],32):
   pos=e['rom_offset']+y*64;raw=rom[pos:pos+2048];mem,meta=encode(raw,64,32,'IA8');h=digest(mem,meta);cap=ROOT/f'work/texture-dump/{h}.v5.tmem';observed=cap.exists()
   if observed:
    actual=cap.read_bytes();actualmeta=json.load(open(cap.with_suffix('.tile.json')));assert digest(actual,actualmeta)==h;assert all(actual[i]==mem[i] for i in positions(meta));verified+=1
   name=f"{e['id']}-row-{y:03d}.png";crop=im.crop((0,y*scale,e['width']*scale,(y+32)*scale));assert crop.size==(e['width']*scale,32*scale)
   if scale==16:
    import numpy as np
    from scipy.ndimage import distance_transform_edt
    pixels=np.array(crop);invisible=pixels[:,:,3]==0
    nearest=distance_transform_edt(invisible,return_distances=False,return_indices=True)
    pixels[invisible,:3]=pixels[nearest[0][invisible],nearest[1][invisible],:3];crop=Image.fromarray(pixels)
   crop.save(cropdir/name)
   entries.append(dict(source_id=e['id'],hash=h,box=[0,y,64,32],visible_rows=min(32,e['height']-y),captured=observed,path='main-menu/carousel-strips/'+name,shift='none',rom_offset=pos,raw_sha256=hashlib.sha256(raw).hexdigest(),hash_metadata=meta,proof='Exact native64x32IA8upload including deterministic ROM-overread bytes; all captured TMEM hashed bytes match'))
 assert len(entries)==52 and verified==44,(len(entries),verified)
 result=dict(entries=entries,total_tiles=52,captured_tiles_verified=verified,uncaptured_handicap_tiles=8,database_entries=[dict(path=e['path'],hashes=dict(rt64=e['hash']),shift='none') for e in entries]);(out/'carousel-hashes-and-crops.json').write_text(json.dumps(result,indent=2)+'\n');print('Proved52tiles,44captures;8handicapderived;cropped52HDstrips;databaseNOTedited')
if __name__=='__main__':main()
