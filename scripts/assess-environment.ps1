#Requires -Version 5.1

<#
.SYNOPSIS
Collects read-only environment information for TurboServe Milestone 1.

.DESCRIPTION
Prints Windows, NVIDIA, WSL, Python, Git, Docker, and CUDA-related details.
It does not install packages or change system configuration.
#>

$ErrorActionPreference = "Continue"

function Write-Section {
    param([Parameter(Mandatory)][string]$Title)
    Write-Host "`n=== $Title ===" -ForegroundColor Cyan
}

function Invoke-IfAvailable {
    param(
        [Parameter(Mandatory)][string]$Command,
        [string[]]$Arguments = @()
    )

    $resolved = Get-Command $Command -ErrorAction SilentlyContinue
    if ($null -eq $resolved) {
        Write-Host "${Command}: not found"
        return
    }

    Write-Host "$Command path: $($resolved.Source)"
    & $Command @Arguments 2>&1
}

Write-Host "TurboServe Milestone 1 environment assessment"
Write-Host "Collected: $(Get-Date -Format o)"
Write-Host "This script is read-only and intentionally avoids serial numbers and credentials."

Write-Section "Windows and architecture"
$os = Get-CimInstance Win32_OperatingSystem
$computer = Get-CimInstance Win32_ComputerSystem
[PSCustomObject]@{
    Caption        = $os.Caption
    Version        = $os.Version
    BuildNumber    = $os.BuildNumber
    OSArchitecture = $os.OSArchitecture
    SystemType     = $computer.SystemType
} | Format-List

Write-Section "Windows GPU inventory"
Get-CimInstance Win32_VideoController |
    Select-Object Name, DriverVersion, VideoProcessor, AdapterCompatibility |
    Format-List

Write-Section "NVIDIA driver and GPU"
$nvidiaSmi = Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
if ($null -eq $nvidiaSmi) {
    Write-Host "nvidia-smi.exe: not found"
} else {
    Write-Host "nvidia-smi.exe path: $($nvidiaSmi.Source)"
    & nvidia-smi.exe
    Write-Host "`nConcise GPU details:"
    & nvidia-smi.exe --query-gpu=name,driver_version,memory.total,compute_cap --format=csv,noheader
}

Write-Section "WSL status and installed distributions"
$wslCommand = Get-Command wsl.exe -ErrorAction SilentlyContinue
$wslReady = $false
if ($null -eq $wslCommand) {
    Write-Host "wsl.exe: not found"
} else {
    Write-Host "wsl.exe path: $($wslCommand.Source)"
    $wslStatus = @(& wsl.exe --status 2>&1)
    $wslStatusExitCode = $LASTEXITCODE
    $wslStatus | ForEach-Object { Write-Host $_ }

    if ($wslStatusExitCode -eq 0) {
        $wslReady = $true
        & wsl.exe --version 2>&1
        & wsl.exe --list --verbose 2>&1
    } else {
        Write-Host "WSL is not ready; skipping commands that could show an interactive installation prompt."
    }
}

Write-Section "GPU and tooling inside each WSL distribution"
if ($wslReady) {
    $distributions = @(& wsl.exe --list --quiet 2>$null) |
        ForEach-Object { ($_ -replace "`0", "").Trim() } |
        Where-Object { $_ }

    if ($distributions.Count -eq 0) {
        Write-Host "No WSL distributions were reported."
    }

    foreach ($distribution in $distributions) {
        Write-Host "`n--- $distribution ---" -ForegroundColor Yellow
        & wsl.exe --distribution $distribution --exec sh -lc @'
printf 'Kernel: '; uname -srmo
if [ -r /etc/os-release ]; then
  printf 'Distribution: '
  . /etc/os-release
  printf '%s %s\n' "$NAME" "$VERSION_ID"
fi
for tool in nvidia-smi python3 pip3 git docker nvcc; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '%s path: %s\n' "$tool" "$(command -v "$tool")"
  else
    printf '%s: not found\n' "$tool"
  fi
done
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap --format=csv,noheader
fi
python3 --version 2>&1 || true
pip3 --version 2>&1 || true
git --version 2>&1 || true
docker --version 2>&1 || true
nvcc --version 2>&1 || true
'@
    }
} else {
    Write-Host "Skipped because WSL is not installed or configured."
}

Write-Section "Windows Python and pip"
Invoke-IfAvailable -Command "py.exe" -Arguments @("--version")
Invoke-IfAvailable -Command "python.exe" -Arguments @("--version")
Invoke-IfAvailable -Command "pip.exe" -Arguments @("--version")

Write-Section "Windows Git"
Invoke-IfAvailable -Command "git.exe" -Arguments @("--version")
if (Get-Command git.exe -ErrorAction SilentlyContinue) {
    $gitName = & git.exe config --global --get user.name
    $gitEmail = & git.exe config --global --get user.email
    Write-Host "Global user.name configured: $([bool]$gitName)"
    Write-Host "Global user.email configured: $([bool]$gitEmail)"
}

Write-Section "Windows Docker"
Invoke-IfAvailable -Command "docker.exe" -Arguments @("--version")
if (Get-Command docker.exe -ErrorAction SilentlyContinue) {
    & docker.exe version 2>&1
}
$dockerDesktopPaths = @(
    "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
    "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
)
$dockerDesktop = $dockerDesktopPaths | Where-Object { Test-Path $_ }
if ($dockerDesktop) {
    Write-Host "Docker Desktop installation found: $($dockerDesktop -join ', ')"
} else {
    Write-Host "Docker Desktop executable: not found in standard locations"
}

Write-Section "Windows CUDA-related commands"
Invoke-IfAvailable -Command "nvcc.exe" -Arguments @("--version")
Invoke-IfAvailable -Command "where.exe" -Arguments @("nvidia-smi.exe")
Invoke-IfAvailable -Command "where.exe" -Arguments @("nvcc.exe")

Write-Section "Assessment complete"
Write-Host "No software was installed and no system settings were changed."
