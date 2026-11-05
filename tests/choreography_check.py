"""Continuity, contact and floor checks on the authored paired animation."""
import sys,json
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from choreography import skeleton,make_pose,TIMING,PAIR_OFFSET,FRONT_FACING
bones=skeleton();results={}
for kind,(duration,impact) in TIMING.items():
    p=make_pose(bones,kind,'Player',impact)
    v=make_pose(bones,kind,'Victim',impact)
    head=v.pos('Bip01_Head')+np.array([0,.045 if kind=='Neck' else .025,0])
    if kind=='Shove':
        head=v.pos('Bip01_Spine1')+np.array([0,.035,-.04])
    if kind=='Sweep':
        head=v.pos('Bip01_R_Calf')+np.array([.015,-.075,.015])
    if kind in FRONT_FACING:head[[0,2]]*=-1
    head[2]-=PAIR_OFFSET[kind]
    distances={side:float(np.linalg.norm(p.pos('Bip01_'+side+'_Hand')-head)) for side in ['L','R']}
    if kind=='Knife':
        prop=p.world[p.idx['Bip01_Prop1']]
        tip=(prop@np.array([0,.248,.008,1]))[:3]
        target=v.pos('Bip01_Head')+np.array([0,.035,-PAIR_OFFSET[kind]])
        distances={'hunting_knife_tip_to_target':float(np.linalg.norm(tip-target))}
        assert distances['hunting_knife_tip_to_target']<.06,distances
    elif kind=='Sweep':
        distances={'boot_to_lower_leg':float(np.linalg.norm(p.pos('Bip01_R_Foot')-head))}
        assert distances['boot_to_lower_leg']<.07,distances
    else:
        assert distances['R']<(.15 if kind=='Knife' else .10),(kind,distances)
        if kind in ('Neck','Shove'):assert distances['L']<.10,distances
    final=make_pose(bones,kind,'Victim',duration)
    lowest=min(final.pos(b['name'])[1] for b in bones if b['name'].endswith(('_Hand','_Foot','_Head')))
    assert lowest>-.005,(kind,lowest)
    a=make_pose(bones,kind,'Player',0);b=make_pose(bones,kind,'Player',duration)
    assert np.max(np.abs(a.world-b.world))<1e-6,kind
    # The exported death segment is sampled from this same victim motion at impact.
    before=make_pose(bones,kind,'Victim',impact-1e-4)
    after=make_pose(bones,kind,'Victim',impact+1e-4)
    assert np.max(np.abs(before.world-after.world))<.005,kind
    worst_wrist=0;worst_step=0;previous=None
    for frame in range(round(duration*30)+1):
        sample=make_pose(bones,kind,'Player',frame/30);local=sample.local()
        for side in ['L','R']:
            idx=sample.idx['Bip01_'+side+'_Hand']
            delta=local[idx][:3,:3]@np.linalg.inv(bones[idx]['local'][:3,:3])
            angle=float(np.degrees(np.arccos(np.clip((np.trace(delta)-1)/2,-1,1))))
            worst_wrist=max(worst_wrist,angle)
            for part in ['UpperArm','Forearm','Hand']:
                idx=sample.idx['Bip01_'+side+'_'+part]
                if previous is not None:
                    delta=local[idx][:3,:3]@np.linalg.inv(previous[idx][:3,:3])
                    worst_step=max(worst_step,float(np.degrees(np.arccos(np.clip((np.trace(delta)-1)/2,-1,1)))))
        previous=local
    assert worst_wrist<26,(kind,'wrist overextension',worst_wrist)
    assert worst_step<35,(kind,'arm flip between adjacent frames',worst_step)
    results[kind]={'contact_distance_rig_units':distances,'resting_lowest_joint':float(lowest),'entry_matches_recovery':True,'impact_to_death_continuous':True,'max_wrist_rotation_degrees':worst_wrist,'max_arm_step_degrees_at_30fps':worst_step}
    if kind=='Knife':
        previous_prop=None
        worst_prop_step=0
        for frame in range(round(duration*30)+1):
            sample=make_pose(bones,kind,'Player',frame/30)
            prop=sample.world[sample.idx['Bip01_Prop1'],:3,:3]
            if .64<=frame/30<=1.86:
                assert prop[1,1]<-.99,('knife blade must point down',frame)
            if previous_prop is not None:
                delta=prop@np.linalg.inv(previous_prop)
                worst_prop_step=max(worst_prop_step,float(np.degrees(np.arccos(np.clip((np.trace(delta)-1)/2,-1,1)))))
            previous_prop=prop
        assert worst_prop_step<35,('knife flips during regrip',worst_prop_step)
        results[kind]['blade_down_during_strike']=True
        results[kind]['max_knife_step_degrees_at_30fps']=worst_prop_step
    if kind=='Neck':
        # Once the head is released, elbows must drop below the shoulders
        # and stay near the ribs, rather than holding a raised wing pose.
        max_spread=0;min_drop=1
        for t in np.arange(1.75,2.61,1/60):
            sample=make_pose(bones,kind,'Player',t)
            for side in ['L','R']:
                shoulder=sample.pos('Bip01_'+side+'_UpperArm')
                elbow=sample.pos('Bip01_'+side+'_Forearm')
                max_spread=max(max_spread,abs(elbow[0]-shoulder[0]))
                min_drop=min(min_drop,shoulder[1]-elbow[1])
        assert max_spread<.065,('neck release elbows flare out',max_spread)
        assert min_drop>.075,('neck release elbows stay raised',min_drop)
        results[kind]['release_max_elbow_spread']=float(max_spread)
        results[kind]['release_min_elbow_drop']=float(min_drop)
out=Path(__file__).resolve().parents[1]/'validation/choreography.json'
out.write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results))
