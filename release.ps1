<#
.SYNOPSIS
    Automated Release & Publish Script for qgis2ge QGIS Plugin.
.DESCRIPTION
    1. Prompts or accepts new version number & release summary.
    2. Updates qgis2ge/metadata.txt and README.md.
    3. Runs automated unit tests via PyQGIS environment.
    4. Packages clean qgis2ge.zip and deploys to local QGIS profile.
    5. Configures Git (user: iitold, repo: https://github.com/iitold/qgis2ge.git).
    6. Commits, tags (vX.Y.Z), and pushes to GitHub to trigger GitHub Actions release.
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$NewVersion,

    [Parameter(Position = 1)]
    [string]$ReleaseNotes,

    [switch]$SkipTests,
    [switch]$NoPush
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "         qgis2ge - Release & Publish Automation           " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Read current version from metadata.txt
$MetadataPath = Join-Path $ScriptDir "qgis2ge\metadata.txt"
if (-not (Test-Path $MetadataPath)) {
    Write-Error "Could not find metadata.txt at: $MetadataPath"
    exit 1
}

$CurrentVersion = ""
$MetadataContent = Get-Content $MetadataPath -Raw -Encoding UTF8
if ($MetadataContent -match "(?m)^version\s*=\s*(.+)$") {
    $CurrentVersion = $matches[1].Trim()
}
Write-Host "[*] Current version: $CurrentVersion" -ForegroundColor Yellow

# 2. Prompt for version if not provided
if (-not $NewVersion) {
    $PromptVer = Read-Host "Enter new version (e.g. 1.2.0, press Enter to keep '$CurrentVersion')"
    if ([string]::IsNullOrWhiteSpace($PromptVer)) {
        $NewVersion = $CurrentVersion
    } else {
        $NewVersion = $PromptVer.Trim().TrimStart('v')
    }
} else {
    $NewVersion = $NewVersion.Trim().TrimStart('v')
}

if (-not $ReleaseNotes) {
    $PromptNotes = Read-Host "Enter release notes / summary (e.g. Add KMZ support, UI redesign)"
    if ([string]::IsNullOrWhiteSpace($PromptNotes)) {
        $ReleaseNotes = "Release v$NewVersion"
    } else {
        $ReleaseNotes = $PromptNotes.Trim()
    }
}

Write-Host "[+] Preparing release version: v$NewVersion" -ForegroundColor Green
Write-Host "[+] Release notes: $ReleaseNotes" -ForegroundColor Green

# 3. Update metadata.txt
$UpdatedMetadata = $MetadataContent -replace "(?m)^version\s*=.+$", "version=$NewVersion"
[System.IO.File]::WriteAllText($MetadataPath, $UpdatedMetadata, [System.Text.Encoding]::UTF8)
Write-Host "[+] Updated $MetadataPath with version=$NewVersion" -ForegroundColor Green

# 4. Update README.md version if present
$ReadmePath = Join-Path $ScriptDir "README.md"
if (Test-Path $ReadmePath) {
    $ReadmeContent = Get-Content $ReadmePath -Raw -Encoding UTF8
    $ReadmeContent = $ReadmeContent -replace "version-[0-9\.]+-", "version-$NewVersion-"
    $ReadmeContent = $ReadmeContent -replace "Current Version:\s*\*\*[0-9\.]+\*\*", "Current Version: **$NewVersion**"
    [System.IO.File]::WriteAllText($ReadmePath, $ReadmeContent, [System.Text.Encoding]::UTF8)
    Write-Host "[+] Updated $ReadmePath" -ForegroundColor Green
}

# 5. Run Unit Tests (PyQGIS)
if (-not $SkipTests) {
    Write-Host "`n[*] Running automated tests..." -ForegroundColor Cyan
    $QgisPython = "C:\Program Files\QGIS 3.40.12\bin\python-qgis-ltr.bat"
    $TestCmd = ""

    if (Test-Path $QgisPython) {
        $TestCmd = "& `"$QgisPython`" -m unittest qgis2ge.tests.test_exporter"
    } else {
        # Check standard python
        $TestCmd = "python -m unittest qgis2ge.tests.test_exporter"
    }

    Write-Host "Executing: $TestCmd" -ForegroundColor Gray
    try {
        Invoke-Expression $TestCmd
        if ($LASTEXITCODE -ne 0) {
            throw "Unit tests failed with exit code $LASTEXITCODE"
        }
        Write-Host "[+] All tests passed successfully!" -ForegroundColor Green
    } catch {
        Write-Error "[-] Test verification failed: $_"
        Write-Error "Release aborted to prevent deploying broken code."
        exit 1
    }
} else {
    Write-Host "[!] Skipping unit tests as requested." -ForegroundColor Yellow
}

# 6. Package clean qgis2ge.zip
Write-Host "`n[*] Packaging qgis2ge.zip..." -ForegroundColor Cyan
$ZipPath = Join-Path $ScriptDir "qgis2ge.zip"
if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }

$StageDir = Join-Path $env:TEMP "qgis2ge_stage_$([System.Guid]::NewGuid().ToString('N'))"
$StagePluginDir = Join-Path $StageDir "qgis2ge"
New-Item -ItemType Directory -Path $StagePluginDir -Force | Out-Null

Copy-Item -Path (Join-Path $ScriptDir "qgis2ge\*") -Destination $StagePluginDir -Recurse -Exclude "__pycache__","*.pyc"
Compress-Archive -Path $StagePluginDir -DestinationPath $ZipPath -Force
Remove-Item -Recurse -Force $StageDir
Write-Host "[+] Packaged clean $ZipPath ($((Get-Item $ZipPath).Length) bytes)" -ForegroundColor Green

# 7. Deploy to local QGIS profile for immediate testing
$LocalPluginDir = Join-Path $env:APPDATA "QGIS\QGIS3\profiles\default\python\plugins\qgis2ge"
if (Test-Path (Join-Path $env:APPDATA "QGIS\QGIS3\profiles\default")) {
    Write-Host "`n[*] Deploying to local QGIS profile..." -ForegroundColor Cyan
    if (Test-Path $LocalPluginDir) { Remove-Item -Recurse -Force $LocalPluginDir }
    New-Item -ItemType Directory -Path $LocalPluginDir -Force | Out-Null
    Copy-Item -Path (Join-Path $ScriptDir "qgis2ge\*") -Destination $LocalPluginDir -Recurse -Force
    Write-Host "[+] Installed to: $LocalPluginDir" -ForegroundColor Green
}

# 8. Git Configuration & Repository Setup
Write-Host "`n[*] Setting up Git..." -ForegroundColor Cyan
if (-not (Test-Path (Join-Path $ScriptDir ".git"))) {
    Write-Host "Initializing new Git repository..." -ForegroundColor Yellow
    git init
    git branch -M main
}

# Enforce required user identity
git config user.name "iitold"
git config user.email "iitold@users.noreply.github.com"
Write-Host "[+] Configured Git user: iitold <iitold@users.noreply.github.com>" -ForegroundColor Green

# Configure origin remote
$TargetRemote = "https://github.com/iitold/qgis2ge.git"
$Remotes = git remote
if ($Remotes -contains "origin") {
    git remote set-url origin $TargetRemote
} else {
    git remote add origin $TargetRemote
}
Write-Host "[+] Configured Git remote origin: $TargetRemote" -ForegroundColor Green

# 9. Stage and Commit
git add .
$Status = git status --porcelain
if ($Status) {
    git commit -m "Release v${NewVersion} - $ReleaseNotes"
    Write-Host "[+] Committed changes for v$NewVersion" -ForegroundColor Green
} else {
    Write-Host "[*] No new file changes to commit." -ForegroundColor Yellow
}

# 10. Tagging
$TagName = "v$NewVersion"
$ExistingTags = git tag -l $TagName
if ($ExistingTags -contains $TagName) {
    Write-Host "[!] Tag $TagName already exists. Replacing tag..." -ForegroundColor Yellow
    git tag -d $TagName | Out-Null
}
git tag -a $TagName -m "Release ${TagName} - $ReleaseNotes"
Write-Host "[+] Created Git tag: $TagName" -ForegroundColor Green

# 11. Push to GitHub
if (-not $NoPush) {
    Write-Host "`n==========================================================" -ForegroundColor Cyan
    $Confirm = Read-Host "Push commit and tag '$TagName' to GitHub ($TargetRemote)? (Y/N)"
    if ($Confirm -eq 'Y' -or $Confirm -eq 'y') {
        Write-Host "[*] Pushing to origin main and tag $TagName..." -ForegroundColor Cyan
        git push -u origin main
        git push origin $TagName --force

        Write-Host "`n==========================================================" -ForegroundColor Green
        Write-Host "  SUCCESS! Release $TagName pushed to GitHub!             " -ForegroundColor Green
        Write-Host "==========================================================" -ForegroundColor Green
        Write-Host "GitHub Action is now running:"
        Write-Host "  -> https://github.com/iitold/qgis2ge/actions"
        Write-Host "It will compile qgis2ge.zip and attach it to:"
        Write-Host "  -> https://github.com/iitold/qgis2ge/releases/tag/$TagName"
        Write-Host "In QGIS, users can simply open qgis2ge, click"
        Write-Host "'Check for Updates' -> 'Update Now' to update automatically!"
    } else {
        Write-Host "[*] Push skipped. You can manually push when ready using:" -ForegroundColor Yellow
        Write-Host "    git push origin main"
        Write-Host "    git push origin $TagName"
    }
} else {
    Write-Host "[*] --NoPush specified. Commit and tag created locally." -ForegroundColor Yellow
}

Write-Host "`n[Done] Release process completed." -ForegroundColor Cyan
