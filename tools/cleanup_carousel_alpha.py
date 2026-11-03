"""Extract reviewed ImageGen edge edit with a matte bounded by intended dark contour.
Only carouselword masters and their52existing mappedcrops are changed.
"""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw,ImageFilter,ImageChops
ROOT=Path(__file__).resolve().parents[1]
def intended_matte(art):
 raw=art.tobytes();dark=Image.new('L',art.size);dark.putdata([255 if raw[i+3]>=128 and max(raw[i:i+3])<160 else 0 for i in range(0,len(raw),4)])
 # Close a one-pixel break in the dark outline, then fill enclosed letterfaces.
 dark=dark.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3));filled=dark.copy();ImageDraw.floodfill(filled,(0,0),127,thresh=0);filled=filled.point(lambda a:0 if a==127 else 255)
 # Original zero-alpha counters/cutouts must remain open: no intensity->alpha conversion.
 return ImageChops.multiply(filled,art.getchannel('A').point(lambda a:255 if a>=128 else 0))
def stats(im):
 raw=im.tobytes();alpha=raw[3::4]
 return dict(size=list(im.size),sha256=hashlib.sha256(raw).hexdigest(),nonzero_alpha=sum(a>0 for a in alpha),low_alpha_1_31=sum(0<a<32 for a in alpha),transparent_nonzero_rgb=sum(raw[i+3]==0 and bool(raw[i] or raw[i+1] or raw[i+2]) for i in range(0,len(raw),4)),neutral_rgb=im.getchannel('R').tobytes()==im.getchannel('G').tobytes()==im.getchannel('B').tobytes())
def main():
 work=ROOT/'work/main-menu-texture-audit/redraw';atlas_path=work/'carousel-edge-cleanup-generated-pending-qa.png';atlas=Image.open(atlas_path).convert('RGBA');names=['classic','practice','pro','handicap','challenge','multiplay','options'];results=[]
 for j,name in enumerate(names):
  x0=j%2*atlas.width//2;x1=(j%2+1)*atlas.width//2;y0=j//2*atlas.height//4;y1=(j//2+1)*atlas.height//4;art=atlas.crop((x0,y0,x1,y1));matte=intended_matte(art);bbox=matte.getbbox();assert bbox;art.putalpha(matte);art=art.crop(bbox)
  native=Image.open(ROOT/f'work/main-menu-texture-audit/native/carousel-{name}.png').convert('RGBA');upright=native.transpose(Image.Transpose.ROTATE_90);nb=upright.getchannel('A').getbbox();target=tuple(v*4 for v in nb);art=art.resize((target[2]-target[0],target[3]-target[1]),Image.Resampling.LANCZOS)
  lum=art.convert('L');art=Image.merge('RGBA',(lum,lum,lum,art.getchannel('A')));canvas=Image.new('RGBA',(upright.width*4,upright.height*4));canvas.alpha_composite(art,(target[0],target[1]));stored=canvas.transpose(Image.Transpose.ROTATE_270);raw=bytearray(stored.tobytes())
  for n in range(0,len(raw),4):
   if raw[n+3]<32:raw[n:n+4]=b'\0\0\0\0'
  stored=Image.frombytes('RGBA',stored.size,bytes(raw));dest=ROOT/f'Textures/hd-sprites/main-menu/carousel-{name}.png';before=Image.open(work/'edge-cleanup-before'/dest.name).convert('RGBA');assert stored.size==before.size;stored.save(dest)
  record=dict(name=name,before=stats(before),after=stats(stored),native_alpha_bbox_upright=nb,imagegen_matte_bbox=bbox);assert record['after']['neutral_rgb'] and not record['after']['transparent_nonzero_rgb'] and not record['after']['low_alpha_1_31'];results.append(record)
 # Rebuild only the existing52knownhashcrops; noDBwrites or newmappingcreation.
 plan=json.load(open(ROOT/'work/main-menu-texture-audit/carousel-hashes-and-crops.json'))
 for e in plan['entries']:
  im=Image.open(ROOT/f'Textures/hd-sprites/main-menu/{e["source_id"]}.png').convert('RGBA');x,y,w,h=e['box'];crop=im.crop((x*4,y*4,(x+w)*4,(y+h)*4));crop.save(ROOT/'Textures/hd-sprites'/e['path'])
 for label,bg in [('black',(0,0,0,255)),('gray',(100,100,100,255)),('white',(255,255,255,255)),('purple',(90,30,140,255))]:
  sheet=Image.new('RGBA',(1600,len(names)*160),bg);draw=ImageDraw.Draw(sheet)
  for j,name in enumerate(names):
   for col,stage in enumerate(['before','after']):
    p=work/'edge-cleanup-before'/f'carousel-{name}.png' if stage=='before' else ROOT/f'Textures/hd-sprites/main-menu/carousel-{name}.png';im=Image.open(p).convert('RGBA').transpose(Image.Transpose.ROTATE_90);im.thumbnail((760,110),Image.Resampling.LANCZOS);sheet.alpha_composite(im,(col*800+20,j*160+35));draw.text((col*800+20,j*160+5),name+' '+stage,fill=(255,0,128,255))
  sheet.save(work/f'carousel-edge-qa-{label}.png')
 report=dict(status='52crops rebuilt; noDBwrites',imagegen_provenance=dict(reference='carousel-edge-cleanup-input.png',generated_atlas=atlas_path.name,generated_atlas_sha256=hashlib.sha256(atlas_path.read_bytes()).hexdigest(),request='precisealphaedgeedit preserving customlettering/details/intendedblackshadow, removeexternalrim/wires/specks/haze'),matte_method='intendeddarkcontour closure+enclosedfacefill intersected with originalopaquealpha; preserves zerotransparentcounters; straightRGBA neutralRGB; not intensitytoalpha',rgba_interpretation='IA8nativeintensity is RGB and nativealpha is independent. ReplacementRGBA retains independent grayscaleRGB andalpha; blackshadow remains opaque. No multipliedintensityalpha.',results=results,rebuilt_crops=len(plan['entries']));(work/'carousel-edge-cleanup-qa-report.json').write_text(json.dumps(report,indent=2)+'\n');print('7carouselwordmasters+52cropscleaned; nativecanvases/neutralRGB asserted; zeroRGBatA0 andzeroA1..31; DBuntouched')
if __name__=='__main__':main()
