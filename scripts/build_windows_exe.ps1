param(
    [switch] $SkipInstall
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $Python = $VenvPython
} else {
    $Python = "python"
}

$ModelPath = Join-Path $ProjectRoot "assets\face_landmarker.task"
if (-not (Test-Path $ModelPath)) {
    throw "Missing assets\face_landmarker.task. Download the MediaPipe Face Landmarker model before building."
}

if (-not $SkipInstall) {
    & $Python -m pip install -e ".[build]"
}

function Build-FocusLensExecutable {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Name,
        [Parameter(Mandatory = $true)]
        [string] $EntryPoint
    )

    $PyInstallerArgs = @(
        "--noconfirm",
        "--clean",
        "--name", $Name,
        "--onefile",
        "--collect-all", "mediapipe",
        "--collect-all", "cv2",
        "--collect-all", "streamlit",
        "--hidden-import", "focuslens.dashboard",
        "--hidden-import", "pandas",
        "--hidden-import", "altair",
        "--hidden-import", "pyarrow",
        "--hidden-import", "pydeck",
        "--add-data", "assets\face_landmarker.task;assets",
        "--add-data", "dashboard.py;.",
        $EntryPoint
    )

    & $Python -m PyInstaller @PyInstallerArgs
}

Build-FocusLensExecutable -Name "FocusLens" -EntryPoint "scripts\focuslens_launcher.py"
Build-FocusLensExecutable -Name "Dashboard" -EntryPoint "scripts\dashboard_launcher.py"

$ZipPath = Join-Path $ProjectRoot "dist\FocusLens-windows-x64.zip"
Compress-Archive -Path "dist\FocusLens.exe", "dist\Dashboard.exe", "README.md", "LICENSE" -DestinationPath $ZipPath -Force

Write-Host ""
Write-Host "Built dist\FocusLens.exe"
Write-Host "Built dist\Dashboard.exe"
Write-Host "Packaged dist\FocusLens-windows-x64.zip"
Write-Host "Try: .\dist\FocusLens.exe --version"
Write-Host "Run: .\dist\FocusLens.exe run"
Write-Host "Dashboard: .\dist\FocusLens.exe dashboard"
Write-Host "Dashboard shortcut: .\dist\Dashboard.exe"
