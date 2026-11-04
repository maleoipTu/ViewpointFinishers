param([string]$ZomboidProfile=(Join-Path $env:USERPROFILE 'Zomboid'))
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'ViewpointFinishers'
$mods=Join-Path $ZomboidProfile 'mods'
$destination=Join-Path $mods 'ViewpointFinishers'
if (!(Test-Path -LiteralPath "$source\42\mod.info")) { throw 'Mod source is missing.' }
if(Test-Path -LiteralPath $destination) {
    $backup=Join-Path $PSScriptRoot ('backups\ViewpointFinishers-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
    Copy-Item -LiteralPath $destination -Destination $backup -Recurse
    Write-Output "Previous addon backed up: $backup"
}
New-Item -ItemType Directory -Path $mods -Force | Out-Null
Copy-Item -LiteralPath $source -Destination $mods -Recurse -Force
foreach($file in Get-ChildItem -LiteralPath $source -Recurse -File) {
    $relative=$file.FullName.Substring($source.Length+1)
    if((Get-FileHash -LiteralPath $file.FullName).Hash -ne (Get-FileHash -LiteralPath (Join-Path $destination $relative)).Hash) { throw "Copy verification failed: $relative" }
}
Write-Output "Installed and verified: $destination"
Write-Output 'Enable Viewpoint Finishers in the in-game mod menu. Existing save configuration was not changed.'
