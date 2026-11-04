param([string]$GamePath='C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid')
$ErrorActionPreference='Stop'
$workspace=Split-Path -Parent $PSScriptRoot
$classes=Join-Path $workspace '.lab\classes'
New-Item -ItemType Directory -Path $classes -Force | Out-Null
& 'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot\bin\javac.exe' -d $classes "$workspace\tests\LuaCheck.java"
if($LASTEXITCODE -ne 0) { throw 'Harness compilation failed' }
Push-Location $GamePath
try {
    & "$GamePath\jre64\bin\java.exe" '-Dfile.encoding=UTF-8' '-Dstdout.encoding=UTF-8' -cp "$classes;$GamePath\projectzomboid.jar" LuaCheck "$workspace\tests\bootstrap.lua" "$workspace\ViewpointFinishers\42\media\lua\shared\VF\Rules.lua" "$workspace\ViewpointFinishers\42\media\lua\client\VF\FinishAction.lua" "$workspace\tests\behavior.lua"
    if($LASTEXITCODE -ne 0) { throw 'Lua behavior tests failed' }
} finally { Pop-Location }
& 'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot\bin\javac.exe' -d $classes "$workspace\tests\InspectAnimation.java"
if($LASTEXITCODE -ne 0) { throw 'Animation harness compilation failed' }
$clips=Get-ChildItem -LiteralPath "$workspace\ViewpointFinishers\42\media\anims_X\Bob" -Filter '*.x' | ForEach-Object { $_.FullName }
& "$GamePath\jre64\bin\java.exe" --enable-native-access=ALL-UNNAMED "-Djava.library.path=$GamePath" -cp "$classes;$GamePath\projectzomboid.jar" InspectAnimation @clips
if($LASTEXITCODE -ne 0) { throw 'Native animation import failed' }
