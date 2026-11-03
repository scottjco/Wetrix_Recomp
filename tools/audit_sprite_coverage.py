"""Audit source descriptor boundaries; extract only statically proven bank cuts."""
from pathlib import Path
import json, struct, hashlib
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def decompress_native(data):
 # func8002CB1C: four independently RLE coded byte lanes, LE output byte length.
 length=int.from_bytes(data[:4],'little'); assert length%4==0
 output=bytearray(length); pos=4
 for channel in range(4):
  lane=bytearray()
  while len(lane)<length//4:
   control=data[pos];pos+=1
   if control>=128:
    n=control-127;lane.extend(data[pos:pos+n]);pos+=n
   else:
    n=control;value=data[pos];pos+=1;lane.extend([value]*n)
   assert len(lane)<=length//4
  output[channel::4]=lane
 return bytes(output),pos

def english_review(out,dynamic):
 from PIL import ImageDraw
 labels=['RESUME','QUIT','START AGAIN','PLAY AGAIN','ATTACK!','BOMB','EARTHQUAKE','GAME ON!','GAME OVER','ICE CUBE WARNING','Ice cube icon (IC)','LEVEL UP','LOST!','PAUSED','QUAKE','RAINBOW MULTIPLIER','RE-BOMB!','WATER','WON!','1 MINUTE','5 MINUTE','100 PIECES','500 PIECES','PRESET A','PRESET B','SCORE CODES','FLOOR','PLAY','RAISED LAND A','RAISED LAND B','ICE LAYER A','ICE LAYER B','RANDOM LAND','RANDOM HOLES','HALF FULL DRAIN','LESSON','MUSIC','SAVE SCORES']
 entries=[e for e in dynamic if e['language_index']==0];sheet=Image.new('RGBA',(1600,2000),(24,24,30,255));draw=ImageDraw.Draw(sheet);review=[]
 upright=out/'english-upright';upright.mkdir(exist_ok=True)
 for j,e in enumerate(entries):
  im=Image.open(out/e['file']).convert('RGBA');rotate=36<=e['sprite_id']<=50
  up=im.transpose(Image.Transpose.ROTATE_90) if rotate else im
  up.save(upright/f"{e['sprite_id']:02d}.png")
  x=j%4*400;y=j//4*200;sheet.alpha_composite(up.resize((up.width*2,up.height*2),Image.Resampling.NEAREST),(x+8,y+35));draw.text((x+8,y+5),f"ID {e['sprite_id']}: {labels[j]}",fill='white')
  alpha=im.getchannel('A');hist=alpha.histogram();rgba=list(im.getdata())
  review.append(dict(sprite_id=e['sprite_id'],text_or_identity=labels[j],native_size=list(im.size),upright_size=list(up.size),native_file=e['file'],upright_file=f"english-upright/{e['sprite_id']:02d}.png",native_to_upright='rotate90degrees_counterclockwise' if rotate else 'identity',upright_to_native='rotate90degrees_clockwise' if rotate else 'identity',alpha=dict(fully_transparent=hist[0],fully_opaque=hist[255],partially_transparent=sum(hist[1:255]),transparent_with_nonzero_rgb=sum(a==0 and bool(r or g or b) for r,g,b,a in rgba)),replacement_rule='Redraw in upright orientation then invert transform; preserve entire native canvas, transparency and independent sprite ID.'))
 sheet.save(out/'english-menu-upright-contact.png');(out/'english-menu-art-direction.json').write_text(json.dumps(dict(language_index=0,entries=review,notes=['Rotations are display-only and must be inverted for native replacements.','Source PNG files remain untouched.','Alpha is original straight RGBA32 channel data, not inferred from RGB colors.']),indent=2)+'\n')

