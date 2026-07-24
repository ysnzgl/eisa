# E-İSA — Rancher / Kubernetes Dağıtım Rehberi

**Tarih:** 2026-06-04  
**Kapsam:** `portal.eisa.com.tr` ve `api.eisa.com.tr` servislerinin E-İSA App/Data Node mimarisine uygun Kubernetes dağıtımı  
**Cluster:** Rancher tarafından yönetilen workload K3s cluster — `app-k3s-vm / 10.200.202.20`  
**Namespace:** `eisa-app`  
**Ingress:** Traefik + cert-manager + `letsencrypt-prod`  
**Gizli bilgi politikası:** Parola, token, private key, registry token, DB password ve S3 secret değerleri Git'e yazılmaz.

Bu doküman E-İSA monorepo'sunun **API/backend** ve **Portal/frontend** servislerini mevcut E-İSA altyapısına göre dağıtmak için kullanılır.

> Kiosk uçbirim (`kiosk_edge/`) bu akışın dışındadır. Kiosk cihazları Mender golden image / OTA akışıyla yönetilir.

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

Cluster içi cert-manager HTTP-01 self-check için CoreDNS split DNS tarafında da şu çözümleme bulunmalıdır:

```text
portal.eisa.com.tr -> 10.200.202.20
api.eisa.com.tr    -> 10.200.202.20
```

Doğrulama:

```bash
kubectl run dns-test -n cert-manager --image=busybox:1.36 --restart=Never --rm -it -- nslookup portal.eisa.com.tr
kubectl run dns-test -n cert-manager --image=busybox:1.36 --restart=Never --rm -it -- nslookup api.eisa.com.tr
```

Beklenen cevap: `10.200.202.20`.

---

## 3. Container registry kararı

Rancher üzerinde görülen **Continuous Delivery**, image registry değildir. Continuous Delivery, Rancher'ın Fleet tabanlı GitOps dağıtım özelliğidir. Image build/push yapmaz; Git reposundaki YAML/Helm/Kustomize kaynaklarını cluster'a uygular.

Bu nedenle iki ayrı mekanizma gerekir:

| İhtiyaç | Önerilen araç |
| --- | --- |
| Image saklama | GHCR, Docker Hub private, GitLab Registry, Harbor vb. |
| GitOps deploy | Rancher Continuous Delivery / Fleet |

### 3.1 Kısa vadeli öneri

İlk üretim öncesi en temiz seçenek:

```text
GHCR veya GitLab Container Registry
```

Sebep: Registry'yi kurmadan image push/pull akışı hemen çalışır. Daha sonra self-host registry gerekiyorsa Harbor kurulabilir.

### 3.2 Uzun vadeli self-host registry seçeneği

İleride `registry.eisa.com.tr` istenirse Harbor kurulabilir. Ancak ilk aşamada Harbor'u aynı workload cluster içinde çalıştırmak bootstrap karmaşası yaratır: cluster'ın bazı image'ları çekebilmesi için registry'nin zaten çalışıyor olması gerekir. Bu yüzden ilk adımda GHCR/GitLab Registry daha sağlıklıdır.

---

## 4. Image build & push

Örnek GHCR akışı:

```powershell
$REGISTRY = "10.200.202.20:30500"
$TAG      = "1.0.3"

docker build --no-cache -t "$REGISTRY/eisa-api:$TAG" ./backend
docker build --no-cache -t "$REGISTRY/eisa-portal:$TAG" ./web_panels
docker build --no-cache -t "$REGISTRY/eisa-kiosk:$TAG" ./kiosk_edge

docker push "$REGISTRY/eisa-api:$TAG"
docker push "$REGISTRY/eisa-portal:$TAG"
docker push "$REGISTRY/eisa-kiosk:$TAG"

Write-Host "Yeni tag: $TAG"
```

REGISTRY="10.200.202.20:30500"
TAG="1.0.3"

kubectl -n eisa-app set image deploy/eisa-api api=${REGISTRY}/eisa-api:${TAG}
kubectl -n eisa-app set image deploy/eisa-portal portal=${REGISTRY}/eisa-portal:${TAG}
kubectl -n eisa-app set image deploy/eisa-kiosk-demo kiosk=${REGISTRY}/eisa-kiosk:${TAG}

