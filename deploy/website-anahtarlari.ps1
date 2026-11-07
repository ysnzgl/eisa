<#
.SYNOPSIS
    eisa.com.tr web sitesi anahtarlarını (app-key + revalidate) Kubernetes'te yönetir.
    Hiçbir anahtar değeri ekrana, loga veya komut geçmişine yazılmaz.

.DESCRIPTION
    Anahtarlar tek yerde durur: eisa-app namespace'indeki `eisa-app-secrets` Secret'ı.
      WEBSITE_SERVER_TOKEN  Site → API app-key (X-Website-Token). Yoksa/yanlışsa API 404 döner.
      REVALIDATE_SECRET     API → site yayın bildirimi (X-Revalidate-Secret).
    Backend (eisa-api, eisa-scheduler) Secret'ın tamamını envFrom ile, site (eisa-site) yalnızca bu
    iki anahtarı secretKeyRef ile okur. Aynı Secret'tan okudukları için değerler hiçbir zaman ayrışmaz;
    yeter ki değişiklikten sonra pod'lar yeniden başlatılsın (betik bunu yapar).

    İşlemler:
      durum   (varsayılan) Anahtarlar var mı, güçlü mü, pod'lardaki değer Secret ile aynı mı,
              site API'ye app-key ile erişebiliyor mu, backend uyarı veriyor mu → rapor.
      olustur Eksik anahtarları rastgele üretir (var olanlara DOKUNMAZ), pod'ları yeniden başlatır.
      yenile  İki anahtarı da yeni değerle değiştirir (rotasyon), pod'ları yeniden başlatır.
              Yeniden başlatma sırasında birkaç saniye site API'ye erişemeyebilir (ISR önbelleği sunar).

.EXAMPLE
    .\deploy\website-anahtarlari.ps1                 # durum raporu
    .\deploy\website-anahtarlari.ps1 -Islem olustur  # ilk kurulum
    .\deploy\website-anahtarlari.ps1 -Islem yenile   # rotasyon

.NOTES
    kubectl doğru cluster context'inde olmalı (kubectl config current-context).
    Lokal geliştirmede bu betiğe gerek yoktur: iki taraf da aynı geliştirme varsayılanını kullanır.
#>
param(
    [ValidateSet('durum', 'olustur', 'yenile')]
    [string]$Islem = 'durum',
    [string]$Namespace = 'eisa-app',
    [string]$Secret = 'eisa-app-secrets',
    # Pod'ları yeniden başlatma (yalnızca Secret'ı güncelle)
    [switch]$YenidenBaslatma
)

$ErrorActionPreference = 'Stop'
$ANAHTARLAR = @('WEBSITE_SERVER_TOKEN', 'REVALIDATE_SECRET')
$MIN_UZUNLUK = 32
# deployment adı → container adı
$OKUYANLAR = [ordered]@{ 'eisa-api' = 'api'; 'eisa-scheduler' = 'scheduler'; 'eisa-site' = 'site' }
$API_ADRESI = "http://eisa-api.$Namespace.svc.cluster.local/api/website/public/sayfalar/"
$hataSayisi = 0

function Yaz([string]$durum, [string]$mesaj) {
    $renk = @{ 'OK' = 'Green'; 'UYARI' = 'Yellow'; 'HATA' = 'Red'; 'BILGI' = 'Cyan' }[$durum]
    Write-Host ("[{0,-5}] {1}" -f $durum, $mesaj) -ForegroundColor $renk
    if ($durum -eq 'HATA') { $script:hataSayisi++ }
}

function Kc {
    # Not: Adı 'kubectl' olamaz — PowerShell'de fonksiyon, aynı adlı programdan önce çözülür (sonsuz özyineleme).
    # Native komut hatası PS 5.1'de istisna üretmez; çıkış kodunu kontrol ederiz.
    # PS 5.1: 'Stop' tercihinde native stderr satırı istisnaya dönüşür; burada yerel olarak gevşetilir.
    $ErrorActionPreference = 'Continue'
    $cikti = & kubectl @args 2>&1
    return [pscustomobject]@{ Kod = $LASTEXITCODE; Cikti = ($cikti | Out-String).Trim() }
}

