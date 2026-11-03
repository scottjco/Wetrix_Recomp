from pathlib import Path
from PIL import Image,ImageDraw,ImageChops
import struct,json,hashlib
r=Path('Assets/data.z64').read_bytes();out=Path('work/main-menu-texture-audit');matches=json.load(open(out/'ci8-strip-matches.json'));byoff={e['rom_offset']:e for e in matches};sheet=Image.new('RGBA',(1350,1050),(28,28,34,255));d=ImageDraw.Draw(sheet);es=[]
for g in range(7):
 base=0xfa6c0+g*0x7430;paloff=base+9*3248;pal=[]
 for j in range(256):
  p=struct.unpack_from('>H',r,paloff+j*2)[0];pal.append(((((p>>11)<<3)|((p>>11)>>2)),((((p>>6)&31)<<3)|(((p>>6)&31)>>2)),((((p>>1)&31)<<3)|(((p>>1)&31)>>2)),255*(p&1)))
 for f in range(9):
  off=base+f*3248;data=r[off:off+3248];raw=bytes(v for i in data for v in pal[i]);im=Image.frombytes('RGBA',(56,58),raw);name=f'piece-group-{g}-frame-{f}.png';im.save(out/'native'/name);sheet.alpha_composite(im.resize((112,116),Image.Resampling.NEAREST),(f*150,g*150+24));d.text((f*150,g*150),f'G{g} F{f} {off:X}',fill='white');strips=[]
  for half in range(2):
   m=byoff[off+half*56*29];capture=Image.open('work/texture-dump/'+m['hash']+'.v5.png').convert('RGBA');expected=im.crop((0,half*29,56,(half+1)*29));diff=ImageChops.difference(capture,expected);maxdiff=max(v[1] for v in diff.getextrema());strips.append(dict(hash=m['hash'],box=[0,half*29,56,29],maximum_channel_difference=maxdiff))
  es.append(dict(id=f'menu-piece-{g}-frame-{f}',group=g,frame=f,file='native/'+name,rom_offset=off,palette_rom_offset=paloff,width=56,height=58,format='CI8',palette_format='RGBA16',byte_length=3248,strips=strips))
sheet.save(out/'piece-icons-contact.png');(out/'piece-icons-manifest.json').write_text(json.dumps(dict(entries=es,source='ROM CI8 indices and trailing RGBA16 palette; each two captured56x29halves matched'),indent=2));print('max pixel diff',max(s['maximum_channel_difference'] for e in es for s in e['strips']))
