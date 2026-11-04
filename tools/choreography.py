"""Original paired choreography. Reads skeletal compatibility data, never source motion/meshes."""
from pathlib import Path
import re, json, math
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid')
TIMING={'Neck':(3.1,1.30),'Knee':(3.2,1.72),'Knife':(3.1,1.18)}

def skeleton():
    source=(GAME/'media/anims_X/Bob/Bob_AttackFloorStamp.x').read_text()
    # Only the rig declaration; no AnimationSet, Mesh or SkinWeights are read.
    source=source[source.index('Frame Dummy01 {'):source.index('Frame Body {')]
    tokens=re.findall(r'Frame\s+(\w+)\s*\{|FrameTransformMatrix\s*\{([^}]+)\}|([{}])',source)
    bones=[]; stack=[]
    for name,matrix,brace in tokens:
        if name:
            bones.append(dict(name=name,parent=stack[-1] if stack else -1))
            stack.append(len(bones)-1)
        elif matrix:
            values=[float(x) for x in re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?',matrix)]
            bones[stack[-1]]['local']=np.array(values).reshape(4,4).T
        elif brace=='}':
            if stack: stack.pop()
    for b in bones:
        parent=b['parent']
        b['world']=(bones[parent]['world'] if parent>=0 else np.eye(4))@b['local']
    return bones

def unit(v):
    v=np.asarray(v,dtype=float); n=np.linalg.norm(v)
    return v/max(n,1e-8)

def rot(axis,angle):
    a=unit(axis); c=math.cos(angle); s=math.sin(angle)
    x,y,z=a; k=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
    return np.eye(3)*c+(1-c)*np.outer(a,a)+s*k

def align(a,b):
    a,b=unit(a),unit(b); cross=np.cross(a,b); dot=np.clip(a@b,-1,1)
    if np.linalg.norm(cross)<1e-7:
        return np.eye(3) if dot>0 else rot(np.cross(a,[1,.3,.2]),math.pi)
    return rot(cross,math.acos(dot))

class Pose:
    def __init__(self,bones):
        self.bones=bones; self.idx={b['name']:i for i,b in enumerate(bones)}
        self.world=np.array([b['world'].copy() for b in bones])
    def pos(self,n): return self.world[self.idx[n]][:3,3].copy()
    def descendants(self,n):
        root=self.idx[n]
        for i in range(len(self.bones)):
            j=i
            while j>=0:
                if j==root: yield i; break
                j=self.bones[j]['parent']
    def rotate(self,n,R):
        center=self.pos(n)
        for i in self.descendants(n):
            self.world[i,:3,3]=center+R@(self.world[i,:3,3]-center)
            self.world[i,:3,:3]=R@self.world[i,:3,:3]
    def translate(self,n,delta):
        for i in self.descendants(n): self.world[i,:3,3]+=delta
    def limb(self,root,mid,tip,target,pole,hinge=False):
        a,b,c=self.pos(root),self.pos(mid),self.pos(tip)
        l1,l2=np.linalg.norm(b-a),np.linalg.norm(c-b)
        direction=unit(np.array(target)-a)
        distance=np.clip(np.linalg.norm(np.array(target)-a),abs(l1-l2)+.002,l1+l2-(.012 if hinge else .002))
        projected=unit(np.array(pole)-a-direction*(direction@(np.array(pole)-a)))
        along=(l1*l1-l2*l2+distance*distance)/(2*distance)
        elbow=a+direction*along+projected*math.sqrt(max(0,l1*l1-along*along))
        if hinge:
            # Orient the upper arm's entire bend plane. Shortest-arc aiming of
            # each bone independently leaves the forearm with arbitrary roll.
            def frame(axis,normal):
                x=unit(axis);z=unit(normal);y=unit(np.cross(z,x))
                return np.column_stack((x,y,z))
            old=frame(b-a,np.cross(b-a,c-b))
            new=frame(elbow-a,np.cross(elbow-a,a+direction*distance-elbow))
            self.rotate(root,new@old.T)
        else:self.rotate(root,align(b-a,elbow-a))
        self.rotate(mid,align(self.pos(tip)-self.pos(mid),a+direction*distance-self.pos(mid)))
    def arms(self,left,right):
        for side,target,sign in [('L',left,1),('R',right,-1)]:
            root,mid,tip=['Bip01_'+side+'_'+part for part in ['UpperArm','Forearm','Hand']]
            a,b,c=self.pos(root),self.pos(mid),self.pos(tip)
            neutral=unit(b-a-unit(c-a)*(unit(c-a)@(b-a)))
            reach=np.clip(np.linalg.norm(np.asarray(target)-c)/.18,0,1)
            reach=reach*reach*(3-2*reach)
            # Pole follows the shoulder, never crosses the reach line on the
            # way back down, and eases back to the rig's neutral elbow plane.
            bend=unit(neutral*(1-reach)+unit([sign,.05,.65])*reach)
            self.limb(root,mid,tip,target,a+bend*.5,hinge=True)
        # The game attaches weapon props to separate rig nodes, not to the hand itself.
        for prop,hand in [('Bip01_Prop1','Bip01_R_Hand'),('Bip01_Prop2','Bip01_L_Hand')]:
            h=self.idx[hand]; pr=self.idx[prop]
            offset=np.linalg.inv(self.bones[h]['world'])@self.bones[pr]['world']
            self.world[pr]=self.world[h]@offset
    def legs(self,left,right):
        for side,target,sign in [('L',left,1),('R',right,-1)]:
            foot='Bip01_'+side+'_Foot'
            orientation=self.bones[self.idx[foot]]['world'][:3,:3]
            self.limb('Bip01_'+side+'_Thigh','Bip01_'+side+'_Calf','Bip01_'+side+'_Foot',target,[sign*.08,.27,-.45])
            self.rotate(foot,orientation@np.linalg.inv(self.world[self.idx[foot],:3,:3]))
    def hand(self,side,direction,curl):
        hand='Bip01_'+side+'_Hand'
        finger='Bip01_'+side+'_Finger1'
        source=unit(self.pos(finger)-self.pos(hand));target=unit(direction)
        angle=math.acos(np.clip(source@target,-1,1))
        # Keep the neutral wrist inherited from the forearm, with at most 25
        # degrees of extra bend. Never turn the palm by 100+ degrees at the wrist.
        axis=np.cross(source,target)
        if np.linalg.norm(axis)>1e-7:self.rotate(hand,rot(axis,min(angle,math.radians(25))*min(1,curl*2)))
        for digit in ['Finger0','Finger1']:
            name='Bip01_'+side+'_'+digit
            axis=self.world[self.idx[hand],:3,1]
            self.rotate(name,rot(axis,min(curl,.65)*(1 if side=='L' else -1)))
        prop='Bip01_Prop2' if side=='L' else 'Bip01_Prop1'
        h,pr=self.idx[hand],self.idx[prop]
        self.world[pr]=self.world[h]@np.linalg.inv(self.bones[h]['world'])@self.bones[pr]['world']
    def local(self):
        return [np.linalg.inv(self.world[b['parent']])@self.world[i] if b['parent']>=0 else self.world[i] for i,b in enumerate(self.bones)]

def curve(t,keys):
    if t<=keys[0][0]: return np.array(keys[0][1],dtype=float)
    for i,((a,x),(b,y)) in enumerate(zip(keys,keys[1:])):
        if t<=b:
            # Monotone Hermite: keep momentum through travel keys, stop only
            # at a hold or reversal. Component-wise limiting prevents overshoot.
            x,y=np.array(x,dtype=float),np.array(y,dtype=float)
            slope=(y-x)/(b-a)
            def tangent(j):
                if j==0 or j==len(keys)-1:return np.zeros_like(x)
                ta,xa=keys[j-1];tb,xb=keys[j];tc,xc=keys[j+1]
                d0=(np.array(xb)-np.array(xa))/(tb-ta);d1=(np.array(xc)-np.array(xb))/(tc-tb)
                same=d0*d1>0
                return np.where(same,np.sign(d0)*np.minimum((np.abs(d0)+np.abs(d1))*.5,2*np.minimum(np.abs(d0),np.abs(d1))),0)
            u=(t-a)/(b-a)
            return (2*u**3-3*u*u+1)*x+(u**3-2*u*u+u)*(b-a)*tangent(i)+(-2*u**3+3*u*u)*y+(u**3-u*u)*(b-a)*tangent(i+1)
    return np.array(keys[-1][1],dtype=float)

def base_pose(bones,kind,role,t):
    p=Pose(bones)
    feet=[p.pos('Bip01_L_Foot'),p.pos('Bip01_R_Foot')]
    hands=[p.pos('Bip01_L_Hand'),p.pos('Bip01_R_Hand')]
    if kind=='Neck' and role=='Player':
        reach=float(curve(t,[(0,0),(.55,1),(1.6,1),(2.6,0)]))
        twist=float(curve(t,[(0,0),(.95,0),(1.25,1),(1.6,.7),(2.5,0)]))
        p.translate('Bip01',np.array([-.025*twist,-.025*reach,-.065*reach]))
        p.rotate('Bip01_Spine',rot([1,0,0],-.18*reach))
        p.rotate('Bip01_Spine1',rot([0,1,0],-.25*twist))
        left=curve(t,[(0,hands[0]),(.6,[.055,.795,-.285]),(1.0,[.035,.81,-.305]),(1.28,[-.075,.79,-.275]),(1.7,[-.10,.74,-.21]),(2.6,hands[0])])
        right=curve(t,[(0,hands[1]),(.55,[-.055,.765,-.30]),(1.0,[-.04,.79,-.32]),(1.28,[.06,.80,-.28]),(1.7,[.10,.71,-.18]),(2.6,hands[1])])
        p.legs(*feet); p.arms(left,right)
    elif kind=='Neck':
        grasp=float(curve(t,[(0,0),(.5,0),(.8,1),(2.6,1)]))
        twist=float(curve(t,[(0,0),(.98,0),(1.25,1),(2.6,1)]))
        p.translate('Bip01',np.array([0,-.03*twist,.025*grasp]))
        p.rotate('Bip01_Spine',rot([1,0,0],.12*grasp))
        p.rotate('Bip01_Neck',rot([0,1,0],-.85*twist))
        p.rotate('Bip01_Head',rot([0,0,1],.20*twist))
        p.legs(*feet)
        p.arms(hands[0]*(1-grasp)+np.array([.065,.75,-.03])*grasp,hands[1]*(1-grasp)+np.array([-.07,.73,-.04])*grasp)
    elif kind=='Knee' and role=='Player':
        kick=float(curve(t,[(0,0),(.25,.3),(.60,1),(.90,0),(2.8,0)]))
        stomp=float(curve(t,[(0,0),(1.0,0),(1.35,1),(1.70,.4),(2.1,0),(2.8,0)]))
        p.translate('Bip01',np.array([-.02*kick,-.04*kick-.055*stomp,-.055*kick]))
        p.rotate('Bip01_Spine',rot([1,0,0],-.12*kick-.25*stomp))
        left=curve(t,[(0,feet[0]),(.25,[.08,.19,-.08]),(.60,[.03,.26,-.34]),(.90,feet[0]),(2.8,feet[0])])
        right=feet[1]
        p.legs(left,right)
        guard=float(curve(t,[(0,0),(.3,1),(2.0,1),(2.8,0)]))
        right_hand=curve(t,[(0,hands[1]),(.3,[-.18,.65,-.15]),(1.05,[-.18,.65,-.15]),(1.35,[-.06,.84,-.17]),(1.70,[-.018,.45,-.245]),(1.85,[-.018,.45,-.245]),(2.8,hands[1])])
        p.arms(hands[0]*(1-guard)+np.array([.19,.68,-.12])*guard,right_hand)
    elif kind=='Knee':
        collapse=float(curve(t,[(0,0),(.56,0),(1.15,1),(2.8,1)]))
        p.translate('Bip01',np.array([.015*collapse,-.29*collapse,.06*collapse]))
        p.rotate('Bip01_Spine',rot([1,0,0],-.65*collapse))
        p.rotate('Bip01_Spine1',rot([1,0,0],-.30*collapse))
        p.rotate('Bip01_Head',rot([1,0,0],-.2*collapse))
        p.legs(np.array([.075,.07,.08]),np.array([-.07,.07,.04]))
        p.arms(hands[0]*(1-collapse)+np.array([.12,.16,-.24])*collapse,hands[1]*(1-collapse)+np.array([-.14,.18,-.22])*collapse)
    elif kind=='Knife' and role=='Player':
        crouch=float(curve(t,[(0,0),(.65,1),(1.8,1),(2.7,0)]))
        p.translate('Bip01',np.array([0,-.26*crouch,-.035*crouch]))
        p.rotate('Bip01_Spine',rot([1,0,0],-.45*crouch))
        p.rotate('Bip01_Spine1',rot([1,0,0],-.15*crouch))
        p.legs(np.array([.09,.065,-.03]),np.array([-.095,.07,.055]))
        left=curve(t,[(0,hands[0]),(.7,[.07,.16,-.23]),(1.75,[.07,.16,-.23]),(2.7,hands[0])])
        right=curve(t,[(0,hands[1]),(.7,[-.06,.48,-.1]),(1.05,[-.04,.17,-.23]),(1.25,[-.04,.17,-.23]),(1.6,[-.09,.39,-.16]),(2.7,hands[1])])
        p.arms(left,right)
    else: # Supine victim: authored pose, no extracted on-ground clip.
        root=p.pos('Bip01')
        p.rotate('Bip01',rot([1,0,0],math.pi/2))
        p.translate('Bip01',np.array([0,.09,0])-root)
        flinch=float(curve(t,[(0,0),(.98,0),(1.08,1),(1.4,.1),(2.7,.1)]))
        p.rotate('Bip01_Neck',rot([0,1,0],.15*flinch))
        p.rotate('Bip01_L_UpperArm',rot([0,1,0],-.15*flinch))
    return p

def quaternion(m):
    # Proper rotations only; remove the source rig's tiny export roundoff.
    u,_,v=np.linalg.svd(m); r=u@v
    tr=np.trace(r)
    if tr>0:
        s=math.sqrt(tr+1)*2
        return np.array([s/4,(r[2,1]-r[1,2])/s,(r[0,2]-r[2,0])/s,(r[1,0]-r[0,1])/s])
    i=int(np.argmax(np.diag(r))); j=(i+1)%3; k=(i+2)%3
    s=math.sqrt(1+r[i,i]-r[j,j]-r[k,k])*2
    q=np.zeros(4);q[0]=(r[k,j]-r[j,k])/s;q[i+1]=s/4;q[j+1]=(r[j,i]+r[i,j])/s;q[k+1]=(r[k,i]+r[i,k])/s
    return q

def rotation(q):
    w,x,y,z=unit(q)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def blend_pose(a,b,u):
    p=Pose(a.bones)
    for i,(ma,mb) in enumerate(zip(a.local(),b.local())):
        qa,qb=quaternion(ma[:3,:3]),quaternion(mb[:3,:3])
        if qa@qb<0: qb=-qb
        angle=math.acos(np.clip(qa@qb,-1,1))
        q=qa*(1-u)+qb*u if angle<1e-5 else (qa*math.sin((1-u)*angle)+qb*math.sin(u*angle))/math.sin(angle)
        m=np.eye(4);m[:3,:3]=rotation(q);m[:3,3]=ma[:3,3]*(1-u)+mb[:3,3]*u
        parent=p.bones[i]['parent'];p.world[i]=(p.world[parent] if parent>=0 else np.eye(4))@m
    return p

def landing_pose(bones,kind):
    if kind=='Knife':return base_pose(bones,kind,'Victim',2.7)
    p=Pose(bones)
    if kind=='Neck':
        p.rotate('Bip01',rot([0,1,0],-.22)@rot([1,0,0],-math.pi/2))
        target=np.array([.05,.105,-.24])
        p.rotate('Bip01_Head',rot([0,1,0],.5))
    else:
        # Sideways collapse from the kneel; no return to a standing death pose.
        p.rotate('Bip01',rot([0,1,0],-.25)@rot([0,0,1],-math.pi/2))
        target=np.array([.18,.11,.01])
        p.rotate('Bip01_L_Calf',rot([0,1,0],-.65))
        p.rotate('Bip01_R_Calf',rot([0,1,0],-.45))
    p.translate('Bip01',target-p.pos('Bip01'))
    for side in ['L','R']:
        p.rotate('Bip01_'+side+'_UpperArm',rot([0,1,0],.15 if side=='L' else -.2))
    if kind=='Knee':p.arms([.35,.07,-.05],[.40,.15,.03])
    # Keep extremities above the floor without changing joint lengths.
    low=min(p.pos(n)[1] for n in ['Bip01_Head','Bip01_L_Hand','Bip01_R_Hand','Bip01_L_Foot','Bip01_R_Foot'])
    p.translate('Bip01',np.array([0,max(0,.035-low),0]))
    return p

def make_pose(bones,kind,role,t):
    duration,impact=TIMING[kind]
    if role=='Victim':
        p=base_pose(bones,kind,role,min(t,impact))
        if t>impact:
            if kind=='Knife':
                p=base_pose(bones,kind,role,min(t,2.7))
            else:
                fall=float(curve(t,[(impact,0),(impact+.22,.08),(impact+.68,.78),(impact+1.05,1),(duration,1)]))
                p=blend_pose(p,landing_pose(bones,kind),fall)
        return p
    p=Pose(bones);feet=[p.pos('Bip01_'+s+'_Foot') for s in ['L','R']];hands=[p.pos('Bip01_'+s+'_Hand') for s in ['L','R']]
    victim=make_pose(bones,kind,'Victim',min(t,impact))
    def contact(name,offset=(0,0,0)):
        v=victim.pos(name)+np.array(offset)
        if kind=='Knee':v[0]=-v[0];v[2]=-v[2]
        v[2]-={'Neck':.325,'Knee':.36,'Knife':.5}[kind]
        return v
    if kind=='Neck':
        reach=float(curve(t,[(0,0),(.55,1),(1.5,1),(2.5,0),(duration,0)]))
        twist=float(curve(t,[(0,0),(.96,0),(1.30,1),(1.6,.65),(2.5,0)]))
        p.translate('Bip01',np.array([-.025*twist,-.032*reach,-.055*reach]))
        p.rotate('Bip01_Spine',rot([1,0,0],-.12*reach))
        p.rotate('Bip01_Spine1',rot([0,1,0],-.20*twist))
        windup=float(curve(t,[(0,0),(.22,1),(.55,0),(duration,0)]))
        p.translate('Bip01',np.array([.012*windup,.008*windup,.018*windup]))
        for side,sign in [('L',1),('R',-1)]:p.rotate('Bip01_'+side+'_Clavicle',rot([0,0,1],sign*.07*reach))
        head=contact('Bip01_Head',(0,.045,0))
        left=head+rot([0,1,0],-.85*twist)@np.array([.055,-.012,-.004])
        right=head+rot([0,1,0],-.85*twist)@np.array([-.05,-.035,.015])
        grip=float(curve(t,[(0,0),(.58,1),(1.38,1),(1.8,0),(duration,0)]))
        release=float(curve(t,[(0,0),(1.42,0),(1.85,1),(2.65,0)]))
        p.legs(*feet)
        p.arms(hands[0]*(1-grip)+left*grip+np.array([.07,.16,-.09])*release,
               hands[1]*(1-grip)+right*grip+np.array([-.07,.16,-.09])*release)
        p.hand('L',unit([-.4*grip,-1,.15]),.65*grip);p.hand('R',unit([.4*grip,-1,.15]),.75*grip)
    elif kind=='Knee':
        kick=float(curve(t,[(0,0),(.30,.25),(.58,1),(.86,0),(duration,0)]))
        strike=float(curve(t,[(0,0),(1.12,0),(1.45,.2),(impact,1),(1.94,.7),(2.7,0)]))
        p.translate('Bip01',np.array([-.025*kick,-.035*kick-.065*strike,-.04*kick-.02*strike]))
        p.rotate('Bip01_Spine',rot([1,0,0],-.10*kick-.25*strike))
        p.rotate('Bip01_Spine1',rot([0,1,0],-.20*strike))
        counter=float(curve(t,[(0,0),(.30,.12),(.58,-.10),(.9,0),(1.43,.13),(impact,-.16),(2.1,0),(duration,0)]))
        p.rotate('Bip01_Spine1',rot([0,1,0],counter))
        p.rotate('Bip01_Head',rot([1,0,0],-.08*strike))
        foot=curve(t,[(0,feet[0]),(.30,[.08,.19,-.10]),(.58,[.04,.255,-.31]),(.86,feet[0]),(duration,feet[0])])
        p.legs(foot,feet[1])
        head=contact('Bip01_Head',(0,.025,0))
        right=curve(t,[(0,hands[1]),(.32,[-.15,.65,-.12]),(1.12,[-.15,.65,-.12]),(1.43,[-.12,.82,-.12]),(impact,head),(1.86,head+np.array([.01,-.025,.01])),(2.15,[-.12,.56,-.13]),(duration,hands[1])])
        guard=float(curve(t,[(0,0),(.32,1),(1.96,1),(2.8,0)]))
        p.arms(hands[0]*(1-guard)+np.array([.17,.63,-.14])*guard,right)
        p.hand('R',[-.05,-1,-.1],.85*guard);p.hand('L',[0,-.4,-1],.6*guard)
    else:
        crouch=float(curve(t,[(0,0),(.64,1.035),(.82,1),(1.75,1),(2.7,0),(duration,0)]))
        weight=float(curve(t,[(0,0),(.94,0),(impact,1),(1.4,.35),(1.8,0),(duration,0)]))
        p.translate('Bip01',np.array([.012*crouch,-.275*crouch-.009*weight,-.055*crouch-.012*weight]))
        p.rotate('Bip01_Spine',rot([1,0,0],-.43*crouch));p.rotate('Bip01_Spine1',rot([1,0,0],-.15*crouch))
        p.rotate('Bip01_Neck',rot([1,0,0],-.10*crouch))
        p.legs(feet[0]*(1-crouch)+np.array([.105,.06,-.05])*crouch,feet[1]*(1-crouch)+np.array([-.105,.07,.07])*crouch)
        head=contact('Bip01_Head',(0,.035,0))
        left=curve(t,[(0,hands[0]),(.68,head+np.array([.05,.025,0])),(1.65,head+np.array([.05,.025,0])),(2.25,[.13,.40,-.10]),(duration,hands[0])])
        # A short controlled thrust, held beat, withdrawal, then standing recovery.
        right=curve(t,[(0,hands[1]),(.72,head+np.array([-.035,.30,.06])),(.93,head+np.array([-.035,.32,.04])),(impact,head+np.array([-.035,.08,0])),(1.36,head+np.array([-.035,.08,0])),(1.68,head+np.array([-.05,.27,.06])),(2.35,[-.12,.40,-.10]),(duration,hands[1])])
        p.arms(left,right);p.hand('L',[0,-.3,-1],.2*crouch);p.hand('R',[0,-1,-.05],.85*crouch)
    # Avoid a wrist pop at entry, and restore both hands during recovery.
    if t<.18:p=blend_pose(Pose(bones),p,float(curve(t,[(0,0),(.18,1)])))
    if t>duration-.40:p=blend_pose(p,Pose(bones),float(curve(t,[(duration-.4,0),(duration,1)])))
    return p

def matrix_text(m): return ','.join(f'{v:.8f}' for v in m.T.flatten())

def write_x(path,bones,poses,name,fps):
    out=['xof 0303txt 0032','AnimTicksPerSecond { 30; }']
    local=poses[0].local()
    def frame(i,indent=''):
        b=bones[i]
        out.append(indent+'Frame '+b['name']+' {')
        out.append(indent+' FrameTransformMatrix { '+matrix_text(local[i])+';; }')
        for k,child in enumerate(bones):
            if child['parent']==i: frame(k,indent+' ')
        out.append(indent+'}')
    for i,b in enumerate(bones):
        if b['parent']<0: frame(i)
    # Original tiny carrier mesh provides bone declarations to Assimp; no game geometry.
    n=len(bones)
    out+=['Mesh VF_Carrier {',str(n*3)+';']
    vertices=[]
    for i in range(n): vertices.extend(['0;0;0;','0.001;0;0;','0;0.001;0;'])
    out.append(',\n'.join(vertices)+';')
    out.append(str(n)+';')
    out.append(',\n'.join(f'3;{i*3},{i*3+1},{i*3+2};' for i in range(n))+';')
    for i,b in enumerate(bones):
        # PZ's bundled Assimp X importer requires decimal literals for weights.
        out.append('SkinWeights { "'+b['name']+'"; 3; '+f'{i*3},{i*3+1},{i*3+2}; 1.0,1.0,1.0; '+matrix_text(np.linalg.inv(poses[0].world[i]))+';; }')
    out.append('}')
    out.append('AnimationSet '+name+' {')
    locals_by_frame=[p.local() for p in poses]
    for i,b in enumerate(bones):
        out.append('Animation { { '+b['name']+' } AnimationKey { 4; '+str(len(poses))+';')
        out.append(',\n'.join(str(f)+';16;'+matrix_text(locals_by_frame[f][i])+';;' for f in range(len(poses)))+';')
        out.append('} }')
    out.append('}')
    path.write_text('\n'.join(out)+'\n',encoding='ascii')

def build():
    bones=skeleton(); fps=30
    # Human's registered animation directory. Unregistered folders are skipped
    # by B42 when a mod has no common animation directory.
    out=ROOT/'ViewpointFinishers/42/media/anims_X/Bob'; out.mkdir(parents=True,exist_ok=True)
    preview=ROOT/'animation_source'; preview.mkdir(exist_ok=True)
    manifest={'fps':fps,'bones':[dict(name=b['name'],parent=b['parent']) for b in bones],'clips':{}}
    for kind,(duration,impact) in TIMING.items():
        for role in ['Player','Victim']:
            name='VF_'+role+'_'+kind
            poses=[make_pose(bones,kind,role,f/fps) for f in range(round(duration*fps)+1)]
            write_x(out/(name+'.x'),bones,poses,name,fps)
            manifest['clips'][name]={'duration':duration,'world':[p.world.tolist() for p in poses]}
            if role=='Victim':
                death=[make_pose(bones,kind,role,impact+f/fps) for f in range(round((duration-impact)*fps)+1)]
                write_x(out/('VF_Death_'+kind+'.x'),bones,death,'VF_Death_'+kind,fps)
    (preview/'poses.json').write_text(json.dumps(manifest,separators=(',',':')),encoding='utf-8')
    print('Authored 6 paired clips and 3 continuous death segments.')

if __name__=='__main__': build()
