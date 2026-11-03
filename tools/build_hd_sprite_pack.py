"""Build reproducible, alignment-safe RT64 replacements from reviewed redraws.

No interpolation fallback is enabled: missing redraws remain original in game.
The input JSON has a `sprites` array: id, original, redraw, optional regions
[{box:[x,y,w,h], redraw:path}], optional hashes:[hex], alpha:original|redraw.
Paths are relative to the project root. Outputs never modify rt64.json.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]

def fingerprint(im):
    im = im.convert('RGBA')
    # RGB behind fully transparent texels is not visible and differs by decoder.
    raw = bytearray(im.tobytes())
    for i in range(0, len(raw), 4):
        if raw[i + 3] == 0:
            raw[i:i + 3] = b'\0\0\0'
    return (im.size, hashlib.sha256(raw).hexdigest())

def normalized_bytes(im):
    raw = bytearray(im.convert('RGBA').tobytes())
    for i in range(0,len(raw),4):
        if raw[i+3] == 0:
            raw[i:i+3] = b'\0\0\0'
    return bytes(raw)

def exact_subimages(source, tile):
    """Return every exact native-orientation crop, ignoring invisible RGB only."""
    if tile.width > source.width or tile.height > source.height or not tile.getchannel('A').getbbox():
        return []
    big, small = normalized_bytes(source), normalized_bytes(tile)
    stride, rowlen = source.width*4, tile.width*4
    # Anchor the most opaque row to avoid searching an all-transparent first row.
    anchor = max(range(tile.height), key=lambda y: sum(small[y*rowlen+3:(y+1)*rowlen:4]))
    needle = small[anchor*rowlen:(anchor+1)*rowlen]
    hits = []
    for y in range(source.height-tile.height+1):
        row = big[(y+anchor)*stride:(y+anchor+1)*stride]
        start = 0
        while (offset := row.find(needle,start)) >= 0:
            start = offset+1
            x = offset//4
            if offset%4 or x+tile.width > source.width:
                continue
            if all(big[(y+r)*stride+x*4:(y+r)*stride+x*4+rowlen] == small[r*rowlen:(r+1)*rowlen] for r in range(tile.height)):
                hits.append((x,y,x+tile.width,y+tile.height))
    return hits

def read(path):
    with Image.open(path) as im:
        return im.convert('RGBA')

def path(value):
    p = Path(value)
    return p if p.is_absolute() else ROOT / p

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', default='work/hd-art-pipeline/redraws.json')
    ap.add_argument('--dump', default='work/texture-dump')
    ap.add_argument('--output', default='Textures/hd-sprites')
    ap.add_argument('--report', default='work/hd-art-pipeline/build-report.json')
    ap.add_argument('--scale', type=int, default=4)
    ap.add_argument('--coverage', default='work/sprite-coverage/manifest.json')
    ap.add_argument('--merge-database', action='store_true', help='Merge these redraw mappings into existing rt64.json; preserve all other assets')
    ap.add_argument('--proven-tiles-only', action='store_true', help='Use runtime-agent byte-proven strip hashes; skip expensive capture image matching')
    args = ap.parse_args()
    if args.scale < 2:
        ap.error('scale must be an integer of at least 2')
    plan = json.loads(path(args.plan).read_text(encoding='utf-8'))
    output = path(args.output)
    (output / 'sprites').mkdir(parents=True, exist_ok=True)
    captures = {}
    capture_images = {}
    for p in ([] if args.proven_tiles_only else sorted(path(args.dump).glob('*.png'))):
        m = re.fullmatch(r'([0-9a-fA-F]{16})\.v5', p.stem)
        if m:
            capture_images[m[1].lower()] = read(p)
            captures.setdefault(fingerprint(capture_images[m[1].lower()]), []).append(m[1].lower())
    report = {'scale': args.scale, 'sprites': [], 'textures': [], 'unmapped': []}
    used = {}
    coverage = json.loads(path(args.coverage).read_text()) if path(args.coverage).exists() else {}
    proven_path=ROOT/'work/texture-hash/sprite-strip-hashes.json'
    proven=json.loads(proven_path.read_text()) if proven_path.exists() else {}
    for spec in plan.get('sprites', []):
        name = spec['id']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name):
            raise ValueError(f'Unsafe sprite id: {name}')
        original = read(path(spec['original']))
        size = tuple(v * args.scale for v in original.size)
        if spec.get('regions'):
            result = original.resize(size, Image.Resampling.NEAREST)
            for region in spec['regions']:
                x, y, w, h = region['box']
                if min(x, y) < 0 or min(w, h) <= 0 or x+w > original.width or y+h > original.height:
                    raise ValueError(f'{name}: region outside original atlas')
                art = read(path(region['redraw']))
                expected = (w * args.scale, h * args.scale)
                if art.size != expected:
                    raise ValueError(f'{name}: redraw must be exactly {expected}, got {art.size}')
                result.paste(art, (x * args.scale, y * args.scale))
        elif spec.get('redraw'):
            result = read(path(spec['redraw']))
            if spec.get('align_bbox'):
                # Ignore near-transparent generation dust when locating the artwork.
                bbox = result.getchannel('A').point(lambda a: 255 if a >= 16 else 0).getbbox()
                target = original.getchannel('A').getbbox()
                if bbox is None or target is None:
                    raise ValueError(f'{name}: cannot align empty alpha bounds')
                x0,y0,x1,y1 = [v * args.scale for v in target]
                art = result.crop(bbox).resize((x1-x0,y1-y0), Image.Resampling.LANCZOS)
                result = Image.new('RGBA', size)
                result.paste(art,(x0,y0))
            if result.size != size:
                raise ValueError(f'{name}: redraw must be exactly {size}, got {result.size}')
        else:
            report['sprites'].append({'id': name, 'status': 'missing-redraw'})
            continue
        if spec.get('alpha', 'original') == 'original':
            result.putalpha(original.getchannel('A').resize(size, Image.Resampling.NEAREST))
        elif spec['alpha'] != 'redraw':
            raise ValueError(f'{name}: invalid alpha policy')
        folder = spec.get('folder', 'sprites')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', folder):
            raise ValueError(f'Unsafe output folder: {folder}')
        (output / folder).mkdir(exist_ok=True)
        dest = output / folder / f'{name}.png'
        result.save(dest, compress_level=9)
        hashes = sorted(set(spec.get('hashes', []) + captures.get(fingerprint(original), [])))
        for h in hashes:
            if not re.fullmatch(r'[0-9a-fA-F]{16}', h):
                raise ValueError(f'{name}: invalid RT64 hash {h}')
            h = h.lower()
            if h in used and used[h] != name:
                raise ValueError(f'Conflicting redraws for RT64 hash {h}')
            used[h] = name
            report['textures'].append({'path': f'{folder}/{name}.png', 'hashes': {'rt64': h}, 'shift': 'none'})
        # Runtime TMEM uploads can be overlapping strips of one source image.
        # Require both descriptor provenance and exact captured-pixel validation.
        coverage_id = spec.get('coverage_id', name)
        needs_history = not proven or any(t['source_id']==coverage_id for t in proven.get('unresolved_tiles',[]))
        coverage_entries = sum((coverage.get(k, []) for k in ['entries','additional_static_entries','dynamic_menu_entries']), [])
        entry = next((e for e in coverage_entries if e['id'] == coverage_id), None)
        for strip in ([] if args.proven_tiles_only else coverage.get('captured_bank_strips', [])):
            if entry is None or coverage_id not in strip['source_ids']:
                continue
            pixel_offset, remainder = divmod(strip['rom_offset'] - entry['rom_offset'], 4)
            sy, sx = divmod(pixel_offset, original.width)
            sw, sh = strip['width'], strip['height']
            if remainder or sx + sw > original.width or sy + sh > original.height:
                continue
            capture = path(args.dump) / (strip['hash'] + '.v5.png')
            box = (sx, sy, sx+sw, sy+sh)
            if not capture.exists() or fingerprint(read(capture)) != fingerprint(original.crop(box)):
                continue
            h = strip['hash']
            if h in used:
                raise ValueError(f'Conflicting strip hash {h}')
            used[h] = name
            strip_name = f'{name}-strip-{sx}-{sy}.png'
            result.crop(tuple(v*args.scale for v in box)).save(output / folder / strip_name)
            report['textures'].append({'path': f'{folder}/{strip_name}', 'hashes': {'rt64': h}, 'shift': 'none'})
            hashes.append(h)
        for h, capture in (capture_images.items() if needs_history else []):
            if h in hashes:
                continue
            boxes = exact_subimages(original, capture)
            if len(boxes) != 1:
                continue
            sx,sy,ex,ey = boxes[0]
            if h in used:
                if used[h] != name:
                    raise ValueError(f'Conflicting verified source match {h}')
                continue
            used[h] = name
            strip_name = f'{name}-crop-{sx}-{sy}-{ex}-{ey}.png'
            result.crop(tuple(v*args.scale for v in boxes[0])).save(output / folder / strip_name)
            report['textures'].append({'path': f'{folder}/{strip_name}', 'hashes': {'rt64': h}, 'shift': 'none'})
            hashes.append(h)
        # Edge TMEM tiles retain a full32x32 upload even where a source sprite
        # ends. Verify every in-bounds texel at the renderer's31-texel stride;
        # require substantial visible evidence and a unique tile/source offset.
        for h,capture in (capture_images.items() if needs_history else []):
            if h in used or capture.size != (32,32):
                continue
            candidates=[]
            for sy in range(0, original.height,31):
                for sx in range(0, original.width,31):
                    w,hgt=min(32,original.width-sx),min(32,original.height-sy)
                    if w==32 and hgt==32 or min(w,hgt)<8:
                        continue
                    native=original.crop((sx,sy,sx+w,sy+hgt))
                    if sum(a>0 for a in native.getchannel('A').tobytes()) < 64:
                        continue
                    if fingerprint(native)==fingerprint(capture.crop((0,0,w,hgt))):
                        candidates.append((sx,sy,w,hgt))
            if len(candidates)!=1:
                continue
            sx,sy,w,hgt=candidates[0]
            tile=Image.new('RGBA',(32*args.scale,32*args.scale))
            tile.paste(result.crop((sx*args.scale,sy*args.scale,(sx+w)*args.scale,(sy+hgt)*args.scale)),(0,0))
            file=f'{name}-edge-{sx}-{sy}.png'
            tile.save(output/folder/file)
            used[h]=name
            hashes.append(h)
            report['textures'].append({'path':f'{folder}/{file}','hashes':{'rt64':h},'shift':'none'})
            report.setdefault('verified_edge_tiles',[]).append({'id':name,'hash':h,'native_box':[sx,sy,w,hgt],
                'verification':'all in-bounds RGBA texels exact; alpha0 RGB normalized; source edge padding excluded'})
        for tile_spec in proven.get('deterministic_tiles',[]):
            if tile_spec['source_id']!=coverage_id:
                continue
            h=tile_spec['rt64_hash']
            if h in hashes:
                continue
            x,y=tile_spec['x'],tile_spec['y']
            w,hgt=tile_spec['loaded_width'],tile_spec['loaded_height']
            tile=Image.new('RGBA',(tile_spec['hash_width']*args.scale,tile_spec['hash_height']*args.scale))
            tile.paste(result.crop((x*args.scale,y*args.scale,(x+w)*args.scale,(y+hgt)*args.scale)),(0,0))
            if h in used:
                existing=next(t for t in report['textures'] if t['hashes']['rt64']==h)
                if fingerprint(read(output/existing['path']))!=fingerprint(tile):
                    report.setdefault('conflicting_proven_tiles',[]).append({'id':name,'hash':h,'existing':used[h], 'box':[x,y,w,hgt]})
                else:
                    hashes.append(h)
                continue
            file=f'{name}-proven-{x}-{y}.png'
            tile.save(output/folder/file)
            used[h]=name
            hashes.append(h)
            report['textures'].append({'path':f'{folder}/{file}','hashes':{'rt64':h},'shift':'none'})
            report.setdefault('proven_tiles',[]).append({'id':name,'hash':h,'captured':tile_spec['captured'],'native_box':[x,y,w,hgt],
                'verification':tile_spec['proof']})
        report['sprites'].append({'id': name, 'status': 'redrawn', 'size': size,
            'alpha': spec.get('alpha', 'original'), 'hashes': hashes,
            'sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
            'provenance': spec.get('provenance', 'unspecified')})
        if not hashes:
            report['unmapped'].append(name)
    report['configuration'] = {'configurationVersion': 3, 'hashVersion': 5,
        'autoPath': 'rt64', 'defaultOperation': 'stream', 'defaultShift': 'none'}
    report_path = path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if args.merge_database:
        db_path=output/'rt64.json'
        db=json.loads(db_path.read_text()) if db_path.exists() else {'configuration':report['configuration'],'textures':[]}
        folders={s.get('folder','sprites')+'/' for s in plan.get('sprites',[])}
        old=[t for t in db.get('textures',[]) if not any(t['path'].startswith(f) for f in folders)]
        index={t['hashes']['rt64']:t for t in old}
        for t in report['textures']:
            h=t['hashes']['rt64']
            if h in index and index[h]['path']!=t['path']:
                raise ValueError(f'Conflicting unrelated replacement hash {h}')
            index[h]=t
        db['textures']=list(index.values())
        db_path.write_text(json.dumps(db,indent=2)+'\n')
    print(f"Built {sum(s['status']=='redrawn' for s in report['sprites'])} redraws; "
          f"{len(report['textures'])} mapped hashes; {len(report['unmapped'])} awaiting capture")

if __name__ == '__main__':
    main()
