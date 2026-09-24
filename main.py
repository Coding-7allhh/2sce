#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,os,random,re,subprocess,sys,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont
from moviepy.editor import CompositeVideoClip,ImageClip,VideoFileClip,crop

ROOT=Path(__file__).resolve().parent
ASSETS=ROOT/'assets'; BG_DIR=ASSETS/'Bg_Pic'; TOP_DIR=ASSETS/'top_clips'; BOTTOM_DIR=ROOT/'clips'
OUT=ROOT/'output'/'reaction_720p'; LOG=ROOT/'output'/'processing_log.csv'
TOP_DRIVE_URL=os.getenv('TOP_DRIVE_URL','https://drive.google.com/drive/folders/1l9ayaXiRBwUr1Hrjag7r3CycVDiN24fh')
BOTTOM_DRIVE_URL=os.getenv('BOTTOM_DRIVE_URL','https://drive.google.com/drive/folders/10DSjb9etdFzQTg_rftRJpJkC5jKBjsNT')
W,H=720,1280
TOP=(72,78,576,500); BOT=(17,595,686,493)
TOP_R,BOT_R=23,27; TOP_B,BOT_B=7,9
TOP_C=(205,44,224); BOT_C=(255,204,0)

def cmd(a):
    print('$',' '.join(a),flush=True); subprocess.run(a,check=True)

def drive(url,dst,force=False):
    dst.mkdir(parents=True,exist_ok=True); marker=dst/'.gdown_complete'
    if marker.exists() and not force and any(dst.rglob('*')): return
    if force and marker.exists(): marker.unlink()
    cmd([sys.executable,'-m','gdown','--folder',url,'-O',str(dst),'--remaining-ok'])
    marker.write_text('ok\n',encoding='utf-8')

def files(d,exts): return sorted(p for p in d.rglob('*') if p.is_file() and p.suffix.lower() in exts)
def safe(s): return re.sub(r'_+','_',re.sub(r'[^\w.-]+','_',s)).strip('._')[:100] or 'video'

def rounded_mask(w,h,r):
    im=Image.new('L',(w,h),0); ImageDraw.Draw(im).rounded_rectangle((0,0,w-1,h-1),radius=r,fill=255); return im

