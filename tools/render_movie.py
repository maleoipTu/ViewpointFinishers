"""Playable .blend and smooth review frames from the authored skeletal poses."""
from pathlib import Path
script=Path(__file__).with_name('render_choreography.py').read_text()
exec(compile(script[:script.index('for kind,times in')],__file__,'exec'))
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO'
scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True
scene.render.resolution_x=640; scene.render.resolution_y=480
scene.render.fps=30
timeline=[]
for kind in ['Neck','Knee','Knife']:
    clip=data['clips']['VF_Player_'+kind]
    timeline.extend((kind,i) for i in range(len(clip['world'])))
scene.frame_start=1; scene.frame_end=len(timeline); scene.frame_step=3
for role,mat in [('Player',actor),('Victim',victim)]:
    matrices=data['clips']['VF_'+role+'_Neck']['world'][0]
    for a,b,r in pairs: segment(point(matrices,a,role,'Neck'),point(matrices,b,role,'Neck'),r,mat)
    segment(Vector((0,0,.85)),Vector((0,0,.95)),.057,mat)
for frame,(kind,index) in enumerate(timeline,1):
    objindex=0
    for role in ['Player','Victim']:
        matrices=data['clips']['VF_'+role+'_'+kind]['world'][index]
        segments=[(point(matrices,a,role,kind),point(matrices,b,role,kind),r) for a,b,r in pairs]
        a=point(matrices,'Bip01_Head',role,kind); b=point(matrices,'Bip01_HeadNub',role,kind)
        segments.append((a+(b-a)*.2,a+(b-a)*.8,.057))
        for a,b,r in segments:
            obj=objects[objindex]; objindex+=1
            obj.location=(a+b)*.5; obj.scale=(r,r,(b-a).length*.5+r*.35)
            obj.rotation_mode='QUATERNION'; q=(b-a).to_track_quat('Z','Y')
            if q.dot(obj.rotation_quaternion)<0: q.negate()
            obj.rotation_quaternion=q
            for prop in ['location','scale','rotation_quaternion']: obj.keyframe_insert(prop,frame=frame)
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'animation_source/choreography_animated.blend'))
movieframes=root/'animation_source/movieframes'; movieframes.mkdir(exist_ok=True)
scene.render.image_settings.file_format='PNG'; scene.render.filepath=str(movieframes/'pose_')
bpy.ops.render.render(animation=True)