kubectl -n eisa-app rollout status deploy/eisa-api --timeout=180s
kubectl -n eisa-app rollout status deploy/eisa-portal --timeout=180s
kubectl -n eisa-app rollout status deploy/eisa-kiosk-demo --timeout=180s

#migration için:

kubectl -n eisa-app exec deployment/eisa-api -- python manage.py migrate
kubectl -n eisa-app rollout restart deployment/eisa-api
kubectl -n eisa-app rollout status deployment/eisa-api

#Manifest içindeki image alanları buna göre güncellenir:

```yaml
image: registry.eisa.local:80/eisa-api:1.0.0
image: registry.eisa.local:80/eisa-portal:1.0.0
```

`latest` kullanılmaz. Her deploy versiyonlu veya commit SHA tabanlı tag ile yapılır.

Örnek tag stratejisi:

```text
1.0.0
2026.06.04-001
git-<short-sha>
```

---


## 6. Uygulama secret'ları

`eisa-app-production.yaml` secret içermez. Şu secret cluster üzerinde oluşturulur:

```bash
kubectl -n eisa-app create secret generic eisa-app-secrets \
  --from-literal=DJANGO_SECRET_KEY='J0b1h4QCpEfvADXwuSXr76FlyqwLyJU69zkceuUaQZP_2mvzVwXcFzowr_N7e9tB-EdCOise9G-azbOmenqYgw' \
  --from-literal=DB_USER='eisa_user' \
  --from-literal=DB_PASSWORD='zVz4BW7KazGSSsLa' \
  --from-literal=S3_ACCESS_KEY='eisaadmin' \
  --from-literal=S3_SECRET_KEY='Pv03niPXk0p0rSsMVhRXAErsoY1x7LCNF6PkVgno' \
  --dry-run=client -o yaml | kubectl apply -f -
```

Beklenen secret/config ayrımı:

| Değer | Nerede durur? |
| --- | --- |
| `DB_HOST`, `DB_PORT`, `DB_NAME`| ConfigMap |
| `DB_PASSWORD`, `DB_USER`  | Secret |
| `S3_ENDPOINT`, `S3_BUCKET`, `S3_REGION` | ConfigMap |
| `S3_ACCESS_KEY`, `S3_SECRET_KEY` | Secret |
| `DJANGO_SECRET_KEY` | Secret |

RustFS root/admin key uygulamaya verilmez. Uygulama için sadece `eisa-files` bucket yetkisi olan ayrı kullanıcı açılır.

---

## 7. Manifest dosyası

Güncel manifest dosyası:

```text
eisa-app-production.yaml
```

Kaynaklar:

```text
Namespace:    eisa-app
ConfigMap:    eisa-app-config
Deployment:   eisa-api
Service:      eisa-api
Deployment:   eisa-portal
Service:      eisa-portal
Ingress:      eisa-app
```

kubectl -n eisa-app exec -it deploy/eisa-api -- python manage.py createsuperuser --username yasin.ozgul --password 92746**Ysn92746** --email yasin.ozgul@eisa.com.tr

Migrate varsa

kubectl -n eisa-app exec -it deploy/eisa-api -- python manage.py migrate --noinput

Ardından:

kubectl -n eisa-app exec -it deploy/eisa-api -- python manage.py collectstatic --noinput

Önemli düzeltmeler:

