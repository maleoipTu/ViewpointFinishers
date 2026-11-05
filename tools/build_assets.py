"""Generate our own AnimSets definitions, referring to clips in the user's game."""
from pathlib import Path
from copy import deepcopy
import xml.etree.ElementTree as ET
from choreography import TIMING

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "ViewpointFinishers/42/media"
PROFILES = {
    "Stomp": ("Bob_AttackFloorStamp", .33, 1.0),
    "Knife": ("Bob_AttackFloorStab", .40, .85),
    "OneHand": ("Bob_AttackFloor1Hand", .25, .85),
    "TwoHand": ("Bob_AttackFloorBat", .35, .80),
    "Heavy": ("Bob_AttackFloor2H_Heavy", .25, .80),
    "Spear": ("Bob_AttackFloorSpear", .40, .85),
    "RifleStomp": ("Bob_AttackFloorStamp_Rifle", .33, 1.0),
    "HandgunStomp": ("Bob_AttackFloorStamp_Hgun", .33, 1.0),
}
PAIRED = TIMING

def add(parent, key, value):
    ET.SubElement(parent, key).text = str(value)

out = MEDIA / "AnimSets/player/actions"
out.mkdir(parents=True, exist_ok=True)
for name, (clip, impact, speed) in PROFILES.items():
    node = ET.Element("animNode")
    for key, value in {
        "m_Name": "VF_"+name, "m_AnimName": clip, "m_Priority": 10,
        "m_Looped": "false", "m_BlendTime": .18, "m_BlendOutTime": .25,
        "m_SpeedScale": speed, "m_SyncTrackingEnabled": "false",
        "m_EarlyTransitionOut": "false",
    }.items():
        add(node,key,value)
    condition = ET.SubElement(node,"m_Conditions")
    for key,value in {"m_Name":"PerformingAction","m_Type":"STRING","m_Value":"VF_"+name}.items():
        add(condition,key,value)
    for event, at in [("VF_Impact",impact),("VF_Finished",.97)]:
        element = ET.SubElement(node,"m_Events")
        add(element,"m_EventName",event)
        add(element,"m_TimePc",at)
    for bone in ["Dummy01","Translation_Data","Bip01"]:
        add(ET.SubElement(node,"m_SubStateBoneWeights"),"boneName",bone)
    ET.indent(node)
    ET.ElementTree(node).write(out/f"VF_{name}.xml",encoding="utf-8",xml_declaration=True)

for kind,(duration,impact) in PAIRED.items():
    for role in ["Player","Victim"]:
        name=f"VF_{role}_{kind}"
        node=ET.Element("animNode")
        for key,value in {"m_Name":name,"m_AnimName":name,"m_ConditionPriority":100,"m_Looped":"false","m_BlendTime":.20,"m_BlendOutTime":.30,"m_EarlyTransitionOut":"false","m_SpeedScale":1,"m_SyncTrackingEnabled":"false","m_randomAdvanceFraction":0}.items():
            add(node,key,value)
        cond=ET.SubElement(node,"m_Conditions")
        for key,value in {"m_Name":"PerformingAction" if role=="Player" else "VF_Pair","m_Type":"STRING","m_Value":name if role=="Player" else kind}.items(): add(cond,key,value)
        if role=="Player":
            for event,at in [("VF_Impact",impact/duration),("VF_Finished",.98)]:
                e=ET.SubElement(node,"m_Events"); add(e,"m_EventName",event); add(e,"m_TimePc",at)
            for bone in ["Dummy01","Translation_Data","Bip01"]:
                add(ET.SubElement(node,"m_SubStateBoneWeights"),"boneName",bone)
            directories=[out]
        else:
            states=["idle","walktoward","walktoward-network"] if kind!="Knife" else ["onground","onground-ragdoll","onground-ragdoll-breathing"]
            directories=[MEDIA/"AnimSets/zombie"/state for state in states]
        ET.indent(node)
        for directory in directories:
            directory.mkdir(parents=True,exist_ok=True)
            ET.ElementTree(node).write(directory/f"{name}.xml",encoding="utf-8",xml_declaration=True)

# Death segments start with the exact contact pose of their paired victim clip.
# Dedicated conditions affect only a zombie actually finished by this addon.
DEATH_STATES=['falldown-speardeath1','falldown-speardeath1-ragdoll','falldown',
              'falldown-ragdoll','falldown-uppercut','falldown-uppercut-ragdoll',
              'hitreaction','hitreaction-ragdoll','hitreaction-onfloor']
