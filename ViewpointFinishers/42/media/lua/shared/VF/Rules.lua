VF = VF or {}
VF.Rules = {}
local R = VF.Rules
R.range = 1.25
R.minimumEndurance = 0.12
R.profiles = {
    sweep = {anim="VF_Player_Sweep",victim="Sweep",cost=0.08,label="Sweep",distance=0.56,bareHands=true},
    shove = {anim="VF_Player_Shove",victim="Shove",cost=0.08,label="Shove",distance=0.53,bareHands=true,front=true},
    neck = {anim="VF_Player_Neck",victim="Neck",cost=0.07,label="Neck",distance=0.65},
    knee = {anim="VF_Player_Knee",victim="Knee",cost=0.09,label="Knee",distance=0.72},
    groundknife = {anim="VF_Player_Knife",victim="Knife",cost=0.055,label="GroundKnife",distance=1.0},
    stomp = {anim="VF_Stomp", cost=0.045, label="Stomp"},
    knife = {anim="VF_Knife", cost=0.025, label="Knife"},
    onehand = {anim="VF_OneHand", cost=0.035, label="OneHand"},
    twohand = {anim="VF_TwoHand", cost=0.050, label="TwoHand"},
    heavy = {anim="VF_Heavy", cost=0.065, label="Heavy"},
    spear = {anim="VF_Spear", cost=0.040, label="Spear"},
    rifle = {anim="VF_RifleStomp", cost=0.045, label="Stomp"},
    handgun = {anim="VF_HandgunStomp", cost=0.045, label="Stomp"},
}

function R.profile(weapon)
    if not weapon or not instanceof(weapon, "HandWeapon") or weapon:isBroken() then
        return R.profiles.stomp
    end
    local swing = string.lower(tostring(weapon:getSwingAnim() or ""))
    if weapon:isRanged() then
        return weapon:isTwoHandWeapon() and R.profiles.rifle or R.profiles.handgun
    end
    if swing == "stab" then return R.profiles.knife end
    if swing == "spear" then return R.profiles.spear end
    if swing == "heavy" then return R.profiles.heavy end
    if weapon:isTwoHandWeapon() then return R.profiles.twohand end
    return R.profiles.onehand
end

function R.distanceSquared(a, b)
    local x, y = a:getX()-b:getX(), a:getY()-b:getY()
    return x*x+y*y
end

function R.playerReady(p,allowPathMotion)
    return p and p:isAlive() and not p:getVehicle() and not p:isSitting()
        and not p:isOnFloor() and not p:isClimbing() and not p:isAttacking()
        and not p:hasHitReaction() and (allowPathMotion or not p:isMoving())
end

-- Recheck on selection, start and impact. Never hit through an edge or a corner.
function R.targetValid(p, z)
    if not z or not z:isAlive() or z:isUnderVehicle() then return false end
    if z:isCrawling() then return false end
    if math.abs(p:getZ()-z:getZ()) > 0.1 then return false end
    if R.distanceSquared(p,z) > R.range*R.range then return false end
    local a, b = p:getSquare(), z:getSquare()
    if not a or not b then return false end
    if a ~= b and (a:isSomethingTo(b) or a:isBlockedTo(b)) then return false end
    local state = z:getActionStateName()
    if z:isOnFloor() then
        return state == "onground" or state == "onground-ragdoll" or state == "onground-ragdoll-breathing"
    end
    return state == "idle" or state == "walktoward" or state == "walktoward-network"
end

function R.relativeSide(p,z)
    local dx,dy=p:getX()-z:getX(),p:getY()-z:getY()
    local length=math.sqrt(dx*dx+dy*dy)
    if length<0.01 then return 0 end
    return (dx*z:getForwardDirectionX()+dy*z:getForwardDirectionY())/length
end

function R.selectProfile(p,z,alternate)
    if not z:isOnFloor() then
        local side=R.relativeSide(p,z)
        if side < -0.45 then return alternate and R.profiles.sweep or R.profiles.neck end
        if side > 0.45 then return alternate and R.profiles.shove or R.profiles.knee end
        return nil
    end
    if alternate then return nil end
    local profile=R.profile(p:getPrimaryHandItem())
    if profile==R.profiles.knife and not z:isFallOnFront() then return R.profiles.groundknife end
    return profile
end

function R.anchor(z,profile)
    local sign=(profile==R.profiles.knee or profile.front) and 1 or -1
    return z:getX()+z:getForwardDirectionX()*profile.distance*sign,
           z:getY()+z:getForwardDirectionY()*profile.distance*sign
end

function R.aligned(p,z,profile)
    if not profile.victim then return true end
    local x,y=R.anchor(z,profile)
    return (p:getX()-x)^2+(p:getY()-y)^2<0.22^2
end

function R.closest(p, zombies)
    local best, bestDistance = nil, math.huge
    for i=0,zombies:size()-1 do
        local z = zombies:get(i)
        if R.targetValid(p,z) then
            local d = R.distanceSquared(p,z)
            if d < bestDistance then best,bestDistance=z,d end
        end
    end
    return best
end
