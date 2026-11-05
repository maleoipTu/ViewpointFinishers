"""Build a GIF from actual lab screenshots, retaining recorded frame intervals."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json
import argparse

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('capture',nargs='?',type=Path,default=root/'.lab/profile/Screenshots')
source=parser.parse_args().capture
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
frames,durations,manifest=[],[],[]
for kind,label in [('Sweep','Подсечка'),('Shove','Толчок'),('Neck','Захват сзади'),('Knee','Удар по ноге и добивание')]:
    files=sorted(source.glob(f'vf050-{kind}-*.png'))
    assert len(files)>=8,kind
    times=[int(p.stem.rsplit('-',1)[1]) for p in files]
    end=next((i for i,t in enumerate(times) if t-times[0]>5500),len(files))
    segment=[]
    for i in range(end):
        delay=times[i+1]-times[i] if i+1<len(times) else 300
        assert 0<delay<1200,(kind,delay)
        with Image.open(files[i]) as im:
            view=im.convert('RGB').crop((260,315,800,675)).resize((648,432),Image.Resampling.LANCZOS)
        frame=Image.new('RGB',(648,500),'#161e27')
        frame.paste(view,(0,40))
        draw=ImageDraw.Draw(frame)
        draw.text((14,8),label+' · ragdoll',font=font,fill='white')
        draw.text((14,478),'Viewpoint Finishers 0.5.0 | Кадры реальной игры',font=small,fill='#c9d1d9')
        frames.append(frame);durations.append(max(10,round(delay/10)*10))
        segment.append(files[i].name)
    manifest.append({'kind':kind,'frames':segment})
samples=Image.new('RGB',(1000,800))
for i in range(25):
    samples.paste(frames[round(i*(len(frames)-1)/24)].resize((200,160)),((i%5)*200,(i//5)*160))
palette=samples.quantize(colors=256)
indexed=[f.quantize(palette=palette,dither=Image.Dither.FLOYDSTEINBERG) for f in frames]
output=root/'validation/ragdoll-0.5.0.gif'
indexed[0].save(output,save_all=True,append_images=indexed[1:],duration=durations,loop=0,optimize=False,disposal=1)
with Image.open(output) as gif:
    assert gif.n_frames==len(frames)
    total=0
    for i in range(gif.n_frames):
        gif.seek(i);gif.load();total+=gif.info['duration']
    assert total==sum(durations)
(root/'.lab/ragdoll-gif-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(f'{output.name}: {len(frames)} frames, {total/1000:.2f}s, {output.stat().st_size} bytes')
