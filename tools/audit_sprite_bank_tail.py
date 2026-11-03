from pathlib import Path
from PIL import Image,ImageDraw
import struct,json
r=Path('Assets/data.z64').read_bytes();out=Path('work/sprite-bank-tail');es=[]
def rgba16(raw):
 out=[]
 for n in range(0,len(raw),2):
  p=int.from_bytes(raw[n:n+2],'big');c=[(p>>11)&31,(p>>6)&31,(p>>1)&31];out.extend([(x<<3)|(x>>2) for x in c]+[255*(p&1)])
 return bytes(out)
for i in range(8):es.append(dict(id=f'meter-wave-{i}',rom_offset=0xbd3c0+0x1f910+i*160,width=16,height=5,format='RGBA16',evidence='func80047128:RGBA16FD10,F510tile15x4inclusive;frameoffsetD8007917C'))
es.extend([dict(id='soft-shadow',rom_offset=0xbd3c0+0x1fe10,width=32,height=32,format='RGBA32',evidence='func80047FAC FD18/F518 tile31x31inclusive'),dict(id='grid-overlay',rom_offset=0xbd3c0+0x20e10,width=32,height=32,format='RGBA32',evidence='func800482D4 pointer20E10'),dict(id='meter-single',rom_offset=0xbd3c0+0x21e40,width=32,height=200,format='RGBA16',evidence='8003BFCC..8003BFFC source pointer21E40,width32,height200,siz2;800486FC RGBA16upload'),dict(id='meter-multiplayer',rom_offset=0xbd3c0+0x25040,width=16,height=100,format='RGBA16',evidence='8003C014..8003C054 sourcepointer25040,width16,height100,siz2')])
for e in es:
 n=e['width']*e['height']*(4 if e['format']=='RGBA32' else 2);raw=r[e['rom_offset']:e['rom_offset']+n];e['byte_length']=n;e['file']='native/'+e['id']+'.png';Image.frombytes('RGBA',(e['width'],e['height']),raw if e['format']=='RGBA32' else rgba16(raw)).save(out/e['file'])
sheet=Image.new('RGBA',(1200,900),(28,28,34,255));d=ImageDraw.Draw(sheet)
for j,e in enumerate(es):
 im=Image.open(out/e['file']);im=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST);x=(j%6)*200;y=(j//6)*200;sheet.alpha_composite(im,(x,y+20));d.text((x,y),f"{e['id']} {e['format']}",fill='white')
matches=0
for e in es:e['captured_tiles']=[]
for f in Path('work/texture-dump').glob('*.v5.tile.json'):
 t=json.load(open(f));fmt=t['tile']['fmt'];siz=t['tile']['siz']
 if fmt!=0 or siz not in (2,3):continue
 data=f.with_name(f.name.replace('.tile.json','.rice.rdram')).read_bytes();raw=b''.join(data[n:n+4][::-1] for n in range(0,len(data),4))
 for e in es:
  if siz!=(3 if e['format']=='RGBA32' else 2):continue
  pos=r.find(raw,e['rom_offset'],e['rom_offset']+e['byte_length'])
  if pos<0:continue
  bpp=4 if siz==3 else 2;pixel=(pos-e['rom_offset'])//bpp;y,x=divmod(pixel,e['width']);e['captured_tiles'].append(dict(hash=f.name.split('.')[0],x=x,y=y,width=t['width'],height=t['height'],rom_offset=pos,byte_length=len(raw),proof='Entire word-reversed riceRDRAMupload bytes exactly present in source native range'));matches+=1
sheet.save(out/'native-contact.png');(out/'manifest.json').write_text(json.dumps(dict(entries=es,unassigned_48bytes=dict(rom_start=0xbd3c0+0x21e10,rom_end=0xbd3c0+0x21e40,hex=r[0xbd3c0+0x21e10:0xbd3c0+0x21e40].hex())),indent=2)+'\n');print('frameoffsetstride',struct.unpack_from('>I',r,0x79d7c)[0])
