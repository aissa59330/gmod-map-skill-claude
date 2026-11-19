# Bench en charge (LOCAL UNIQUEMENT) : serveur d'écoute 128 places, 89 bots qui bougent, mesures serveur + client.
# Usage : tools\bench.ps1 -Tag ref
# Résultats : logs\bench_<Tag>\bench_server.txt, bench_client.txt, console.log
param(
    [Parameter(Mandatory = $true)][string]$Tag,
    [string]$GMod = "C:\Program Files (x86)\Steam\steamapps\common\GarrysMod",
    [int]$Timeout = 1700
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$AddonSrc = Join-Path $Root "addons\givre_noir_bench"
$AddonDst = Join-Path $GMod "garrysmod\addons\givre_noir_bench"
$Data = Join-Path $GMod "garrysmod\data\givre_noir_bench"
$Out = Join-Path $Root "logs\bench_$Tag"

if (Get-Process gmod, hl2 -ErrorAction SilentlyContinue) { Write-Host "Garry's Mod est deja ouvert : ferme-le avant le bench."; exit 3 }
New-Item -ItemType Directory -Force $Out | Out-Null
if (Test-Path $Data) { Remove-Item $Data -Recurse -Force }
if (Test-Path $AddonDst) { Remove-Item $AddonDst -Recurse -Force }
Copy-Item $AddonSrc $AddonDst -Recurse
# mêmes points que la tournée caméra
New-Item -ItemType Directory -Force (Join-Path $AddonDst "lua\givre_noir_bench") | Out-Null
Copy-Item (Join-Path $Root "addons\givre_noir_devtour\lua\givre_noir_devtour\points.lua") (Join-Path $AddonDst "lua\givre_noir_bench\points.lua")
$conlog = Join-Path $GMod "garrysmod\console.log"
$conBefore = if (Test-Path $conlog) { (Get-Item $conlog).Length } else { 0 }
$start = Get-Date
try {
    # sv_lan 1 : serveur d'écoute invisible depuis Internet (bench local uniquement)
    $gargs = "-condebug -novid -windowed -w 1920 -h 1080 -nojoy +sv_lan 1 +maxplayers 128 +engine_no_focus_sleep 0 +fps_max 0 +map givre_noir"
    Start-Process -FilePath (Join-Path $GMod "gmod.exe") -ArgumentList $gargs | Out-Null
    $deadline = $start.AddSeconds($Timeout)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 5
        if (Test-Path (Join-Path $Data "done.txt")) { Start-Sleep -Seconds 2; break }
    }
} finally {
    foreach ($pass in 1..2) {
        Get-Process gmod, hl2 -ErrorAction SilentlyContinue | Where-Object { $_.StartTime -ge $start.AddSeconds(-5) } | Stop-Process -Force
        Start-Sleep -Seconds 4
    }
    if (Test-Path $Data) { Copy-Item (Join-Path $Data "*") $Out -Force; Remove-Item $Data -Recurse -Force }
    if (Test-Path $AddonDst) { Remove-Item $AddonDst -Recurse -Force }
    if (Test-Path $conlog) {     # seulement la partie de ce bench
        $fs = [System.IO.File]::Open($conlog, 'Open', 'Read', 'ReadWrite'); $fs.Seek($conBefore, 'Begin') | Out-Null
        $sr = New-Object System.IO.StreamReader($fs); $sr.ReadToEnd() | Out-File (Join-Path $Out "console.log") -Encoding utf8; $sr.Close()
    }
}
$done = Test-Path (Join-Path $Out "done.txt")
Write-Host "Bench $Tag termine=$done -> $Out ; addon de bench retire : $(-not (Test-Path $AddonDst))"
if ($done) { exit 0 } else { exit 1 }