def main():
 r=(ROOT/'Assets/data.z64').read_bytes(); out=ROOT/'work/sprite-coverage'; dest=out/'verified';dest.mkdir(parents=True,exist_ok=True)
 assert hashlib.sha256(r).hexdigest()=='790f36a3ddd64e4dcd08c479b0b66f9080d0191473e92fa895f53d15706167bb'
 captures=[]
 for f in (ROOT/'work/texture-dump').glob('*.v5.png'):
  im=Image.open(f).convert('RGBA'); captures.append((f.name.split('.')[0],im.size,im.tobytes()))
 entries=[]; intervals=[]
 for i in range(32):
  ptr=struct.unpack_from('>I',r,0x76910+i*4)[0];w,h=struct.unpack_from('>hh',r,0x7b6c0+i*4)
  off=0xbd3c0+(ptr&0xffffff);size=w*h*4;raw=r[off:off+size];name=f'sprite-{i:02d}.png';Image.frombytes('RGBA',(w,h),raw).save(dest/name)
  entries.append(dict(id=f'sprite-{i:02d}',sprite_id=i,file='verified/'+name,width=w,height=h,format='RGBA32',palette=None,rom_offset=off,byte_length=size,segmented_pointer=hex(ptr),captured_rt64_hashes=[x[0] for x in captures if x[1]==(w,h) and x[2]==raw],source_sha256=hashlib.sha256(raw).hexdigest(),evidence='func8004A190 at8004A258..8004A26C reads dimensions from8007AAC0; pointer80075D10 indexed by ID'))
  intervals.append((off,off+size))
 gaps=[];cursor=0xbd3c0
 for a,b in sorted(intervals):
  if a>cursor:gaps.append(dict(start=cursor,end=a,bytes=a-cursor))
  cursor=max(cursor,b)
 if cursor<0xe3080:gaps.append(dict(start=cursor,end=0xe3080,bytes=0xe3080-cursor))
 dynamic=[]
 for language in range(6):
  source=struct.unpack_from('>I',r,0x6c9fc+language*8)[0]&0xfffffff
  table=struct.unpack_from('>I',r,0x6ca2c+language*4)[0]-0x80000000+0xc00
  for index in range(19):
   compressed_size=struct.unpack_from('>H',r,table+index*2)[0]
   raw,consumed=decompress_native(r[source:source+compressed_size]);i=32+index
   w,h=struct.unpack_from('>hh',r,0x7b6c0+i*4);assert len(raw)==w*h*4,(language,i,len(raw),w,h)
   name=f'language-{language}-sprite-{i:02d}.png';Image.frombytes('RGBA',(w,h),raw).save(dest/name)
   dynamic.append(dict(id=f'language-{language}-sprite-{i:02d}',sprite_id=i,language_index=language,file='verified/'+name,width=w,height=h,format='RGBA32',palette=None,rom_offset=source,compressed_byte_length=compressed_size,consumed_bytes=consumed,byte_length=len(raw),source_sha256=hashlib.sha256(raw).hexdigest(),captured_rt64_hashes=[x[0] for x in captures if x[1]==(w,h) and x[2]==raw],evidence='8002D008 language source table8006BDFC, compressed-size table8006BE2C; decoder8002CB1C'))
   source+=compressed_size
 for language in range(6):
  source=struct.unpack_from('>I',r,0x6ca74+language*8)[0]&0xfffffff
  table=struct.unpack_from('>I',r,0x6caa4+language*4)[0]-0x80000000+0xc00
  for index in range(19):
   compressed_size=struct.unpack_from('>H',r,table+index*2)[0]
   raw,consumed=decompress_native(r[source:source+compressed_size]);i=51+index
   w,h=struct.unpack_from('>hh',r,0x7b6c0+i*4);assert len(raw)==w*h*4,(language,i,len(raw),w,h)
   name=f'language-{language}-sprite-{i:02d}.png';Image.frombytes('RGBA',(w,h),raw).save(dest/name)
   dynamic.append(dict(id=f'language-{language}-sprite-{i:02d}',sprite_id=i,language_index=language,file='verified/'+name,width=w,height=h,format='RGBA32',palette=None,rom_offset=source,compressed_byte_length=compressed_size,consumed_bytes=consumed,byte_length=len(raw),source_sha256=hashlib.sha256(raw).hexdigest(),captured_rt64_hashes=[x[0] for x in captures if x[1]==(w,h) and x[2]==raw],evidence='8002CEC0 language source table8006BE74, compressed-size table8006BEA4; decoder8002CB1C'))
   source+=compressed_size
 static_extra=[]
 for i in range(70,105):
  ptr=struct.unpack_from('>I',r,0x76910+i*4)[0];w,h=struct.unpack_from('>hh',r,0x7b6c0+i*4)
  base=0xeec00 if i<100 else 0x7f140;source=base+(ptr&0xffffff);raw=r[source:source+w*h*4]
  name=f'sprite-{i:02d}.png';Image.frombytes('RGBA',(w,h),raw).save(dest/name)
  static_extra.append(dict(id=f'sprite-{i:02d}',sprite_id=i,file='verified/'+name,width=w,height=h,format='RGBA32',palette=None,rom_offset=source,byte_length=len(raw),source_sha256=hashlib.sha256(raw).hexdigest(),captured_rt64_hashes=[x[0] for x in captures if x[1]==(w,h) and x[2]==raw],evidence='80025ACC loads ROM EEC00 into800876C4;80025B4C loads7F140 into800AFC94;8004A190 selects bank by ID'))
 #80025B18..80025B48 conditionally overwrites sprite84 (0407D028) with7D1C0 source.
 raw=r[0x7d1c0:0x7f140];name='sprite-84-alternate.png';Image.frombytes('RGBA',(48,42),raw).save(dest/name)
 static_extra.append(dict(id='sprite-84-alternate',sprite_id=84,file='verified/'+name,width=48,height=42,format='RGBA32',palette=None,rom_offset=0x7d1c0,byte_length=len(raw),source_sha256=hashlib.sha256(raw).hexdigest(),evidence='conditional DMA replacement80025B18..80025B48'))
 strip_matches=[]
 for hash_id, dims, raw in captures:
  offset=r.find(raw,0xbd3c0,0xe3080)
  if offset>=0:
   owners=[e['id'] for e in entries if e['rom_offset']<=offset and offset+len(raw)<=e['rom_offset']+e['byte_length']]
   strip_matches.append(dict(hash=hash_id,width=dims[0],height=dims[1],rom_offset=offset,byte_length=len(raw),source_ids=owners))
 report=dict(additional_static_entries=static_extra,dynamic_menu_entries=dynamic,captured_bank_strips=strip_matches,entries=entries,descriptor_table=dict(dimensions_rom=hex(0x7b6c0),pointers_rom=hex(0x76910)),bank=dict(start=0xbd3c0,end=0xe3080,total_bytes=0xe3080-0xbd3c0,verified_bytes=sum(b-a for a,b in intervals),unmapped_ranges=gaps),limitations=['IDs32..50 extracted for all6language banks through original four-lane RLE decoder; source output length checked against descriptor dimensions.','IDs51..69 extracted for all6languages; IDs70..104 extracted from native bank-select branches and84alternate conditional DMA source.','Whole-source PNG capture matches exclude renderer tile strips and partial uploads; missing whole hashes does not imply asset absent at runtime.','Bank tail unassigned: no guessed dimensions.'])
 all_entries=entries+dynamic+static_extra
 report['summary']=dict(native_sprite_ids=105,source_variants=len(all_entries),unique_rgba_images=len({e['source_sha256'] for e in all_entries}),dynamic_language_variants=len(dynamic),whole_image_capture_matches=sum(bool(e.get('captured_rt64_hashes')) for e in all_entries),partial_capture_matches=len(strip_matches),maximum_compressed_alignment_padding=max(e['compressed_byte_length']-e['consumed_bytes'] for e in dynamic))
 english_review(out,dynamic)
 (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['bank']));print('32 verified source textures extracted')
if __name__=='__main__':main()
