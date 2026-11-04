local passed=0
local function check(condition,message)
    assert(condition,message)
    passed=passed+1
end
local function square(blocked)
    return {isBlockedTo=function() return blocked end,isSomethingTo=function() return blocked end}
end
local function actor(x,y)
    local a={x=x,y=y,z=0,alive=true,floor=false,state="onground",square=square(false),timer=17,useless=false,held=nil,health=100,endurance=1,hits=0}
    function a:getX() return self.x end
    function a:getY() return self.y end
    function a:getZ() return self.z end
    function a:getSquare() return self.square end
    function a:isAlive() return self.alive end
    function a:isOnFloor() return self.floor end
    function a:isUnderVehicle() return false end
    function a:isCrawling() return self.crawler end
    function a:isFallOnFront() return false end
    function a:getForwardDirectionX() return 1 end
    function a:getForwardDirectionY() return 0 end
    function a:getStateMachine() return {isLocked=function() return self.stateLocked or false end} end
    function a:setStateMachineLocked(value) self.stateLocked=value end
    function a:setVariable(k,v) self[k]=v end
    function a:clearVariable(k) self[k]=nil end
    function a:getActionStateName() return self.state end
    function a:getVehicle() return nil end
    function a:isSitting() return false end
    function a:isClimbing() return false end
    function a:isAttacking() return false end
    function a:hasHitReaction() return false end
    function a:isMoving() return self.moving end
    function a:getPrimaryHandItem() return self.held end
    function a:getSecondaryHandItem() return nil end
    function a:getBodyDamage() return {getOverallBodyHealth=function() return self.health end} end
    function a:getStats()
        return {get=function() return self.endurance end,remove=function(_,stat,cost) self.endurance=self.endurance-cost end}
    end
    function a:isUseless() return self.useless end
    function a:isAlwaysKnockedDown() return self.alwaysDown or false end
    function a:setAlwaysKnockedDown(value) self.alwaysDown=value end
    function a:setUseless(value) self.useless=value end
    function a:getReanimateTimer() return self.timer end
    function a:setReanimateTimer(value) self.timer=value end
    function a:faceThisObject() end
    function a:shouldBeTurning() return false end
    function a:setHitHeadWhileOnFloor() end
    function a:setHitLegsWhileOnFloor() end
    function a:getHitReaction() return self.hitReaction or "" end
    function a:setHitReaction(v) self.hitReaction=v end
    function a:getVariableBoolean(k) return self[k]==true or self[k]=="true" end
    function a:getVariableString(k) return tostring(self[k] or "") end
    function a:setRagdollFall(v) self.ragdoll=v end
    function a:Hit(w,p,damage) self.hits=self.hits+1; self.alive=false; self.damage=damage end
    return a
end
local function pair()
    TEST_TIME=1000
    local p,z=actor(0,0),actor(.8,0)
    z.floor=true
    return p,z
