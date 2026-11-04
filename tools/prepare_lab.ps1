param([string]$GamePath='C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid')
$ErrorActionPreference='Stop'
$workspace=Split-Path -Parent $PSScriptRoot
$profile=Join-Path $workspace '.lab\profile'
New-Item -ItemType Directory -Path "$profile\mods\VFLab\common","$profile\mods\VFLab\42\media\lua\client" -Force | Out-Null
'Isolated development profile: preserve enabled mods.' | Set-Content -LiteralPath "$profile\mods\reset-mods-42_00.txt"
Copy-Item -LiteralPath "$workspace\ViewpointFinishers" -Destination "$profile\mods" -Recurse -Force
Copy-Item -LiteralPath "$PSScriptRoot\LabScenario.lua" -Destination "$profile\mods\VFLab\42\media\lua\client\VFLab.lua" -Force
@'
name=VF Lab (development only)
id=VFLab
require=ViewpointFinishers
'@ | Set-Content -LiteralPath "$profile\mods\VFLab\42\mod.info" -Encoding utf8
@'
VERSION = 1,
mods
{
    mod = ViewpointFinishers,
    mod = VFLab,
    mod = ProperRagdolls,
    mod = ZombieBuddy,
    mod = Viewpoint,
}
maps
{
}
'@ | Set-Content -LiteralPath "$profile\mods\default.txt" -Encoding utf8
if (!(Test-Path -LiteralPath "$profile\options.ini")) {
@'
version=8
width=1280
height=720
fullScreen=false
borderless=false
language=EN
zoom=true
soundVolume=0
musicVolume=0
showFirstTimeSneakTutorial=false
'@ | Set-Content -LiteralPath "$profile\options.ini" -Encoding utf8
}
Write-Output "Prepared isolated profile: $profile"
