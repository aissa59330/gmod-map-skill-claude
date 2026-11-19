# Tournée caméra Gmod en solo local : installe l'addon de dev, lance le jeu, attend les captures,
# ferme le jeu, rapatrie les images dans shots\<Iter>\gmod\ et RETIRE l'addon de dev.
param(
    [Parameter(Mandatory = $true)][string]$Iter,
    [switch]$Vues,              # captures seules (rapide)
    [string]$GMod = "C:\Program Files (x86)\Steam\steamapps\common\GarrysMod",
    [int]$ShotTimeout = 0,      # 0 = calcule d'apres le nombre de points (3,5 s par capture + marge)
    [int]$TotalTimeout = 0
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$AddonSrc = Join-Path $Root "addons\givre_noir_devtour"
$AddonDst = Join-Path $GMod "garrysmod\addons\givre_noir_devtour"
$Data = Join-Path $GMod "garrysmod\data\givre_noir_shots"
$Out = Join-Path $Root "shots\$Iter\gmod"

if (Get-Process gmod, hl2 -ErrorAction SilentlyContinue) {
    Write-Host "Garry's Mod est deja ouvert : ferme-le avant la tournee."; exit 3
}
$pts = (Select-String -Path (Join-Path $AddonSrc "lua\givre_noir_devtour\points.lua") -Pattern 'ang = Angle').Count   # points de camera seulement (pas les points de marche)
$expected = if ($Vues) { $pts } else { $pts * 2 + 1 }
if ($ShotTimeout -le 0) { $ShotTimeout = if ($Vues) { [int]($expected * 3.5) + 60 } else { [int]($expected * 3.5) + 900 } }   # captures + logique + portes + marche
if ($TotalTimeout -le 0) { $TotalTimeout = $ShotTimeout + 120 }   # + chargement du jeu

New-Item -ItemType Directory -Force $Out | Out-Null
if (Test-Path $Data) { Remove-Item $Data -Recurse -Force }
if (Test-Path $AddonDst) { Remove-Item $AddonDst -Recurse -Force }
Copy-Item $AddonSrc $AddonDst -Recurse
$mode = if ($Vues) { 'GN_MODE = "vues"' } else { 'GN_MODE = "complet"' }
$mode | Out-File (Join-Path $AddonDst "lua\givre_noir_devtour\mode.lua") -Encoding ascii
$start = Get-Date
try {
    $exe = Join-Path $GMod "gmod.exe"
    Start-Process -FilePath $exe -ArgumentList "-windowed -w 1280 -h 720 -novid -nojoy +sv_cheats 1 +maxplayers 1 +map givre_noir" | Out-Null
    $deadline = $start.AddSeconds($TotalTimeout)
    $shotDeadline = $null
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        $n = if (Test-Path $Data) { (Get-ChildItem $Data -Filter *.png).Count } else { 0 }
        if ($n -gt 0 -and -not $shotDeadline) { $shotDeadline = (Get-Date).AddSeconds($ShotTimeout) }
        if (Test-Path (Join-Path $Data "done.txt")) { break }
        if ($shotDeadline -and (Get-Date) -gt $shotDeadline -and $n -lt $expected) { Write-Host "Timeout captures ($n/$expected)"; break }
    }
} finally {
    # deux passes : le lanceur de Gmod peut relancer un processus pendant la fermeture
    foreach ($pass in 1..2) {
        Get-Process gmod, hl2 -ErrorAction SilentlyContinue | Where-Object { $_.StartTime -ge $start.AddSeconds(-5) } | Stop-Process -Force
        Start-Sleep -Seconds 4
    }
    if (Test-Path $Data) { Copy-Item (Join-Path $Data "*") $Out -Force; Remove-Item $Data -Recurse -Force }
    if (Test-Path $AddonDst) { Remove-Item $AddonDst -Recurse -Force }
}
$got = (Get-ChildItem $Out -Filter *.png -ErrorAction SilentlyContinue).Count
Write-Host "Captures : $got/$expected -> $Out ; addon de dev retire : $(-not (Test-Path $AddonDst))"
if ($got -lt $expected) { exit 1 } else { exit 0 }
