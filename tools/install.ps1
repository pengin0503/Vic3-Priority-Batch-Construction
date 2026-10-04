[CmdletBinding()]
param(
    [string]$GameDir = "",
    [string]$OutputDir = "",
    [switch]$Probe
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Builder = Join-Path $PSScriptRoot "build_mod.py"

function Find-Victoria3GameDir {
    $candidates = New-Object System.Collections.Generic.List[string]

    try {
        $steam = (Get-ItemProperty -Path "HKCU:\Software\Valve\Steam" -ErrorAction Stop).SteamPath
        if ($steam) {
            $candidates.Add((Join-Path $steam "steamapps\common\Victoria 3"))
            $vdf = Join-Path $steam "steamapps\libraryfolders.vdf"
            if (Test-Path $vdf) {
                $raw = Get-Content -Raw -Path $vdf
                foreach ($m in [regex]::Matches($raw, '"path"\s+"(?<path>[^"]+)"')) {
                    $lib = $m.Groups['path'].Value -replace '\\\\','\'
                    $candidates.Add((Join-Path $lib "steamapps\common\Victoria 3"))
                }
            }
        }
    } catch {
        # Registry-less / portable Steam installs are handled by -GameDir.
    }

    $candidates.Add("C:\Program Files (x86)\Steam\steamapps\common\Victoria 3")
    $candidates.Add("C:\Program Files\Steam\steamapps\common\Victoria 3")

    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (Test-Path (Join-Path $candidate "game\gui\building_details_panel.gui")) {
            return $candidate
        }
    }
    return $null
}

if ([string]::IsNullOrWhiteSpace($GameDir)) {
    $GameDir = Find-Victoria3GameDir
    if (-not $GameDir) {
        throw "Victoria 3 installation was not found. Re-run with -GameDir 'X:\path\to\Victoria 3'."
    }
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $documents = [Environment]::GetFolderPath("MyDocuments")
    $folderName = if ($Probe) { "Vic3PriorityBatchProbe" } else { "Vic3PriorityBatch" }
    $OutputDir = Join-Path $documents "Paradox Interactive\Victoria 3\mod\$folderName"
}

$python = $null
$pythonPrefix = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    $python = "py"
    $pythonPrefix = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $python = "python"
} else {
    throw "Python 3 was not found. Install Python 3 or run tools\build_mod.py with another Python 3 interpreter."
}

$argsList = @()
$argsList += $pythonPrefix
$argsList += $Builder
$argsList += "--game-dir"
$argsList += $GameDir
$argsList += "--output"
$argsList += $OutputDir
if ($Probe) {
    $argsList += "--probe"
}

$label = if ($Probe) { "Priority Batch Construction modifier probe" } else { "Priority Batch Construction" }
Write-Host "Building $label for Victoria 3..."
Write-Host "Game: $GameDir"
Write-Host "Mod:  $OutputDir"
& $python @argsList
if ($LASTEXITCODE -ne 0) {
    throw "build_mod.py failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Generated mod: $OutputDir"
if ($Probe) {
    Write-Host "Enable only 'Priority Batch Construction — Modifier Probe' and follow docs\modifier-dispatch-probe.md."
} else {
    Write-Host "Open the Paradox Launcher, add/enable 'Priority Batch Construction', then follow docs\runtime-verification.md from this package."
}
