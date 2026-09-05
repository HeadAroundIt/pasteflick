# Start the headless Auto-paste helper on 127.0.0.1:8768 if it is not already up.
# Official installs use the bundled helper. Dev copies can still use .venv.
param(
    [switch]$SkipUpdate
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$InstallRoot = Join-Path $env:LOCALAPPDATA "PasteFlick"
$VenvPyw = Join-Path $RepoRoot ".venv\Scripts\pythonw.exe"
$VenvPy = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Requirements = Join-Path $RepoRoot "requirements.txt"
$env:PASTEFLICK_ROOT = $InstallRoot

function Test-HelperUp {
    try {
        $req = [System.Net.HttpWebRequest]::Create("http://127.0.0.1:8768/api/health")
        $req.Proxy = New-Object System.Net.WebProxy
        $req.Timeout = 800
        $res = $req.GetResponse()
        try {
            $reader = New-Object System.IO.StreamReader($res.GetResponseStream())
            $body = $reader.ReadToEnd()
            $reader.Close()
            return $body -match "pasteflick"
        }
        finally {
            $res.Close()
        }
    }
    catch {
        return $false
    }
}

function Get-BundledHelper {
    foreach ($root in @($InstallRoot, $RepoRoot)) {
        $exe = Join-Path $root "helper\PasteFlickHelper.exe"
        if (Test-Path -LiteralPath $exe) {
            return $exe
        }
    }
    return $null
}

function Install-StartupShortcut {
    $startup = [Environment]::GetFolderPath("Startup")
    foreach ($stale in @("PasteFlick Auto-paste.lnk")) {
        $old = Join-Path $startup $stale
        if (Test-Path -LiteralPath $old) {
            Remove-Item -LiteralPath $old -Force -ErrorAction SilentlyContinue
        }
    }
    $installStart = Join-Path $InstallRoot "installer\start-pastehost.ps1"
    $target = $PSCommandPath
    $work = $RepoRoot
    if (Test-Path -LiteralPath $installStart) {
        $target = $installStart
        $work = $InstallRoot
    }
    $lnk = Join-Path $startup "PasteFlick.lnk"
    $wsh = New-Object -ComObject WScript.Shell
    $sc = $wsh.CreateShortcut($lnk)
    $sc.TargetPath = "powershell.exe"
    $sc.Arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $target + '"'
    $sc.WorkingDirectory = $work
    $sc.WindowStyle = 7
    $sc.Description = "PasteFlick"
    $sc.Save()
}

function Invoke-GitHubUpdate {
    if ($SkipUpdate) {
        return
    }
    $helper = Get-BundledHelper
    if ($helper) {
        try {
            $upd = Start-Process -FilePath $helper -ArgumentList @("--update") -WorkingDirectory (Split-Path $helper) -Wait -PassThru -WindowStyle Hidden
            if ($upd.ExitCode -ne 0) {
                Write-Host "PasteFlick update check did not apply (will try again later)"
            }
        }
        catch {
            Write-Host "PasteFlick update check skipped"
        }
        return
    }
    if (-not (Test-Path -LiteralPath $VenvPy)) {
        return
    }
    try {
        $upd = Start-Process -FilePath $VenvPy -ArgumentList @("-m", "app.update") -WorkingDirectory $RepoRoot -Wait -PassThru -WindowStyle Hidden
        if ($upd.ExitCode -ne 0) {
            Write-Host "PasteFlick update check did not apply (will try again later)"
        }
    }
    catch {
        Write-Host "PasteFlick update check skipped"
    }
}

function Stop-PasteHost {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -eq "PasteFlickHelper.exe" -or
            ($_.CommandLine -and $_.CommandLine -match "app\.pastehost|helper_main")
        } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
}

