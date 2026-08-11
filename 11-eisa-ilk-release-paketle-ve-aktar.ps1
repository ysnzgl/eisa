$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = "D:\Projeler\eisa\e-isa-monorepo"

if (-not (Test-Path -LiteralPath $repoRoot -PathType Container)) {
    throw "Monorepo kok dizini bulunamadi: $repoRoot"
}

Set-Location -LiteralPath $repoRoot

function Read-KioskIPv4 {
    while ($true) {
        $value = (Read-Host "Kiosk IP adresini girin (ornek: 192.168.1.170)").Trim()
        $parsed = $null

        $isValid = [System.Net.IPAddress]::TryParse($value, [ref]$parsed) -and
            $parsed.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork

        if ($isValid) {
            return $value
        }

        Write-Host "Gecerli bir IPv4 adresi girin." -ForegroundColor Yellow
    }
}

function Assert-LastExitCode {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Operation,

        [int]$MaximumSuccessCode = 0
    )

    if ($LASTEXITCODE -gt $MaximumSuccessCode) {
        throw "$Operation basarisiz. Cikis kodu: $LASTEXITCODE"
    }
}

$requiredPaths = @(
    ".\kiosk_edge\api-node",
    ".\kiosk_edge\ui"
)

foreach ($path in $requiredPaths) {
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        throw "Monorepo yapisi eksik. Bulunamadi: $path"
    }
}

foreach ($command in @("robocopy.exe", "tar.exe", "scp.exe")) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Gerekli komut bulunamadi: $command"
    }
}

$kioskIp = Read-KioskIPv4
$stage = Join-Path $env:TEMP "eisa-kiosk-release"
$archive = Join-Path $env:TEMP "eisa-kiosk-source.tar.gz"

Write-Host "`nMonorepo: $repoRoot" -ForegroundColor DarkGray
Write-Host "`nKaynak dosyalar hazirlaniyor..." -ForegroundColor Cyan

Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force `
    (Join-Path $stage "api"), `
    (Join-Path $stage "ui") | Out-Null

& robocopy.exe ".\kiosk_edge\api-node" (Join-Path $stage "api") /E `
    /XD node_modules .git `
    /XF .env local.db "*.db" "*.db-shm" "*.db-wal"
Assert-LastExitCode -Operation "API kopyalama" -MaximumSuccessCode 7

& robocopy.exe ".\kiosk_edge\ui" (Join-Path $stage "ui") /E `
    /XD node_modules dist .git `
    /XF .env ".env.*"
Assert-LastExitCode -Operation "UI kopyalama" -MaximumSuccessCode 7

& tar.exe -C $stage -czf $archive api ui
Assert-LastExitCode -Operation "Arsiv olusturma"

Write-Host "`nPaket eisa@${kioskIp} adresine aktariliyor..." -ForegroundColor Cyan
Write-Host "Yalnizca eisa kullanicisinin parolasi sorulacak." -ForegroundColor DarkGray

& scp.exe `
    -o "StrictHostKeyChecking=accept-new" `
    -o "LogLevel=ERROR" `
    $archive `
    "eisa@${kioskIp}:/tmp/eisa-kiosk-source.tar.gz"
Assert-LastExitCode -Operation "Kioska dosya aktarimi"

Write-Host "`nAktarim tamamlandi." -ForegroundColor Green
Write-Host "Kiosktaki dosya: /tmp/eisa-kiosk-source.tar.gz"
