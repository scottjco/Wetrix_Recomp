"""Extract verified native Wetrix font textures and preserve source metadata.
No runtime/source changes. Requires Pillow. ROM revision is checked strictly.
"""
from pathlib import Path
import argparse, hashlib, json, struct
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,default=ROOT/'Assets/data.z64');p.add_argument('--out',type=Path,default=ROOT/'work/sprite-inventory');a=p.parse_args()
 r=a.rom.read_bytes()
 if hashlib.sha256(r).hexdigest()!='790f36a3ddd64e4dcd08c479b0b66f9080d0191473e92fa895f53d15706167bb':raise ValueError('Unsupported ROM revision')
 a.out.mkdir(parents=True,exist_ok=True);(a.out/'font').mkdir(exist_ok=True)
 entries=[];sheet=Image.new('RGBA',(8*160,12*100),(28,28,32,255));d=ImageDraw.Draw(sheet)
 glyph_chars=r[0x76c40:0x76c40+93] # func80040750 builds ASCII map from this byte table
 for i in range(93):
  off=0x88ec0+i*2304;im=Image.frombytes('RGBA',(36,16),r[off:off+2304]);name=f'font/font-{i:02d}.png';im.save(a.out/name)
  # Native texture stores two sideways color treatments in adjacent18x16 rectangles.
  preview=Image.new('RGBA',(32,18));preview.paste(im.crop((0,0,18,16)).transpose(Image.Transpose.TRANSPOSE),(0,0));preview.paste(im.crop((18,0,36,16)).transpose(Image.Transpose.TRANSPOSE),(16,0))
  preview.save(a.out/'font'/f'glyph-{i:02d}-preview.png')
  x=(i%8)*160;y=(i//8)*100;sheet.alpha_composite(preview.resize((128,72),Image.Resampling.NEAREST),(x,y+20));d.text((x+2,y+2),str(i),fill='white')
  chars=[chr(c) for c,g in enumerate(range(256)) if c==glyph_chars[i] and 32<=c<127]
  entries.append(dict(id=f'font-{i:02d}',file=name,rom_offset=off,byte_length=2304,width=36,height=16,format='RGBA32',palette=None,ascii_candidates=chars,layout='two adjacent18x16 sideways color variants; preserve source layout'))
 sheet.convert('RGB').save(a.out/'font-contact.png')
 (a.out/'numbers').mkdir(exist_ok=True)
 numbers=Image.new('RGBA',(64,210))
 for i in range(10):
  off=0xbd3c0+i*0x1500;im=Image.frombytes('RGBA',(32,42),r[off:off+0x1500]);name=f'numbers/number-{i}.png';im.save(a.out/name);numbers.paste(im,((i%2)*32,(i//2)*42))
  entries.append(dict(id=f'number-{i}',file=name,rom_offset=off,byte_length=0x1500,width=32,height=42,format='RGBA32',palette=None))
 numbers.save(a.out/'numbers-reference.png');numbers.resize((256,840),Image.Resampling.NEAREST).save(a.out/'numbers-reference-4x.png')

 # Whole sprite bank diagnostic preserves every byte; dimensions here are a scan layout, not native descriptors.
 bank=r[0xbd3c0:0xe3080];(a.out/'sprite-bank.bin').write_bytes(bank)
 Image.frombytes('RGBA',(32,len(bank)//128),bank).save(a.out/'sprite-bank-scan.png')
 meta=dict(rom_sha256=hashlib.sha256(r).hexdigest(),entries=entries,verified_coverage='93 complete RGBA32 font textures (including animated copyright glyph sources) and 10 RGBA32 digit textures',sprite_bank=dict(rom_start=0xbd3c0,rom_end=0xe3080,scan_width=32,native_dimensions_verified=False),limitations=['Sprite bank native image descriptor boundaries still require mapping.','No claim of complete all-2D extraction.','Copyright animation is procedural geometry; no additional raster frames inferred.'])
 (a.out/'manifest.json').write_text(json.dumps(meta,indent=2));print(f'Extracted {len(entries)} textures; raw sprite bank {len(bank)} bytes')
if __name__=='__main__':main()
