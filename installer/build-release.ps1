param(
    [string]$OutputDir = "",
    [string]$Version = "",
    [switch]$SkipHelper
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

if (-not $OutputDir) {
    $OutputDir = Join-Path $RepoRoot "dist"
}
elseif (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir = Join-Path $RepoRoot $OutputDir
}

$manifestPath = Join-Path $RepoRoot "extension\manifest.json"
$appVersionPath = Join-Path $RepoRoot "app\__init__.py"
$manifestVersion = [string]((Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json).version)
$appVersionText = Get-Content -LiteralPath $appVersionPath -Raw
$appVersionMatch = [regex]::Match($appVersionText, '__version__\s*=\s*"([^"]+)"')
if (-not $appVersionMatch.Success) {
    throw "Could not read the app version from $appVersionPath"
}
$appVersion = $appVersionMatch.Groups[1].Value
if ($manifestVersion -ne $appVersion) {
    throw "Version mismatch: extension is $manifestVersion but app is $appVersion"
}

$requestedVersion = $Version.Trim()
if ($requestedVersion.StartsWith("v")) {
    $requestedVersion = $requestedVersion.Substring(1)
}
if ($requestedVersion -and $requestedVersion -ne $manifestVersion) {
    throw "Requested version $requestedVersion does not match product version $manifestVersion"
}
$Version = $manifestVersion

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

function Copy-CommonPayload {
    param([Parameter(Mandatory = $true)][string]$Stage)

    New-Item -ItemType Directory -Force -Path $Stage | Out-Null
    foreach ($name in @("README.md", "LICENSE", "requirements.txt")) {
        Copy-Item -LiteralPath (Join-Path $RepoRoot $name) -Destination (Join-Path $Stage $name) -Force
    }

    $extensionDst = Join-Path $Stage "extension"
    $iconsDst = Join-Path $extensionDst "icons"
    New-Item -ItemType Directory -Force -Path $iconsDst | Out-Null
    foreach ($name in @(
            "manifest.json", "popup.html", "popup.js", "background.js", "content.js",
            "extractor.js", "pasteflick.js", "setup.html", "setup.js", "STORE.md"
        )) {
        Copy-Item -LiteralPath (Join-Path $RepoRoot "extension\$name") -Destination (Join-Path $extensionDst $name) -Force
    }
    foreach ($name in @("icon16.png", "icon32.png", "icon48.png", "icon128.png")) {
        Copy-Item -LiteralPath (Join-Path $RepoRoot "extension\icons\$name") -Destination (Join-Path $iconsDst $name) -Force
    }

    $appDst = Join-Path $Stage "app"
    New-Item -ItemType Directory -Force -Path $appDst | Out-Null
    Get-ChildItem -LiteralPath (Join-Path $RepoRoot "app") -Filter "*.py" -File | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $appDst $_.Name) -Force
    }

    $installerDst = Join-Path $Stage "installer"
    New-Item -ItemType Directory -Force -Path $installerDst | Out-Null
    foreach ($name in @(
            "install.ps1", "start-pastehost.ps1", "sync-extension.ps1",
            "copy-payload.ps1", "Setup.bat", "build-helper.ps1", "build-release.ps1"
        )) {
        Copy-Item -LiteralPath (Join-Path $RepoRoot "installer\$name") -Destination (Join-Path $installerDst $name) -Force
    }
}

function Write-Checksum {
    param([Parameter(Mandatory = $true)][string]$ZipPath)
    $checksumPath = $ZipPath + ".sha256"
    $hash = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    [System.IO.File]::WriteAllText(
        $checksumPath,
        "$hash  $([System.IO.Path]::GetFileName($ZipPath))`n",
        (New-Object System.Text.UTF8Encoding $false)
    )
    Write-Host "Built $ZipPath"
    Write-Host "SHA256 $checksumPath"
}

$packageName = "PasteFlick-$Version-windows"
$stageRoot = Join-Path ([System.IO.Path]::GetTempPath()) ($packageName + "-" + [guid]::NewGuid().ToString("N"))
$stage = Join-Path $stageRoot $packageName
$zipPath = Join-Path $OutputDir ($packageName + ".zip")
try {
    Copy-CommonPayload -Stage $stage
    Copy-Item -LiteralPath (Join-Path $RepoRoot "Install PasteFlick.bat") -Destination (Join-Path $stage "Install PasteFlick.bat") -Force

    $helperSrc = Join-Path $RepoRoot "dist\helper"
    if (-not $SkipHelper) {
        & (Join-Path $ScriptDir "build-helper.ps1") -OutputDir $helperSrc
    }
    $helperExe = Join-Path $helperSrc "PasteFlickHelper.exe"
    if (Test-Path -LiteralPath $helperExe) {
        Copy-Item -LiteralPath $helperSrc -Destination (Join-Path $stage "helper") -Recurse -Force
    }
    elseif (-not $SkipHelper) {
        throw "Bundled Flick helper was not built"
    }

    Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath ($zipPath + ".sha256") -Force -ErrorAction SilentlyContinue
    Compress-Archive -LiteralPath $stage -DestinationPath $zipPath -CompressionLevel Optimal
    Write-Checksum -ZipPath $zipPath
}
finally {
    Remove-Item -LiteralPath $stageRoot -Recurse -Force -ErrorAction SilentlyContinue
}
