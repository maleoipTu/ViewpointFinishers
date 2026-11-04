"""Make a labelled evidence preview from captured, unaltered game-window frames."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json
root=Path(__file__).resolve().parents[1]
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
frames=[]
durations=[]
capture=root/'.lab/capture-arms-final'
timing={r['i']:r['time'] for r in json.loads((capture/'timing.json').read_text())}
for label,start,end in [('Захват сзади — сворачивание шеи',52,86),('Удар по ноге и добивание',116,151),('Добивание лежащего ножом',184,221)]:
    for i in range(start,end):
        original=Image.open(capture/f'{i:03}.png').convert('RGB')
        view=original.crop((280,325,820,715)).resize((756,546),Image.Resampling.LANCZOS)
        frame=Image.new('RGB',(756,622),'#141a21')
        frame.paste(view,(0,45))
        d=ImageDraw.Draw(frame)
        d.text((16,10),label,font=font,fill='white')
        d.text((16,598),'Project Zomboid 42.21 + Viewpoint | реальные кадры игры | 0.3.0',font=small,fill='#c5ccd5')
        frames.append(frame)
        durations.append(max(20,round((timing.get(i+1,timing[i]+105)-timing[i])/10)*10))
frames[0].save(root/'validation/gameplay-preview-0.3.gif',save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=True)
frames[14].save(root/'validation/gameplay-neck-0.3.png')
frames[45].save(root/'validation/gameplay-knee-0.3.png')
frames[82].save(root/'validation/gameplay-knife-0.3.png')
print(f'Saved {len(frames)} captured frames, {sum(durations)/1000:.2f} seconds; crop, resize and labels only.')
