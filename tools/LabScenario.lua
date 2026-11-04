-- Development-only original choreography verification. Never shipped in the mod.
require "VF/Input"
local tick,started=0,false
local runRequested=false
local caseIndex,phase,victim,deadline=0,"waiting",nil,180
local cases={"Neck","Knee","Knife"}
local lastVictimState=nil
local scenario={
 name="VF paired choreography verification",
 startLoc={x=10649,y=10635,z=0},
 setSandbox=function() SandboxVars.Zombies=6; SandboxVars.StartTime=2 end,
 onStart=function()
  started=true
  getCore():setOptionShowSurvivalGuide(false)
  print("[VF-LAB] paired world started")
 end,
}
Events.OnMainMenuEnter.Add(function()
 if not DebugScenarios.instance then doDebugScenarios() end
 DebugScenarios.instance:launchScenario(scenario)
end)
Events.OnTick.Add(function()
 if not started then return end
 tick=tick+1
 local p=getPlayer()
 if tick==5 then
  if ISCharacterInfoWindow.instance then ISCharacterInfoWindow.instance:setVisible(false) end
  if UIManager.getDebugConsole() then UIManager.getDebugConsole():setVisible(false) end
 end
 if (tick==10 or tick==30) and Viewpoint and Viewpoint.View and Viewpoint.View.next()~="isometric" then
  Viewpoint.View.cycle()
 end
 if not runRequested then
  if tick%30==0 then
   local file=getFileReader("vf-run.txt",false)
   if file then file:close(); runRequested=true; deadline=tick+180; print("[VF-LAB] capture trigger received") end
  end
  return
 end
 if phase=="waiting" and tick>=deadline then
  caseIndex=caseIndex+1
  if not cases[caseIndex] then phase="done"; print("[VF-LAB] ALL CASES FINISHED"); return end
  p:setPrimaryHandItem(nil); p:setSecondaryHandItem(nil)
  if cases[caseIndex]=="Knife" then p:setPrimaryHandItem(p:getInventory():AddItem("Base.HuntingKnife")) end
  p:getStats():set(CharacterStat.ENDURANCE,1)
  local spawned=addZombiesInOutfit(math.floor(p:getX())+1,math.floor(p:getY()),0,1,"Generic01",50,false,false,false,false,false,false,1,false,0,false,false)
  if not spawned or spawned:size()==0 then print("[VF-LAB] SPAWN FAILED"); phase="done"; return end
  victim=spawned:get(0)
  lastVictimState=nil
  local distance=cases[caseIndex]=="Neck" and .65 or (cases[caseIndex]=="Knee" and .72 or 1.0)
  victim:setX(p:getX()+distance); victim:setY(p:getY())
  victim:setForwardDirection(cases[caseIndex]=="Knee" and -1 or 1,0)
  victim:setDirectionAngle(cases[caseIndex]=="Knee" and 180 or 0)
  victim:setUseless(true)
  if cases[caseIndex]=="Knife" then
   victim:setFallOnFront(false); victim:setAlwaysKnockedDown(true); victim:knockDown(false)
  end
  phase="prepare"; deadline=tick+180
  print("[VF-LAB] case="..cases[caseIndex].." spawned alive="..tostring(victim:isAlive()))
 elseif phase=="prepare" and tick>=deadline then
  local profile=VF.Rules.selectProfile(p,victim)
  print("[VF-LAB] case="..cases[caseIndex].." selected="..tostring(profile and profile.anim).." valid="..tostring(VF.Rules.targetValid(p,victim)).." state="..victim:getActionStateName())
  if not victim:isAlive() then print("[VF-LAB] FAIL: target died before test"); phase="done"; return end
  if cases[caseIndex]=="Knife" and not VF.Rules.targetValid(p,victim) then deadline=tick+120; return end
  VF.tryFinish(p,victim)
  phase="verify"; deadline=tick+600
 elseif phase=="verify" and tick>=deadline then
  print("[VF-LAB] RESULT "..cases[caseIndex].." alive="..tostring(victim:isAlive()).." active="..tostring(VF.active[p]~=nil))
  phase="waiting"; deadline=tick+120
 end
 if victim and phase=="verify" then
  local st=victim:getActionStateName()
  if st~=lastVictimState then
   lastVictimState=st
   print("[VF-LAB] state="..st.." death="..tostring(victim:getVariableString("VF_Death")).." playing="..tostring(victim:getVariableBoolean("VF_DeathPlaying")))
  end
 end
end)
