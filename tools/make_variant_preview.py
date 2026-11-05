"""Make the 0.4 gameplay GIF from one run of the lab's native screen captures."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('capture', type=Path, help='Directory of vf040-<case>-<timestamp>.png files')
parser.add_argument('--knife', action='store_true', help='Build the 0.4.1 reverse-grip knife preview')
args = parser.parse_args()
title = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 23)
frames, durations = [], []
variants=[('Knife','Нож — обратный хват')] if args.knife else [('Sweep','Подсечка сзади'),('Shove','Толчок в грудь')]
prefix='vf041' if args.knife else 'vf040'
for kind, label in variants:
    files = sorted(args.capture.glob(f'{prefix}-{kind}-*.png'))
    if len(files) < 8:
        raise ValueError(f'Incomplete {kind} capture ({len(files)} frames)')
    times = [int(f.stem.rsplit('-', 1)[1]) for f in files]
    intervals = [b-a for a,b in zip(times,times[1:])]
    if max(intervals) > 2500:
        raise ValueError(f'Use one contiguous run for {kind}')
    intervals.append(sorted(intervals)[len(intervals)//2])
    for path, delay in zip(files, intervals):
        with Image.open(path) as image:
            # Third-person camera and the 1280x720 isolated test profile.
            bounds=(325,350,745,650) if args.knife else (265,310,805,695)
            view = image.convert('RGB').crop(bounds).resize((648,462), Image.Resampling.LANCZOS)
        frame = Image.new('RGB',(648,505),'#182029')
        frame.paste(view,(0,43))
        ImageDraw.Draw(frame).text((14,7),label,font=title,fill='white')
        frames.append(frame)
        durations.append(max(10,round(delay/10)*10))
out = root/'validation'/('knife-reverse-0.4.1.gif' if args.knife else 'new-finishers-0.4.0.gif')
frames[0].save(out,save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=True)
print(f'{out.name}: {len(frames)} captured frames, {sum(durations)/1000:.2f}s')
