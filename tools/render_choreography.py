"""Blender review scene of original paired poses, with original mannequin geometry."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

root=Path(__file__).resolve().parents[1]
data=json.loads((root/'animation_source/poses.json').read_text())
out=root/'animation_source/preview'; out.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.render.resolution_x=960; scene.render.resolution_y=720; scene.render.resolution_percentage=100
scene.world.color=(.2,.2,.2)

def material(name,color):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1)
    m.use_nodes=True; m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*color,1)
    return m
actor=material('Player blue',(.08,.40,.65)); victim=material('Zombie rust',(.52,.15,.08))
floor=material('Ground',(.15,.18,.20))
bpy.ops.mesh.primitive_plane_add(size=200); bpy.context.object.data.materials.append(floor)
bpy.ops.object.light_add(type='AREA',location=(1,-2,4)); bpy.context.object.data.energy=400; bpy.context.object.data.shape='DISK'; bpy.context.object.data.size=4
bpy.ops.object.camera_add(location=(1.8,-2.1,1.7))
cam=bpy.context.object; cam.rotation_euler=(Vector((0,.30,.45))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.type='ORTHO'; cam.data.ortho_scale=2.0; scene.camera=cam
ids={b['name']:i for i,b in enumerate(data['bones'])}
pairs=[('Bip01_Spine','Bip01_Spine1',.064),('Bip01_Spine1','Bip01_Neck',.085),('Bip01_Pelvis','Bip01_Spine',.07)]
for side in ['L','R']:
    for a,b,r in [('UpperArm','Forearm',.030),('Forearm','Hand',.025),('Thigh','Calf',.039),('Calf','Foot',.028),('Foot','Toe0',.025),('Hand','Finger1',.021)]:
        pairs.append(('Bip01_'+side+'_'+a,'Bip01_'+side+'_'+b,r))

objects=[]
def point(matrices,name,role,kind):
    m=matrices[ids[name]]; x,y,z=[m[i][3] for i in range(3)]
    if role=='Victim':
        if kind=='Knee': x,z=-x,-z
        z-= {'Neck':.325,'Knee':.36,'Knife':.5}[kind]
    return Vector((x,-z,y))

def clear():
    for o in objects: bpy.data.objects.remove(o,do_unlink=True)
    objects.clear()

def segment(a,b,r,mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=1,location=(a+b)*.5)
    obj=bpy.context.object; obj.scale=(r,r,(b-a).length*.5+r*.35); obj.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler(); obj.data.materials.append(mat); objects.append(obj)

for kind,times in [('Neck',[0,.65,1.30,1.9,2.5,3.1]),('Knee',[0,.58,1.2,1.72,2.3,3.2]),('Knife',[0,.70,1.18,1.7,2.4,3.1])]:
    for k,t in enumerate(times):
        clear()
        for role,mat in [('Player',actor),('Victim',victim)]:
            matrices=data['clips']['VF_'+role+'_'+kind]['world'][round(t*30)]
            for a,b,r in pairs: segment(point(matrices,a,role,kind),point(matrices,b,role,kind),r,mat)
            a=point(matrices,'Bip01_Head',role,kind); b=point(matrices,'Bip01_HeadNub',role,kind)
            segment(a+(b-a)*.2,a+(b-a)*.8,.057,mat)
        scene.render.filepath=str(out/f'{kind}_{k}.png'); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'animation_source/choreography_review.blend'))
print('Paired pose review rendered')
