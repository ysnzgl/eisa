# E-İSA — Rancher / Kubernetes Dağıtım Rehberi

**Tarih:** 2026-11-07 (web sitesi + güvenlik güncellemesi)  
**Kapsam:** `api.eisa.com.tr`, `portal.eisa.com.tr` ve `eisa.com.tr` (kurumsal site) servislerinin E-İSA App/Data Node mimarisine uygun Kubernetes dağıtımı  
**Cluster:** Rancher tarafından yönetilen workload K3s cluster — `app-k3s-vm / 10.200.202.20`  
**Namespace:** `eisa-app`  
**Ingress:** Traefik (≥ 2.11) + cert-manager + `letsencrypt-prod`  
**Gizli bilgi politikası:** Parola, token, private key, registry token, DB password, S3 secret ve app-key değerleri **Git'e, dokümana, komut geçmişine yazılmaz.** Bu dokümandaki tüm gizli değerler `<...>` yer tutucusudur.

> Kiosk uçbirim (`kiosk_edge/`) bu akışın dışındadır. Kiosk cihazları Mender golden image / OTA akışıyla yönetilir.

> ⚠️ **Acil — sır rotasyonu:** Bu dokümanın önceki sürümünde ve Git'te takip edilen `backend/.env.prod` dosyasında üretim sırları düz metin olarak bulunuyordu ve GitHub geçmişinde duruyor. Dosyalardan kaldırılmaları yetmez; **§6.4'teki rotasyon adımları uygulanmalıdır.**

---

## 1. Mevcut E-İSA altyapısı

### 1.1 App Node

| Bileşen | Değer |
| --- | --- |
| App PVE public yönetim IP | `31.57.33.172` |
| Public ingress IP | `31.57.33.154` |
| Workload VM | `app-k3s-vm` |
| Workload VM private IP | `10.200.202.20` |
| Kubernetes | K3s |
| Ingress Controller | Traefik |
| TLS | cert-manager + `letsencrypt-prod` |
| Public yönlendirme | `31.57.33.154:80/443 -> 10.200.202.20:80/443` |

### 1.2 Data Node

| Servis | Hedef | Kullanım |
| --- | --- | --- |
| PgBouncer | `10.200.201.10:6432` | API database bağlantısı |
| PostgreSQL | `10.200.201.10:5432` | Doğrudan uygulama bağlantısı için kullanılmaz |
| RustFS S3 API | `http://10.200.201.11:9000` | Dosya / object storage |
| RustFS Console | `http://10.200.201.11:9001` | Sadece VPN/admin |

Karar: API, PostgreSQL'e doğrudan değil PgBouncer üzerinden bağlanır. Büyük dosya, upload, medya ve artifact benzeri kalıcı dosyalar local container filesystem'e değil RustFS/S3'e yazılır.

---

## 2. Domain ve DNS

