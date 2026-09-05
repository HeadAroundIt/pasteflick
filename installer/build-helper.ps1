param(
    [string]$OutputDir = "",
    [switch]$Console
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

if (-not $OutputDir) {
    $OutputDir = Join-Path $RepoRoot "dist\helper"
}
elseif (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir = Join-Path $RepoRoot $OutputDir
}

$py = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $py)) {
    $py = "python"
}

$work = Join-Path $RepoRoot "build\helper-work"
New-Item -ItemType Directory -Force -Path $work | Out-Null
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

Write-Host "Installing PyInstaller..."
$pip = Start-Process -FilePath $py -ArgumentList @("-m", "pip", "install", "pyinstaller>=6.0") -Wait -PassThru -WindowStyle Hidden
if ($pip.ExitCode -ne 0) {
    throw "Could not install PyInstaller"
}

$icon = Join-Path $RepoRoot "extension\icons\icon128.png"
$entry = Join-Path $RepoRoot "app\helper_main.py"
$args = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onedir",
    $(if ($Console) { "--console" } else { "--noconsole" }),
    "--noupx",
    "--name", "PasteFlickHelper",
    "--distpath", $work,
    "--workpath", (Join-Path $work "work"),
    "--specpath", $work,
    "--collect-all", "fastapi",
    "--collect-all", "starlette",
    "--collect-all", "pydantic",
    "--collect-all", "uvicorn",
    "--collect-all", "fpdf",
    "--hidden-import", "uvicorn.logging",
    "--hidden-import", "uvicorn.loops.auto",
    "--hidden-import", "uvicorn.loops.asyncio",
    "--hidden-import", "uvicorn.protocols.http.auto",
    "--hidden-import", "uvicorn.protocols.http.h11_impl",
    "--hidden-import", "uvicorn.protocols.websockets.auto",
    "--hidden-import", "uvicorn.lifespan.on",
    "--exclude-module", "pytest",
    "--exclude-module", "pywebview",
    "--exclude-module", "tkinter",
    "--exclude-module", "webview"
)
if (Test-Path -LiteralPath $icon) {
    $args += @("--icon", $icon)
}
$args += $entry

Write-Host "Building bundled Flick helper..."
$build = Start-Process -FilePath $py -ArgumentList $args -WorkingDirectory $RepoRoot -Wait -PassThru -NoNewWindow
if ($build.ExitCode -ne 0) {
    throw "PyInstaller failed"
}

$built = Join-Path $work "PasteFlickHelper"
$exe = Join-Path $built "PasteFlickHelper.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "PyInstaller did not produce PasteFlickHelper.exe"
}

if (Test-Path -LiteralPath $OutputDir) {
    Remove-Item -LiteralPath $OutputDir -Recurse -Force
}
Copy-Item -LiteralPath $built -Destination $OutputDir -Recurse -Force
Write-Host "Bundled helper at $OutputDir"
