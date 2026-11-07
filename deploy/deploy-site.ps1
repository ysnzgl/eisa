<#
.SYNOPSIS
    e-isa kurumsal sitesini (web_site, Next.js) build eder, registry'ye push eder
    ve eisa-app namespace'indeki eisa-site deployment'ını yeni imaja geçirir.

.DESCRIPTION
    Eski e-isa-company-websit/deploy.ps1 mantığının monorepo karşılığıdır:
      1. docker build  (bağlam: web_site/, Dockerfile: web_site/Dockerfile)
      2. docker push
      3. (opsiyonel -Apply) kubectl apply -f deploy/eisa-site-production.yaml
      4. kubectl set image deployment/eisa-site site=<imaj>
      5. kubectl rollout status (başarısızsa geri alma komutu yazdırılır)

    Cluster'a dokunan adımlar için kubectl'in doğru context'te olduğundan emin olun
    (kubectl config current-context).

.PARAMETER Tag
    İmaj etiketi (zorunlu). Örn: 2.0.0, 2.0.1

.PARAMETER Registry
    Varsayılan: 10.200.202.20:30500 (docs/rancher-deployment-updated.md §4 ile aynı registry).

.PARAMETER Apply
    set image öncesinde manifesti de uygular. İlk geçişte (eski nginx sitesinden
    yeni Next.js sitesine) veya manifest değiştiğinde kullanın.

.PARAMETER NoCache
    docker build --no-cache ile derler.

.PARAMETER SkipBuild
    Build ve push adımlarını atlar (imaj registry'de zaten varsa).

.PARAMETER DryRun
    Komutları yalnızca yazdırır, hiçbirini çalıştırmaz.

.EXAMPLE
    .\deploy\deploy-site.ps1 -Tag 2.0.0 -Apply

.EXAMPLE
    .\deploy\deploy-site.ps1 -Tag 2.0.1

.EXAMPLE
    .\deploy\deploy-site.ps1 -Tag 2.0.1 -DryRun
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$')]
    [string]$Tag,

    [string]$Registry = "10.200.202.20:30500",
    [string]$Namespace = "eisa-app",
    [switch]$Apply,
    [switch]$NoCache,
    [switch]$SkipBuild,
    [switch]$DryRun
)

# Native komutların (docker/kubectl) başarısı $LASTEXITCODE ile denetlenir.
$RepoRoot   = Split-Path -Parent $PSScriptRoot
$SiteDir    = Join-Path $RepoRoot "web_site"
$Dockerfile = Join-Path $SiteDir "Dockerfile"
$Manifest   = Join-Path $PSScriptRoot "eisa-site-production.yaml"
$Image      = "$Registry/eisa-site:$Tag"
$Deployment = "deployment/eisa-site"
$Container  = "site"

function Invoke-Adim {
    param(
        [string]$Baslik,
        [string]$Exe,
        [string[]]$Argumanlar
    )
    Write-Host "`n==> $Baslik" -ForegroundColor Cyan
    Write-Host "    $Exe $($Argumanlar -join ' ')" -ForegroundColor DarkGray
    if ($DryRun) { return }

    & $Exe @Argumanlar
    if ($LASTEXITCODE -ne 0) {
        Write-Host "HATA: '$Baslik' adımı başarısız oldu (çıkış kodu $LASTEXITCODE)." -ForegroundColor Red
        exit 1
    }
}

Write-Host "e-isa site deploy" -ForegroundColor Green
Write-Host "  İmaj      : $Image"
Write-Host "  Namespace : $Namespace"
if ($DryRun) { Write-Host "  Mod       : DRY-RUN (hiçbir komut çalıştırılmaz)" -ForegroundColor Yellow }

if (-not $SkipBuild) {
    if (-not (Test-Path $Dockerfile)) {
        if (-not $DryRun) {
            Write-Host "HATA: $Dockerfile bulunamadı." -ForegroundColor Red
            exit 1
        }
        Write-Host "UYARI: $Dockerfile bulunamadı (dry-run devam ediyor)." -ForegroundColor Yellow
    }

    $buildArgs = @("build", "-f", $Dockerfile, "-t", $Image)
    if ($NoCache) { $buildArgs += "--no-cache" }
    $buildArgs += $SiteDir

    Invoke-Adim -Baslik "Docker imajı derleniyor" -Exe "docker" -Argumanlar $buildArgs
    Invoke-Adim -Baslik "Docker imajı registry'ye gönderiliyor" -Exe "docker" -Argumanlar @("push", $Image)
}

if (-not $DryRun) {
    $context = (& kubectl config current-context)
    if ($LASTEXITCODE -ne 0) {
        Write-Host "HATA: kubectl context okunamadı." -ForegroundColor Red
        exit 1
    }
    Write-Host "`nkubectl context: $context" -ForegroundColor Yellow
}

if ($Apply) {
    Invoke-Adim -Baslik "Kubernetes manifesti uygulanıyor" -Exe "kubectl" -Argumanlar @("apply", "-f", $Manifest)
}

Invoke-Adim -Baslik "Deployment imajı güncelleniyor" -Exe "kubectl" -Argumanlar @(
    "-n", $Namespace, "set", "image", $Deployment, "$Container=$Image"
)

# rollout history'de hangi imajın yayınlandığı görünsün.
Invoke-Adim -Baslik "Değişiklik notu yazılıyor" -Exe "kubectl" -Argumanlar @(
    "-n", $Namespace, "annotate", $Deployment, "kubernetes.io/change-cause=eisa-site $Tag", "--overwrite"
)

Write-Host "`n==> Rollout bekleniyor" -ForegroundColor Cyan
Write-Host "    kubectl -n $Namespace rollout status $Deployment --timeout=180s" -ForegroundColor DarkGray
if (-not $DryRun) {
    & kubectl -n $Namespace rollout status $Deployment --timeout=180s
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nRollout başarısız oldu veya zaman aşımına uğradı." -ForegroundColor Red
        Write-Host "İnceleme : kubectl -n $Namespace describe pod -l app.kubernetes.io/name=eisa-site" -ForegroundColor Yellow
        Write-Host "Loglar   : kubectl -n $Namespace logs -l app.kubernetes.io/name=eisa-site --tail=100" -ForegroundColor Yellow
        Write-Host "Geri alma: kubectl -n $Namespace rollout undo $Deployment" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "`nDeploy başarılı. Kaynak durumu:" -ForegroundColor Green
    Write-Host "`nPod'lar:" -ForegroundColor Yellow
    & kubectl -n $Namespace get pods -l app.kubernetes.io/name=eisa-site -o wide
    Write-Host "`nService'ler:" -ForegroundColor Yellow
    & kubectl -n $Namespace get svc eisa-site eisa-site-headless
    Write-Host "`nIngress:" -ForegroundColor Yellow
    & kubectl -n $Namespace get ingress eisa-site
    Write-Host "`nTLS sertifikası:" -ForegroundColor Yellow
    & kubectl -n $Namespace get certificate eisa-site-tls
}

Write-Host "`nTamamlandı." -ForegroundColor Green
