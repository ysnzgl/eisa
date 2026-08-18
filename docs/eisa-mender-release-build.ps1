[CmdletBinding()]
param(
    [string]$Version,
    [string]$Repo = "D:\Projeler\eisa\e-isa-monorepo",
    [string]$ArtifactsRoot = "D:\mender"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$DeviceType = "eisa-kiosk-x86_64"
$PayloadType = "eisa-app"
$NodeImage = "node:22.23.2-bookworm-slim"
$ArtifactToolImage = "mendersoftware/mender-ci-tools:1.0.0"

function Invoke-Docker {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$DockerArguments,

        [Parameter(Mandatory = $true)]
        [string]$Operation,

        [switch]$DiscardOutput
    )

    # Windows PowerShell 5.1, native uygulamalarin stderr ciktisini
    # $ErrorActionPreference=Stop altinda terminating error'a cevirebilir.
    # Docker ilerleme ve image-pull mesajlarini stderr'e yazdigi icin
    # komutu gecici olarak Continue ile calistirip gercek exit code'u denetliyoruz.
    $PreviousErrorActionPreference = $ErrorActionPreference

    try {
        $ErrorActionPreference = "Continue"

        if ($DiscardOutput) {
            & docker @DockerArguments *> $null
        }
        else {
            & docker @DockerArguments
        }

        $DockerExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }

    if ($DockerExitCode -ne 0) {
        throw "$Operation basarisiz. Docker cikis kodu: $DockerExitCode"
    }
}

function Test-DockerImagePresent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Image
    )

    $PreviousErrorActionPreference = $ErrorActionPreference

    try {
        $ErrorActionPreference = "Continue"
        & docker image inspect $Image *> $null
        return $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }
}

function Test-SemVer {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    return $Value -match '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$'
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = (Read-Host "Yeni E-ISA surumunu girin (ornek: 1.0.2)").Trim()
}

if (-not (Test-SemVer -Value $Version)) {
    throw "Gecersiz SemVer surumu: '$Version'. Ornek: 1.0.2 veya 1.0.2-rc.1"
}

if (-not (Test-Path -LiteralPath $Repo -PathType Container)) {
    throw "Monorepo bulunamadi: $Repo"
}

$Repo = (Resolve-Path -LiteralPath $Repo).Path

$ArtifactName = "$PayloadType-$Version"
$Output = Join-Path $ArtifactsRoot $Version
$PayloadFile = "$ArtifactName.tar.gz"
$ArtifactFile = "$ArtifactName.mender"
$PayloadPath = Join-Path $Output $PayloadFile
$ArtifactPath = Join-Path $Output $ArtifactFile
$BuildScript = Join-Path $Output "build-release.sh"

Write-Host "`n=== RELEASE BILGILERI ===" -ForegroundColor Cyan
Write-Host "Surum       : $Version"
Write-Host "Artifact    : $ArtifactName"
Write-Host "Device type : $DeviceType"
Write-Host "Node image  : $NodeImage"
Write-Host "Cikti       : $Output"

Write-Host "`n=== ON KONTROLLER ===" -ForegroundColor Cyan

if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    throw "Docker komutu bulunamadi. Docker Desktop'i kurup tekrar deneyin."
}

$RequiredFiles = @(
    (Join-Path $Repo "kiosk_edge\api-node\package.json"),
    (Join-Path $Repo "kiosk_edge\api-node\package-lock.json"),
    (Join-Path $Repo "kiosk_edge\api-node\src\index.js"),
    (Join-Path $Repo "kiosk_edge\ui\package.json"),
    (Join-Path $Repo "kiosk_edge\ui\package-lock.json")
)

foreach ($RequiredFile in $RequiredFiles) {
    if (-not (Test-Path -LiteralPath $RequiredFile -PathType Leaf)) {
        throw "Gerekli dosya bulunamadi: $RequiredFile"
    }
}

Set-Location -LiteralPath $Repo

