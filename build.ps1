# =====================================================================
#  一键重新编译脚本
#  用法： 右键“使用 PowerShell 运行”，或在本目录执行：
#          powershell -ExecutionPolicy Bypass -File build.ps1
#
#  说明：使用 Windows 自带的 C# 编译器（.NET Framework 4.x），
#        无需安装 Visual Studio / .NET SDK。
#        注意：csc.exe 在“含中文的输出文件名”下写临时资源会失败，
#        因此这里先用英文名 TcmReview.exe 编译，再改名为中文名。
# =====================================================================
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

# ---------- 0. 找 Python（用于重新生成题库数据；不重新生成可跳过） ----------
function Find-Python {
    $cands = @()
    $cands += (Join-Path $env:LOCALAPPDATA "Programs\Python")
    $cands += "C:\"
    $cands += "C:\Users\$env:USERNAME\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python"
    $found = $null
    foreach ($c in $cands) {
        if (Test-Path $c) {
            $p = Get-ChildItem $c -Filter "python.exe" -Recurse -Depth 3 -ErrorAction SilentlyContinue |
                 Select-Object -First 1
            if ($p) { $found = $p.FullName; break }
        }
    }
    if (-not $found) {
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        if ($cmd) { $found = $cmd.Source }
    }
    return $found
}

$py = Find-Python
if ($py) {
    Write-Host "[1/7] 重新生成题库数据 ..." -ForegroundColor Cyan
    & $py build_herbs.py | Out-Null
    & $py gen_embedded.py
} else {
    Write-Host "[1/7] 未找到 Python，跳过题库重建（使用现有 src\EmbeddedData.cs）" -ForegroundColor Yellow
}

# ---------- 2. 找编译器 ----------
Write-Host "[2/7] 定位 C# 编译器 ..." -ForegroundColor Cyan
$csc = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) { $csc = "C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe" }
if (-not (Test-Path $csc)) { throw "找不到 csc.exe，请安装 .NET Framework 4.x" }
Write-Host "      $csc"

# ---------- 3. 打包图片资源 ----------
Write-Host "[3/7] 打包中药图片资源 ..." -ForegroundColor Cyan
$imagesDir = Join-Path $here "images"
$imgRes = Join-Path $here "res\images.res"
$resArgs = @()
if (Test-Path $imagesDir) {
    $packerExe = Join-Path $env:TEMP "tcm_packer.exe"
    & $csc /nologo /target:exe /platform:anycpu /optimize+ /codepage:65001 `
        "/out:$packerExe" /reference:System.dll /reference:System.Drawing.dll `
        (Join-Path $here "tools\Packer.cs")
    if (-not (Test-Path $packerExe)) { throw "打包工具编译失败" }
    if (Test-Path $imgRes) { Remove-Item $imgRes -Force }
    & $packerExe $imagesDir $imgRes 420 70
    if (Test-Path $imgRes) { $resArgs += "/resource:$imgRes" }
} else {
    Write-Host "      未找到 images 目录，本次不含图片（可用 fetch_images.py 抓取）" -ForegroundColor Yellow
}

# ---------- 4. 编译主程序 ----------
Write-Host "[4/7] 编译主程序 ..." -ForegroundColor Cyan
$src = @("Core.cs", "Engine.cs", "HomeForm.cs", "QuizForm.cs", "Widgets.cs",
         "Program.cs", "VersionInfo.cs", "EmbeddedData.cs", "EmbeddedImages.cs")
$srcPaths = @()
foreach ($f in $src) {
    $p = Join-Path $here "src\$f"
    if (Test-Path $p) { $srcPaths += $p }
}

$outDir = Join-Path $here "发布"
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }
$tmpExe = Join-Path $outDir "TcmReview.exe"
$finalExe = Join-Path $outDir "中药学复习系统.exe"
foreach ($f in @($tmpExe, $finalExe)) { if (Test-Path $f) { Remove-Item $f -Force } }
if (Test-Path $finalExe) { throw "请先关闭正在运行的程序：$finalExe" }

$ico = Join-Path $here "res\app.ico"
$icoArgs = @()
if (Test-Path $ico) {
    $icoArgs = @("/win32icon:$ico", "/resource:$ico,app.ico")
}

& $csc /nologo /target:winexe /platform:anycpu /optimize+ /codepage:65001 `
    $icoArgs $resArgs "/out:$tmpExe" `
    /reference:System.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll `
    $srcPaths

if (-not (Test-Path $tmpExe)) { throw "编译失败" }
Move-Item $tmpExe $finalExe -Force

# ---------- 5. 自测 ----------
Write-Host "[5/7] 运行出题引擎自测（60 套随机卷）..." -ForegroundColor Cyan
& $finalExe --selftest 60

# ---------- 6. 复制来源清单 ----------
Write-Host "[6/7] 复制图片来源清单 ..." -ForegroundColor Cyan
$credits = Join-Path $here "images_credits.txt"
if (Test-Path $credits) { Copy-Item $credits $outDir -Force }

Write-Host "[7/7] 完成" -ForegroundColor Green

Write-Host ""
Write-Host "完成：$finalExe" -ForegroundColor Green
Write-Host "（详细自测报告见本目录 selftest.txt）" -ForegroundColor Gray
Get-Item $finalExe | Select-Object Name, Length, LastWriteTime | Format-List