| Domain | Hedef |
| --- | --- |
| `portal.eisa.com.tr` | Public A kaydı: `31.57.33.154` |
| `api.eisa.com.tr` | Public A kaydı: `31.57.33.154` |
| `eisa.com.tr` | Public A kaydı: `31.57.33.154` |
| `www.eisa.com.tr` | Public A kaydı: `31.57.33.154` (Traefik `eisa.com.tr`'ye 301 yönlendirir) |

Cluster içi cert-manager HTTP-01 self-check için CoreDNS split DNS tarafında da şu çözümleme bulunmalıdır:

```text
portal.eisa.com.tr -> 10.200.202.20
api.eisa.com.tr    -> 10.200.202.20
eisa.com.tr        -> 10.200.202.20
www.eisa.com.tr    -> 10.200.202.20
```

Doğrulama:

```bash
for h in portal.eisa.com.tr api.eisa.com.tr eisa.com.tr www.eisa.com.tr; do
  kubectl run dns-test -n cert-manager --image=busybox:1.36 --restart=Never --rm -it -- nslookup $h
done
```

Beklenen cevap: `10.200.202.20`.

---

## 3. Container registry kararı

Rancher üzerinde görülen **Continuous Delivery**, image registry değildir. Continuous Delivery, Rancher'ın Fleet tabanlı GitOps dağıtım özelliğidir. Image build/push yapmaz; Git reposundaki YAML/Helm/Kustomize kaynaklarını cluster'a uygular.

| İhtiyaç | Önerilen araç |
| --- | --- |
| Image saklama | Mevcut: `10.200.202.20:30500` (cluster içi registry). Alternatif: GHCR, GitLab Registry, Harbor |
| GitOps deploy | Rancher Continuous Delivery / Fleet |

İleride `registry.eisa.com.tr` istenirse Harbor kurulabilir; ilk aşamada Harbor'u aynı workload cluster içinde çalıştırmak bootstrap karmaşası yaratır.

> Registry `10.200.202.20:30500` dışarıya (public IP) açılmamalıdır; yalnızca VPN/iç ağdan erişilmelidir.

---

## 4. Image build & push

```powershell
$REGISTRY = "10.200.202.20:30500"
$TAG      = "1.0.14"     # API / Portal / Kiosk demo
$SITE_TAG = "2.0.0"      # Kurumsal site (ayrı sürümlenir)

docker build --no-cache -t "$REGISTRY/eisa-api:$TAG" ./backend
docker push "$REGISTRY/eisa-api:$TAG"

docker build --no-cache -t "$REGISTRY/eisa-portal:$TAG" ./web_panels
docker push "$REGISTRY/eisa-portal:$TAG"

docker build --no-cache -t "$REGISTRY/eisa-kiosk:$TAG" ./kiosk_edge
docker push "$REGISTRY/eisa-kiosk:$TAG"

# Kurumsal site — build sırasında backend'e erişim GEREKMEZ
docker build --no-cache -t "$REGISTRY/eisa-site:$SITE_TAG" ./web_site
docker push "$REGISTRY/eisa-site:$SITE_TAG"
# veya tek komut: .\deploy\deploy-site.ps1 -Tag $SITE_TAG

Write-Host "Yeni tag: $TAG / site: $SITE_TAG"
```

> `backend/.dockerignore` ortam dosyalarını (`.env*`), yerel veritabanını ve logları imaja almaz. İmajlarda sır bulunmaz; tüm değerler ConfigMap/Secret'tan gelir.

Rollout:

```bash
REGISTRY="10.200.202.20:30500"
TAG="1.0.14"
SITE_TAG="2.0.0"

# API
kubectl -n eisa-app set image deployment/eisa-api api="${REGISTRY}/eisa-api:${TAG}"
kubectl -n eisa-app rollout status deployment/eisa-api --timeout=180s

# Migration (web sitesi başlangıç içeriği, boş veritabanında otomatik yüklenir — §5.4)
kubectl -n eisa-app exec deployment/eisa-api -c api -- python manage.py migrate --noinput
kubectl -n eisa-app exec deployment/eisa-api -c api -- python manage.py check

# Scheduler
kubectl -n eisa-app set image deployment/eisa-scheduler scheduler="${REGISTRY}/eisa-api:${TAG}"
kubectl -n eisa-app rollout status deployment/eisa-scheduler --timeout=180s

# Web Panel
kubectl -n eisa-app set image deploy/eisa-portal portal="${REGISTRY}/eisa-portal:${TAG}"
kubectl -n eisa-app rollout status deploy/eisa-portal --timeout=180s

# Kurumsal site
kubectl -n eisa-app set image deploy/eisa-site site="${REGISTRY}/eisa-site:${SITE_TAG}"
kubectl -n eisa-app rollout status deploy/eisa-site --timeout=180s

# demo.eisa.com.tr
kubectl -n eisa-app set image deploy/eisa-kiosk-demo kiosk="${REGISTRY}/eisa-kiosk:${TAG}"
kubectl -n eisa-app rollout status deploy/eisa-kiosk-demo --timeout=180s

kubectl -n eisa-app get pods
```

`latest` kullanılmaz. Her deploy versiyonlu veya commit SHA tabanlı tag ile yapılır (`1.0.0`, `2026.06.04-001`, `git-<short-sha>`).

---

## 5. Kurumsal site (eisa.com.tr)

### 5.1 Mimari ve güvenlik katmanları

```text
Tarayıcı ──https──► eisa.com.tr (Next.js, eisa-site) ──http + X-Website-Token──► eisa-api (cluster içi)
Tarayıcı ──https──► portal.eisa.com.tr ──https + JWT çerezi──► api.eisa.com.tr/api/website/admin/*
eisa-api ──http + X-Revalidate-Secret──► eisa-site pod'ları (headless service, yayın bildirimi)
İnternet ──► api.eisa.com.tr/api/website/public|preview/*   → 403 (Traefik ipAllowList)
İnternet ──► eisa.com.tr/api/revalidate                      → 403 (Traefik ipAllowList)
```

| Katman | Koruma |
| --- | --- |
| Tarayıcı ↔ API | Tarayıcı API'ye bağlanmaz. Sayfa, form (server action) ve görseller `eisa.com.tr` üzerinden; API'yi yalnızca site sunucusu çağırır. |
| Site → API (app-key) | `X-Website-Token` = `WEBSITE_SERVER_TOKEN`. Yoksa/yanlışsa API **404** döner. Üretimde geliştirme token'ı kabul edilmez (fail-closed). |
| İnternet → site uçları | `eisa-api-website-ic-yollar` Ingress'i public/preview yollarını dışarıya kapatır. |
| API → site (revalidate) | `X-Revalidate-Secret`, sabit zamanlı karşılaştırma; `/api/revalidate` dışarıya kapalı (`eisa-site-ic-yollar`). |
| Önizleme | İmzalı, 1 saat geçerli token + app-key. |
| Portal (yönetim) | JWT çerezi; yalnızca `superadmin` / `editor` rolleri. Editör yalnızca Web Sitesi modülünü görür. |
| Pod güvenliği | Non-root (uid 1001), salt-okunur kök FS, tüm capability'ler kapalı, SA token bağlanmaz. |
| Başvuru formu | Honeypot + IP başına saatte 5 istek (gerçek istemci IP'si site sunucusundan app-key ile aktarılır). |

### 5.2 Manifestler

| Dosya | İçerik |
| --- | --- |
| `deploy/eisa-site-production.yaml` | Deployment, PDB, Service, headless Service, www yönlendirme + HSTS middleware, Ingress, `/api/revalidate` kapatma |
| `deploy/eisa-site-networkpolicy.yaml` | **Opsiyonel** NetworkPolicy (yalnızca Traefik, eisa-api ve kubelet erişir) |
| `deploy/eisa-app-production.yaml` | Backend ConfigMap'te `SITE_PUBLIC_URL`, `SITE_REVALIDATE_HEADLESS_HOST`; public/preview kapatma Ingress'i |

### 5.3 İlk kurulum (eski statik siteden geçiş)

1. Traefik sürümünü doğrula (≥ 2.11, `ipAllowList` için):

   ```bash
   kubectl -n kube-system get deploy traefik -o jsonpath='{.spec.template.spec.containers[0].image}'
   ```

   2.11'den eskiyse manifestlerde `ipAllowList` yerine `ipWhiteList` yazılır.

2. Secret anahtarlarını ekle (§6.2) — **site, anahtarlar olmadan başlamaz.**
3. Backend'i güncelle ve migrate et (§4). `python manage.py check` çıktısında `website.W001/W002` uyarısı **olmamalı.**
4. Eski siteyi yedekle: `kubectl -n eisa-app get deploy,svc,ingress eisa-site -o yaml > eisa-site-eski-yedek.yaml`
5. Site imajını push et (§4) ve manifesti uygula:

   ```bash
   kubectl apply -f deploy/eisa-site-production.yaml
   kubectl -n eisa-app rollout status deployment/eisa-site --timeout=180s
   ```

6. Doğrula (§5.5). Sonra (opsiyonel) NetworkPolicy: dosyanın başındaki kontrolleri yapıp `kubectl apply -f deploy/eisa-site-networkpolicy.yaml`.

### 5.4 İçerik ve kullanıcılar

- **Başlangıç içeriği:** `migrate` sonunda site içeriği hiç yoksa (7 sayfa, menüler, ayarlar, 3 blog yazısı) otomatik yüklenir; mevcut içeriğe dokunulmaz. Kapatmak için `WEBSITE_AUTO_SEED=False`.
- **Editör kullanıcısı:** Portal → Kullanıcı Yönetimi → rol: *Editör (Web Sitesi)*. Editör yalnızca `/admin/web-sitesi` modülünü görür.
- İçerik yönetimi: portal → Web Sitesi → her ekranda **Yardım** ve **Önizle** butonları.

### 5.5 Doğrulama

```bash
# Site ayakta
curl -sI https://eisa.com.tr | head -n 1                     # HTTP/2 200
curl -sI https://www.eisa.com.tr | grep -i location          # https://eisa.com.tr/

# Dışarıya kapalı olması gerekenler (403 beklenir)
curl -s -o /dev/null -w "%{http_code}\n" https://api.eisa.com.tr/api/website/public/site/
curl -s -o /dev/null -w "%{http_code}\n" https://api.eisa.com.tr/api/website/preview/sayfalar/anasayfa/
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://eisa.com.tr/api/revalidate

# Site pod'u API'ye app-key ile erişebiliyor mu? (token pod içindeki ortam değişkeninden okunur,
# komut geçmişine yazılmaz) — 200 ve JSON beklenir
kubectl -n eisa-app exec deploy/eisa-site -- sh -c \
  'wget -qO- --header "X-Website-Token: $WEBSITE_SERVER_TOKEN" http://eisa-api.eisa-app.svc.cluster.local/api/website/public/sayfalar/ | head -c 200; echo'

# Yayın bildirimi: portalda bir sayfayı yayınlayın, site loglarında görünmeli
kubectl -n eisa-app logs deploy/eisa-site --tail=20 | grep "e-isa revalidate"
```

### 5.6 Geri alma

```bash
kubectl -n eisa-app rollout undo deployment/eisa-site
# Eski statik siteye tam dönüş:
kubectl apply -f eisa-site-eski-yedek.yaml
```

---

## 6. Uygulama secret'ları

`eisa-app-production.yaml` ve `eisa-site-production.yaml` **secret içermez.** Tüm gizli değerler `eisa-app-secrets` Secret'ında durur.

### 6.1 Değer üretimi

Her anahtar için ayrı, rastgele değer üretin (değerleri bir parola yöneticisinde saklayın):

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"   # DJANGO_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"   # WEBSITE_SERVER_TOKEN
python -c "import secrets; print(secrets.token_urlsafe(48))"   # REVALIDATE_SECRET
```

### 6.2 Web sitesi anahtarları — tek komutla yönetim (önerilen)

```powershell
.\deploy\website-anahtarlari.ps1                  # durum raporu (hiçbir değer gösterilmez)
.\deploy\website-anahtarlari.ps1 -Islem olustur   # ilk kurulum: eksik anahtarları üretir, pod'ları yeniden başlatır
.\deploy\website-anahtarlari.ps1 -Islem yenile    # rotasyon: iki anahtarı da yeniler (onay ister)
```

Betik: değerleri kriptografik rastgele üretir, Secret'ı diğer anahtarlara dokunmadan günceller, `eisa-api`, `eisa-scheduler`, `eisa-site`'ı yeniden başlatır ve sonra doğrular: anahtarlar var mı/güçlü mü, **pod'lar Secret'taki güncel değeri mi kullanıyor** (özet karşılaştırması), site API'ye app-key ile erişebiliyor mu (200), `manage.py check` uyarı veriyor mu. Sorun varsa çıkış kodu 1.

### 6.2.1 Elle ekleme (diğer anahtarları SİLMEZ)

**Rancher UI:** Cluster → *Storage → Secrets* → `eisa-app` / `eisa-app-secrets` → **Edit Config** → *Add* → anahtar adı ve değer → Save.

**PowerShell (Windows):** `docs/web-sitesi/README.md` §6.1 — değerleri kendisi üretir, ekrana basmaz, `--patch-file` ile ekler.

**kubectl / bash** (değerleri komut geçmişine yazmamak için önce ortam değişkenine okuyun):

```bash
read -rs WEBSITE_SERVER_TOKEN && read -rs REVALIDATE_SECRET
kubectl -n eisa-app patch secret eisa-app-secrets --type merge -p "$(printf \
  '{"stringData":{"WEBSITE_SERVER_TOKEN":"%s","REVALIDATE_SECRET":"%s"}}' \
  "$WEBSITE_SERVER_TOKEN" "$REVALIDATE_SECRET")"
unset WEBSITE_SERVER_TOKEN REVALIDATE_SECRET

# Uygula: secret değişikliği çalışan pod'lara otomatik yansımaz
kubectl -n eisa-app rollout restart deploy/eisa-api deploy/eisa-scheduler deploy/eisa-site
```

> ⚠️ `kubectl create secret ... --dry-run=client -o yaml | kubectl apply -f -` komutu Secret'ı **yalnızca verilen anahtarlarla yeniden yazar**; diğer anahtarlar (DB parolası vb.) silinir. Yeni anahtar eklerken `patch` veya Rancher UI kullanın.

### 6.3 İlk oluşturma (sıfır kurulum)

```bash
kubectl -n eisa-app create secret generic eisa-app-secrets \
  --from-literal=DJANGO_SECRET_KEY='<64+ karakter rastgele>' \
  --from-literal=DB_USER='eisa_user' \
  --from-literal=DB_PASSWORD='<güçlü parola>' \
  --from-literal=S3_ACCESS_KEY='<eisa-files bucket kullanıcısı>' \
  --from-literal=S3_SECRET_KEY='<bucket kullanıcısı secret>' \
  --from-literal=WEBSITE_SERVER_TOKEN='<48+ karakter rastgele>' \
  --from-literal=REVALIDATE_SECRET='<48+ karakter rastgele>'
```

> Komut satırına yazılan değerler shell geçmişine düşer. Mümkünse Rancher UI'ı veya `read -rs` ile ortam değişkeni kullanın; işlem sonrası `history -c`.

Secret/config ayrımı:

| Değer | Nerede durur? | Kim okur? |
| --- | --- | --- |
| `DB_HOST`, `DB_PORT`, `DB_NAME` | ConfigMap | API, scheduler |
| `DB_USER`, `DB_PASSWORD` | Secret | API, scheduler |
| `S3_ENDPOINT`, `S3_BUCKET`, `S3_REGION` | ConfigMap | API, scheduler |
| `S3_ACCESS_KEY`, `S3_SECRET_KEY` | Secret | API, scheduler |
| `DJANGO_SECRET_KEY` | Secret | API, scheduler |
| `WEBSITE_SERVER_TOKEN` | Secret | API (envFrom) + **site** (yalnızca bu anahtar, secretKeyRef) |
| `REVALIDATE_SECRET` | Secret | API (envFrom) + **site** (yalnızca bu anahtar, secretKeyRef) |
| `SITE_PUBLIC_URL`, `SITE_REVALIDATE_HEADLESS_HOST` | ConfigMap | API |

Site pod'u Secret'ın tamamını değil, **yalnızca iki anahtarını** görür; DB ve S3 sırlarına erişimi yoktur.

RustFS root/admin key uygulamaya verilmez. Uygulama için sadece `eisa-files` bucket yetkisi olan ayrı kullanıcı açılır.

### 6.4 Sızmış sırların rotasyonu (zorunlu)

Önceki sürümde bu doküman ve `backend/.env.prod` (Git'te takip ediliyordu, artık değil) üretim sırlarını içeriyordu. Git geçmişi silinse bile kopyalar (klonlar, GitHub önbelleği) kalabileceği için **değerler değiştirilmelidir:**

| Sır | Rotasyon | Etki |
| --- | --- | --- |
| `DB_PASSWORD` | Data Node'da `ALTER ROLE eisa_user WITH PASSWORD '<yeni>';` + PgBouncer `userlist.txt` güncelle → Secret'ı patch'le → API/scheduler restart | Kısa bağlantı kesintisi |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | RustFS console → `eisa-files` kullanıcısına yeni key → Secret → restart → eski key'i sil | — |
| `DJANGO_SECRET_KEY` | Yeni değer → Secret → restart | Tüm oturumlar/JWT'ler geçersiz olur; kullanıcılar yeniden giriş yapar |
| Superuser parolası | `kubectl -n eisa-app exec -it deploy/eisa-api -- python manage.py changepassword yasin.ozgul` | — |
| Yerel geliştirme (`backend/.env`) parolaları | Yerel Postgres/RustFS parolalarını değiştirin (canlıyla aynıysa öncelikli) | — |

Git geçmişinden temizlik (opsiyonel, rotasyondan **sonra**): `git filter-repo` ile dosya geçmişi temizlenip force-push yapılır; tüm ekip yeniden klonlamalıdır. Rotasyon yapılmadan geçmiş temizliği tek başına yeterli değildir.

---

## 7. Manifest dosyaları

```text
deploy/eisa-app-production.yaml       # API, Portal, Scheduler, ConfigMap, Ingress'ler
deploy/eisa-site-production.yaml      # Kurumsal site
deploy/eisa-site-networkpolicy.yaml   # (opsiyonel) site ağ izolasyonu
deploy/eisa-kiosk-demo.yaml           # demo.eisa.com.tr
```

Kaynaklar:

```text
Namespace:     eisa-app
ConfigMap:     eisa-app-config
Deployment:    eisa-api, eisa-portal, eisa-scheduler, eisa-site
Service:       eisa-api, eisa-portal, eisa-site, eisa-site-headless
PDB:           eisa-site
Middleware:    eisa-api-website-ic-yollar, eisa-site-www-redirect, eisa-site-guvenlik-basliklari, eisa-site-ic-yollar
Ingress:       eisa-app, eisa-api-website-ic-yollar, eisa-site, eisa-site-ic-yollar
```

Superuser oluşturma (parola **etkileşimli** sorulur; komut satırına ve geçmişe yazılmaz):

```bash
kubectl -n eisa-app exec -it deploy/eisa-api -- python manage.py createsuperuser --username yasin.ozgul --email yasin.ozgul@eisa.com.tr
```

Migrate ve statik dosyalar:

```bash
kubectl -n eisa-app exec -it deploy/eisa-api -- python manage.py migrate --noinput
kubectl -n eisa-app exec -it deploy/eisa-api -- python manage.py collectstatic --noinput
```

Önemli düzeltmeler:

- `DB_USER=eisa_user` olarak Data Node standardına çekildi.
- `image:latest` kaldırıldı; versiyonlu image tag kullanıldı.
- API readiness/liveness probe içine `Host: api.eisa.com.tr` header'ı eklendi.
- Django için `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, `SECURE_PROXY_SSL_HEADER`, `USE_X_FORWARDED_HOST` env değerleri eklendi.
- Portal probe `/` üzerinden kontrol edilir.
- Traefik + cert-manager + `letsencrypt-prod` kullanılır.
- Web sitesi: app-key, public/preview yollarının ve `/api/revalidate`'in dışarıya kapatılması, salt-okunur kök FS (ISR önbelleği emptyDir), PDB.

---

## 8. Manuel kubectl deploy akışı

```bash
kubectl apply -f deploy/eisa-app-production.yaml
kubectl apply -f deploy/eisa-site-production.yaml
```

Rollout kontrolü:

```bash
kubectl -n eisa-app rollout status deploy/eisa-api --timeout=180s
kubectl -n eisa-app rollout status deploy/eisa-portal --timeout=180s
kubectl -n eisa-app rollout status deploy/eisa-site --timeout=180s
kubectl -n eisa-app get pods -o wide
kubectl -n eisa-app get svc
kubectl -n eisa-app get ingress
kubectl -n eisa-app get certificate
```

HTTP testleri:

```bash
curl -I https://api.eisa.com.tr/healthz
curl -I https://portal.eisa.com.tr
curl -I https://eisa.com.tr
```

Site için güvenlik doğrulaması: §5.5.

---

## 9. Rancher UI ile manuel deploy

1. Rancher UI → workload cluster: `eisa-app-workload` veya mevcut workload cluster.
2. **Cluster Explorer → Workloads → Import YAML**.
3. Önce `eisa-app-production.yaml`, sonra `eisa-site-production.yaml` içeriğini yapıştır → Apply.
4. **Workloads → Deployments** altında `eisa-api`, `eisa-portal`, `eisa-site` podlarını kontrol et.
5. **Service Discovery → Ingresses** altında `eisa-app`, `eisa-api-website-ic-yollar`, `eisa-site`, `eisa-site-ic-yollar` ingress'lerini kontrol et.
6. **Certificates** altında `eisa-app-tls` ve `eisa-site-tls` sertifikalarının `Ready` olduğunu doğrula.

---

## 10. Rancher Continuous Delivery / Fleet kullanımı

Rancher Continuous Delivery, Fleet tabanlı GitOps akışıdır. Önerilen kullanım:

```text
Developer commit/push
-> CI image build
-> Registry image push
-> Manifest tag güncelleme
-> Git commit
-> Rancher Continuous Delivery / Fleet manifesti cluster'a uygular
```

### 10.1 Repo dizin önerisi

```text
repo-root/
├─ backend/
├─ web_panels/
├─ web_site/
├─ deploy/
│  ├─ eisa-app-production.yaml
│  ├─ eisa-site-production.yaml
│  └─ fleet.yaml
└─ .github/
   └─ workflows/
      └─ build-images.yml
```

### 10.2 `fleet.yaml` örneği

```yaml
namespace: eisa-app
helm:
  releaseName: eisa-app
```

> Fleet ile yalnızca manifestler senkronize edilir; **Secret'lar Git'e konmaz**, cluster'da elle (§6) veya SealedSecrets / External Secrets ile yönetilir.

### 10.3 Rancher UI üzerinden GitRepo oluşturma

1. Rancher UI → sol menü → **Continuous Delivery**.
2. Workspace olarak genelde `fleet-default` seçilir.
3. **Git Repos → Create**.
4. Repository URL girilir. Branch: `main`. Paths: `deploy`.
5. Target olarak workload cluster seçilir (örn. `eisa-app-workload`).
6. Repo private ise Git credential secret tanımlanır.
7. Save → Fleet bundle `Active/Ready` olana kadar beklenir.

### 10.4 GitRepo CR örneği

```yaml
apiVersion: fleet.cattle.io/v1alpha1
kind: GitRepo
metadata:
  name: eisa-app
  namespace: fleet-default
spec:
  repo: https://github.com/ysnzgl/REPLACE_REPO.git
  branch: main
  clientSecretName: eisa-git-credentials   # private repo
  paths:
    - deploy
  targets:
    - name: eisa-workload
      clusterName: eisa-app-workload
```

---

## 11. GitHub Actions örnek mantığı

Continuous Delivery image build yapmadığı için CI pipeline gerekir:

```text
1. backend, portal, site image build
2. registry'ye push
3. deploy/*.yaml içindeki image tag değerini güncelle
4. değişikliği main branch'e commit et
5. Fleet değişikliği algılar ve deploy eder
```

> CI'da registry/cluster kimlik bilgileri yalnızca CI secret'larında tutulur; workflow dosyasına yazılmaz. `10.200.202.20:30500` iç ağda olduğundan CI runner'ın VPN/iç ağ erişimi gerekir (veya GHCR kullanılır).

---

## 12. Sürüm yükseltme

Manuel yaklaşım: §4 rollout komutları.

GitOps yaklaşımı: yeni image tag push → YAML'da tag değişikliği → Git commit → Fleet reconcile.

Rollback:

```bash
kubectl -n eisa-app rollout undo deploy/eisa-api
kubectl -n eisa-app rollout undo deploy/eisa-portal
kubectl -n eisa-app rollout undo deploy/eisa-site
```

GitOps kullanılıyorsa kalıcı rollback için Git'teki image tag de eski sürüme çekilmelidir.

---

## 13. Ölçekleme

| Servis | Replika | Not |
| --- | ---: | --- |
| `eisa-api` | 2+ | Stateless kalmalı |
| `eisa-portal` | 2+ | Stateless statik içerik |
| `eisa-site` | 2+ | ISR önbelleği pod başına; yayın bildirimi headless service ile tüm pod'lara gider. PDB: en az 1 pod |
| Scheduler / background job | 1 | APScheduler duplicate job riskinden dolayı tek replika |
| PostgreSQL | App cluster içinde değil | Data Node üzerinde |
| RustFS | App cluster içinde değil | Data Node üzerinde |

---

## 14. Backup yaklaşımı

| Katman | Backup |
| --- | --- |
| PostgreSQL (site içeriği dahil) | `pg_dump`, `pg_dumpall`, ileride WAL/Barman |
| MongoDB / Mender | `mongodump` |
| RustFS (site görselleri dahil: `website/` prefix) | bucket mirror/replication |
| Kubernetes manifests | Git repo |
| Secrets | Parola yöneticisi; hedef: SealedSecrets/SOPS/Vault/External Secrets |

---

## 15. Sorun giderme

| Belirti | İlk kontrol |
| --- | --- |
| `ImagePullBackOff` | `eisa-regcred` doğru namespace'te mi? Image adı/tag doğru mu? K3s `registries.yaml` iç registry'yi tanıyor mu? |
| API readiness fail | `kubectl -n eisa-app logs deploy/eisa-api --previous`; `/healthz` var mı? `Host` header sorunu var mı? |
| Django `DisallowedHost` | `DJANGO_ALLOWED_HOSTS` (cluster içi `eisa-api.eisa-app.svc.cluster.local` dahil) ve probe Host header |
| CORS/CSRF hatası | `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOW_CREDENTIALS` |
| DB bağlantı hatası | `10.200.201.10:6432` erişimi, DB password ve PgBouncer |
| S3 bağlantı hatası | RustFS endpoint, bucket, access policy ve path-style ayarı |
| TLS sertifikası gelmiyor | Public DNS ve CoreDNS split DNS (§2) |
| Fleet deploy etmiyor | GitRepo path, branch, target cluster ve Git credential secret |
| `eisa-site` `CreateContainerConfigError` | `eisa-app-secrets` içinde `WEBSITE_SERVER_TOKEN` / `REVALIDATE_SECRET` yok (§6.2) |
| Site sayfaları 404 / "içerik yüklenemedi" | Site ve API'deki `WEBSITE_SERVER_TOKEN` farklı veya API'de varsayılan değer. `python manage.py check` → `website.W001`. Secret değişikliği sonrası **iki tarafı da** restart edin. |
| Yayınlanan değişiklik sitede görünmüyor | API ConfigMap `SITE_REVALIDATE_HEADLESS_HOST`, `REVALIDATE_SECRET` iki tarafta aynı mı? `kubectl logs deploy/eisa-api | grep website_revalidate` |
| Site loglarında `Failed to update prerender cache` | `route-cache` emptyDir bağlı mı (`/app/.next/server/route-cache`)? |
| `ipAllowList` Middleware hatası | Traefik < 2.11 → `ipWhiteList` kullanın (§5.3) |

---

## 16. Güvenlik kontrol listesi

**Sırlar**

- [ ] §6.4 rotasyonu yapıldı (DB, S3, DJANGO_SECRET_KEY, superuser)
- [ ] Git'te `.env` / `.env.prod` takip edilmiyor (`git ls-files | grep .env`); `.gitignore` kuralı aktif
- [ ] `DJANGO_SECRET_KEY` secret içinde ve 50+ karakter
- [ ] `DB_PASSWORD`, `S3_SECRET_KEY` secret içinde
- [ ] `WEBSITE_SERVER_TOKEN`, `REVALIDATE_SECRET` secret içinde, 32+ karakter, birbirinden farklı
- [ ] `python manage.py check` → `website.W00x` uyarısı yok
- [ ] Registry token secret içinde; registry public IP'ye açık değil
- [ ] Doküman/komut geçmişinde düz sır yok

**Uygulama**

- [ ] `DJANGO_DEBUG=0`
- [ ] Image tag `latest` değil; imajlarda `.env` yok (`docker run --rm <imaj> ls -a /app`)
- [ ] API, Portal ve Site non-root container olarak çalışıyor; site kök FS salt-okunur
- [ ] API CORS sadece `https://portal.eisa.com.tr`
- [ ] JWT cookie `Secure=True`, `SameSite=Strict`
- [ ] TLS cert-manager ile aktif (`eisa-app-tls`, `eisa-site-tls`)

**Web sitesi**

- [ ] `https://api.eisa.com.tr/api/website/public/site/` dışarıdan **403**
- [ ] `https://eisa.com.tr/api/revalidate` dışarıdan **403**
- [ ] Site pod'u API'ye app-key ile erişiyor (§5.5)
- [ ] `www.eisa.com.tr` → `eisa.com.tr` 301
- [ ] Editör kullanıcıları yalnızca Web Sitesi modülünü görüyor

**Altyapı**

- [ ] DB/S3 public açılmıyor
- [ ] Git repo gerçek secret içermiyor
- [ ] Rancher management cluster'a workload deploy edilmiyor
- [ ] (Opsiyonel) `eisa-site-networkpolicy.yaml` uygulandı