function Yeni-Deger {
    # 48 bayt kriptografik rastgele → 64 karakter base64url (header/ortam değişkeni güvenli)
    $b = New-Object byte[] 48
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
    return ([Convert]::ToBase64String($b)).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function Sha256([string]$metin) {
    $sha = [Security.Cryptography.SHA256]::Create()
    return -join ($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($metin)) | ForEach-Object { $_.ToString('x2') })
}

function Secret-Oku {
    # → @{ AD = 'çözülmüş değer' } (yalnızca bellekte; asla yazdırılmaz)
    $r = Kc -n $Namespace get secret $Secret -o json
    if ($r.Kod -ne 0) { return $null }
    $json = $r.Cikti | ConvertFrom-Json
    $degerler = @{}
    foreach ($ad in $ANAHTARLAR) {
        $ham = $json.data.$ad
        if ($ham) { $degerler[$ad] = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($ham)) }
    }
    return $degerler
}

function Secret-Guncelle([hashtable]$yeniDegerler) {
    # stringData ile merge patch: Secret'taki diğer anahtarlar (DB parolası vb.) korunur.
    $gecici = Join-Path $env:TEMP ("eisa-anahtar-" + [guid]::NewGuid().ToString('N') + '.json')
    try {
        $govde = @{ stringData = $yeniDegerler } | ConvertTo-Json -Compress
        [IO.File]::WriteAllText($gecici, $govde)  # BOM'suz
        $r = Kc -n $Namespace patch secret $Secret --type merge --patch-file $gecici
        if ($r.Kod -ne 0) { throw "Secret güncellenemedi: $($r.Cikti)" }
    }
    finally {
        if (Test-Path $gecici) { Remove-Item $gecici -Force }
    }
}

function Yeniden-Baslat {
    foreach ($dep in $OKUYANLAR.Keys) {
        $var = Kc -n $Namespace get deployment $dep -o name
        if ($var.Kod -ne 0) { Yaz 'UYARI' "$dep deployment'ı yok, atlandı."; continue }
        $null = Kc -n $Namespace rollout restart deployment/$dep
        Yaz 'BILGI' "$dep yeniden başlatılıyor…"
    }
    foreach ($dep in $OKUYANLAR.Keys) {
        $r = Kc -n $Namespace rollout status deployment/$dep --timeout=180s
        if ($r.Kod -eq 0) { Yaz 'OK' "$dep hazır." }
        elseif ($r.Cikti -notmatch 'not found') { Yaz 'HATA' "$dep hazır olmadı: $($r.Cikti)" }
    }
}

