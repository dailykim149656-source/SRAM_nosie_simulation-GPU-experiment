param(
    [string]$PythonExe = "python",
    [switch]$InstallScikitLearn = $true,
    [switch]$InstallNgspice = $true,
    [switch]$InstallXyce = $true,
    [switch]$FetchPdks = $true,
    [switch]$BuildNative = $true
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Invoke-Step([string]$Name, [scriptblock]$Action) {
    Write-Host "[step] $Name"
    & $Action
}

function Ensure-Dir([string]$PathValue) {
    if (-not (Test-Path $PathValue)) {
        New-Item -ItemType Directory -Force -Path $PathValue | Out-Null
    }
}

Invoke-Step "temp-dir" {
    Ensure-Dir "C:\temp"
}

if ($InstallScikitLearn) {
    Invoke-Step "pip install scikit-learn" {
        & $PythonExe -m pip install scikit-learn
    }
}

if ($InstallNgspice) {
    Invoke-Step "install ngspice via MSYS2" {
        if (-not (Test-Path "C:\msys64\usr\bin\bash.exe")) {
            throw "MSYS2 is required at C:\msys64\usr\bin\bash.exe"
        }
        & "C:\msys64\usr\bin\bash.exe" -lc "pacman -Sy --noconfirm --needed mingw-w64-ucrt-x86_64-ngspice"
    }
}

if ($InstallXyce) {
    Invoke-Step "install Xyce" {
        $xyceBin = "C:\Program Files\XyceNF_7.10\bin\Xyce.exe"
        if (-not (Test-Path $xyceBin)) {
            $zipPath = "C:\temp\xyce_windows.zip"
            $extractDir = "C:\temp\xyce_windows"
            curl.exe -L "https://xyce.sandia.gov/download/2000/?tmstv=1754506753" -o $zipPath | Out-Null
            Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
            & (Join-Path $extractDir "Install_XyceNF_7.10.0.exe") /S
        }
        if (-not (Test-Path $xyceBin)) {
            throw "Xyce install did not produce $xyceBin"
        }
    }
}

if ($FetchPdks) {
    Invoke-Step "fetch open pdks" {
        Ensure-Dir "$RepoRoot\vendor\pdks"

        if (-not (Test-Path "$RepoRoot\vendor\pdks\sky130_fd_pr")) {
            git clone --filter=blob:none --sparse --depth 1 https://github.com/google/skywater-pdk-libs-sky130_fd_pr.git vendor/pdks/sky130_fd_pr
            git -C vendor/pdks/sky130_fd_pr sparse-checkout set models cells
        }
        if (-not (Test-Path "$RepoRoot\vendor\pdks\gf180mcu_fd_pr")) {
            git clone --filter=blob:none --sparse --depth 1 https://github.com/google/globalfoundries-pdk-libs-gf180mcu_fd_pr.git vendor/pdks/gf180mcu_fd_pr
            git -C vendor/pdks/gf180mcu_fd_pr sparse-checkout set models cells
        }
        if (-not (Test-Path "$RepoRoot\vendor\pdks\asap7_pdk_r1p7")) {
            git clone --filter=blob:none --sparse --depth 1 https://github.com/The-OpenROAD-Project/asap7_pdk_r1p7.git vendor/pdks/asap7_pdk_r1p7
            git -C vendor/pdks/asap7_pdk_r1p7 sparse-checkout set models
        }
        if (-not (Test-Path "$RepoRoot\vendor\pdks\OpenRAM")) {
            git clone --filter=blob:none --sparse --depth 1 https://github.com/VLSIDA/OpenRAM.git vendor/pdks/OpenRAM
            git -C vendor/pdks/OpenRAM sparse-checkout set technology/freepdk45 compiler/tests/golden
        }
    }
}

if ($BuildNative) {
    Invoke-Step "build native module" {
        Push-Location "$RepoRoot\native\rust_core"
        try {
            cargo build --release
        }
        finally {
            Pop-Location
        }
        Copy-Item -Force "$RepoRoot\native\rust_core\target\release\_sram_native.dll" "$RepoRoot\_sram_native.pyd"
    }
}

Invoke-Step "preflight" {
    & $PythonExe "$RepoRoot\scripts\check_ops_plan_v1_env.py" --out-json "$RepoRoot\reports\ops_plan_v1_env_check.json"
}
