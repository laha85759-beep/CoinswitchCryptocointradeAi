Param(
    [string]$ServiceName = "cs_bot",
    [string]$PythonPath = "$PSScriptRoot\..\.venv\Scripts\python.exe",
    [string]$AppPath = "$PSScriptRoot\..\cs_bot_v2\run_forever.py",
    [string]$NssmPath = "nssm"
)

Write-Host "Installing NSSM service $ServiceName"
if (-not (Get-Command $NssmPath -ErrorAction SilentlyContinue)) {
    Write-Error "nssm not found in PATH. Please install NSSM and add to PATH."
    exit 1
}

$python = Resolve-Path -Path $PythonPath
$app = Resolve-Path -Path $AppPath

Start-Process -FilePath $NssmPath -ArgumentList @('install', $ServiceName, $python, $app) -Wait
Start-Process -FilePath $NssmPath -ArgumentList @('set', $ServiceName, 'AppDirectory', (Split-Path $app -Parent)) -Wait
Start-Process -FilePath $NssmPath -ArgumentList @('set', $ServiceName, 'AppStdout', (Join-Path (Split-Path $app -Parent) 'service.stdout.log')) -Wait
Start-Process -FilePath $NssmPath -ArgumentList @('set', $ServiceName, 'AppStderr', (Join-Path (Split-Path $app -Parent) 'service.stderr.log')) -Wait
Start-Process -FilePath $NssmPath -ArgumentList @('start', $ServiceName) -Wait

Write-Host "Service $ServiceName installed and started (if nssm available)."
