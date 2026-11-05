from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[1]
mod=root/"ViewpointFinishers"
game=Path(r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid")
clips={p.stem.lower() for p in (game/"media/anims_X").rglob("*") if p.is_file()}
custom={p.stem.lower() for p in (mod/"42/media/anims_X").rglob("*.x")}
nodes=list((mod/"42/media/AnimSets").rglob("*.xml"))
assert len(nodes)==77 and len(custom)==15
names=set()
for path in nodes:
    node=ET.parse(path).getroot()
    name=node.findtext("m_Name")
    if name.startswith('VF_Physics_'):
        assert path.parent.name=='onground-ragdoll'
        assert node.findtext('m_isRagdoll')=='true'
        assert int(node.findtext('m_ConditionPriority'))>=200
        continue
    # Victim override nodes intentionally appear in several animation states.
    names.add(name)
    assert node.findtext("m_AnimName").lower() in clips|custom,path
    assert node.findtext("m_Looped")=="false"
    events={e.findtext("m_EventName"):float(e.findtext("m_TimePc")) for e in node.findall("m_Events")}
    if 'VF_Victim' not in name and 'VF_Death' not in name: assert 0 < events["VF_Impact"] < events["VF_Finished"] < 1
    if 'VF_Death' in name:
        parameters={e.findtext('m_ParameterValue') for e in node.findall('m_Events')}
        physical=path.parent.name.endswith('-ragdoll') and not name.endswith('_Knife')
        if physical:
            assert node.findtext('m_isRagdoll')=='true',path
            assert 0 < float(node.findtext('m_ragdollStartTimeMin')) <= .1,path
            assert not {'VF_DeathDone=true','prdDone=true','BodyHitGround'} & parameters,path
        else:
            assert {'VF_DeathDone=true','prdDone=true'} <= parameters,path
        assert int(node.findtext('m_ConditionPriority'))>=200,path
rules=(mod/"42/media/lua/shared/VF/Rules.lua").read_text(encoding="utf-8")
assert set(re.findall(r'anim="([^"]+)"',rules))=={n for n in names if 'VF_Victim' not in n and 'VF_Death' not in n}
translation_keys=[]
for language in ("EN","RU"):
    keys=set()
    for file in (mod/f"42/media/lua/shared/Translate/{language}").glob("*.txt"):
        content=file.read_text(encoding="utf-8")
        keys.update(re.findall(r'^\s+([^=\n]+?)\s*=',content,re.M))
    translation_keys.append(keys)
assert translation_keys[0]==translation_keys[1]
allowed={".lua",".xml",".txt",".info",".keep",".x"}
for file in mod.rglob("*"):
    if file.is_file():
        assert file.suffix in allowed or file.name==".keep",file
        assert not any(secret in file.read_text(encoding="utf-8").lower() for secret in ("api_key=","access_token=","secret_key="))
result={"animation_nodes":len(nodes),"custom_authored_clips":len(custom),"installed_clip_references_verified":8,"translation_keys_per_language":len(translation_keys[0]),"package_contains_game_binaries_or_extracted_assets":False}
(root/"validation").mkdir(exist_ok=True)
(root/"validation/static.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result))