function Durum-Raporu {
    Write-Host "`n── Secret: $Namespace/$Secret ──" -ForegroundColor Cyan
    $degerler = Secret-Oku
    if ($null -eq $degerler) { Yaz 'HATA' "Secret bulunamadı. İlk kurulum için: -Islem olustur"; return }
    foreach ($ad in $ANAHTARLAR) {
        if (-not $degerler.ContainsKey($ad)) { Yaz 'HATA' "$ad yok (→ -Islem olustur)"; continue }
        $u = $degerler[$ad].Length
        if ($degerler[$ad] -like 'dev-*') { Yaz 'HATA' "$ad geliştirme varsayılanı (→ -Islem yenile)" }
        elseif ($u -lt $MIN_UZUNLUK) { Yaz 'HATA' "$ad çok kısa ($u < $MIN_UZUNLUK karakter) (→ -Islem yenile)" }
        else { Yaz 'OK' "$ad mevcut ($u karakter)" }
    }
    if ($degerler.Count -eq 2 -and $degerler[$ANAHTARLAR[0]] -eq $degerler[$ANAHTARLAR[1]]) {
        Yaz 'HATA' "İki anahtar aynı değere sahip; farklı olmalı (→ -Islem yenile)"
    }

    Write-Host "`n── Pod'lar Secret'taki güncel değeri kullanıyor mu? (karşılaştırma özetle, değer gösterilmez) ──" -ForegroundColor Cyan
    foreach ($dep in $OKUYANLAR.Keys) {
        $container = $OKUYANLAR[$dep]
        foreach ($ad in $ANAHTARLAR) {
            if (-not $degerler.ContainsKey($ad)) { continue }
            $r = Kc -n $Namespace exec deploy/$dep -c $container '--' sh -c "printf %s `$$ad | sha256sum"
            if ($r.Kod -ne 0) { Yaz 'UYARI' "$dep/$ad kontrol edilemedi (pod yok veya hazır değil)"; continue }
            $podOzet = ($r.Cikti -split '\s+')[0]
            if ($podOzet -eq (Sha256 $degerler[$ad])) { Yaz 'OK' "$dep → $ad güncel" }
            else { Yaz 'HATA' "$dep → $ad ESKİ değerle çalışıyor (Secret değişmiş, pod yeniden başlatılmamış)" }
        }
    }

    Write-Host "`n── Uçtan uca ──" -ForegroundColor Cyan
    $r = Kc -n $Namespace exec deploy/eisa-site -c site '--' sh -c "wget -q -S -O /dev/null --header X-Website-Token:`$WEBSITE_SERVER_TOKEN $API_ADRESI 2>&1 | head -n 1"
    if ($r.Cikti -match ' 200 ') { Yaz 'OK' "Site → API app-key ile erişiyor (200)" }
    elseif ($r.Cikti -match ' 404 ') { Yaz 'HATA' "API site anahtarını reddediyor (404): değerler uyuşmuyor veya API'de varsayılan değer" }
    else { Yaz 'UYARI' "Site → API kontrol edilemedi: $($r.Cikti)" }

    $r = Kc -n $Namespace exec deploy/eisa-api -c api '--' python manage.py check
    if ($r.Cikti -match 'website\.W00\d') { Yaz 'HATA' "Backend güvenlik uyarısı: $([regex]::Matches($r.Cikti, 'website\.W00\d') -join ', ')" }
    elseif ($r.Kod -eq 0) { Yaz 'OK' "Backend 'manage.py check' web sitesi uyarısı vermiyor" }
    else { Yaz 'UYARI' "manage.py check çalıştırılamadı" }
}

# ── Ana akış ──────────────────────────────────────────────────────────────────
$ctx = Kc config current-context
if ($ctx.Kod -ne 0) { Write-Host "kubectl bir cluster'a bağlı değil: $($ctx.Cikti)" -ForegroundColor Red; exit 2 }
Yaz 'BILGI' "Cluster context: $($ctx.Cikti)   Namespace: $Namespace"

if ($Islem -ne 'durum') {
    $mevcut = Secret-Oku
    if ($null -eq $mevcut) { throw "Secret '$Secret' bulunamadı. Önce rehber §6.3 ile oluşturun (DB/S3 anahtarlarıyla birlikte)." }
    $yeni = @{}
    foreach ($ad in $ANAHTARLAR) {
        if ($Islem -eq 'yenile' -or -not $mevcut.ContainsKey($ad)) { $yeni[$ad] = Yeni-Deger }
    }
    if ($yeni.Count -eq 0) {
        Yaz 'OK' "Anahtarlar zaten mevcut; değişiklik yapılmadı. Değiştirmek için: -Islem yenile"
    }
    else {
        if ($Islem -eq 'yenile') {
            $onay = Read-Host "İki anahtar yenilenecek ve eisa-api, eisa-scheduler, eisa-site yeniden başlatılacak. Devam? (evet/hayir)"
            if ($onay -ne 'evet') { Write-Host 'Vazgeçildi.'; exit 0 }
        }
        Secret-Guncelle $yeni
        Yaz 'OK' ("Secret güncellendi: " + (($yeni.Keys | Sort-Object) -join ', '))
        $yeni.Clear()
        if (-not $YenidenBaslatma) { Yeniden-Baslat }
        else { Yaz 'UYARI' "Pod'lar yeniden başlatılmadı; yeni değerler ancak yeniden başlatınca devreye girer." }
    }
}

Durum-Raporu
Write-Host ""
if ($hataSayisi -gt 0) { Write-Host "$hataSayisi sorun bulundu." -ForegroundColor Red; exit 1 }
Write-Host "Her şey yolunda." -ForegroundColor Green