- `DB_USER=eisa_user` olarak Data Node standardına çekildi.
- `image:latest` kaldırıldı; versiyonlu image tag kullanıldı.
- API readiness/liveness probe içine `Host: api.eisa.com.tr` header'ı eklendi.
- Django için `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, `SECURE_PROXY_SSL_HEADER`, `USE_X_FORWARDED_HOST` env değerleri eklendi.
- API migration initContainer yerine ayrı `Job` haline getirildi.
- Portal probe `/` üzerinden kontrol edilir.
- Traefik + cert-manager + `letsencrypt-prod` kullanılır.

---

## 8. Manuel kubectl deploy akışı

```bash
kubectl apply -f eisa-app-production.yaml
```

Eğer migration job daha önce çalıştıysa ve tekrar migration koşturulacaksa:

```bash
kubectl -n eisa-app delete job eisa-api-migrate --ignore-not-found
kubectl apply -f eisa-app-production.yaml
kubectl -n eisa-app wait --for=condition=complete job/eisa-api-migrate --timeout=180s
```

Rollout kontrolü:

```bash
kubectl -n eisa-app rollout status deploy/eisa-api --timeout=180s
kubectl -n eisa-app rollout status deploy/eisa-portal --timeout=180s
kubectl -n eisa-app get pods -o wide
kubectl -n eisa-app get svc
kubectl -n eisa-app get ingress
kubectl -n eisa-app get certificate
```

HTTP testleri:

```bash
curl -I https://api.eisa.com.tr/healthz
curl -I https://portal.eisa.com.tr
```

---

## 9. Rancher UI ile manuel deploy

1. Rancher UI → workload cluster: `eisa-app-workload` veya mevcut workload cluster.
2. **Cluster Explorer → Workloads → Import YAML**.
3. `eisa-app-production.yaml` içeriğini yapıştır.
4. Apply.
5. **Workloads → Deployments** altında `eisa-api` ve `eisa-portal` podlarını kontrol et.
6. **Service Discovery → Ingresses** altında `eisa-app` ingress'ini kontrol et.
7. **Certificates** altında `eisa-app-tls` sertifikasının `Ready` olduğunu doğrula.

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
├─ k8s/
│  └─ eisa-app/
│     ├─ eisa-app-production.yaml
│     └─ fleet.yaml
└─ .github/
   └─ workflows/
      └─ build-images.yml
```

### 10.2 `fleet.yaml` örneği

`k8s/eisa-app/fleet.yaml`:

```yaml
namespace: eisa-app
helm:
  releaseName: eisa-app
```

### 10.3 Rancher UI üzerinden GitRepo oluşturma

1. Rancher UI → sol menü → **Continuous Delivery**.
2. Workspace olarak genelde `fleet-default` seçilir. Downstream/workload cluster'lar burada görünür.
3. **Git Repos → Create**.
4. Repository URL girilir.
5. Branch: `main`.
6. Paths:

```text
k8s/eisa-app
```

7. Target olarak workload cluster seçilir. Cluster adı örnek:

```text
eisa-app-workload
```

8. Repo private ise Git credential secret tanımlanır.
9. Save.
10. Fleet bundle `Active/Ready` olana kadar beklenir.

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
  paths:
    - k8s/eisa-app
  targets:
    - name: eisa-workload
      clusterName: eisa-app-workload
```

Private Git repo için `clientSecretName` eklenir:

```yaml
spec:
  clientSecretName: eisa-git-credentials
```

Git credential secret, GitRepo ile aynı namespace'te bulunmalıdır. Örneğin `fleet-default`.

---

## 11. GitHub Actions örnek mantığı

Continuous Delivery image build yapmadığı için CI pipeline gerekir.

Örnek görevler:

```text
1. backend image build
2. portal image build
3. registry.eisa.local:80 üzerine push
4. k8s/eisa-app/eisa-app-production.yaml içindeki image tag değerini güncelle
5. değişikliği main branch'e commit et
6. Fleet değişikliği algılar ve deploy eder
```

Kısa örnek:

```yaml
name: build-and-push
on:
  push:
    branches: [main]

jobs:
  images:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: registry.eisa.local:80
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build and push API
        run: |
          TAG=git-${GITHUB_SHA::7}
          docker build -t registry.eisa.local:80/ysnzgl/eisa-api:$TAG ./backend
          docker push registry.eisa.local:80/ysnzgl/eisa-api:$TAG
      - name: Build and push Portal
        run: |
          TAG=git-${GITHUB_SHA::7}
          docker build -t registry.eisa.local:80/ysnzgl/eisa-portal:$TAG ./web_panels
          docker push registry.eisa.local:80/ysnzgl/eisa-portal:$TAG
