require "TimedActions/ISBaseTimedAction"
require "TimedActions/ISTimedActionQueue"
require "VF/Rules"

VF.FinishAction = ISBaseTimedAction:derive("VFFinishAction")
local A = VF.FinishAction
VF.active = VF.active or {}
VF.deaths = VF.deaths or {}

function A:isValid()
    local p = self.character
    if isClient() or isServer() or not VF.Rules.playerReady(p,true) then return false end
    if p:getPrimaryHandItem() ~= self.held then return false end
    if self.started and p:getBodyDamage():getOverallBodyHealth() < self.healthAtStart then return false end
    if self.struck then return true end -- let recovery play after the body is removed
    return VF.Rules.targetValid(p,self.target)
        and VF.Rules.aligned(p,self.target,self.profile)
        and (self.started or VF.Rules.selectProfile(p,self.target)==self.profile
            or VF.Rules.selectProfile(p,self.target,true)==self.profile)
        and p:getStats():get(CharacterStat.ENDURANCE) >= (self.started and 0 or VF.Rules.minimumEndurance)
end

function A:waitToStart()
    if not self:isValid() then return false end
    self.character:faceThisObject(self.target)
    return self.character:shouldBeTurning()
end

function A:start()
    if not self:isValid() then self:forceStop(); return end
    self.started = true
    self.startMs = getTimestampMs()
    self.healthAtStart = self.character:getBodyDamage():getOverallBodyHealth()
    self.wasUseless = self.target:isUseless()
    self.oldTimer = self.target:getReanimateTimer()
    self.wasAlwaysDown = self.target:isAlwaysKnockedDown()
    self.oldHitReaction = self.target:getHitReaction() or ""
    self.locked = true
    self.target:setUseless(true)
    if self.target:isOnFloor() then self.target:setAlwaysKnockedDown(true) end
    if self.profile.victim then
        self.target:setVariable("VF_Pair",self.profile.victim)
    end
    self.target:setReanimateTimer(120)
    VF.active[self.character] = self
    self.character:getStats():remove(CharacterStat.ENDURANCE,self.profile.cost)
    self:setActionAnim(self.profile.anim)
    if self.profile.bareHands or self.profile == VF.Rules.profiles.stomp or self.profile == VF.Rules.profiles.neck or self.profile == VF.Rules.profiles.knee then
        self:setOverrideHandModels(nil,nil)
    else
        self:setOverrideHandModels(self.held,self.character:getSecondaryHandItem())
    end
    print("[VF] start "..self.profile.anim)
end

function A:update()
    if self.closed then return end
    if not self:isValid() or getTimestampMs()-self.startMs > 8000 then
        self:forceStop()
        return
    end
    if not self.struck then
        self.character:faceThisObject(self.target)
        self.target:setReanimateTimer(120)
    end
end

function A:releaseTarget()
    if not self.locked then return end
    self.locked = false
    self.target:setUseless(self.wasUseless)
    self.target:setAlwaysKnockedDown(self.wasAlwaysDown)
    self.target:clearVariable("VF_Pair")
    if self.target:isAlive() then self.target:setReanimateTimer(self.oldTimer) end
end

function A:cleanup()
    if self.closed then return end
    self.closed = true
    self:releaseTarget()
    if VF.active[self.character] == self then VF.active[self.character] = nil end
end

function A:animEvent(event, parameter)
    if not self.started or self.closed then return end
    if event == "VF_Impact" and not self.struck then
        if not self:isValid() then self:forceStop(); return end
        self.struck = true -- event can be delivered twice during blending
        self:releaseTarget()
        if self.profile.victim then
            self.target:setVariable("VF_Death",self.profile.victim)
            self.target:clearVariable("VF_DeathDone")
            self.target:clearVariable("VF_DeathPlaying")
        end
        local weapon = self.held
        if self.profile.bareHands or self.profile == VF.Rules.profiles.stomp or self.profile == VF.Rules.profiles.rifle
            or self.profile == VF.Rules.profiles.handgun or self.profile == VF.Rules.profiles.neck or self.profile == VF.Rules.profiles.knee then
            weapon = instanceItem("Base.BareHands")
        end
        -- Native hit pipeline dispatches OnHitZombie and handles attribution/death.
        -- In particular, do not delete the zombie or create an IsoDeadBody here.
        self.target:setHitHeadWhileOnFloor(1)
        self.target:setHitLegsWhileOnFloor(false)
        self.target:setHitReaction(self.profile==VF.Rules.profiles.neck and "Uppercut" or "Floor")
        self.target:Hit(weapon,self.character,1000,false,1,false)
        if self.profile.victim then
            if not self.target:isOnFloor() then self.target:setHitReaction("HitSpearDeath1") end
            VF.deaths[self.target]={start=getTimestampMs(),posed=false,
                forced=not self.target:isOnFloor(),oldReaction=self.oldHitReaction}
        end
        print("[VF] impact "..self.profile.anim.." alive="..tostring(self.target:isAlive()))
    elseif event == "VF_Finished" then
        if self.struck then self:forceComplete() else self:forceStop() end
    end
end

function A:stop()
    self:cleanup()
    print("[VF] cancelled")
    ISBaseTimedAction.stop(self)
end

function A:perform()
    self:cleanup()
    print("[VF] finished")
    ISBaseTimedAction.perform(self)
end

function A:forceCancel() self:cleanup() end
function A:getDuration() return -1 end
function A:complete() return true end

function A:new(character,target,profile)
    local o = ISBaseTimedAction.new(self,character)
    o.target = target
    o.held = character:getPrimaryHandItem()
    o.profile = profile or VF.Rules.selectProfile(character,target) or VF.Rules.profile(o.held)
    o.maxTime = -1
    o.stopOnWalk, o.stopOnRun, o.stopOnAim = true,true,true
    return o
end

Events.OnPlayerDeath.Add(function(p)
    local action = VF.active[p]
    if action then action:cleanup() end
end)

-- Keep the authored resting pose when the native state creates its corpse.
-- This also works without Proper Ragdolls and never constructs a corpse itself.
Events.OnTick.Add(function()
    for zombie,entry in pairs(VF.deaths) do
        if zombie:isAlive() or not zombie:getSquare() or getTimestampMs()-entry.start>8000 then
            -- PZ reuses zombie objects. Our forced death reaction must not survive
            -- into the next spawn (a later knockdown would otherwise kill it).
            if entry.forced and zombie:getHitReaction()=="HitSpearDeath1" then
                zombie:setHitReaction(entry.oldReaction)
            end
            if entry.posed and zombie:isAlive() then zombie:setRagdollFall(false) end
            zombie:clearVariable("VF_Death")
            zombie:clearVariable("VF_DeathDone")
            zombie:clearVariable("VF_DeathPlaying")
            VF.deaths[zombie]=nil
        elseif not entry.posed and zombie:getVariableBoolean("VF_DeathDone") then
            if zombie:getActionStateName()~="falldown" then zombie:setRagdollFall(true) end
            entry.posed=true
            print("[VF] resting pose "..zombie:getVariableString("VF_Death"))
        end
    end
end)
