param([string]$GamePath='C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid')
$ErrorActionPreference='Stop'
$workspace=Split-Path -Parent $PSScriptRoot
$lab=Join-Path $workspace '.lab'
$profile=Join-Path $lab 'profile'
& "$PSScriptRoot\prepare_lab.ps1" -GamePath $GamePath
$launchArgs=@('-agentlib:zbNative','-Djava.awt.headless=true','--enable-native-access=ALL-UNNAMED','--add-exports=java.base/jdk.internal.misc=ALL-UNNAMED','-Xmx3072m','-Dzomboid.steam=1','-Dzomboid.znetlog=1','-Djava.library.path=win64/;.','-XX:-CreateCoredumpOnCrash','-cp','projectzomboid.jar','zombie.gameStates.MainScreenState','-debug',('-cachedir="'+$profile+'"'))
$p=Start-Process -FilePath "$GamePath\jre64\bin\java.exe" -ArgumentList $launchArgs -WorkingDirectory $GamePath -WindowStyle Hidden -RedirectStandardOutput "$lab\launch.stdout.log" -RedirectStandardError "$lab\launch.stderr.log" -PassThru
$p.Id | Set-Content -LiteralPath "$lab\game.pid"
Write-Output "Lab PID: $($p.Id)"
