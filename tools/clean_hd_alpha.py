"""Remove AI alpha dust from explicitly selected opaque UI/font PNGs.

Not suitable for glow, fire, smoke, splashes or other intentionally translucent
art. Work on reviewed generated alpha, never an opaque original pixel mask.

Defaults retain every substantial A>=192 component and its original AA within
1.5 image pixels. A<8 and isolated dust are removed. RGB under A=0 can be zeroed
or filled with nearest retained edge RGB to avoid filtered matte colors.
Use --min-core-area 0 and a lower --core-threshold for genuinely thin lettering.
At 4x UI resolution start with --aa-radius 1; review four-color composites.

Requires system Python: Pillow, numpy, opencv-python; scipy only for edge bleed.
Example:
 python tools/clean_hd_alpha.py --inputs sprite.png --output-dir work/cleaned \
   --core-threshold 192 --aa-radius 1 --min-core-area 0 --transparent-rgb bleed \
   --composites-dir work/alpha-review
"""
from pathlib import Path
import argparse,json,shutil
import numpy as np
import cv2
from PIL import Image,ImageDraw

BACKGROUNDS=[('black',(0,0,0)),('white',(255,255,255)),('gray',(100,100,100)),('purple',(110,40,130))]

def clean_alpha(image,core_threshold=192,aa_radius=1.5,alpha_floor=8,min_core_area=16,transparent_rgb='zero'):
 """Preserve retained artwork/AA exactly; return RGBA and measurable audit data."""
 if not 1<=core_threshold<=255 or not 0<=alpha_floor<core_threshold or aa_radius<0 or min_core_area<0:raise ValueError('Invalid matte thresholds')
 before=np.array(image.convert('RGBA'));result=before.copy();alpha=before[:,:,3]
 count,labels,stats,_=cv2.connectedComponentsWithStats((alpha>=core_threshold).astype('uint8'));core=np.zeros(alpha.shape,dtype='uint8');retained_components=0
 for k in range(1,count):
  if stats[k,cv2.CC_STAT_AREA]>=min_core_area:core[labels==k]=1;retained_components+=1
 if not np.any(core):raise ValueError('No substantial opaque artwork; lower threshold or do not matte translucent art')
 distance=cv2.distanceTransform(1-core,cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
 result[:,:,3][(distance>aa_radius)|(alpha<alpha_floor)]=0
 invisible=result[:,:,3]==0
 if transparent_rgb=='zero':result[invisible,:3]=0
 elif transparent_rgb=='bleed':
  from scipy.ndimage import distance_transform_edt
  # Copy the nearest retained visible edge, never a white generation matte.
  nearest=distance_transform_edt(invisible,return_distances=False,return_indices=True)
  result[invisible,:3]=result[nearest[0][invisible],nearest[1][invisible],:3]
 else:raise ValueError('transparent_rgb must be zero or bleed')
 core_changed=int(np.count_nonzero(core.astype(bool)&np.any(before!=result,axis=2)))
 assert core_changed==0
 report=dict(changed_pixels=int(np.count_nonzero(np.any(before!=result,axis=2))),removed_alpha_pixels=int(np.count_nonzero((alpha>0)&(result[:,:,3]==0))),retained_core_components=retained_components,retained_core_pixels=int(core.sum()),core_pixels_changed=core_changed,remaining_aa_pixels=int(np.count_nonzero((result[:,:,3]>0)&(result[:,:,3]<255))),core_threshold=core_threshold,aa_radius=aa_radius,alpha_floor=alpha_floor,min_core_area=min_core_area,transparent_rgb=transparent_rgb)
 return Image.fromarray(result),report

def composites(before,after,destination):
 """Full-size before/after: columns before/after; rows black/white/gray/purple."""
 sheet=Image.new('RGB',(before.width*2,before.height*4))
 for row,(_,color) in enumerate(BACKGROUNDS):
  for column,im in enumerate([before,after]):
   bg=Image.new('RGB',im.size,color);bg.paste(im,(0,0),im);sheet.paste(bg,(column*im.width,row*im.height))
 sheet.save(destination)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--inputs',nargs='+',type=Path,required=True);group=ap.add_mutually_exclusive_group(required=True);group.add_argument('--output-dir',type=Path);group.add_argument('--in-place',action='store_true');ap.add_argument('--backup-dir',type=Path,default=Path('work/alpha-backups'));ap.add_argument('--core-threshold',type=int,default=192);ap.add_argument('--aa-radius',type=float,default=1.5);ap.add_argument('--alpha-floor',type=int,default=8);ap.add_argument('--min-core-area',type=int,default=16);ap.add_argument('--transparent-rgb',choices=['zero','bleed'],default='zero');ap.add_argument('--composites-dir',type=Path);ap.add_argument('--report',type=Path,default=Path('work/alpha-cleanup-report.json'));args=ap.parse_args();reports=[]
 if len({p.name for p in args.inputs})!=len(args.inputs):ap.error('Input filenames must be unique to avoid overwriting output/backup')
 for source in args.inputs:
  if not source.is_file() or source.suffix.lower()!='.png':ap.error(f'Explicit PNG file required: {source}')
  before=Image.open(source).convert('RGBA');after,report=clean_alpha(before,args.core_threshold,args.aa_radius,args.alpha_floor,args.min_core_area,args.transparent_rgb)
  if args.in_place:
   args.backup_dir.mkdir(parents=True,exist_ok=True);backup=args.backup_dir/source.name
   if not backup.exists():shutil.copy2(source,backup)
   destination=source
  else:args.output_dir.mkdir(parents=True,exist_ok=True);destination=args.output_dir/source.name
  after.save(destination)
  if args.composites_dir:args.composites_dir.mkdir(parents=True,exist_ok=True);composites(before,after,args.composites_dir/(source.stem+'-comparison.png'))
  reports.append(dict(source=str(source),output=str(destination),**report))
 args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(reports,indent=2)+'\n');print(f"Reviewed {len(reports)} explicit PNGs; removed {sum(r['removed_alpha_pixels'] for r in reports)} alpha-dust pixels; retained opaque artwork unchanged")
if __name__=='__main__':main()
