# Copy the installed product into a stable folder. Keep lists in sync with app/update.py.

function Copy-PasteFlickPayload {
    param(
        [Parameter(Mandatory = $true)][string]$SourceRoot,
        [Parameter(Mandatory = $true)][string]$InstallRoot
    )

    $SourceExtension = Join-Path $SourceRoot "extension"
    $manifest = Join-Path $SourceExtension "manifest.json"
    if (-not (Test-Path -LiteralPath $manifest)) {
        throw "Extension source not found at $SourceExtension"
    }

    $ExtensionDir = Join-Path $InstallRoot "extension"
    $iconsDst = Join-Path $ExtensionDir "icons"
    New-Item -ItemType Directory -Force -Path $iconsDst | Out-Null

    foreach ($name in @(
            "manifest.json", "popup.html", "popup.js", "background.js", "content.js", "extractor.js",
            "pasteflick.js", "setup.html", "setup.js"
        )) {
        Copy-Item -LiteralPath (Join-Path $SourceExtension $name) -Destination (Join-Path $ExtensionDir $name) -Force
    }
    foreach ($icon in @("icon16.png", "icon32.png", "icon48.png", "icon128.png")) {
        Copy-Item -LiteralPath (Join-Path $SourceExtension "icons\$icon") -Destination (Join-Path $iconsDst $icon) -Force
    }

    $privDst = Join-Path $ExtensionDir "private"
    if (Test-Path -LiteralPath $privDst) {
        Remove-Item -LiteralPath $privDst -Recurse -Force
    }

    $appSrc = Join-Path $SourceRoot "app"
    $appDst = Join-Path $InstallRoot "app"
    if (Test-Path -LiteralPath $appSrc) {
        New-Item -ItemType Directory -Force -Path $appDst | Out-Null
        $sourceNames = @{}
        Get-ChildItem -LiteralPath $appSrc -Filter "*.py" -File | ForEach-Object {
            $sourceNames[$_.Name] = $true
        }
        Get-ChildItem -LiteralPath $appDst -Filter "*.py" -File -ErrorAction SilentlyContinue | ForEach-Object {
            if (-not $sourceNames.ContainsKey($_.Name)) {
                Remove-Item -LiteralPath $_.FullName -Force
            }
        }
        Get-ChildItem -LiteralPath $appSrc -Filter "*.py" -File | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $appDst $_.Name) -Force
        }

        $appPrivDst = Join-Path $appDst "private"
        if (Test-Path -LiteralPath $appPrivDst) {
            Remove-Item -LiteralPath $appPrivDst -Recurse -Force
        }
    }

    $instSrc = Join-Path $SourceRoot "installer"
    $instDst = Join-Path $InstallRoot "installer"
    if (Test-Path -LiteralPath $instSrc) {
        New-Item -ItemType Directory -Force -Path $instDst | Out-Null
        foreach ($name in @(
                "install.ps1", "start-pastehost.ps1", "sync-extension.ps1",
                "copy-payload.ps1", "Setup.bat", "build-helper.ps1", "build-release.ps1"
            )) {
            $src = Join-Path $instSrc $name
            if (Test-Path -LiteralPath $src) {
                Copy-Item -LiteralPath $src -Destination (Join-Path $instDst $name) -Force
            }
        }
    }

    $req = Join-Path $SourceRoot "requirements.txt"
    if (Test-Path -LiteralPath $req) {
        Copy-Item -LiteralPath $req -Destination (Join-Path $InstallRoot "requirements.txt") -Force
    }

    $helperSrc = Join-Path $SourceRoot "helper"
    $helperExe = Join-Path $helperSrc "PasteFlickHelper.exe"
    if (Test-Path -LiteralPath $helperExe) {
        $helperDst = Join-Path $InstallRoot "helper"
        if (Test-Path -LiteralPath $helperDst) {
            Remove-Item -LiteralPath $helperDst -Recurse -Force
        }
        Copy-Item -LiteralPath $helperSrc -Destination $helperDst -Recurse -Force
    }

    $Version = "1.0.8"
    try {
        $Version = ((Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json).version)
    }
    catch { }

    Set-Content -LiteralPath (Join-Path $InstallRoot "version.txt") -Value $Version -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $InstallRoot "extension-path.txt") -Value $ExtensionDir -Encoding UTF8
    $updatesJson = '{"repo":"HeadAroundIt/pasteflick","ref":"main"}'
    $tokenPath = Join-Path $InstallRoot "api-token.txt"
    $apiToken = ""
    if (Test-Path -LiteralPath $tokenPath) {
        $apiToken = (Get-Content -LiteralPath $tokenPath -Raw).Trim()
    }
    if ($apiToken.Length -lt 32) {
        $bytes = New-Object byte[] 32
        $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
        $apiToken = ([System.BitConverter]::ToString($bytes)).Replace("-", "").ToLowerInvariant()
    }
    $infoJson = (@{ extensionPath = $ExtensionDir; apiToken = $apiToken } | ConvertTo-Json -Compress)
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($tokenPath, $apiToken + "`n", $utf8)
    if (-not (Test-Path -LiteralPath (Join-Path $InstallRoot "updates.json"))) {
        [System.IO.File]::WriteAllText((Join-Path $InstallRoot "updates.json"), $updatesJson, $utf8)
    }
    [System.IO.File]::WriteAllText((Join-Path $ExtensionDir "install-info.json"), $infoJson, $utf8)
    return $Version
}