Invoke-Docker `
    -DockerArguments @("version") `
    -Operation "Docker Desktop kontrolu" `
    -DiscardOutput

if (-not (Test-DockerImagePresent -Image $NodeImage)) {
    Write-Host "`nNode build image'i yerelde yok; indiriliyor: $NodeImage" `
        -ForegroundColor Yellow

    Invoke-Docker `
        -DockerArguments @("pull", $NodeImage) `
        -Operation "Node build image indirme"
}
else {
    Write-Host "Node build image'i yerelde hazir: $NodeImage" `
        -ForegroundColor DarkGray
}

if (-not (Test-DockerImagePresent -Image $ArtifactToolImage)) {
    throw "Mender arac image'i yerelde bulunamadi: $ArtifactToolImage"
}

Write-Host "Yerel Mender arac image'i kullanilacak: $ArtifactToolImage" `
    -ForegroundColor DarkGray

if (Test-Path -LiteralPath $Output) {
    throw "Bu surum icin cikti dizini zaten var. Uzerine yazilmayacak: $Output"
}

$OutputCreatedByThisRun = $false

try {
    New-Item -ItemType Directory -Path $Output -Force | Out-Null
    $OutputCreatedByThisRun = $true

$LinuxScript = @'
#!/usr/bin/env bash
set -Eeuo pipefail

export DEBIAN_FRONTEND=noninteractive

: "${EISA_VERSION:?EISA_VERSION tanimli degil}"
EISA_NODE_VERSION=22.23.2
PAYLOAD_FILE="/out/eisa-app-${EISA_VERSION}.tar.gz"

echo "=== BUILD ORTAMI ==="
cat /etc/os-release
echo
node --version
npm --version
getconf GNU_LIBC_VERSION
uname -m

test "$(uname -m)" = "x86_64"
test "$(node --version)" = "v${EISA_NODE_VERSION}"
grep -Eq '^VERSION_ID="?12("?)$' /etc/os-release
grep -Eq '^VERSION_CODENAME=bookworm$' /etc/os-release

echo "=== BUILD ARACLARI ==="
apt-get update
apt-get install -y --no-install-recommends \
  build-essential \
  python3 \
  ca-certificates \
  file \
  binutils
rm -rf /var/lib/apt/lists/*

rm -rf /build
install -d \
  /build/api \
  /build/ui-source \
  /build/release/api \
  /build/release/ui

echo "=== API BUILD VE TEST ==="
cp -a /repo/kiosk_edge/api-node/. /build/api/
rm -rf \
  /build/api/node_modules \
  /build/api/coverage \
  /build/api/.nyc_output

find /build/api -type d -name .git -prune -exec rm -rf {} +
find /build/api -type f \
  \( -name '.env' -o -name '.env.*' -o -name '*.db' \
     -o -name '*.sqlite' -o -name '*.sqlite3' \) -delete

cd /build/api
test -f package.json
test -f package-lock.json
test -f src/index.js

echo "Native Node modulleri Debian 12 uzerinde kaynak koddan derleniyor."
npm_config_build_from_source=true \
npm_config_ignore_scripts=false \
npm ci --omit=dev

echo "=== API RELEASE KOPYASI ==="
cp -a /build/api/. /build/release/api/
rm -rf \
  /build/release/api/coverage \
  /build/release/api/.nyc_output

echo "=== UI BUILD ==="
cp -a /repo/kiosk_edge/ui/. /build/ui-source/
rm -rf \
  /build/ui-source/node_modules \
  /build/ui-source/dist \
  /build/ui-source/coverage

find /build/ui-source -type d -name .git -prune -exec rm -rf {} +
find /build/ui-source -type f \
  \( -name '.env' -o -name '.env.*' -o -name '*.db' \
     -o -name '*.sqlite' -o -name '*.sqlite3' \) -delete

cd /build/ui-source
test -f package.json
test -f package-lock.json

npm_config_ignore_scripts=false npm ci
npm run build
test -f /build/ui-source/dist/index.html
cp -a /build/ui-source/dist/. /build/release/ui/

printf '%s\n' "${EISA_VERSION}" > /build/release/VERSION

echo "=== RELEASE KONTROLU ==="
test -f /build/release/VERSION
test -f /build/release/api/package.json
test -f /build/release/api/src/index.js
test -f /build/release/ui/index.html
test -d /build/release/api/node_modules
test "$(cat /build/release/VERSION)" = "${EISA_VERSION}"

FORBIDDEN_PATH="$(find /build/release -type f \
  \( -name '.env' -o -name '.env.*' -o -name '*.db' \
     -o -name '*.sqlite' -o -name '*.sqlite3' \) -print -quit)"

if [ -n "${FORBIDDEN_PATH}" ]; then
  echo "HATA: Yasakli dosya payload'a girdi: ${FORBIDDEN_PATH}" >&2
  exit 1
fi

echo "=== NATIVE MODUL KONTROLLERI ==="
NATIVE_COUNT=0

while IFS= read -r -d '' NATIVE_MODULE; do
  NATIVE_COUNT=$((NATIVE_COUNT + 1))
  echo "Native modul: ${NATIVE_MODULE}"
  file "${NATIVE_MODULE}" | grep -F 'x86-64'
  ldd "${NATIVE_MODULE}"

  MAX_GLIBC="$(
    objdump -T "${NATIVE_MODULE}" 2>/dev/null \
      | grep -oE 'GLIBC_[0-9]+\.[0-9]+' \
      | sed 's/^GLIBC_//' \
      | sort -Vu \
      | tail -n 1 \
      || true
  )"

  echo "Azami GLIBC gereksinimi: ${MAX_GLIBC:-glibc-sembolu-yok}"

  if [ -n "${MAX_GLIBC}" ] \
    && ! dpkg --compare-versions "${MAX_GLIBC}" le "2.36"; then
    echo "HATA: Debian 12 GLIBC 2.36 ile uyumsuz modul: ${NATIVE_MODULE}" >&2
    exit 1
  fi
done < <(find /build/release/api/node_modules -type f -name '*.node' -print0)

test "${NATIVE_COUNT}" -ge 1

BETTER_SQLITE3="$(find /build/release/api/node_modules \
  -type f -name 'better_sqlite3.node' -print -quit)"
test -n "${BETTER_SQLITE3}"

echo "=== BETTER-SQLITE3 CALISMA TESTI ==="
cd /build/release/api
node - <<'NODE'
const Database = require('better-sqlite3');

const db = new Database(':memory:');
db.exec(`
  CREATE TABLE release_test (
    id INTEGER PRIMARY KEY,
    value TEXT NOT NULL
  );
`);
db.prepare('INSERT INTO release_test (value) VALUES (?)').run('E-ISA');

const result = db
  .prepare('SELECT value FROM release_test WHERE id = ?')
  .get(1);

if (!result || result.value !== 'E-ISA') {
  throw new Error('Release SQLite testi basarisiz.');
}

db.close();
console.log('Release better-sqlite3: OK');
NODE

echo "=== RELEASE DOSYALARI ==="
find /build/release -maxdepth 2 -type f -print | sort | head -n 100

echo "=== PAYLOAD URETIMI ==="
LC_ALL=C tar \
  --sort=name \
  --numeric-owner \
  --owner=0 \
  --group=0 \
  --create \
  --gzip \
  --file="${PAYLOAD_FILE}" \
  --directory=/build/release \
  .

test -s "${PAYLOAD_FILE}"

echo "=== PAYLOAD ICERIK KONTROLU ==="
tar -tzf "${PAYLOAD_FILE}" \
  | grep -E '^\./(VERSION|api/package.json|api/src/index.js|ui/index.html)$'

echo "=== PAYLOAD SONUCU ==="
ls -lh "${PAYLOAD_FILE}"
sha256sum "${PAYLOAD_FILE}"
echo "Payload basariyla uretildi."
'@

$LinuxScript = $LinuxScript -replace "`r`n", "`n"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($BuildScript, $LinuxScript, $Utf8NoBom)

Write-Host "`n=== DEBIAN 12 BOOKWORM / NODE 22.23.2 RELEASE BUILD ===" -ForegroundColor Cyan

$BuildArgs = @(
    "run", "--rm",
    "--platform", "linux/amd64",
    "--env", "EISA_VERSION=$Version",
    "--mount", "type=bind,source=$Repo,target=/repo,readonly",
    "--mount", "type=bind,source=$Output,target=/out",
    $NodeImage,
    "bash", "/out/build-release.sh"
)

Invoke-Docker `
    -DockerArguments $BuildArgs `
    -Operation "Debian 12 Bookworm release build"

if (-not (Test-Path -LiteralPath $PayloadPath -PathType Leaf)) {
    throw "Payload dosyasi olusmadi: $PayloadPath"
}

if ((Get-Item -LiteralPath $PayloadPath).Length -eq 0) {
    throw "Payload dosyasi bos olustu: $PayloadPath"
}

Write-Host "`n=== MENDER ARTIFACT ARACI ===" -ForegroundColor Cyan

$ToolVersionArgs = @(
    "run", "--rm",
    "--platform", "linux/amd64",
    $ArtifactToolImage,
    "mender-artifact", "--version"
)

Invoke-Docker `
    -DockerArguments $ToolVersionArgs `
    -Operation "mender-artifact surum kontrolu"

Write-Host "`n=== MENDER ARTIFACT URETIMI ===" -ForegroundColor Cyan

$ArtifactArgs = @(
    "run", "--rm",
    "--platform", "linux/amd64",
    "--mount", "type=bind,source=$Output,target=/work",
    "--workdir", "/work",
    $ArtifactToolImage,
    "mender-artifact", "write", "module-image",
    "--device-type", $DeviceType,
    "--type", $PayloadType,
    "--artifact-name", $ArtifactName,
    "--file", $PayloadFile,
    "--output-path", $ArtifactFile
)

Invoke-Docker `
    -DockerArguments $ArtifactArgs `
    -Operation "Mender artifact uretimi"

if (-not (Test-Path -LiteralPath $ArtifactPath -PathType Leaf)) {
    throw "Artifact dosyasi olusmadi: $ArtifactPath"
}

if ((Get-Item -LiteralPath $ArtifactPath).Length -eq 0) {
    throw "Artifact dosyasi bos olustu: $ArtifactPath"
}

Write-Host "`n=== ARTIFACT VALIDATION ===" -ForegroundColor Cyan

$ValidateArgs = @(
    "run", "--rm",
    "--platform", "linux/amd64",
    "--mount", "type=bind,source=$Output,target=/work,readonly",
    "--workdir", "/work",
    $ArtifactToolImage,
    "mender-artifact", "validate", $ArtifactFile
)

Invoke-Docker `
    -DockerArguments $ValidateArgs `
    -Operation "Mender artifact dogrulamasi"

Write-Host "`n=== ARTIFACT METADATA ===" -ForegroundColor Cyan

$ReadArgs = @(
    "run", "--rm",
    "--platform", "linux/amd64",
    "--mount", "type=bind,source=$Output,target=/work,readonly",
    "--workdir", "/work",
    $ArtifactToolImage,
    "mender-artifact", "read", $ArtifactFile
)

Invoke-Docker `
    -DockerArguments $ReadArgs `
    -Operation "Mender artifact metadata okuma"

Remove-Item -LiteralPath $BuildScript -Force

Write-Host "`n=== URETILEN DOSYALAR ===" -ForegroundColor Cyan

Get-Item -LiteralPath $PayloadPath, $ArtifactPath |
    Select-Object Name, Length, LastWriteTime, FullName |
    Format-Table -AutoSize

Write-Host "`n=== SHA256 ===" -ForegroundColor Cyan

Get-FileHash -LiteralPath $PayloadPath, $ArtifactPath -Algorithm SHA256 |
    Format-Table -AutoSize

Write-Host "`nARTIFACT HAZIR:" -ForegroundColor Green
Write-Host $ArtifactPath -ForegroundColor Green
Write-Host "Bu .mender dosyasini Mender web arayuzunde Releases > Upload artifact ile yukleyin." -ForegroundColor Green
}
catch {
    $OriginalError = $_

    if ($OutputCreatedByThisRun -and (Test-Path -LiteralPath $Output)) {
        Write-Host "`nBuild basarisiz; yarim kalan surum klasoru siliniyor:" `
            -ForegroundColor Yellow
        Write-Host $Output -ForegroundColor Yellow
        Remove-Item -LiteralPath $Output -Recurse -Force -ErrorAction SilentlyContinue
    }

    throw $OriginalError
}
