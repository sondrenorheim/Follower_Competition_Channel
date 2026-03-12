param(
    [string]$SourcePath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$TargetPath = "S:\Follower Battlegrounds",
    [switch]$CreateCompatibilityJunction
)

$ErrorActionPreference = "Stop"

function Resolve-ExistingPath([string]$PathValue, [string]$Label) {
    if (-not (Test-Path -LiteralPath $PathValue)) {
        throw "$Label does not exist: $PathValue"
    }
    return (Resolve-Path -LiteralPath $PathValue).Path
}

function Test-RobocopySuccess([int]$Code) {
    # Robocopy codes 0-7 are success/warning states.
    return $Code -le 7
}

$source = Resolve-ExistingPath -PathValue $SourcePath -Label "SourcePath"
$target = Resolve-ExistingPath -PathValue $TargetPath -Label "TargetPath"

Write-Host "Source: $source"
Write-Host "Target: $target"

if ($source -ieq $target) {
    Write-Host "Source and target are the same path. Nothing to do."
    exit 0
}

$required = @("config.py", "main.py", "requirements.txt")
foreach ($name in $required) {
    $candidate = Join-Path $target $name
    if (-not (Test-Path -LiteralPath $candidate)) {
        throw "Target is missing required file: $candidate"
    }
}

Write-Host "Syncing changed files from source to target with robocopy..."
$robocopyArgs = @(
    $source,
    $target,
    "/E",
    "/COPY:DAT",
    "/DCOPY:DAT",
    "/R:1",
    "/W:1",
    "/MT:16",
    "/FFT",
    "/XJ",
    "/NFL",
    "/NDL",
    "/NP"
)
& robocopy @robocopyArgs | Out-Null
$robocopyCode = $LASTEXITCODE
if (-not (Test-RobocopySuccess -Code $robocopyCode)) {
    throw "Robocopy failed with exit code $robocopyCode"
}
Write-Host "Sync complete."

if (-not $CreateCompatibilityJunction) {
    Write-Host "Cutover sync complete. To preserve old launch paths, rerun with -CreateCompatibilityJunction."
    exit 0
}

$cwdResolved = (Get-Location).Path
if ($cwdResolved.StartsWith($source, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Current working directory is inside SourcePath. Run this script from outside the source folder when creating the junction."
}

$sourceItem = Get-Item -LiteralPath $source -Force
if ($sourceItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
    Write-Host "Source path is already a reparse point. Skipping junction creation."
    exit 0
}

$backupPath = "$source`_pre_ssd_" + (Get-Date -Format "yyyyMMdd_HHmmss")
Write-Host "Moving source folder to backup: $backupPath"
Move-Item -LiteralPath $source -Destination $backupPath

Write-Host "Creating compatibility junction: $source -> $target"
$mklinkResult = cmd /c "mklink /J `"$source`" `"$target`""
if ($LASTEXITCODE -ne 0) {
    throw "mklink failed. Source was moved to: $backupPath`nOutput: $mklinkResult"
}

Write-Host "Junction created successfully."
Write-Host "Backup of original source remains at: $backupPath"