end
local p,z=pair()
check(VF.Rules.targetValid(p,z),"fallen living nearby target")
z.floor=false; check(not VF.Rules.targetValid(p,z),"standing target rejected"); z.floor=true
z.z=1; check(not VF.Rules.targetValid(p,z),"other floor rejected"); z.z=0
z.alive=false; check(not VF.Rules.targetValid(p,z),"corpse rejected"); z.alive=true
z.x=1.26; check(not VF.Rules.targetValid(p,z),"out of reach rejected"); z.x=.8
p.square=square(true); check(not VF.Rules.targetValid(p,z),"wall rejected"); p.square=square(false)
z.state="getup"; check(not VF.Rules.targetValid(p,z),"getting up rejected"); z.state="onground"
z.crawler=true; check(not VF.Rules.targetValid(p,z),"crawler rejected"); z.crawler=false
local a=VF.FinishAction:new(p,z)
a:start()
check(z.useless and z.timer==120,"target held only after start")
check(p.endurance==.955,"stomp endurance charged once")
check(z.hits==0,"windup does not deal damage")
a:animEvent("VF_Impact","")
a:animEvent("VF_Impact","")
check(z.hits==1,"duplicate blended event cannot double hit")
check(not z.useless,"target flag restored at impact")
check(a:isValid(),"dead target does not interrupt recovery")
a:animEvent("VF_Finished","")
check(a.completed and not VF.active[p],"recovery releases action")
p,z=pair(); a=VF.FinishAction:new(p,z); a:start(); a:stop()
check(z.hits==0 and z.timer==17 and not z.useless and not z.alwaysDown,"cancel before impact restores zombie")
a:animEvent("VF_Impact",""); check(z.hits==0,"late event after cancel ignored")
p,z=pair(); z.useless=true; a=VF.FinishAction:new(p,z); a:start(); a:stop()
check(z.useless,"preexisting useless flag preserved")
p,z=pair(); a=VF.FinishAction:new(p,z); a:start(); z.x=3; a:animEvent("VF_Impact","")
check(a.stopped and z.hits==0,"range rechecked on impact")
p,z=pair(); a=VF.FinishAction:new(p,z); a:start(); p.health=99; a:update()
check(a.stopped and z.hits==0 and not z.useless,"injury interrupts and releases")
p,z=pair(); a=VF.FinishAction:new(p,z); a:start(); TEST_TIME=10000; a:update()
check(a.stopped and not z.useless,"missing animation event watchdog releases")
p,z=pair(); p.endurance=.1; a=VF.FinishAction:new(p,z)
check(not a:isValid(),"exhaustion blocks start")
function isClient() return true end
p,z=pair(); a=VF.FinishAction:new(p,z); check(not a:isValid(),"MP mutation blocked")
function isClient() return false end
local weapon={weapon=true,isBroken=function() return false end,getSwingAnim=function() return "Stab" end,isRanged=function() return false end,isTwoHandWeapon=function() return false end}
check(VF.Rules.profile(weapon)==VF.Rules.profiles.knife,"knife profile")
p,z=pair(); z.floor=false; z.state="idle"; p.x=z.x-.65
check(VF.Rules.selectProfile(p,z)==VF.Rules.profiles.neck,"rear neck selection")
a=VF.FinishAction:new(p,z); a:start()
check(a.started and z.useless and z.VF_Pair=="Neck","paired victim starts restrained and synchronized")
a:stop(); check(not z.useless and not z.VF_Pair,"paired cancellation clears animation and AI restraint")
p.x=z.x+.72
check(VF.Rules.selectProfile(p,z)==VF.Rules.profiles.knee,"front leg kick selection")
p.x=z.x; p.y=z.y+.72
check(VF.Rules.selectProfile(p,z)==nil,"side angle is rejected")
p,z=pair();z.floor=false;z.state="idle";p.x=z.x-.65
a=VF.FinishAction:new(p,z);a:start();a:animEvent("VF_Impact","")
check(z.VF_Death=="Neck" and z.hitReaction=="HitSpearDeath1","paired impact selects continuous death")
z.VF_DeathDone="true";z.state="falldown-speardeath1";TEST_TICK()
check(z.ragdoll and VF.deaths[z].posed,"resting pose preserved for native corpse")
z.square=nil;TEST_TICK()
check(not VF.deaths[z] and not z.VF_Death and z.hitReaction=="","death reaction cleared before pooled zombie is reused")
for _,case in ipairs({{"sweep",-.56},{"shove",.53}}) do
    p,z=pair(); z.floor=false; z.state="idle"; p.x=z.x+case[2]
    local profile=VF.Rules.selectProfile(p,z,true)
    check(profile==VF.Rules.profiles[case[1]] and VF.Rules.aligned(p,z,profile),"alternate selection and anchor")
    a=VF.FinishAction:new(p,z,profile); a:start()
    check(a.started and z.VF_Pair==profile.victim,"alternate pair synchronized")
    a:animEvent("VF_Impact",""); a:animEvent("VF_Impact",""); a:animEvent("VF_Finished","")
    check(z.hits==1 and z.VF_Death==profile.victim and not VF.active[p],"one impact and clean recovery")
end
print("BEHAVIOR TESTS: "..passed.." passed")
