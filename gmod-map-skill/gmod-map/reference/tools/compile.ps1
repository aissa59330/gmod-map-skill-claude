# Compile givre_noir : vbsp -> vvis -> vrad -> copie du .bsp dans garrysmod\maps
# Usage : tools\compile.ps1 [-Final] [-Tag iter_1]
param(
    [switch]$Final,
    [switch]$Fast,              # itération rapide UNIQUEMENT : vvis/vrad -fast (visibilité dégradée, à ne jamais livrer)
    [string]$Tag = "latest",
    [string]$GMod = "C:\Program Files (x86)\Steam\steamapps\common\GarrysMod"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Bin = Join-Path $GMod "bin\win64"
if (-not (Test-Path (Join-Path $Bin "vbsp.exe"))) { $Bin = Join-Path $GMod "bin" }
$Game = Join-Path $GMod "garrysmod"
$GmodGame = $Game       # destination du .bsp (garrysmod\maps), indépendante du profil de compilation
# Profil de compilation (dans le projet, rien n'est modifié dans Garry's Mod) :
# copie de gameinfo.txt + cfg/mount.cfg qui monte garrysmod et les addons Workshop extraits
# listés dans tools/content_paths.txt (le vbsp de Gmod ignore les chemins absolus de gameinfo.txt).
$Paths = Join-Path $PSScriptRoot "content_paths.txt"
if (Test-Path $Paths) {
    $Prof = Join-Path $Root "compile_game"
    New-Item -ItemType Directory -Force (Join-Path $Prof "cfg") | Out-Null
    Copy-Item (Join-Path $GmodGame "gameinfo.txt") $Prof -Force
    foreach ($rad in (Join-Path $GmodGame "lights.rad"), (Join-Path $GMod "bin\lights.rad")) {
        if (Test-Path $rad) { Copy-Item $rad $Prof -Force; break }
    }
    $mounts = @("`t`"garrysmod`"`t`"$GmodGame`"")
    foreach ($line in Get-Content $Paths) {
        if (-not $line -or $line.StartsWith("#")) { continue }
        if (-not (Test-Path $line)) { Write-Host "Contenu introuvable : $line"; exit 4 }
        $mounts += "`t`"$(Split-Path $line -Leaf)`"`t`"$line`""
    }
    "`"mountcfg`"`r`n{`r`n$($mounts -join "`r`n")`r`n}" | Out-File (Join-Path $Prof "cfg\mount.cfg") -Encoding ascii
    $Game = $Prof
}
$Src = Join-Path $Root "maps_src\givre_noir"
$Logs = Join-Path $Root "logs"
New-Item -ItemType Directory -Force $Logs | Out-Null
$Log = Join-Path $Logs "compile_$Tag.log"
"=== compile $Tag  $(Get-Date -Format s)  final=$Final  bin=$Bin" | Out-File $Log -Encoding utf8

function Run-Tool($exe, $toolArgs) {
    "`n>>> $exe $toolArgs" | Out-File $Log -Append -Encoding utf8
    $p = Start-Process -FilePath (Join-Path $Bin $exe) -ArgumentList $toolArgs -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput "$Log.tmp" -RedirectStandardError "$Log.err"
    Get-Content "$Log.tmp", "$Log.err" -ErrorAction SilentlyContinue | Out-File $Log -Append -Encoding utf8
    Remove-Item "$Log.tmp", "$Log.err" -ErrorAction SilentlyContinue
    return $p.ExitCode
}

Remove-Item "$Src.bsp", "$Src.lin", "$Src.prt" -ErrorAction SilentlyContinue
$visFast = if ($Fast) { "-fast " } else { "" }      # VVIS complet par défaut (sinon tout est rendu à travers les murs)
$rc = Run-Tool "vbsp.exe" "-game `"$Game`" `"$Src.vmf`""
if (Test-Path "$Src.lin") { Write-Host "LEAK detecte ($Src.lin) - voir $Log"; exit 2 }
if ($rc -ne 0 -or -not (Test-Path "$Src.bsp")) { Write-Host "vbsp a echoue (code $rc) - voir $Log"; exit 1 }
$rc = Run-Tool "vvis.exe" "$visFast-game `"$Game`" `"$Src`""
if ($rc -ne 0) { Write-Host "vvis a echoue (code $rc)"; exit 1 }
$radArgs = if ($Final) { "-ldr -final -StaticPropLighting -StaticPropPolys" } elseif ($Fast) { "-fast -ldr -StaticPropLighting" } else { "-ldr -StaticPropLighting" }
$rc = Run-Tool "vrad.exe" "$radArgs -game `"$Game`" `"$Src`""
if ($rc -ne 0) { Write-Host "vrad a echoue (code $rc)"; exit 1 }
# fichiers que les outils n'ont pas pu lire (ex. chemin > 260 caractères) : à corriger, sinon props mal éclairés
$unread = Select-String -Path $Log -Pattern "Unable to load file" | ForEach-Object { $_.Line.Trim() } | Select-Object -Unique
if ($unread) { Write-Host "ALERTE fichiers illisibles :"; $unread | ForEach-Object { Write-Host "  $_" } }
# textures maison (panneaux) embarquées dans le .bsp : aucun addon nécessaire
$Pack = Join-Path $Root "compile_game\pack_list.txt"
# liste reconstruite ICI à chaque compilation, depuis tous les dossiers de contenu maison :
# un script de textures ou de sons ne peut plus l'écraser avec une liste partielle
$CG = Join-Path $Root "compile_game"
$lines = @()
foreach ($sub in "materials\givre_noir", "sound\givre_noir", "models\givre_noir", "models\gnl") {
    $d = Join-Path $CG $sub
    if (Test-Path $d) {
        Get-ChildItem $d -Recurse -File | ForEach-Object {
            $lines += $_.FullName.Substring($CG.Length + 1).Replace("\", "/")
            $lines += $_.FullName
        }
    }
}
# contenu pris aux packs Workshop NON requis (4 packs requis max) : embarqué aussi (tools/embed_content.py)
& python (Join-Path $PSScriptRoot "embed_content.py") | Out-File $Log -Append -Encoding utf8
$Emb = "C:\Users\<UTILISATEUR>\gn_content\_embed"     # chemin court (limite des 260 caractères de bspzip)
$nEmb = 0
if (Test-Path $Emb) {
    Get-ChildItem $Emb -Recurse -File | ForEach-Object {
        $lines += $_.FullName.Substring($Emb.Length + 1).Replace("\", "/")
        $lines += $_.FullName
        $nEmb++
    }
}
$lines | Out-File $Pack -Encoding ascii
"pack : $($lines.Count / 2) fichiers maison" | Out-File $Log -Append -Encoding utf8
if (Test-Path $Pack) {
    $rc = Run-Tool "bspzip.exe" "-game `"$Game`" -addlist `"$Src.bsp`" `"$Pack`" `"$Src.packed.bsp`""
    if ($rc -ne 0 -or -not (Test-Path "$Src.packed.bsp")) { Write-Host "bspzip a echoue (code $rc)"; exit 1 }
    Move-Item "$Src.packed.bsp" "$Src.bsp" -Force
    # contrôle : tout le contenu maison doit être DANS le .bsp (sinon textures violettes / modèles ERROR en jeu)
    $inBsp = (& (Join-Path $Bin "bspzip.exe") -dir "$Src.bsp" | Select-String -Pattern "^(materials/givre_noir|sound/givre_noir|models/givre_noir|models/gnl)/").Count
    $expected = $lines.Count / 2 - $nEmb
    "pack verifie : $inBsp / $expected" | Out-File $Log -Append -Encoding utf8
    if ($inBsp -lt $expected) { Write-Host "ALERTE contenu maison incomplet dans le .bsp : $inBsp / $expected"; exit 5 }
}
Copy-Item "$Src.bsp" (Join-Path $GmodGame "maps\givre_noir.bsp") -Force
$size = [math]::Round((Get-Item "$Src.bsp").Length / 1MB, 1)
Write-Host "OK : givre_noir.bsp ($size Mo) copie dans garrysmod\maps. Log : $Log"
exit 0
