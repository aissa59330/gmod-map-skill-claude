# Bench SERVEUR DÃ‰DIÃ‰ (local, sv_lan 1) : 100 bots joueurs en combat + PNJ par paliers 0/100/200/300.
# Installe au besoin SteamCMD + Garry's Mod Dedicated Server (app 4020, connexion anonyme) dans $Srv, hors de Garry's Mod.
# Usage : tools\bench_server.ps1 -Tag optim_4
param(
    [Parameter(Mandatory = $true)][string]$Tag,
    [string]$Srv = "C:\Users\<UTILISATEUR>\gn_srcds",     # chemin COURT obligatoire : Source ne lit pas les chemins > 260 caracteres
    [int]$Timeout = 1500
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$SteamCmd = Join-Path $Srv "steamcmd"
$Game = Join-Path $Srv "server"
$Out = Join-Path $Root "logs\bench_srv_$Tag"
New-Item -ItemType Directory -Force $SteamCmd, $Game, $Out | Out-Null

# 1) SteamCMD + serveur dÃ©diÃ© (une seule fois ; app_update ne retÃ©lÃ©charge que ce qui manque)
if (-not (Test-Path (Join-Path $SteamCmd "steamcmd.exe"))) {
    $zip = Join-Path $SteamCmd "steamcmd.zip"
    Invoke-WebRequest "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip" -OutFile $zip
    Expand-Archive $zip -DestinationPath $SteamCmd -Force
}
foreach ($try in 1..3) {      # au 1er lancement, SteamCMD se met Ã  jour puis peut quitter sans installer
    if (Test-Path (Join-Path $Game "srcds.exe")) { break }
    & (Join-Path $SteamCmd "steamcmd.exe") +force_install_dir $Game +login anonymous +app_update 4020 validate +quit | Select-Object -Last 5 | Out-Host
}
if (-not (Test-Path (Join-Path $Game "srcds.exe"))) { Write-Host "Installation du serveur dedie impossible"; exit 2 }
New-Item -ItemType Directory -Force (Join-Path $Game "garrysmod\maps") | Out-Null
$exe = if (Test-Path (Join-Path $Game "srcds_win64.exe")) { Join-Path $Game "srcds_win64.exe" } else { Join-Path $Game "srcds.exe" }

# 2) contenu (mÃªmes packs que la compilation), map, addon de bench
$cfg = Join-Path $Game "garrysmod\cfg"
New-Item -ItemType Directory -Force $cfg | Out-Null
$mounts = @()
foreach ($line in Get-Content (Join-Path $PSScriptRoot "content_paths.txt")) {
    if ($line -and -not $line.StartsWith("#")) { $mounts += "`t`"$(Split-Path $line -Leaf)`"`t`"$line`"" }
}
"`"mountcfg`"`r`n{`r`n$($mounts -join "`r`n")`r`n}" | Out-File (Join-Path $cfg "mount.cfg") -Encoding ascii
Copy-Item (Join-Path $Root "maps_src\givre_noir.bsp") (Join-Path $Game "garrysmod\maps\givre_noir.bsp") -Force
$addon = Join-Path $Game "garrysmod\addons\givre_noir_srvbench"
if (Test-Path $addon) { Remove-Item $addon -Recurse -Force }
Copy-Item (Join-Path $Root "addons\givre_noir_srvbench") $addon -Recurse
$data = Join-Path $Game "garrysmod\data\givre_noir_srvbench"
if (Test-Path $data) { Remove-Item $data -Recurse -Force }
Remove-Item (Join-Path $Out "cpu.txt") -ErrorAction SilentlyContinue

# 3) lancement, attente, fermeture
$start = Get-Date
$p = Start-Process -FilePath $exe -ArgumentList "-console -condebug -game garrysmod -tickrate 66 -norestart +sv_lan 1 +sv_hibernate_think 1 +maxplayers 128 +map givre_noir" -WorkingDirectory $Game -WindowStyle Minimized -PassThru
try {
    $deadline = $start.AddSeconds($Timeout)
    while ((Get-Date) -lt $deadline -and -not $p.HasExited) {
        Start-Sleep -Seconds 5
        $p.Refresh()
        # temps CPU cumulé du processus serveur (pour en déduire les ms de CPU par tick par palier)
        "$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) $($p.TotalProcessorTime.TotalMilliseconds)" | Out-File (Join-Path $Out "cpu.txt") -Append -Encoding ascii
        if (Test-Path (Join-Path $data "done.txt")) { break }
    }
} finally {
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
    Start-Sleep -Seconds 3
    if (Test-Path $data) { Copy-Item (Join-Path $data "*") $Out -Force }
    if (Test-Path $addon) { Remove-Item $addon -Recurse -Force }
}
$done = Test-Path (Join-Path $Out "done.txt")
Write-Host "Bench serveur $Tag termine=$done -> $Out ($exe)"
if ($done) { exit 0 } else { exit 1 }



