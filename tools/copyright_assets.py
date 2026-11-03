"""Extract native animated copyright glyph references without changing typography.

The 36x16 RGBA32 source contains two sideways 18x16 color variants.
Keep replacements in this orientation: func_80040BA8 uses flipped rectangles
and a moving per-letter split. A whole-screen replacement loses that animation.
"""
import argparse, hashlib, json, struct
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,default=ROOT/'Assets/data.z64');p.add_argument('--captures',type=Path,default=ROOT/'work/texture-dump');p.add_argument('--package-atlas',type=Path);p.add_argument('--order',type=Path);p.add_argument('--columns',type=int,default=5);p.add_argument('--rows',type=int,default=5);args=p.parse_args()
 if args.package_atlas:
  package_atlas(args.package_atlas,args.order,args.columns,args.rows);return
 rom=args.rom.read_bytes()
 assert hashlib.sha256(rom).hexdigest()=='790f36a3ddd64e4dcd08c479b0b66f9080d0191473e92fa895f53d15706167bb'
 out=ROOT/'work/copyright-assets';native=out/'native';native.mkdir(parents=True,exist_ok=True)
 captures={}
 for f in args.captures.glob('*.v5.png'):
  im=Image.open(f).convert('RGBA')
  if im.size==(36,16): captures.setdefault(im.tobytes(),[]).append(f.name.split('.')[0])
 chars=rom[0x76c40:0x76c40+93];entries=[]
 sheet=Image.new('RGBA',(12*150,8*110),(24,24,24,255));draw=ImageDraw.Draw(sheet)
 for i,code in enumerate(chars):
  offset=0x88ec0+i*2304;raw=rom[offset:offset+2304];im=Image.frombytes('RGBA',(36,16),raw)
  im.save(native/f'glyph-{i:03d}-ascii-{code:03d}.png')
  x=i%12*150;y=i//12*110
  # Display rotated variants upright for artists, while saved native tiles remain unchanged.
  upright=im.transpose(Image.Transpose.ROTATE_90)
  sheet.alpha_composite(upright.resize((64,72),Image.Resampling.NEAREST),(x,y))
  draw.text((x,y+76),f'{i}: {chr(code)!r}',fill='white')
  entries.append(dict(glyph_id=i,character=chr(code),ascii=code,rom_offset=hex(offset),native_size=[36,16],upright_variant_size=[16,18],bearing=struct.unpack_from('>i',rom,0x76e14+i*4)[0],advance_half_pixels=struct.unpack_from('>i',rom,0x76ca0+i*4)[0],captured_rt64_hashes=captures.get(raw,[])))
 sheet.save(out/'glyph-reference.png')
 strings=[]
 for offset in [0x30ec,0x3104,0x3120,0x3134]:
  strings.append(dict(rom_offset=hex(offset),text=rom[offset:rom.index(0,offset)].decode('ascii')))
 used=set(''.join(s['text'] for s in strings))-{' '}
 copyright_entries=[e for e in entries if e['character'] in used]
 coverage=dict(unique_text_glyphs=len(copyright_entries),captured_text_glyphs=sum(bool(e['captured_rt64_hashes']) for e in copyright_entries),missing_characters=sorted(used-set(map(chr,chars))))
 report=dict(copyright_coverage=coverage,source='Original ROM; no font substitution or generated approximation',glyph_count=len(entries),mapped_captured_glyph_count=sum(bool(e['captured_rt64_hashes']) for e in entries),copyright_strings=strings,animation=dict(renderer='80040BA8',native_glyph_rect=[16,18],split_range=[1,17],texture_format='RGBA32',texture_size=[36,16],replacement_rule='Retain two side-by-side sideways color variants and original glyph IDs; runtime keeps independent animated split rectangles.'),glyphs=entries)
 (out/'mapping.json').write_text(json.dumps(report,indent=2)+'\n')
 print(f"Extracted {len(entries)} glyphs; matched {report['mapped_captured_glyph_count']} captures")

def package_atlas(source,order,columns,rows):
 """Slice reviewed AI artwork; restore native orientation/bounds, retain glyph animation."""
 import cv2
 import numpy as np
 im=Image.open(source).convert('RGBA');entries=json.loads(order.read_text());folder=ROOT/'Textures/hd-sprites/copyright';folder.mkdir(parents=True,exist_ok=True);manifest=[]
 sheet=Image.new('RGBA',(columns*240,rows*150),(25,25,25,255));draw=ImageDraw.Draw(sheet)
 for i,e in enumerate(entries):
  col=i%columns;row=i//columns;native=Image.open(ROOT/f"work/copyright-assets/native/glyph-{e['glyph_id']:03d}-ascii-{e['ascii']:03d}.png");tile=Image.new('RGBA',(576,256))
  for j in range(2):
   box=(round((col+j/2)*im.width/columns),round(row*im.height/rows),round((col+(j+1)/2)*im.width/columns),round((row+1)*im.height/rows));a=im.crop(box);pixels=np.array(a)
   count,labels,stats,_=cv2.connectedComponentsWithStats((pixels[:,:,3]>40).astype('uint8'))
   # Retain real disconnected punctuation/accents. Discard only tiny edge noise.
   maximum=max(stats[1:,cv2.CC_STAT_AREA],default=0);keep=np.zeros(labels.shape,dtype='uint8')
   for component in range(1,count):
    if stats[component,cv2.CC_STAT_AREA]>=max(3,maximum*.05):keep[labels==component]=1

   if j==0:keep[(pixels[:,:,0].astype(float)>pixels[:,:,1].astype(float)*1.35)&(pixels[:,:,0]>80)&(pixels[:,:,2]<pixels[:,:,0]*.85)]=0
   keep=cv2.dilate(keep,np.ones((3,3),dtype='uint8'));pixels[:,:,3]*=keep;a=Image.fromarray(pixels);bbox=a.getchannel('A').point(lambda v:255 if v>40 else 0).getbbox()
   if bbox is None:raise ValueError(f"Empty generated glyph {e['glyph_id']} variant {j}")
   a=a.crop(bbox);b=native.crop((j*18,0,j*18+18,16)).transpose(Image.Transpose.ROTATE_90).getchannel('A').point(lambda v:255 if v>40 else 0).getbbox();cell=Image.new('RGBA',(256,288));a=a.resize(((b[2]-b[0])*16,(b[3]-b[1])*16),Image.Resampling.LANCZOS);cell.alpha_composite(a,(b[0]*16,b[1]*16));tile.alpha_composite(cell.transpose(Image.Transpose.ROTATE_270),(j*288,0))
  name=f"glyph-{e['glyph_id']:03d}-ascii-{e['ascii']:03d}";tile.save(folder/(name+'.png'))
  for h in e['captured_rt64_hashes']:manifest.append(dict(hashes=dict(rt64=h),path='copyright/'+name))
  x=col*240;y=row*150;orig=native.crop((0,0,18,16)).transpose(Image.Transpose.ROTATE_90).resize((96,108),Image.Resampling.NEAREST);hd=tile.crop((0,0,288,256)).transpose(Image.Transpose.ROTATE_90).resize((96,108),Image.Resampling.LANCZOS);sheet.alpha_composite(orig,(x,y+20));sheet.alpha_composite(hd,(x+110,y+20));draw.text((x,y),f"slot {e['glyph_id']} Original / HD",fill='white')
 sheet.save(order.with_name(order.stem+'-comparison.png'));order.with_name(order.stem+'-rt64-entries.json').write_text(json.dumps(manifest,indent=2)+'\n');print(f"Packaged {len(entries)} glyphs; {len(manifest)} captured mappings")

if __name__=='__main__':main()
