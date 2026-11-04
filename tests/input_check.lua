-- Drive the registered key and menu callbacks with the same front/rear target.
local player={getX=function() return 0 end,getY=function() return 0 end}
local zombie={x=.56,getX=function(z) return z.x end,getY=function() return 0 end,
    getForwardDirectionX=function() return 1 end,getForwardDirectionY=function() return 0 end,
    isOnFloor=function() return false end}
local shifted=false
function isShiftKeyDown() return shifted end
function isGamePaused() return false end
function getCore() return {getKey=function() return Keyboard.KEY_K end} end
function getSpecificPlayer() return player end
function getCell() return {getZombieList=function() return {} end} end
function getText(key) return key end
VF.Rules.closest=function() return zombie end
local invoked={}
VF.tryFinish=function(p,z,alt) invoked={p,z,alt} end
TEST_KEY(Keyboard.KEY_K)
assert(invoked[1]==player and not invoked[3])
shifted=true
TEST_KEY(Keyboard.KEY_K)
assert(invoked[1]==player and invoked[3])
for _,case in ipairs({{.56,'Sweep'},{-.53,'Shove'}}) do
    zombie.x=case[1]
    local options={}
    local menu={addOption=function(_,label,p,callback,z,alt)
        table.insert(options,{label=label,call=function() callback(p,z,alt) end})
    end}
    TEST_MENU(0,menu,{},false)
    assert(#options==2 and options[2].label=='ContextMenu_VF_'..case[2])
    options[2].call()
    assert(invoked[1]==player and invoked[2]==zombie and invoked[3]==true)
end