function Test-Python {
    param(
        [Parameter(Mandatory = $true)][string]$Exe,
        [string[]]$Prefix = @()
    )
    try {
        $args = @($Prefix) + @(
            "-c",
            "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3, 11), (3, 12)) else 1)"
        )
        & $Exe @args *> $null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Get-VenvPython {
    param([string]$Root)
    return (Join-Path $Root ".venv\Scripts\python.exe")
}

function Find-ExistingVenv {
    $roots = New-Object System.Collections.Generic.List[string]
    foreach ($root in @($RepoRoot, $InstallRoot)) {
        if ($root -and -not $roots.Contains($root)) {
            $roots.Add($root) | Out-Null
        }
    }
    foreach ($root in $roots) {
        $py = Get-VenvPython $root
        if (Test-Path -LiteralPath $py) {
            return $py
        }
    }
    return $null
}

function Set-VenvPaths {
    param([Parameter(Mandatory = $true)][string]$PythonExe)
    $script:VenvPy = $PythonExe
    $script:VenvPyw = Join-Path (Split-Path -Parent $PythonExe) "pythonw.exe"
}

function Ensure-Venv {
    $existing = Find-ExistingVenv
    if ($existing) {
        Set-VenvPaths $existing
    }

    $created = $false
    if (-not (Test-Path -LiteralPath $VenvPy)) {
        $launcher = $null
        $prefix = @()
        if (Get-Command py -ErrorAction SilentlyContinue) {
            foreach ($ver in @("-3.12", "-3.11")) {
                if (Test-Python -Exe "py" -Prefix @($ver)) {
                    $launcher = "py"
                    $prefix = @($ver)
                    break
                }
            }
        }
        if (-not $launcher -and (Get-Command python -ErrorAction SilentlyContinue)) {
            if (Test-Python -Exe "python") {
                $launcher = "python"
                $prefix = @()
            }
        }
        if (-not $launcher) {
            Write-Host "This copy has no bundled Auto-paste helper, and Python 3.12 (or 3.11) is not installed."
            Write-Host "Install from the official Windows zip, or install Python and run Setup again."
            return $false
        }

        Write-Host "Creating Python environment for Auto-paste..."
        $venvDir = Join-Path $RepoRoot ".venv"
        $venvArgs = @($prefix) + @("-m", "venv", $venvDir)
        $create = Start-Process -FilePath $launcher -ArgumentList $venvArgs -Wait -PassThru -WindowStyle Hidden
        $createdPy = Get-VenvPython $RepoRoot
        if ($create.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $createdPy)) {
            Write-Host "Could not create the Python environment for Auto-paste."
            return $false
        }
        Set-VenvPaths $createdPy
        $created = $true
    }

    $venvDir = Split-Path -Parent (Split-Path -Parent $VenvPy)
    $marker = Join-Path $venvDir "pasteflick-requirements.sha256"
    $wanted = (Get-FileHash -LiteralPath $Requirements -Algorithm SHA256).Hash.ToLowerInvariant()
    $installed = ""
    if (Test-Path -LiteralPath $marker) {
        $installed = (Get-Content -LiteralPath $marker -Raw).Trim().ToLowerInvariant()
    }
    if ($created) {
        $pipUpgrade = Start-Process -FilePath $VenvPy -ArgumentList @("-m", "pip", "install", "--upgrade", "pip") -Wait -PassThru -WindowStyle Hidden
        if ($pipUpgrade.ExitCode -ne 0) {
            return $false
        }
    }
    if ($created -or $installed -ne $wanted) {
        $pipInstall = Start-Process -FilePath $VenvPy -ArgumentList @("-m", "pip", "install", "-r", $Requirements) -Wait -PassThru -WindowStyle Hidden
        if ($pipInstall.ExitCode -ne 0) {
            return $false
        }
        Set-Content -LiteralPath $marker -Value $wanted -Encoding ASCII
    }
    return (Test-Path -LiteralPath $VenvPy)
}

Install-StartupShortcut
$bundled = Get-BundledHelper
if (-not $bundled) {
    if (-not (Ensure-Venv)) {
        exit 1
    }
}
Invoke-GitHubUpdate
Stop-PasteHost
Start-Sleep -Milliseconds 250

if (Test-HelperUp) {
    Write-Host "PasteFlick Auto-paste already running"
    exit 0
}

$bundled = Get-BundledHelper
if ($bundled) {
    Start-Process -FilePath $bundled -WorkingDirectory (Split-Path $bundled) -WindowStyle Hidden | Out-Null
}
else {
    $py = $null
    if (Test-Path -LiteralPath $VenvPy) {
        $py = $VenvPy
    }
    elseif (Test-Path -LiteralPath $VenvPyw) {
        $py = $VenvPyw
    }
    if (-not $py) {
        Write-Host "No bundled helper or Python venv. Install from the official Windows zip."
        exit 1
    }
    Start-Process -FilePath $py -ArgumentList "-m", "app.pastehost" -WorkingDirectory $RepoRoot -WindowStyle Hidden | Out-Null
}

for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 250
    if (Test-HelperUp) {
        Write-Host "PasteFlick Auto-paste helper started"
        exit 0
    }
}

Write-Host "Started Auto-paste helper, but it is not answering yet"
exit 0
