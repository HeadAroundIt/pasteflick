# Copy the repo product into the unpacked install folder Chrome actually loads.
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
. (Join-Path $ScriptDir "copy-payload.ps1")

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot "extension\manifest.json"))) {
    throw "Extension source not found at $RepoRoot\extension"
}

$roots = New-Object System.Collections.Generic.List[string]
$install = Join-Path $env:LOCALAPPDATA "PasteFlick"
if (Test-Path -LiteralPath $install) {
    $roots.Add($install) | Out-Null
}

if ($roots.Count -eq 0) {
    Write-Host "No installed copy at $install. Load unpacked from the repo extension folder, or run the installer."
    exit 0
}

foreach ($root in $roots) {
    $ver = Copy-PasteFlickPayload -SourceRoot $RepoRoot -InstallRoot $root
    $hold = Join-Path $root "dev-hold"
    Set-Content -LiteralPath $hold -Value "Local copy. GitHub updates are paused while this file exists." -Encoding UTF8
    Write-Host ("PasteFlick " + $ver + " copied to " + (Join-Path $root "extension"))
}

& (Join-Path $ScriptDir "start-pastehost.ps1") -SkipUpdate
