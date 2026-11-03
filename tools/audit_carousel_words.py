from pathlib import Path
from PIL import Image,ImageDraw,ImageChops
import struct,json
r=Path('Assets/data.z64').read_bytes();out=Path('work/main-menu-texture-audit');entries=[];sheet=Image.new('RGBA',(900,7*160),(28,28,34,255));d=ImageDraw.Draw(sheet)
for j,o in enumerate([0x6d6fc,0x6d874,0x6d9ec,0x6db64,0x6dcdc,0x6de54,0x6dfcc]):
 name=r[o-16:o].split(b'\0')[0].decode();ptr,h,w=struct.unpack_from('>III',r,o);off=0xeec00+(ptr&0xffffff);data=r[off:off+w*h];raw=bytes(v for p in data for v in [(p>>4)*17]*3+[(p&15)*17]);im=Image.frombytes('RGBA',(w,h),raw);im.save(out/f'native/carousel-{name}.png');up=im.transpose(Image.Transpose.ROTATE_90);up.save(out/f'native/carousel-{name}-upright.png');sheet.alpha_composite(up.resize((up.width*2,up.height*2),Image.Resampling.NEAREST),(200,j*160+20));d.text((0,j*160+20),f'{name}: native{w}x{h}',fill='white');entries.append(dict(id='carousel-'+name,name=name,file=f'native/carousel-{name}.png',upright_file=f'native/carousel-{name}-upright.png',format='IA8',width=w,height=h,rom_offset=off,byte_length=w*h,descriptor_rom=o,native_to_upright='rotate90CCW',strips=[]))
for f in Path('work/texture-dump').glob('*.v5.tile.json'):
 t=json.load(open(f));tile=t['tile']
 if (t['width'],t['height'],tile['fmt'],tile['siz'])!=(64,32,3,1):continue
 p=f.with_name(f.name.replace('.tile.json','.rice.rdram'));raw=p.read_bytes();sw=b''.join(raw[n:n+4][::-1] for n in range(0,len(raw),4));pos=r.find(sw)
 for e in entries:
  if e['rom_offset']<=pos<e['rom_offset']+e['byte_length']:
   delta=pos-e['rom_offset'];assert delta%64==0;y=delta//64;im=Image.open(out/e['file']);cap=Image.open(f.with_name(f.name.replace('.tile.json','.png'))).convert('RGBA');decoded=bytes(v for q in r[pos:pos+2048] for v in [(q>>4)*17]*3+[(q&15)*17]);ex=Image.frombytes('RGBA',(64,32),decoded);dif=ImageChops.difference(cap,ex);mx=max(v[1] for v in dif.getextrema());e['strips'].append(dict(hash=f.name.split('.')[0],box=[0,y,64,32],max_channel_difference=mx,visible_rows=min(32,e['height']-y),tail_overreads_next_rom_bytes=(y+32>e['height'])))
sheet.save(out/'carousel-words-contact.png');(out/'carousel-words-manifest.json').write_text(json.dumps(dict(entries=entries),indent=2)+'\n');print([(e['name'],hex(e['rom_offset']),e['height'],len(e['strips'])) for e in entries])