def border(w,h,r,b,c):
    im=Image.new('RGBA',(w,h),(0,0,0,0)); ImageDraw.Draw(im).rounded_rectangle((b//2,b//2,w-b//2-1,h-b//2-1),radius=r,outline=c+(255,),width=b); return im

def shadow(w,h,r):
    pad=24; im=Image.new('RGBA',(w+pad*2,h+pad*2),(0,0,0,0)); a=Image.new('L',im.size,0)
    ImageDraw.Draw(a).rounded_rectangle((pad,pad+7,pad+w,pad+h+7),radius=r,fill=130); a=a.filter(ImageFilter.GaussianBlur(13)); black=Image.new('RGBA',im.size,(0,0,0,0)); black.putalpha(a); return black

def fit(v,w,h):
    s=max(w/v.w,h/v.h); nw=max(1,round(v.w*s)); nh=max(1,round(v.h*s)); r=v.resize(newsize=(nw,nh)); return crop(r,width=w,height=h,x_center=nw/2,y_center=nh/2)

def framed(v,x,y,w,h,r,b,c):
    iw,ih=w-2*b,h-2*b; inner=fit(v,iw,ih).set_position((x+b,y+b))
    mask=ImageClip(np.asarray(rounded_mask(iw,ih,max(1,r-b)))/255.0,ismask=True).set_duration(v.duration); inner=inner.set_mask(mask)
    br=ImageClip(np.asarray(border(w,h,r,b,c))).set_position((x,y)).set_duration(v.duration)
    sh=shadow(w,h,r); si=ImageClip(np.asarray(sh)).set_position((x-sh.width//2+w//2,y-sh.height//2+h//2)).set_duration(v.duration)
    return [si,inner,br]

def background(p,dur):
    im=Image.open(p).convert('RGB'); s=max(W/im.width,H/im.height); nw=max(W,round(im.width*s)); nh=max(H,round(im.height*s)); im=im.resize((nw,nh),Image.Resampling.LANCZOS); l=max(0,(nw-W)//2); t=max(0,(nh-H)//2); im=im.crop((l,t,l+W,t+H)); im=im.filter(ImageFilter.GaussianBlur(13)); ov=Image.new('RGBA',(W,H),(0,0,0,48)); im=Image.alpha_composite(im.convert('RGBA'),ov).convert('RGB'); return ImageClip(np.asarray(im)).set_duration(dur)

def label(text,size=31):
    fp='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'; font=ImageFont.truetype(fp,size); st=3; px,py=14,8; box=font.getbbox(text,stroke_width=st); tw,th=box[2]-box[0],box[3]-box[1]; im=Image.new('RGBA',(tw+px*2,th+py*2),(0,0,0,0)); d=ImageDraw.Draw(im); d.text((px,py-box[1]),text,font=font,fill=(255,255,255,255),stroke_width=st,stroke_fill=(0,155,210,255)); return ImageClip(np.asarray(im))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--max-outputs',type=int,default=0); ap.add_argument('--part-min',type=int,default=1); ap.add_argument('--part-max',type=int,default=99); ap.add_argument('--seed',type=int); ap.add_argument('--dry-run',action='store_true'); ap.add_argument('--redownload',action='store_true'); a=ap.parse_args(); random.seed(a.seed)
    drive(TOP_DRIVE_URL,TOP_DIR,a.redownload); drive(BOTTOM_DRIVE_URL,BOTTOM_DIR,a.redownload); BG_DIR.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    bgs=files(BG_DIR,('.png','.jpg','.jpeg','.webp')); tops=files(TOP_DIR,('.mp4','.mov','.mkv','.webm')); bots=files(BOTTOM_DIR,('.mp4','.mov','.mkv','.webm'))
    if not bgs: raise RuntimeError(f'No backgrounds in {BG_DIR}. Add PNG/JPG/WebP files.')
    if not tops: raise RuntimeError(f'No top clips in {TOP_DIR}')
    if not bots: raise RuntimeError(f'No bottom clips in {BOTTOM_DIR}')
    jobs=tops[:a.max_outputs] if a.max_outputs>0 else tops
    print(f'Top={len(tops)} Bottom={len(bots)} Jobs={len(jobs)} Backgrounds={len(bgs)}')
    if a.dry_run:
        for i,t in enumerate(jobs,1): print(f'[DRY] {i}: {t} + {bots[(i-1)%len(bots)]}')
        return
    LOG.parent.mkdir(parents=True,exist_ok=True)
    if not LOG.exists():
        with LOG.open('w',newline='',encoding='utf8') as f: csv.writer(f).writerow(['index','top_clip','bottom_clip','background','part_number','fps','status','output','error'])
    for i,tpath in enumerate(jobs,1):
        bpath=bots[(i-1)%len(bots)]; bg=bgs[(i-1)%len(bgs)]; part=random.randint(a.part_min,a.part_max); out=OUT/f'{i:04d}_{safe(tpath.stem)}_720p.mp4'; top=bot=final=None
        try:
            top=VideoFileClip(str(tpath),audio=True); bot=VideoFileClip(str(bpath),audio=True); dur=min(top.duration,bot.duration); top=top.subclip(0,dur); bot=bot.subclip(0,dur)
            fps=float(top.fps or bot.fps or 30)
            layers=[background(bg,dur)]+framed(top,*TOP,TOP_R,TOP_B,TOP_C)+framed(bot,*BOT,BOT_R,BOT_B,BOT_C)
            layers += [label('HardToonz').set_position((BOT[0]+18,BOT[1]+18)).set_duration(dur),label(f'Part {part}').set_position((BOT[0]+BOT[2]-145,BOT[1]+18)).set_duration(dur)]
            final=CompositeVideoClip(layers,size=(W,H)).set_duration(dur); final.write_videofile(str(out),fps=fps,codec='libx264',audio_codec='aac',ffmpeg_params=['-crf','26','-preset','veryfast','-pix_fmt','yuv420p','-movflags','+faststart'],audio_bitrate='96k',threads=max(1,os.cpu_count() or 2),logger='bar')
            row=[i,str(tpath),str(bpath),str(bg),part,f'{fps:g}','OK',str(out),'']; print('[OK]',out)
        except Exception as e:
            row=[i,str(tpath),str(bpath),str(bg),part,'','ERROR','',repr(e)]; print('[ERROR]',e,file=sys.stderr)
        finally:
            for v in (final,top,bot):
                try:
                    if v: v.close()
                except: pass
        with LOG.open('a',newline='',encoding='utf8') as f: csv.writer(f).writerow(row)
if __name__=='__main__': main()
