# PasteFlick Windows installer for Brave / Chrome / Edge / Chromium.
# Browsers block silent extension installs; this stages files and opens Load unpacked.

param(
    [switch]$Uninstall,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$Product = "PasteFlick"
$InstallRoot = Join-Path $env:LOCALAPPDATA "PasteFlick"
$ExtensionDir = Join-Path $InstallRoot "extension"
$GuidePath = Join-Path $InstallRoot "Install-Guide.html"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$SourceExtension = Join-Path $RepoRoot "extension"
$ManifestPath = Join-Path $SourceExtension "manifest.json"
. (Join-Path $ScriptDir "copy-payload.ps1")
$Version = "1.0.8"
if (Test-Path -LiteralPath $ManifestPath) {
    try {
        $Version = ((Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json).version)
    }
    catch { }
}

function Write-Step([string]$Message) {
    Write-Host ("  * " + $Message)
}

function Get-InstalledBrowsers {
    $found = New-Object System.Collections.Generic.List[object]
    $candidates = @(
        @{
            Name = "Brave"
            Exe = @(
                "$env:ProgramFiles\BraveSoftware\Brave-Browser\Application\brave.exe"
                "${env:ProgramFiles(x86)}\BraveSoftware\Brave-Browser\Application\brave.exe"
                "$env:LOCALAPPDATA\BraveSoftware\Brave-Browser\Application\brave.exe"
            )
            ExtensionsUrl = "brave://extensions/"
        }
        @{
            Name = "Chrome"
            Exe = @(
                "$env:ProgramFiles\Google\Chrome\Application\chrome.exe"
                "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
                "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
            )
            ExtensionsUrl = "chrome://extensions/"
        }
        @{
            Name = "Edge"
            Exe = @(
                "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
                "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
            )
            ExtensionsUrl = "edge://extensions/"
        }
        @{
            Name = "Chromium"
            Exe = @(
                "$env:LOCALAPPDATA\Chromium\Application\chrome.exe"
                "$env:ProgramFiles\Chromium\Application\chrome.exe"
            )
            ExtensionsUrl = "chrome://extensions/"
        }
    )

    foreach ($c in $candidates) {
        foreach ($path in $c.Exe) {
            if (Test-Path -LiteralPath $path) {
                $found.Add([pscustomobject]@{
                        Name          = $c.Name
                        ExePath       = $path
                        ExtensionsUrl = $c.ExtensionsUrl
                    }) | Out-Null
                break
            }
        }
    }
    return $found.ToArray()
}

function Get-AssocProgId([string]$RegPath) {
    try {
        return [string](Get-ItemProperty -LiteralPath $RegPath -ErrorAction Stop).ProgId
    }
    catch {
        return ""
    }
}

function Get-BrowserForCurrentDesktop([object[]]$Browsers) {
    $keys = @(
        "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.html\UserChoice",
        "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.htm\UserChoice",
        "HKCU:\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice",
        "HKCU:\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"
    )
    foreach ($key in $keys) {
        $p = (Get-AssocProgId $key).ToLowerInvariant()
        if ([string]::IsNullOrWhiteSpace($p)) { continue }
        $name = $null
        if ($p -like "*brave*") { $name = "Brave" }
        elseif ($p -like "*edge*") { $name = "Edge" }
        elseif ($p -like "*chromium*") { $name = "Chromium" }
        elseif ($p -like "*chrome*") { $name = "Chrome" }
        if ($null -eq $name) { continue }
        foreach ($b in $Browsers) {
            if ($b.Name -eq $name) { return $b }
        }
    }
    return $null
}

function Write-Utf8Bom([string]$Path, [string]$Text) {
    $enc = New-Object System.Text.UTF8Encoding $true
    [System.IO.File]::WriteAllText($Path, $Text, $enc)
}

function Install-ExtensionFiles {
    Copy-PasteFlickPayload -SourceRoot $RepoRoot -InstallRoot $InstallRoot | Out-Null
    Remove-Item -LiteralPath (Join-Path $InstallRoot "dev-hold") -Force -ErrorAction SilentlyContinue
}

function Write-InstallGuide {
    param([object[]]$Browsers)

    $buttons = New-Object System.Collections.Generic.List[string]
    foreach ($b in $Browsers) {
        $buttons.Add(('      <p><strong>{0}</strong>: open <code>{1}</code></p>' -f $b.Name, $b.ExtensionsUrl)) | Out-Null
    }
    if ($buttons.Count -eq 0) {
        $buttons.Add('      <p class="warn">No Brave/Chrome/Edge/Chromium install was found.</p>') | Out-Null
    }
    $browserBlock = [string]::Join("`r`n", $buttons)

    $pathHtml = [System.Net.WebUtility]::HtmlEncode($ExtensionDir)
    $html = @"
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>PasteFlick - finish install</title>
  <style>
    body { margin: 0; background: #141312; color: #ebe6df; font-family: Segoe UI, system-ui, sans-serif; }
    main { max-width: 640px; margin: 0 auto; padding: 36px 22px 48px; }
    .brand { display: flex; align-items: center; gap: 14px; margin-bottom: 10px; }
    .brand img { width: 48px; height: 48px; border-radius: 12px; display: block; }
    h1 { font-size: 28px; margin: 0; letter-spacing: -0.03em; }
    .sub { color: #9a948c; margin: 0 0 28px; line-height: 1.45; }
    .card { background: #1c1b19; border: 1px solid #2c2a27; border-radius: 16px; padding: 18px; margin-bottom: 16px; }
    h2 { font-size: 15px; margin: 0 0 10px; }
    h3 { font-size: 13px; margin: 14px 0 8px; font-weight: 650; }
    .card > h3:first-of-type { margin-top: 4px; }
    ol, ul { margin: 0 0 12px; padding-left: 20px; color: #d8d2c9; line-height: 1.55; }
    .callout {
      margin: 0 0 14px; padding: 10px 12px; border-radius: 10px;
      background: #10100f; border: 1px solid #333029; color: #d8d2c9;
      font-size: 13px; line-height: 1.45;
    }
    .path, code {
      display: block; margin: 10px 0 14px; padding: 12px 14px; border-radius: 10px;
      background: #10100f; border: 1px solid #333029; color: #e7d3b0;
      font: 12.5px/1.4 Consolas, monospace; word-break: break-all;
    }
    button {
      border: 0; border-radius: 10px; padding: 11px 14px; font-weight: 650;
      cursor: pointer; background: #c4a882; color: #1a1510;
    }
    .note { color: #9a948c; font-size: 13px; line-height: 1.45; }
    .ok { color: #b7c4a8; font-size: 13px; margin-left: 10px; }
    .warn { color: #c98980; }
  </style>
</head>
<body>
  <main>
    <div class="brand">
      <img src="extension/icons/icon48.png" alt="" width="48" height="48" />
      <h1>PasteFlick</h1>
    </div>
    <p class="sub">Files are installed. Brave, Chrome, Edge, and Chromium all use this same extension. Load it once in each browser you use.</p>

    <div class="card">
      <h2>1. Copy the extension folder path</h2>
      <div class="path" id="path">$pathHtml</div>
      <button id="copy" type="button">Copy path</button><span class="ok" id="copied"></span>
    </div>

    <div class="card">
      <h2>2. Load unpacked</h2>
      <ol>
        <li>Open your browser extensions page.</li>
        <li>Turn on <strong>Developer mode</strong> (top-right).</li>
        <li>Click <strong>Load unpacked</strong>.</li>
        <li>Paste the path from step 1 and open that folder.</li>
      </ol>
$browserBlock
      <p class="note">Leave Developer mode on. Chrome turns unpacked extensions off if you switch it off. After this, updates come from GitHub on their own - you should not need Load unpacked again.</p>
    </div>

    <div class="card">
      <h2>3. How to use</h2>
      <p class="callout">
        The first time you copy, ChatGPT or the browser may ask if it can use the clipboard.
        Allow it - click <strong>Copy</strong> or <strong>Allow</strong> on that chip.
        If you skip it, PasteFlick has nowhere to put the text.
      </p>
      <h3>On the chat</h3>
      <ul>
        <li>Each message has a <strong>Message</strong> card on its left, with <strong>Copy</strong>, <strong>Auto-paste</strong>, and <strong>Save</strong>. ChatGPT's own buttons stay on the right.</li>
        <li>Code, files, and documents get their own smaller cards.</li>
        <li>The bookmark on a Message card is where <strong>Copy from PasteFlick</strong> starts.</li>
      </ul>
      <h3>From the PasteFlick popup</h3>
      <ul>
        <li><strong>Copy selection</strong> - highlight part of the thread, then copy.</li>
        <li><strong>Copy thread</strong> - the whole conversation.</li>
        <li><strong>Copy from PasteFlick</strong> - from the bookmark onward.</li>
      </ul>
      <p class="note">
        Copies stay on the clipboard unless you turn on Auto-paste or File in Settings.
        Auto-paste puts the copy into the last app you were using.
        Closed this page? After the extension is loaded, open the PasteFlick popup and choose <strong>Add to a browser</strong>.
      </p>
    </div>
  </main>
  <script>
    const path = document.getElementById('path').textContent.trim();
    document.getElementById('copy').onclick = async () => {
      try {
        await navigator.clipboard.writeText(path);
        document.getElementById('copied').textContent = 'Copied';
      } catch (e) {
        document.getElementById('copied').textContent = 'Select the path and Ctrl+C';
      }
    };
  </script>
</body>
</html>
"@
    Write-Utf8Bom -Path $GuidePath -Text $html
}

function Write-UninstallFiles {
    $uninstallPs1 = @'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktop = [Environment]::GetFolderPath('Desktop')
$startup = [Environment]::GetFolderPath('Startup')
Remove-Item -LiteralPath (Join-Path $desktop 'PasteFlick Install Guide.lnk') -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $startup 'PasteFlick Auto-paste.lnk') -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $root -Recurse -Force
Write-Host 'PasteFlick files removed.'
Write-Host 'If it still appears in Brave/Chrome/Edge, open Extensions and Remove it there.'
'@
    $uninstallBat = "@echo off`r`npowershell -NoProfile -ExecutionPolicy Bypass -File `"%~dp0uninstall.ps1`"`r`npause`r`n"
    Set-Content -LiteralPath (Join-Path $InstallRoot "uninstall.ps1") -Value $uninstallPs1 -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $InstallRoot "Uninstall.bat") -Value $uninstallBat -Encoding ASCII
}

function Install-Product {
    Write-Host ""
    Write-Host " $Product setup"
    Write-Host " One package for Brave, Chrome, Edge, and Chromium"
    Write-Host ""

    Install-ExtensionFiles
    Write-Step "Installed to $ExtensionDir"

    $browsers = @(Get-InstalledBrowsers)
    if ($browsers.Count -eq 0) {
        Write-Host "  ! No Chromium browser found. Install Brave, then run Setup again." -ForegroundColor Yellow
    }
    else {
        Write-Step ("Found: " + (($browsers | ForEach-Object { $_.Name }) -join ", "))
    }

    Write-InstallGuide -Browsers $browsers
    Write-UninstallFiles

    try {
        $installedStart = Join-Path $InstallRoot "installer\start-pastehost.ps1"
        $startScript = $installedStart
        if (-not (Test-Path -LiteralPath $startScript)) {
            $startScript = Join-Path $ScriptDir "start-pastehost.ps1"
        }
        & $startScript -SkipUpdate
        if ($LASTEXITCODE -eq 0) {
            Write-Step "Auto-paste helper ready"
        }
        else {
            Write-Host "  ! Auto-paste helper did not start. Clipboard copy still works." -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "  ! Auto-paste helper did not start. Clipboard copy still works." -ForegroundColor Yellow
    }

    $desktop = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktop "$Product Install Guide.lnk"
    $wsh = New-Object -ComObject WScript.Shell
    $sc = $wsh.CreateShortcut($shortcutPath)
    $sc.TargetPath = $GuidePath
    $sc.WorkingDirectory = $InstallRoot
    $sc.Description = "$Product install guide"
    $sc.Save()
    Write-Step "Desktop shortcut created"

    try {
        Set-Clipboard -Value $ExtensionDir
        Write-Step "Extension folder path copied to clipboard"
    }
    catch {
        Write-Step "Path: $ExtensionDir"
    }

    Start-Process $GuidePath

    $launch = Get-BrowserForCurrentDesktop $browsers
    if ($null -ne $launch) {
        Write-Step ("Opening " + $launch.Name + " extensions page")
        Start-Process -FilePath ([string]$launch.ExePath) -ArgumentList @("--new-tab", ([string]$launch.ExtensionsUrl))
    }

    Write-Host ""
    Write-Host " Finish in the browser:"
    Write-Host "  1. Enable Developer mode"
    Write-Host "  2. Click Load unpacked"
    Write-Host "  3. Paste the folder path (already on clipboard) and Open"
    Write-Host ""
    Write-Host " Same extension works in every Chromium browser. Repeat Load unpacked in each one you use."
    Write-Host ""
}

function Uninstall-Product {
    Write-Host ""
    Write-Host " Removing $Product files..."
    $desktop = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktop "$Product Install Guide.lnk"
    if (Test-Path -LiteralPath $shortcutPath) {
        Remove-Item -LiteralPath $shortcutPath -Force
    }
    $startupLnk = Join-Path ([Environment]::GetFolderPath("Startup")) "PasteFlick Auto-paste.lnk"
    if (Test-Path -LiteralPath $startupLnk) {
        Remove-Item -LiteralPath $startupLnk -Force
    }
    if (Test-Path -LiteralPath $InstallRoot) {
        Remove-Item -LiteralPath $InstallRoot -Recurse -Force
    }
    Write-Host " Files removed."
    Write-Host " If the extension is still listed in Brave/Chrome/Edge, open Extensions and Remove it there."
    Write-Host ""
}

if ($Uninstall) {
    Uninstall-Product
}
else {
    Install-Product
}

if (-not $Quiet) {
    Write-Host "Press Enter to close..."
    try { [void][System.Console]::ReadLine() } catch { }
}
