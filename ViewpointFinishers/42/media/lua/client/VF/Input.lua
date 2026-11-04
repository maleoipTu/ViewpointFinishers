require "VF/FinishAction"
require "TimedActions/WalkToTimedActionF"
require "keyBinding"

table.insert(keyBinding,{value="[ViewpointFinishers]"})
table.insert(keyBinding,{value="VF_Finish",key=Keyboard.KEY_K})

local function message(p,key)
    if getDebug() then print("[VF] unavailable: "..key) end
    if p then HaloTextHelper.addText(p,getText("UI_VF_"..key)) end
end

function VF.tryFinish(p,target)
    if not p then return end
    if isClient() or isServer() then message(p,"SinglePlayer"); return end
    if VF.active[p] then return end
    if not VF.Rules.playerReady(p) then message(p,"NotReady"); return end
    if #ISTimedActionQueue.getTimedActionQueue(p).queue > 0 then message(p,"NotReady"); return end
    if p:getStats():get(CharacterStat.ENDURANCE) < VF.Rules.minimumEndurance then
        message(p,"Exhausted"); return
    end
    target = target or VF.Rules.closest(p,getCell():getZombieList())
    if not VF.Rules.targetValid(p,target) then message(p,"NoTarget"); return end
    local profile=VF.Rules.selectProfile(p,target)
    if not profile then message(p,"Side"); return end
    if profile.victim and not VF.Rules.aligned(p,target,profile) then
        local x,y=VF.Rules.anchor(target,profile)
        local square=getCell():getGridSquare(math.floor(x),math.floor(y),math.floor(p:getZ()))
        if not square or p:getSquare():isBlockedTo(square) or square:isSolid() or square:isSolidTrans() then
            message(p,"NoTarget"); return
        end
        ISTimedActionQueue.add(ISWalkToTimedActionF:new(p,Vector3f.new(x,y,p:getZ())))
    end
    ISTimedActionQueue.add(VF.FinishAction:new(p,target,profile))
    if getDebug() then print("[VF] queued "..profile.anim) end
end

Events.OnKeyPressed.Add(function(key)
    if key ~= getCore():getKey("VF_Finish") then return end
    if isGamePaused() then return end
    VF.tryFinish(getSpecificPlayer(0))
end)

Events.OnFillWorldObjectContextMenu.Add(function(playerNum,context,worldobjects,test)
    if test or isClient() or isServer() then return end
    local p = getSpecificPlayer(playerNum)
    if not p or not getCell() then return end
    local z = VF.Rules.closest(p,getCell():getZombieList())
    if not z then return end
    local profile = VF.Rules.selectProfile(p,z)
    if not profile then return end
    context:addOption(getText("ContextMenu_VF_"..profile.label),p,VF.tryFinish,z)
end)
