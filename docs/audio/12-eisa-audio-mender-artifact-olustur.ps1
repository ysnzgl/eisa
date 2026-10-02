param(
    [ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+$')]
    [string]$Version = "1.0.0",

    [string]$OutputDirectory = $PSScriptRoot,

    [string]$MenderToolsImage = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$deviceType = "eisa-kiosk-x86_64"
$artifactName = "eisa-audio-$Version"
$artifactFileName = "$artifactName.mender"
$stateScriptName = "ArtifactInstall_Enter_10_eisa-audio"
$stateScriptPath = Join-Path $PSScriptRoot $stateScriptName

if (-not (Test-Path -LiteralPath $stateScriptPath -PathType Leaf)) {
    throw "Mender State Script bulunamadi: $stateScriptPath"
}

if (-not (Get-Command "docker.exe" -ErrorAction SilentlyContinue)) {
    throw "docker.exe bulunamadi. Docker Desktop kurulu ve calisiyor olmali."
}

if ([string]::IsNullOrWhiteSpace($MenderToolsImage)) {
    $MenderToolsImage = @(
        & docker.exe image ls "mendersoftware/mender-ci-tools" `
            --format "{{.Repository}}:{{.Tag}}"
    ) |
        Where-Object { $_ -and $_ -notmatch ':<none>$' } |
        Select-Object -First 1

    if ([string]::IsNullOrWhiteSpace($MenderToolsImage)) {
        throw @"
Yerel mendersoftware/mender-ci-tools imaji bulunamadi.
Daha once kullandiginiz sabit etiketi su parametreyle verin:
  -MenderToolsImage 'mendersoftware/mender-ci-tools:<TAG>'
"@
    }
}

if (-not (Test-Path -LiteralPath $OutputDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
}

$stage = Join-Path $env:TEMP (
    "eisa-audio-mender-" + [Guid]::NewGuid().ToString("N")
)

New-Item -ItemType Directory -Path $stage -Force | Out-Null

try {
    Copy-Item -LiteralPath $stateScriptPath `
        -Destination (Join-Path $stage $stateScriptName)

    Set-Content -LiteralPath (Join-Path $stage "dest_dir") `
        -Value "/var/lib/eisa/device-config" `
        -Encoding ascii `
        -NoNewline

    Set-Content -LiteralPath (Join-Path $stage "filename") `
        -Value "audio-$Version.applied" `
        -Encoding ascii `
        -NoNewline

    Set-Content -LiteralPath (Join-Path $stage "permissions") `
        -Value "644" `
        -Encoding ascii `
        -NoNewline

    Set-Content -LiteralPath (Join-Path $stage "audio-$Version.applied") `
        -Value "eisa audio configuration $Version" `
        -Encoding ascii

    $stageForDocker = $stage -replace '\\', '/'

    $dockerArgs = @(
        "run", "--rm",
        "--volume", "${stageForDocker}:/work",
        "--workdir", "/work",
        $MenderToolsImage,
        "mender-artifact", "write", "module-image",
        "-T", "single-file",
        "-t", $deviceType,
        "-n", $artifactName,
        "--software-name", "eisa-audio",
        "--software-version", $Version,
        "-o", "/work/$artifactFileName",
        "-f", "/work/dest_dir",
        "-f", "/work/filename",
        "-f", "/work/permissions",
        "-f", "/work/audio-$Version.applied",
        "--script", "/work/$stateScriptName"
    )

    Write-Host "Mender tools image: $MenderToolsImage" `
        -ForegroundColor DarkGray

    & docker.exe run --rm `
        $MenderToolsImage `
        mender-artifact --version

    if ($LASTEXITCODE -ne 0) {
        throw "mender-artifact surum kontrolu basarisiz. Cikis kodu: $LASTEXITCODE"
    }

    Write-Host "Mender artifact olusturuluyor: $artifactName" `
        -ForegroundColor Cyan

    & docker.exe @dockerArgs

    if ($LASTEXITCODE -ne 0) {
        throw "mender-artifact olusturma basarisiz. Cikis kodu: $LASTEXITCODE"
    }

    $stageArtifact = Join-Path $stage $artifactFileName

    if (-not (Test-Path -LiteralPath $stageArtifact -PathType Leaf)) {
        throw "Beklenen artifact olusmadi: $stageArtifact"
    }

    & docker.exe run --rm `
        --volume "${stageForDocker}:/work" `
        $MenderToolsImage `
        mender-artifact read "/work/$artifactFileName"

    if ($LASTEXITCODE -ne 0) {
        throw "Artifact dogrulama basarisiz. Cikis kodu: $LASTEXITCODE"
    }

    $outputPath = Join-Path $OutputDirectory $artifactFileName
    Copy-Item -LiteralPath $stageArtifact -Destination $outputPath -Force

    Write-Host "`nArtifact hazir:" -ForegroundColor Green
    Write-Host $outputPath
    Write-Host "Device type: $deviceType"
    Write-Host "Mender Releases ekranina yukleyip once tek pilot cihaza dagitin."
}
finally {
    Remove-Item -LiteralPath $stage -Recurse -Force `
        -ErrorAction SilentlyContinue
}
