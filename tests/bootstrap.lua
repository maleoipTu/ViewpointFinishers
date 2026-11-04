function require() end
function isClient() return false end
function isServer() return false end
function instanceof(w,name) return w.weapon == true end
function getTimestampMs() return TEST_TIME or 1000 end
function instanceItem(name) return {itemType=name} end
CharacterStat = {ENDURANCE="endurance"}
Events = {OnPlayerDeath={Add=function() end},OnTick={Add=function(f) TEST_TICK=f end}}
keyBinding={}
Keyboard={KEY_K=37}
Events.OnKeyPressed={Add=function(f) TEST_KEY=f end}
Events.OnFillWorldObjectContextMenu={Add=function(f) TEST_MENU=f end}
ISBaseTimedAction = {}
function ISBaseTimedAction:derive(name)
    local o = {Type=name}
    setmetatable(o,{__index=self})
    return o
end
function ISBaseTimedAction:new(p)
    local o = {character=p}
    setmetatable(o,{__index=self})
    return o
end
function ISBaseTimedAction:setActionAnim(a) self.animation=a end
function ISBaseTimedAction:setOverrideHandModels() end
function ISBaseTimedAction:forceStop() self:stop() end
function ISBaseTimedAction:forceComplete() self:perform() end
function ISBaseTimedAction:stop() self.stopped=true end
function ISBaseTimedAction:perform() self.completed=true end
