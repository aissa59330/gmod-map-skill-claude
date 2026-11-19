# Prépare l'addon de la map : copie le .bsp compilé dans addons\givre_noir_map\maps et vérifie la taille.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Bsp = Join-Path $Root "maps_src\givre_noir.bsp"
$Dst = Join-Path $Root "addons\givre_noir_map\maps"
if (-not (Test-Path $Bsp)) { Write-Host "BSP introuvable : compile d'abord (tools\compile.ps1 -Final)"; exit 1 }
New-Item -ItemType Directory -Force $Dst | Out-Null
Copy-Item $Bsp (Join-Path $Dst "givre_noir.bsp") -Force
$size = (Get-ChildItem (Join-Path $Root "addons\givre_noir_map") -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
"Addon de la map : {0:N1} Mo (limite 500 Mo)" -f $size
if ($size -gt 500) { Write-Host "TROP GROS"; exit 2 }
$lua = Get-ChildItem (Join-Path $Root "addons\givre_noir_map") -Recurse -Filter *.lua
if ($lua) { Write-Host "Attention : du Lua est present dans l'addon de la map"; exit 3 }
"OK - a publier avec les elements requis : 1206775008, 1987994709, 1518614446, 284266415 (4 seulement) (voir docs\publication.md)"
