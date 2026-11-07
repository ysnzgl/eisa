# eisa.com.tr — Geliştirici ve Operasyon Rehberi

> Kurumsal site (eisa.com.tr), portal.eisa.com.tr üzerinden yönetilen blok tabanlı bir CMS'e taşındı.
> Bağlayıcı sözleşme: [`CONTRACT.md`](CONTRACT.md) · Genel plan: [`PLAN.md`](PLAN.md) (çelişkide CONTRACT geçerlidir).

## İçindekiler

1. [Mimari özet](#1-mimari-özet)
2. [Lokal kurulum](#2-lokal-kurulum)
3. [Ortam değişkenleri](#3-ortam-değişkenleri)
4. [İçerik yönetimi (portal) kılavuzu](#4-içerik-yönetimi-portal-kılavuzu)
5. [Yayın ve önizleme akışı](#5-yayın-ve-önizleme-akışı)
6. [Deploy (Kubernetes)](#6-deploy-kubernetes)
7. [Canlıya geçiş kontrol listesi](#7-canlıya-geçiş-kontrol-listesi)
8. [Rollback](#8-rollback)
9. [Entegrasyon notları (site / backend için)](#9-entegrasyon-notları-site--backend-için)
10. [Bilinen sonraki adımlar](#10-bilinen-sonraki-adımlar)

---

## 1. Mimari özet

```
portal.eisa.com.tr (Vue 3)         api.eisa.com.tr (Django/DRF)            eisa.com.tr (Next.js)
┌──────────────────────┐  JWT     ┌──────────────────────────┐  cluster  ┌─────────────────────────┐
│ Web Sitesi modülü    │ ───────► │ apps/website             │ ◄──────── │ Server Components       │
│  Sayfalar / Menüler  │  cookie  │  admin API  (editor+SA)  │  içi HTTP │  fetch(tag) + ISR cache │
│  Blog / Medya        │          │  public API (AllowAny)   │           │  /api/revalidate        │
│  Başvurular/Ayarlar  │          │  preview API (imzalı)    │ ────────► │  /api/preview (draft)   │
└──────────────────────┘          └──────────────────────────┘ revalidate└─────────────────────────┘
```

| Dizin | Rol |
|-------|-----|
| `backend/apps/website` | Modeller, blok şemaları, public / preview / admin API, revalidate webhook, `website_seed` |
| `web_panels/` | Portal içindeki **Web Sitesi** modülü (`editor` ve `superadmin` rolleri) |
| `web_site/` | Next.js (App Router, `output: 'standalone'`) — eisa.com.tr |
| `deploy/eisa-site-production.yaml` | Site Deployment + Service + headless Service + Traefik Middleware + Ingress |
| `deploy/eisa-app-production.yaml` | API / portal / scheduler; `eisa-app-config` içinde site ile ilgili backend ayarları |
| `deploy/deploy-site.ps1` | Site imajını build/push edip `eisa-site` deployment'ını günceller |

**Temel akış:**
- Site, API'ye **cluster içinden** (`http://eisa-api.eisa-app.svc.cluster.local`) sunucu tarafında erişir; tarayıcı API'ye doğrudan istek atmaz (medya görselleri hariç: `https://api.eisa.com.tr/api/media/website/...`).
- Sayfalar ISR ile önbelleklenir (sayfalar 3600 sn, blog listesi 300 sn). Portalda **Yayınla** denince backend `transaction.on_commit` içinde sitenin `/api/revalidate` ucuna ilgili tag'leri POST eder.
- ISR önbelleği **pod başınadır**. Prod'da backend, `eisa-site-headless` servisinin DNS kaydını çözüp **her pod'a ayrı ayrı** revalidate isteği gönderir (`SITE_REVALIDATE_HEADLESS_HOST`).
- API erişilemezse site son başarılı önbelleği sunmaya devam eder.

---

## 2. Lokal kurulum

### 2.1 Ön koşullar

- Python sanal ortamı: `D:\Projeler\eisa\e-isa-monorepo\.venv` (bağımlılıklar `backend/requirements.txt`)
- Node 24 + npm 11
- Windows PowerShell 5.1 kullanıyorsanız `&&` yoktur; komutları `;` ile veya ayrı satırlarda çalıştırın.

### 2.2 Portlar

| Servis | Port | Adres |
|--------|------|-------|
| Backend (Django, SQLite) | 8000 | http://localhost:8000 (Swagger: `/api/docs/`, yalnızca geliştirmede) |
| Portal (Vite) | 5174 | http://localhost:5174 (`/api` → 8000 proxy) |
| Site (Next.js) | 3000 | http://localhost:3000 |

### 2.3 Backend (SQLite ile)

Lokal geliştirmede `core_api.settings_dev_sqlite` kullanılır (SQLite, `DEBUG=True`, throttle sınıfları kapalı, medya `WEBSITE_MEDIA_LOCAL=True` ile `MEDIA_ROOT/website/...` altına yazılır).

```powershell
cd D:\Projeler\eisa\e-isa-monorepo\backend
$env:DJANGO_SETTINGS_MODULE = "core_api.settings_dev_sqlite"

..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py website_seed          # idempotent; üzerine yazmak için: --force
..\.venv\Scripts\python.exe manage.py createsuperuser       # yoksa
..\.venv\Scripts\python.exe manage.py runserver 8000
```

> `$env:DJANGO_SETTINGS_MODULE` yerine her komuta `--settings=core_api.settings_dev_sqlite` da eklenebilir.

**Editör kullanıcısı oluşturma** (yalnızca Web Sitesi modülünü görür):

- Portal üzerinden: SuperAdmin ile giriş → **Kullanıcılar** → yeni kullanıcı, rol **Editör** (portal formu `editor` rolünü destekliyorsa).
- Komut satırından (lokal):

```powershell
cd D:\Projeler\eisa\e-isa-monorepo\backend
..\.venv\Scripts\python.exe manage.py shell --settings=core_api.settings_dev_sqlite -c "from django.contrib.auth import get_user_model; U = get_user_model(); u, _ = U.objects.get_or_create(username='editor'); u.rol = 'editor'; u.set_password('Editor.12345'); u.save(); print('ok', u.username, u.rol)"
```

> PowerShell'de kodu `|` ile `manage.py shell`'e borulamayın; PS 5.1 başa BOM ekler ve Python `SyntaxError` verir. `-c` kullanın.

### 2.4 Portal

```powershell
npm --prefix D:\Projeler\eisa\e-isa-monorepo\web_panels install
npm --prefix D:\Projeler\eisa\e-isa-monorepo\web_panels run dev      # http://localhost:5174
```

Giriş yaptıktan sonra sol menüde **Web Sitesi** bölümü görünür. `editor` rolü girişte doğrudan bu bölüme yönlenir.

### 2.5 Site

```powershell
npm --prefix D:\Projeler\eisa\e-isa-monorepo\web_site install
npm --prefix D:\Projeler\eisa\e-isa-monorepo\web_site run dev        # http://localhost:3000
```

Tüm site env'lerinin lokal varsayılanı vardır (bkz. §3); `.env.local` gerekmez. Değiştirmek isterseniz `web_site/.env.local`:

```dotenv
API_INTERNAL_URL=http://localhost:8000
MEDIA_BASE_URL=http://localhost:8000
SITE_URL=http://localhost:3000
REVALIDATE_SECRET=dev-revalidate-secret
WEBSITE_SERVER_TOKEN=dev-website-token
```

**Backend olmadan çalışma (MOCK_API):** site, `MOCK_API=1` ile backend'e gitmeden yerleşik örnek verilerle çalışabilir (desteğin ayrıntıları için `web_site/README.md`'ye bakın):

```powershell
$env:MOCK_API = "1"; npm --prefix D:\Projeler\eisa\e-isa-monorepo\web_site run dev
```

### 2.6 Hepsi birlikte (kök `package.json`)

```powershell
cd D:\Projeler\eisa\e-isa-monorepo
npm install                     # concurrently
.\.venv\Scripts\Activate.ps1    # script'ler backend için `py` kullanır; venv aktif olmalı
npm run dev:web                 # backend (SQLite, :8000) + portal (:5174) + site (:3000)
```

| Script | İçerik |
|--------|--------|
| `npm run dev:web` | Web sitesi geliştirmesi için: backend (`--settings=core_api.settings_dev_sqlite`, port 8000) + portal + site |
| `npm run dev:site` | Yalnızca site |
| `npm run dev:all` | Mevcut tam set (portal, backend, scheduler, kiosk api/ui) + site. Backend burada **varsayılan settings** ile (`backend/.env` → PostgreSQL) çalışır; davranışı değiştirilmedi |

> `dev:web` içindeki backend, `migrate` / `website_seed` çalıştırmaz; ilk seferde §2.3'teki adımları elle yapın.

---

## 3. Ortam değişkenleri

Ayrıntılı tanım: `CONTRACT.md §1`.

### Backend

| Değişken | Lokal varsayılan | Prod (nerede) |
|----------|------------------|---------------|
| `SITE_PUBLIC_URL` | `http://localhost:3000` | `https://eisa.com.tr` (ConfigMap `eisa-app-config`) |
| `SITE_REVALIDATE_URLS` | `http://localhost:3000/api/revalidate` | `""` — boş (ConfigMap) |
| `SITE_REVALIDATE_HEADLESS_HOST` | boş | `eisa-site-headless.eisa-app.svc.cluster.local:3000` (ConfigMap) |
| `REVALIDATE_SECRET` | `dev-revalidate-secret` | Secret `eisa-app-secrets` |
| `WEBSITE_SERVER_TOKEN` | `dev-website-token` | Secret `eisa-app-secrets` |

### Site

| Değişken | Lokal varsayılan | Prod (deploy/eisa-site-production.yaml) |
|----------|------------------|------------------------------------------|
| `API_INTERNAL_URL` | `http://localhost:8000` | `http://eisa-api.eisa-app.svc.cluster.local` (Service port 80 → 8080) |
| `MEDIA_BASE_URL` | `http://localhost:8000` | `https://api.eisa.com.tr` |
| `SITE_URL` | `http://localhost:3000` | `https://eisa.com.tr` |
| `REVALIDATE_SECRET` | `dev-revalidate-secret` | `secretKeyRef` → `eisa-app-secrets` |
| `WEBSITE_SERVER_TOKEN` | `dev-website-token` | `secretKeyRef` → `eisa-app-secrets` |
| `MOCK_API` | boş | kullanılmaz |

`REVALIDATE_SECRET` ve `WEBSITE_SERVER_TOKEN` backend ile site arasında **aynı** olmalıdır. Prod'da ikisi de aynı secret'tan okunduğu için bu otomatik sağlanır.

---

## 4. İçerik yönetimi (portal) kılavuzu

Yetki: `superadmin` ve `editor`. Tüm ekranlar portalda **Web Sitesi** menüsü altındadır.

| Ekran | Ne yapılır? |
|-------|-------------|
| **Sayfalar** | Sayfa listesi (durum, son yayın, "taslakta değişiklik var" işareti). Yeni sayfa: slug `a-z0-9-` (ayrılmış: `blog`, `api`, `_next`, `admin`). `anasayfa`, `kvkk`, `cerez-politikasi` silinemez. |
| **Sayfa Editörü** | Solda blok listesi (sürükle-bırak sıralama, gizle/göster, kopyala, sil), sağda bloğun formu (alanlar blok şemasından otomatik gelir). Üstte: **Taslak Kaydet · Önizle · Yayınla · Revizyonlar**. Bloğa `anchor_id` verilirse menüden `/#anchor` ile bağlanabilir. Aynı sayfayı iki kişi düzenlerse ikinci kayıt 409 (çakışma) uyarısı alır; sayfayı yenileyip tekrar deneyin. |
| **Menüler** | Header / Footer / Footer alt sekmeleri; en fazla 2 seviye. Link tipleri: Sayfa, Bölüm (sayfa + anchor), Blog, Dış link. Header'da `CTA` işaretli öğe kırmızı buton olarak görünür. Yayında olmayan sayfaya bağlı öğe sitede görünmez. |
| **Blog** | Yazılar (zengin metin editörü, kapak görseli, kategori, etiketler, SEO, ileri tarihli yayın) ve Kategoriler. İleri tarihli yazı, tarih geldiğinde en geç ~5 dk içinde listede görünür. |
| **Medya** | Görsel yükleme (JPEG/PNG/WebP/GIF/AVIF, en fazla 10 MB; **SVG kabul edilmez**), alt metin düzenleme, arama. Formlardaki "medya seç" diyaloğu bu kütüphaneyi kullanır. Silinen görsel sitede görünmez (kullanım kontrolü yapılmaz). |
| **Başvurular** | Site formlarından gelen pilot / sponsor / genel başvurular. Filtre, detay, durum (`yeni → incelendi → iletişimde → kapandı`), not, atama. Menü rozetinde yeni başvuru sayısı görünür. **E-posta bildirimi yoktur** (bkz. §10). |
| **Site Ayarları** | Site adı, SEO başlık şablonu / açıklama / OG görseli, iletişim bilgileri (boş alanlar sitede gizlenir), footer metni, sosyal linkler. |

**İçerik tonu (zorunlu):** e-isa doktor veya teşhis sistemi değildir; tedavi ya da kesin sonuç vaadi verilmez. Kazanç rakamları "örnek senaryo / potansiyel"dir, garanti değildir. Sistem marka değil kategori önerir; son karar eczacıdadır.

---

## 5. Yayın ve önizleme akışı

1. **Taslak Kaydet** — bloklar taslak olarak kaydedilir; site etkilenmez.
2. **Önizle** — portal `onizleme/` ucundan 1 saat geçerli imzalı bir link alır ve yeni sekmede açar
   (`https://eisa.com.tr/api/preview?tur=sayfa&slug=...&token=...`). Site token'ı backend'de doğrular, draft mode'a geçer ve üstte **"Önizleme modu — Çık"** bandıyla taslağı gösterir. Önizleme yalnızca o tarayıcıyı etkiler.
3. **Yayınla** — taslaktan değişmez bir revizyon oluşturulur ve aktif yapılır. Backend `sayfa:<slug>`, `sayfalar`, `site` tag'lerini revalidate eder; site birkaç saniye içinde güncellenir.
4. **Revizyonlar → Geri al** — seçilen revizyon taslağa kopyalanır ve hemen yeni revizyon olarak yayınlanır.
5. **Yayından kaldır** — sayfa taslağa döner; public API 404 verir, menüdeki bağlantısı gizlenir.

Revalidate isteği başarısız olursa (ör. site pod'u o an yeniden başlıyorsa) içerik yine de en geç zaman bazlı revalidate süresinde (sayfalar 1 saat, blog listesi 5 dk) güncellenir. Acil durumda site pod'larını yeniden başlatmak önbelleği temizler:
`kubectl -n eisa-app rollout restart deployment/eisa-site`.

---

## 6. Deploy (Kubernetes)

Namespace: `eisa-app`. Registry: `10.200.202.20:30500` (site manifesti ve `deploy-site.ps1` varsayılanı; `docs/rancher-deployment-updated.md` §4 ile aynı). Tam dağıtım ve güvenlik adımları: **`docs/rancher-deployment-updated.md` §5–§6.**

### 6.1 Secret'ları ayarla (bir kez)

> **Önerilen:** `.\deploy\website-anahtarlari.ps1 -Islem olustur` — üretir, ekler, pod'ları yeniden başlatır ve doğrular (`docs/rancher-deployment-updated.md` §6.2). Aşağıdaki elle yöntem yalnızca betik kullanılamıyorsa gerekir.

`eisa-app-secrets` cluster'da yönetilir; **repoya yazılmaz**. İki yeni anahtar eklenir. Değerler `CHANGE_ME` yerine rastgele üretilmelidir:

```powershell
# 32 bayt rastgele → 64 karakter hex (header'da sorun çıkarmaz)
function New-Gizli { $b = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); -join ($b | ForEach-Object { $_.ToString('x2') }) }

$patch = @{ stringData = @{ REVALIDATE_SECRET = (New-Gizli); WEBSITE_SERVER_TOKEN = (New-Gizli) } } | ConvertTo-Json -Compress
$tmp = Join-Path $env:TEMP "eisa-secret-patch.json"
[IO.File]::WriteAllText($tmp, $patch)                     # BOM'suz yazar
kubectl -n eisa-app patch secret eisa-app-secrets --type merge --patch-file $tmp
Remove-Item $tmp

# Kontrol (değerleri göstermeden yalnızca anahtar adları):
kubectl -n eisa-app get secret eisa-app-secrets -o jsonpath="{.data}" | ConvertFrom-Json | Get-Member -MemberType NoteProperty | Select-Object Name
```

> PowerShell 5.1'de JSON'u doğrudan `-p '{...}'` ile vermek tırnak kaybına yol açar; bu yüzden `--patch-file` kullanılır.
> ⚠️ `create secret generic ... --dry-run=client -o yaml | kubectl apply -f -` Secret'ı yalnızca verilen anahtarlarla **yeniden yazar** (DB parolası vb. silinir). Anahtar eklerken her zaman yukarıdaki `patch` yöntemini veya Rancher UI'ı kullanın.
> Secret değiştikten sonra iki taraf da yeni değeri okusun diye: `kubectl -n eisa-app rollout restart deployment/eisa-api deployment/eisa-scheduler deployment/eisa-site`. Değerler backend ve sitede aynı Secret'tan okunduğu için uyuşmazlık olmaz.

### 6.2 Backend (API + scheduler)

```powershell
$REGISTRY = "ghcr.io/ysnzgl"     # veya 10.200.202.20:30500
$TAG      = "1.1.0"
cd D:\Projeler\eisa\e-isa-monorepo

docker build -t "$REGISTRY/eisa-api:$TAG" ./backend; if ($?) { docker push "$REGISTRY/eisa-api:$TAG" }

# ConfigMap (SITE_* ve DJANGO_ALLOWED_HOSTS güncellemesi) — tüm dosya apply edilir
kubectl apply -f deploy/eisa-app-production.yaml
kubectl -n eisa-app set image deployment/eisa-api api="$REGISTRY/eisa-api:$TAG"
kubectl -n eisa-app rollout status deployment/eisa-api --timeout=180s

kubectl -n eisa-app exec deployment/eisa-api -c api -- python manage.py migrate --noinput
kubectl -n eisa-app exec deployment/eisa-api -c api -- python manage.py website_seed

kubectl -n eisa-app set image deployment/eisa-scheduler scheduler="$REGISTRY/eisa-api:$TAG"
kubectl -n eisa-app rollout status deployment/eisa-scheduler --timeout=180s
```

> **Dikkat:** `kubectl apply -f deploy/eisa-app-production.yaml` manifestteki imaj etiketlerini (`eisa-api:1.0.0`, `eisa-portal:1.0.0`) de uygular. Canlıda farklı etiket/registry çalışıyorsa apply'dan **hemen sonra** `set image` komutlarını çalıştırın ya da yalnızca ConfigMap'i uygulamak için önce dosyayı inceleyin. ConfigMap değişince pod'lar kendiliğinden yeniden başlamaz; `set image` (veya `rollout restart`) gerekir.

Prod editör kullanıcısı (parolayı komut satırına yazmadan):

```powershell
kubectl -n eisa-app exec deployment/eisa-api -c api -- python manage.py shell -c "from django.contrib.auth import get_user_model; U = get_user_model(); u, c = U.objects.get_or_create(username='editor', defaults={'rol': 'editor'}); u.rol = 'editor'; u.save(); print('olusturuldu' if c else 'guncellendi', u.username)"
kubectl -n eisa-app exec -it deployment/eisa-api -c api -- python manage.py changepassword editor
```

### 6.3 Portal

```powershell
docker build -t "$REGISTRY/eisa-portal:$TAG" ./web_panels; if ($?) { docker push "$REGISTRY/eisa-portal:$TAG" }
kubectl -n eisa-app set image deployment/eisa-portal portal="$REGISTRY/eisa-portal:$TAG"
kubectl -n eisa-app rollout status deployment/eisa-portal --timeout=180s
```

### 6.4 Site

```powershell
cd D:\Projeler\eisa\e-isa-monorepo
.\deploy\deploy-site.ps1 -Tag 2.0.0 -Apply                         # ilk geçiş: manifesti de uygular
.\deploy\deploy-site.ps1 -Tag 2.0.1                                # sonraki sürümler: build + push + set image
.\deploy\deploy-site.ps1 -Tag 2.0.1 -Registry 10.200.202.20:30500  # yerel registry
.\deploy\deploy-site.ps1 -Tag 2.0.1 -DryRun                        # yalnızca komutları yazdırır
```

Parametreler: `-Tag` (zorunlu), `-Registry` (varsayılan `ghcr.io/ysnzgl`), `-Namespace` (varsayılan `eisa-app`), `-Apply`, `-NoCache`, `-SkipBuild`, `-DryRun`. Script `kubectl rollout status` ile bekler; başarısız olursa inceleme ve geri alma komutlarını yazdırır.

`deploy/eisa-site-production.yaml` özet:

| Kaynak | Ayrıntı |
|--------|---------|
| Deployment `eisa-site` | 2 replika, `maxUnavailable: 0`, Node container port 3000 (`http`), non-root (uid/gid 1001 — `web_site/Dockerfile` ile aynı olmalı), `readOnlyRootFilesystem: true` + `/app/.next/cache` ve `/tmp` için emptyDir, probe `/api/health`, requests 50m/128Mi, limits 500m/512Mi |
| Service `eisa-site` | ClusterIP 80 → `http` (Ingress hedefi) |
| Service `eisa-site-headless` | `clusterIP: None`, port 3000 — backend revalidate fan-out |
| Middleware `eisa-site-www-redirect` | Traefik `redirectRegex`: `www.eisa.com.tr/*` → `https://eisa.com.tr/*` (301) |
| Ingress `eisa-site` | `eisa.com.tr` + `www.eisa.com.tr`, Traefik `websecure`, cert-manager `letsencrypt-prod`, TLS secret `eisa-site-tls` (eskisiyle aynı) |

> Middleware `traefik.io/v1alpha1` API'sini kullanır (Traefik ≥ 2.10 / v3). Cluster'da hangisinin olduğunu kontrol edin:
> `kubectl api-resources | Select-String middlewares`. Yalnızca `traefik.containo.us` varsa manifestteki `apiVersion`'ı `traefik.containo.us/v1alpha1` yapın.

---

## 7. Canlıya geçiş kontrol listesi

Staging ortamı yoktur; doğrulama lokal yapılır ve doğrudan canlıya geçilir. Yeni site, eski statik sitenin (nginx) **yerini alır**: Deployment / Service / Ingress adları (`eisa-site`), namespace (`eisa-app`), host'lar ve TLS secret'ı (`eisa-site-tls`) aynıdır. `kubectl apply` bu kaynakları yerinde günceller; **DNS değişmez**.

**Hazırlık (lokal)**
- [ ] `backend`: `..\.venv\Scripts\python.exe -m pytest` yeşil.
- [ ] `npm run dev:web` ile: seed içeriği, menüler, formlar, önizleme ve yayınla → revalidate lokal olarak doğrulandı.
- [ ] `web_site` prod build alındı (`npm --prefix web_site run build`) ve `/api/health` 200 dönüyor.
- [ ] İçerik tonu ve KVKK / çerez metinleri gözden geçirildi.

**Cluster**
- [ ] Mevcut durumun yedeği alındı:
  `kubectl -n eisa-app get deploy,svc,ingress eisa-site -o yaml > eisa-site-eski-yedek.yaml`
  ve çalışan imaj not edildi: `kubectl -n eisa-app get deploy eisa-site -o jsonpath="{..image}"`.
- [ ] Traefik Middleware API sürümü kontrol edildi (§6.4 not).
- [ ] §6.1: `REVALIDATE_SECRET` ve `WEBSITE_SERVER_TOKEN` secret'a eklendi. (Eksikse site pod'ları `CreateContainerConfigError` ile başlamaz.)
- [ ] §6.2: backend imajı deploy edildi, `eisa-app-config` uygulandı, `migrate` ve `website_seed` çalıştı.
- [ ] Editör kullanıcısı oluşturuldu; portalda Web Sitesi modülü açılıyor.
- [ ] Cluster içinden API erişimi doğrulandı (site pod'u ayağa kalkınca):
  `kubectl -n eisa-app exec deploy/eisa-site -- wget -qO- -S http://eisa-api.eisa-app.svc.cluster.local/api/website/public/site/` → 200 JSON (bkz. §9, 301/400 gelirse).
- [ ] §6.4: `.\deploy\deploy-site.ps1 -Tag 2.0.0 -Apply` → rollout başarılı.
- [ ] `https://eisa.com.tr` açılıyor; `https://www.eisa.com.tr/sponsorlar` → 301 `https://eisa.com.tr/sponsorlar`.
- [ ] Eski URL'ler çalışıyor: `/iletisim`, `/sponsorlar`; `sitemap.xml`, `robots.txt` doğru.
- [ ] Portalda küçük bir değişiklik yayınlandı → birkaç saniye içinde **her iki pod**da görünüyor (birkaç kez yenileyin; istekler farklı pod'lara düşer). Backend loglarında revalidate hatası yok.
- [ ] Önizleme linki çalışıyor; "Çık" ile normal moda dönülüyor.
- [ ] Test başvurusu gönderildi → portal **Başvurular**'da göründü; ardından silindi.
- [ ] TLS sertifikası geçerli: `kubectl -n eisa-app get certificate eisa-site-tls`.

**Sonrası**
- [ ] Eski repo `e-isa-company-websit` **arşivlenecek** (GitHub'da "Archive"); README'sine "taşındı: e-isa-monorepo/web_site" notu eklenir. Bu repo üzerinde artık geliştirme yapılmaz.

---

## 8. Rollback

```powershell
kubectl -n eisa-app rollout history deployment/eisa-site
kubectl -n eisa-app rollout undo deployment/eisa-site                  # bir önceki sürüm
kubectl -n eisa-app rollout undo deployment/eisa-site --to-revision=N  # belirli sürüm
```

- **Yeni site → eski statik site:** `rollout undo`, pod şablonunu (nginx imajı, port 8080, uid 101) eski haline döndürür. Service `targetPort` artık **isimli** (`http`) olduğu için eski pod'un 8080 portuna da yönlenir; ek işlem gerekmez. www → apex yönlendirmesi eski sitede de çalışmaya devam eder. Gerekirse §7'de alınan yedekle tamamen dönülebilir: `kubectl apply -f eisa-site-eski-yedek.yaml` (headless service ve middleware zararsızdır, kalabilir).
- **Backend:** `kubectl -n eisa-app rollout undo deployment/eisa-api` (ve `eisa-scheduler`). Migration'lar geri alınmaz; yeni tablolar eski kodu etkilemez.
- **İçerik:** portalda **Revizyonlar → Geri al**.

---

## 9. Entegrasyon notları (site / backend için)

Deploy manifestlerinin varsaydığı, diğer bileşenlerde karşılanması gereken noktalar:

1. **`/api/health` ucu (site):** API'ye dokunmadan `200` dönen hafif bir route (`web_site/src/app/api/health/route.ts`, `dynamic = 'force-dynamic'`). Probe'lar bunu kullanır; `/` API'ye bağımlı olduğundan probe için uygun değildir. Uç yoksa manifestteki probe path'i geçici olarak `/` yapılmalıdır.
2. **Dockerfile (site):** `output: 'standalone'`, çalışma dizini `/app`, kullanıcı uid/gid **1001** (`nextjs:nodejs`), port 3000. Farklı uid kullanılırsa `deploy/eisa-site-production.yaml` içindeki `runAsUser`/`runAsGroup`/`fsGroup` güncellenmelidir. Kök dosya sistemi salt-okunurdur; yazılabilir yerler yalnızca `/app/.next/cache` ve `/tmp`'dir. ISR yeniden üretilen sayfaları `.next/server` altına yazmayı denerse Next uyarı loglayıp bellek içi önbellekle devam eder; sorun olursa `readOnlyRootFilesystem: false` yapılabilir.
3. **Cluster içi HTTP ve Django SSL yönlendirmesi (çözüldü):** Prod'da `SECURE_SSL_REDIRECT=True` olduğundan Django düz HTTP isteklerini `https://`'e yönlendirir. Site API'ye `http://eisa-api.eisa-app.svc.cluster.local` üzerinden gittiği için `core_api/settings.py` içinde `SECURE_REDIRECT_EXEMPT = [r"^api/website/(public|preview)/"]` tanımlandı: yalnızca sitenin okuduğu public/önizleme uçları muaf, admin uçları HTTPS yönlendirmesine tabi (test: `apps/website/tests/test_ssl_yonlendirme.py`).
4. **ALLOWED_HOSTS:** `eisa-app-config` → `DJANGO_ALLOWED_HOSTS` değerine cluster içi host'lar (`eisa-api.eisa-app.svc.cluster.local`, `eisa-api.eisa-app.svc`, `eisa-api`) eklendi; aksi halde Django 400 (`DisallowedHost`) döner.
5. **`SITE_REVALIDATE_URLS=""` (backend):** Prod'da bilinçli olarak boştur (fan-out headless host ile yapılır). `core_api/settings.py` boş değeri boş listeye çevirir; env hiç tanımlanmazsa lokal varsayılan (`http://localhost:3000/api/revalidate`) kullanılır.
6. **İstemci IP'si (site):** Başvuru formu server action'ı `X-Website-Token: <WEBSITE_SERVER_TOKEN>` ve `X-Website-Client-IP: <Traefik'ten gelen X-Forwarded-For'un ilk değeri>` göndermelidir; aksi halde throttle tüm ziyaretçiler için tek IP (site pod'u) üzerinden sayılır.
7. **Medya:** `next/image` `remotePatterns` içinde `https://api.eisa.com.tr/api/media/website/**` (lokal: `http://localhost:8000`) tanımlı olmalıdır. Görsel optimizasyon önbelleği `/app/.next/cache` emptyDir'inde tutulur (pod yeniden başlayınca sıfırlanır).
8. **Turbopack kök dizini (site):** Monorepo kökünde de `package-lock.json` (concurrently) olduğu için `next dev` "multiple lockfiles / inferred workspace root" uyarısı verir. `web_site/next.config.ts` içinde `turbopack.root` (ve standalone için gerekiyorsa `outputFileTracingRoot`) `web_site` dizinine ayarlanmalıdır.

---

## 10. Bilinen sonraki adımlar

- **SMTP bildirimi:** Başvurular şimdilik yalnızca portal gelen kutusuna düşer. SMTP bilgileri netleşince `EMAIL_*` ayarları (`eisa-app-secrets`) ve scheduler job'u ile bildirim eklenecek (`bildirim_alicilari`).
- **Analitik:** Çerez onayı sonrası yüklenecek, KVKK uyumlu bir çözüm (self-hosted Plausible/Umami önerilir) seçilecek; çerez politikası metni buna göre güncellenecek.
- **Kiosk fotoğrafları / render:** Şu an hero ve görseller HTML/SVG mockup'tır. Gerçek fotoğraflar gelince Medya'ya yüklenip ilgili bloklara (ör. `gorsel_metin.gorsel`) eklenebilir.
- **Spam koruması:** Honeypot + IP throttle var; gerekirse Cloudflare Turnstile eklenebilir.
- **Paylaşımlı ISR önbelleği:** Replika sayısı artarsa headless fan-out yerine Redis tabanlı cache handler değerlendirilebilir.
- **Staging:** Yoktur; ileride `yeni.eisa.com.tr` gibi bir host ile ayrı bir Ingress eklenebilir.
- **Eski repo:** `D:\Projeler\e-isa-company-websit` (Spark sitesi) canlıya geçişten sonra arşivlenecek; yalnızca referans olarak kalır.

> **Başlangıç içeriği otomatik yüklenir:** `python manage.py migrate` sonunda site içeriği hiç yoksa (site ayarı ve sayfa yoksa) CONTRACT §9'daki başlangıç içeriği (7 sayfa, menüler, ayarlar, 3 blog yazısı) `website_seed` ile otomatik yüklenir. Mevcut içeriğe asla dokunmaz. Kapatmak için `WEBSITE_AUTO_SEED=False`. Var olan içeriği başlangıç hâline döndürmek için elle: `python manage.py website_seed --force`.

## Site ↔ API güvenliği

```
Tarayıcı ──https──► eisa.com.tr (Next.js sunucusu) ──http + X-Website-Token──► eisa-api (cluster içi)
Tarayıcı ──https──► portal.eisa.com.tr ──https + JWT çerezi──► api.eisa.com.tr/api/website/admin/*
İnternet ──https──► api.eisa.com.tr/api/website/public|preview/*  →  403 (Traefik ipAllowList)
```

- **Tarayıcı API'ye bağlanmaz.** Sayfa HTML'i, form gönderimi (server action) ve görsel optimizasyonu `eisa.com.tr` üzerinden yürür; API çağrılarını yalnızca Next.js sunucusu yapar (BFF).
- **App-key (`X-Website-Token`):** Public ve önizleme uçları token olmadan 404 döner. Değer `eisa-app-secrets` → `WEBSITE_SERVER_TOKEN`, backend ve site pod'larında aynıdır; tarayıcıya gönderilmez (`server-only` modüller).
- **Ingress:** `eisa-api-website-ic-yollar` Ingress + Middleware (`ipAllowList: 127.0.0.1/32`) bu yolları dışarıya kapatır. Traefik ≥ 2.11 gerekir (k3s 1.30+ ile gelir). Daha eski Traefik'te `ipAllowList` yerine `ipWhiteList` yazın.
- **Önizleme:** ayrıca imzalı, 1 saat geçerli token. **Revalidate (backend → site):** `X-Revalidate-Secret`, sabit zamanlı karşılaştırma.
- **Üretim kontrolü:** `WEBSITE_SERVER_TOKEN` / `REVALIDATE_SECRET` boş, varsayılan veya 32 karakterden kısaysa `manage.py check` uyarı verir (`website.W001/W002`); API çalışmaya devam eder, site uçları kapalı kalır (fail-closed).
- **Secret üretimi:** `python -c "import secrets; print(secrets.token_urlsafe(48))"` — iki ayrı değer üretip `eisa-app-secrets`'a ekleyin.
- **Admin uçları** (`/api/website/admin/*`) portal tarafından tarayıcıdan JWT çereziyle çağrıldığı için internete açık kalır; yalnızca `editor`/`superadmin` erişir.
- **Medya** (`/api/media/website/*`) kiosklarla ortak public proxy'dir (yalnızca izinli prefix'ler); site görselleri Next.js görsel optimizasyonu üzerinden sunulur.