```

Bu örnek image basar; manifest tag update kısmı ayrıca eklenmelidir. İlk fazda tag güncellemesini elle yapmak daha kontrollüdür.

---

## 12. Sürüm yükseltme

Manuel yaklaşım:

```bash
kubectl -n eisa-app set image deploy/eisa-api api=registry.eisa.local:80/ysnzgl/eisa-api:1.1.0
kubectl -n eisa-app set image deploy/eisa-portal portal=registry.eisa.local:80/ysnzgl/eisa-portal:1.1.0

kubectl -n eisa-app rollout status deploy/eisa-api
kubectl -n eisa-app rollout status deploy/eisa-portal
```

GitOps yaklaşımı:

```text
1. Yeni image tag push edilir.
2. YAML içindeki image tag değiştirilir.
3. Git'e commit edilir.
4. Fleet otomatik reconcile eder.
```

Rollback:

```bash
kubectl -n eisa-app rollout undo deploy/eisa-api
kubectl -n eisa-app rollout undo deploy/eisa-portal
```

GitOps kullanılıyorsa kalıcı rollback için Git'teki image tag de eski sürüme çekilmelidir.

---

## 13. Ölçekleme

| Servis | Replika | Not |
| --- | ---: | --- |
| `eisa-api` | 2+ | Stateless kalmalı |
| `eisa-portal` | 2+ | Stateless statik içerik |
| Scheduler / background job | 1 | Eğer APScheduler varsa duplicate job riskinden dolayı tek replika |
| PostgreSQL | App cluster içinde değil | Data Node üzerinde |
| RustFS | App cluster içinde değil | Data Node üzerinde |

---

## 14. Backup yaklaşımı

Bu manifest uygulama workload'unu kapsar. Kalıcı veriler dış servislerde durur:

| Katman | Backup |
| --- | --- |
| PostgreSQL | `pg_dump`, `pg_dumpall`, ileride WAL/Barman |
| MongoDB / Mender | `mongodump` |
| RustFS | bucket mirror/replication |
| Kubernetes manifests | Git repo |
| Secrets | SealedSecrets/SOPS/Vault/External Secrets hedefi |

---

## 15. Sorun giderme

| Belirti | İlk kontrol |
| --- | --- |
| `ImagePullBackOff` | `eisa-regcred` doğru namespace'te mi? Image adı/tag doğru mu? Registry token geçerli mi? |
| API readiness fail | `kubectl -n eisa-app logs deploy/eisa-api --previous`; `/healthz` var mı? `Host` header sorunu var mı? |
| Django `DisallowedHost` | `DJANGO_ALLOWED_HOSTS` ve probe Host header kontrol edilir |
| CORS/CSRF hatası | `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOW_CREDENTIALS` kontrol edilir |
| DB bağlantı hatası | `10.200.201.10:6432` erişimi, DB password ve PgBouncer kontrol edilir |
| S3 bağlantı hatası | RustFS endpoint, bucket, access policy ve path-style ayarı kontrol edilir |
| TLS sertifikası gelmiyor | Public DNS ve CoreDNS split DNS kontrol edilir |
| Fleet deploy etmiyor | GitRepo path, branch, target cluster ve Git credential secret kontrol edilir |

---

## 16. Güvenlik kontrol listesi

- [ ] `DJANGO_DEBUG=0`
- [ ] `DJANGO_SECRET_KEY` secret içinde ve 50+ karakter
- [ ] `DB_PASSWORD` secret içinde
- [ ] `S3_SECRET_KEY` secret içinde
- [ ] Registry token secret içinde
- [ ] Image tag `latest` değil
- [ ] API ve Portal non-root container olarak çalışıyor
- [ ] API CORS sadece `https://portal.eisa.com.tr`
- [ ] JWT cookie `Secure=True`, `SameSite=Strict`
- [ ] TLS cert-manager ile aktif
- [ ] DB/S3 public açılmıyor
- [ ] Git repo gerçek secret içermiyor
- [ ] Rancher management cluster'a workload deploy edilmiyor
