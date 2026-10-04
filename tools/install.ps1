[CmdletBinding()]
param(
    [string]$GameDir = "",
    [string]$OutputDir = "",
    [string]$PythonExe = "",
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
    foreach ($disk in Get-PSDrive -PSProvider FileSystem) {
        $candidates.Add((Join-Path $disk.Root "SteamLibrary\steamapps\common\Victoria 3"))
    }

    foreach ($candidate in $candidates | Select-Object -Unique) {
        if ((Test-Path (Join-Path $candidate "game\gui") -PathType Container) -and
            (Test-Path (Join-Path $candidate "launcher\launcher-settings.json") -PathType Leaf)) {
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
$pythonCandidates = @()
if (-not [string]::IsNullOrWhiteSpace($PythonExe)) {
    $pythonCandidates += @{ Command = $PythonExe; Prefix = @() }
} else {
    $pythonCandidates += @{ Command = "py"; Prefix = @("-3") }
    $pythonCandidates += @{ Command = "python"; Prefix = @() }
    $pythonCandidates += @{ Command = "python3"; Prefix = @() }
}
foreach ($candidate in $pythonCandidates) {
    if (-not (Get-Command $candidate.Command -ErrorAction SilentlyContinue)) { continue }
    try {
        $prefix = $candidate.Prefix
        & $candidate.Command @prefix -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" *> $null
        if ($LASTEXITCODE -eq 0) {
            $python = $candidate.Command
            $pythonPrefix = $prefix
            break
        }
    } catch {
        # A stale py registration or Store alias is not a usable interpreter.
    }
}
if (-not $python) {
    throw "No working Python 3.10+ interpreter was found. Use -PythonExe 'X:\path\python.exe', or install the ready-made mod-only ZIP without Python."
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