for kind in PAIRED:
    node=ET.Element('animNode');name='VF_Death_'+kind
    for key,value in {'m_Name':name,'m_AnimName':name,'m_ConditionPriority':200,
                      'm_Looped':'false','m_BlendTime':.06,'m_BlendOutTime':.08,
                      'm_EarlyTransitionOut':'false','m_SpeedScale':1,
                      'm_SyncTrackingEnabled':'false','m_randomAdvanceFraction':0}.items():add(node,key,value)
    for var,typ,value in [('VF_Death','STRING',kind),('bDead','BOOL','true')]:
        cond=ET.SubElement(node,'m_Conditions')
        for key,val in {'m_Name':var,'m_Type':typ,'m_Value':value}.items():add(cond,key,val)
    for event,at,param in [('SetVariable',0.01,'VF_DeathPlaying=true'),
                           ('FallOnFront',.02,'true' if kind=='Neck' else 'false'),
                           ('PlaySound',.55,'BodyHitGround'),
                           ('SetVariable',.94,'VF_DeathDone=true'),
                           # Proper Ragdolls must release its own pending-death
                           # watcher before PZ returns this zombie to the pool.
                           ('SetVariable',.94,'prdDone=true')]:
        e=ET.SubElement(node,'m_Events')
        for key,value in {'m_EventName':event,'m_TimePc':at,'m_ParameterValue':param}.items():add(e,key,value)
    ET.indent(node)
    for state in DEATH_STATES:
        output=deepcopy(node)
        if state.endswith('-ragdoll') and kind!='Knife':
            # Start from the paired contact pose, then let Bullet own the fall.
            # Start times are seconds, not normalized clip positions.
            for key,value in {'m_isRagdoll':'true','m_ragdollStartTimeMin':.08,
                              'm_ragdollStartTimeMax':.08,
                              'm_DeferredBoneName':'Bip01','m_deferredBoneAxis':'Z'}.items():
                add(output,key,value)
            for event in list(output.findall('m_Events')):
                if event.findtext('m_ParameterValue') in ('VF_DeathDone=true','prdDone=true','BodyHitGround'):
                    output.remove(event)
            ET.indent(output)
        directory=MEDIA/'AnimSets/zombie'/state;directory.mkdir(parents=True,exist_ok=True)
        ET.ElementTree(output).write(directory/f'{name}.xml',encoding='utf-8',xml_declaration=True)

# Proper Ragdolls replaces the stock grounded ragdoll with a posed animation.
# Keep the native simulation running for our standing finishers only.
for kind in PAIRED:
    if kind=='Knife': continue
    node=ET.Element('animNode')
    for key,value in {'m_Name':'VF_Physics_'+kind,'m_ConditionPriority':200,
                      'm_isRagdoll':'true','m_deferredBoneAxis':'Z',
                      'm_BlendTime':.08,'m_SpeedScale':1}.items(): add(node,key,value)
    for var,typ,value in [('VF_Death','STRING',kind),('bDead','BOOL','true')]:
        cond=ET.SubElement(node,'m_Conditions')
        for key,val in {'m_Name':var,'m_Type':typ,'m_Value':value}.items(): add(cond,key,val)
    ET.indent(node)
    directory=MEDIA/'AnimSets/zombie/onground-ragdoll'
    ET.ElementTree(node).write(directory/f'VF_Physics_{kind}.xml',encoding='utf-8',xml_declaration=True)

texts = {
    "EN": {
        "UI": {"NoTarget":"Move closer to a living zombie.","NotReady":"Stand still and finish your current action.","Exhausted":"Too exhausted to finish a zombie.","SinglePlayer":"Finishers currently support single player only."},
        "ContextMenu": {"Stomp":"Finish nearby zombie: stomp","Knife":"Finish nearby zombie: knife","OneHand":"Finish nearby zombie: weapon strike","TwoHand":"Finish nearby zombie: two-handed strike","Heavy":"Finish nearby zombie: heavy strike","Spear":"Finish nearby zombie: spear"},
        "UI_options": {"binding_VF_Finish":"Perform finisher", "binding_[ViewpointFinishers]":"Viewpoint Finishers"},
    },
    "RU": {
        "UI": {"NoTarget":"Подойдите ближе к живому зомби.","NotReady":"Остановитесь и завершите текущее действие.","Exhausted":"Недостаточно выносливости для добивания.","SinglePlayer":"Добивания пока доступны только в одиночной игре."},
        "ContextMenu": {"Stomp":"Добить рядом лежащего зомби: ногой","Knife":"Добить рядом лежащего зомби: ножом","OneHand":"Добить рядом лежащего зомби: оружием","TwoHand":"Добить рядом лежащего зомби: двуручным оружием","Heavy":"Добить рядом лежащего зомби: тяжёлым ударом","Spear":"Добить рядом лежащего зомби: копьём"},
        "UI_options": {"binding_VF_Finish":"Выполнить добивание","binding_[ViewpointFinishers]":"Добивания Viewpoint"},
    },
}
texts["RU"]["UI"]["Side"]="Для захвата подойдите сзади; для подсечки — спереди."
texts["EN"]["UI"]["Side"]="Approach from behind for a neck hold, or from the front for a leg kick."
texts["RU"]["ContextMenu"].update({"Sweep":"Подсечь сзади, придерживая за плечо","Shove":"Сбить с ног толчком в грудь","Neck":"Захват сзади: свернуть шею","Knee":"Ударить по ноге и добить в голову","GroundKnife":"Прижать лежащего и добить ножом"})
texts["EN"]["ContextMenu"].update({"Sweep":"Rear hook sweep","Shove":"Two-palm knockdown","Neck":"Rear neck takedown","Knee":"Leg kick and finishing strike","GroundKnife":"Pin and finish with knife"})
for language, groups in texts.items():
    directory = MEDIA / "lua/shared/Translate" / language
    directory.mkdir(parents=True,exist_ok=True)
    ui = dict(groups["UI"])
    for group, entries in groups.items():
        filegroup = "UI" if group == "UI_options" else group
        if group == "UI_options": continue
        lines = [f"{filegroup}_{language} = {{"]
        lines.extend(f'    {group}_VF_{key} = "{value}",' for key,value in entries.items())
        if group == "UI":
            lines.extend(f'    UI_options_{key} = "{value}",' for key,value in groups["UI_options"].items())
        lines.append("}")
        # Build 42 translation files use UTF-8.
        (directory/f"{filegroup}_{language}.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
print(f"Generated {len(PROFILES)} animation nodes and EN/RU translations")
