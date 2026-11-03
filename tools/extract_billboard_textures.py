"""Extract native billboard/effect bank from verified Wetrix US ROM.
Reads16native0x90-byte descriptors, bothLODlevels and16frame slots.
Also extracts direct48x16/24x8 animatedstrip and16x16sparkleframes.
"""
import argparse,hashlib,json,struct
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
SHA='790f36a3ddd64e4dcd08c479b0b66f9080d0191473e92fa895f53d15706167bb'
NAMES=['gray_debris','red_arrow','water_orb_and_splash','green_arrow','bomb_and_explosion','fireball_and_purple_particle','ice_block','yellow_duck','fire_particle_and_rock','splash_and_colored_orbs','rock','spark_and_ring','red_blue_spike','diagonal_arrows','grayscale_glow','gold_arch']
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,default=ROOT/'Assets/data.z64');p.add_argument('--out',type=Path,default=ROOT/'work/billboard-inventory');a=p.parse_args();r=a.rom.read_bytes();assert hashlib.sha256(r).hexdigest()==SHA
 a.out.mkdir(parents=True,exist_ok=True);(a.out/'native').mkdir(exist_ok=True);entries=[];unique={};covered=bytearray(0xfc800)
 # Index exact captured PNG pixel arrays without assuming hashes across layouts.
 captures={};capture_dir=ROOT/'work/texture-dump'
 for cp in capture_dir.glob('*.v5.png'):
  im=Image.open(cp).convert('RGBA');captures.setdefault((im.size,hashlib.sha256(im.tobytes()).hexdigest()),[]).append(cp.name.split('.')[0])
 def add(id,off,w,h,fmt,**details):
  size=w*h*(4 if fmt=='RGBA32' else 1);raw=r[0x18bc40+off:0x18bc40+off+size]
  assert off+size<=0xfc800
  if fmt=='RGBA32':im=Image.frombytes('RGBA',(w,h),raw)
  else:
   im=Image.new('RGBA',(w,h));im.putdata([((v>>4)*17,)*3+((v&15)*17,) for v in raw])
  filename=f'native/{id}.png';im.save(a.out/filename);covered[off:off+size]=b'\1'*size;key=(off,w,h,fmt);alias=unique.get(key);unique.setdefault(key,id)
  entries.append(dict(id=id,file=filename,bank_offset=off,rom_offset=0x18bc40+off,byte_length=size,width=w,height=h,format=fmt,palette=None,source_sha256=hashlib.sha256(raw).hexdigest(),alias_of=alias,captured_rt64_hashes=captures.get((im.size,hashlib.sha256(im.tobytes()).hexdigest()),[]),**details));return im
 for g in range(16):
  v=struct.unpack_from('>36I',r,0x76010+g*0x90)
  for lod in range(2):
   for f in range(16):add(f'group-{g:02d}-lod-{lod}-frame-{f:02d}',v[4+lod*16+f]&0xffffff,v[lod],v[2+lod],'IA8' if g==14 else 'RGBA32',group=g,group_name=NAMES[g],lod=lod,frame=f,descriptor_rom_offset=0x76010+g*0x90,evidence='80013448 RGBA32 or80013F10 IA8; descriptorRAM80075410stride90; frame/lodpointerRAM80075420')
 for lod,(off,w,h) in enumerate([(0x46000,48,16),(0x4c000,24,8)]):
  for f in range(8):add(f'wide-strip-lod-{lod}-frame-{f:02d}',off+f*w*h*4,w,h,'RGBA32',group_name='wide_strip',lod=lod,frame=f,evidence='80014424width48height16;80014478width24height8; frame stridesC00/300')
 for f in range(16):add(f'sparkle-frame-{f:02d}',0xf7800+f*0x400,16,16,'RGBA32',group_name='sparkle_direct',lod=0,frame=f,evidence='800468A4baseF7800;80046A98frameindex<<10; render16x16')
 gaps=[];start=None
 for i,b in enumerate(covered+b'\1'):
  if not b and start is None:start=i
  if b and start is not None:gaps.append(dict(bank_offset=start,rom_offset=0x18bc40+start,byte_length=i-start));start=None
 manifest=dict(rom_sha256=SHA,bank_start=0x18bc40,bank_end=0x288440,bank_byte_length=len(covered),covered_bytes=sum(covered),unmapped_ranges=gaps,entry_count=len(entries),unique_layout_count=len(unique),entries=entries,limitations=['Names describe viewed artwork; gameplay semanticnames are not proven.','No claim that this singlebank covers everytexturebank orprocedurally generatedwaterbackground.','Captured hashes are exactRGBApixelmatches; alluncapturedlayouts require offlinehash derivation.'])
 (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2))
 for lod in (0,1):
  sheet=Image.new('RGB',(16*76,16*76),(28,28,34));d=ImageDraw.Draw(sheet)
  for e in entries:
   if 'group' not in e or e['lod']!=lod:continue
   im=Image.open(a.out/e['file']);im.thumbnail((64,54));x=e['frame']*76;y=e['group']*76;sheet.paste(im,(x+(70-im.width)//2,y+20),im);d.text((x,y),f'{e["group"]}:{e["frame"]}',fill='white')
  sheet.save(a.out/f'groups-lod-{lod}-contact.png')
 sheet=Image.new('RGB',(16*76,3*76),(28,28,34));d=ImageDraw.Draw(sheet)
 for e in entries:
  if 'group' in e:continue
  row=(e.get('lod',0) if e['group_name']=='wide_strip' else 2);x=e['frame']*76;y=row*76;im=Image.open(a.out/e['file']);im.thumbnail((70,54));sheet.paste(im,(x,y+20),im);d.text((x,y),e['id'].replace('frame-','')[-12:],fill='white')
 sheet.save(a.out/'direct-contact.png');print(f'{len(entries)} frame/LOD references; {len(unique)} unique layouts; {sum(covered)}/{len(covered)} bankbytes; {len(gaps)} gaps; {sum(bool(e["captured_rt64_hashes"]) for e in entries)} captured references')
if __name__=='__main__':main()
