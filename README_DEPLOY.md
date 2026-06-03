# E-İSA — Production Deployment

Bu doküman E-İSA platformunun üretim Kubernetes cluster'ına nasıl dağıtılacağını açıklar.

| | |
| --- | --- |
| Workload cluster | K3s — `app-k3s-vm` (`10.200.202.20`) |
| Namespace | `eisa-app` |
| Ingress | Traefik |
| TLS | cert-manager (`ClusterIssuer: letsencrypt-prod`) |
| Public hosts | `api.eisa.com.tr`, `portal.eisa.com.tr` |
| DB | PgBouncer @ `10.200.201.10:6432` (db: `eisa_db`) |
| Object storage | RustFS S3 @ `http://10.200.201.11:9000` (bucket: `eisa-files`) |

> Rancher **management** cluster'ına workload deploy edilmez. Tüm `kubectl` komutları workload K3s context'ine karşı çalıştırılır.

---

## 1. Image Build

Repo kökünden:

```powershell
$REGISTRY = "registry.eisa.local"   # kendi registry'niz
$TAG      = "1.0.0"

docker build -t "$REGISTRY/eisa/eisa-api:$TAG"    ./backend
docker build -t "$REGISTRY/eisa/eisa-portal:$TAG" ./web_panels
```

Image özetleri:

- **eisa-api** — Python 3.12 slim + Gunicorn, port `8080`, non-root (UID 1000), `/healthz` healthcheck.
- **eisa-portal** — Nginx 1.27 alpine, port `8080`, non-root (nginx UID 101), `docker-entrypoint.d` hook ile `API_BASE_URL` ENV'sinden runtime'da `/config.js` üretir.

---

## 2. Image Push

```powershell
docker push "$REGISTRY/eisa/eisa-api:$TAG"
docker push "$REGISTRY/eisa/eisa-portal:$TAG"
```

Özel registry için pull secret (gerektiğinde):

```powershell
kubectl -n eisa-app create secret docker-registry eisa-regcred `
  --docker-server="$REGISTRY" `
  --docker-username='<USER>' `
  --docker-password='<TOKEN>'
```

ve [`deploy/eisa-app.yaml`](deploy/eisa-app.yaml) içindeki Deployment'lara `spec.template.spec.imagePullSecrets: [{ name: eisa-regcred }]` ekleyin.

---

## 3. Namespace + Image Tag

```powershell
kubectl apply -f deploy/eisa-app.yaml --dry-run=client    # önizleme
```

Manifest içindeki image referansı `eisa/eisa-api:latest` ve `eisa/eisa-portal:latest`'tir. Kendi registry/tag'inize göre güncelleyin (sed/Kustomize image override veya doğrudan dosyayı düzenleyin):

```powershell
(Get-Content deploy/eisa-app.yaml) `
  -replace 'eisa/eisa-api:latest',    "$REGISTRY/eisa/eisa-api:$TAG" `
  -replace 'eisa/eisa-portal:latest', "$REGISTRY/eisa/eisa-portal:$TAG" |
  Set-Content deploy/eisa-app.yaml
```

---

## 4. Secret (cluster üzerinde, repo'ya YAZILMAZ)

Sırlar `eisa-app-secrets` adıyla, manifest tarafından `envFrom: secretRef` ile API container'ına bağlanır.

### 4.1 Güçlü değer üretimi

```powershell
# DJANGO_SECRET_KEY (50+ karakter)
python -c "import secrets;print(secrets.token_urlsafe(64))"

# DB_PASSWORD (24+ karakter)
python -c "import secrets;print(secrets.token_urlsafe(24))"
```

### 4.2 Secret oluşturma komutu

> **Anahtarlar manifest contract'ı ile birebir aynı:** `DB_PASSWORD`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `DJANGO_SECRET_KEY`.

```powershell
kubectl -n eisa-app create secret generic eisa-app-secrets `
  --from-literal=DJANGO_SECRET_KEY='REPLACE_WITH_50PLUS_CHAR_RANDOM' `
  --from-literal=DB_PASSWORD='REPLACE_WITH_STRONG_DB_PASSWORD' `
  --from-literal=S3_ACCESS_KEY='REPLACE_WITH_S3_ACCESS_KEY' `
  --from-literal=S3_SECRET_KEY='REPLACE_WITH_S3_SECRET_KEY'
```

Secret rotasyonu (mevcut secret'ı güncelle):

```powershell
kubectl -n eisa-app create secret generic eisa-app-secrets `
  --from-literal=DJANGO_SECRET_KEY='...' `
  --from-literal=DB_PASSWORD='...' `
  --from-literal=S3_ACCESS_KEY='...' `
  --from-literal=S3_SECRET_KEY='...' `
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n eisa-app rollout restart deploy/eisa-api
```

> Üretim önerisi: SealedSecrets / External Secrets Operator + Vault. Bu doküman düz `kubectl create` yolunu örneklemiştir; gerçek değerler shell history'sinden temizlenmelidir (`Clear-History`).

---

## 5. Apply

```powershell
kubectl apply -f deploy/eisa-app.yaml
```

Beklenen kaynaklar:

```
namespace/eisa-app
configmap/eisa-app-config
deployment.apps/eisa-api
service/eisa-api
deployment.apps/eisa-portal
service/eisa-portal
ingress.networking.k8s.io/eisa-app
```

---

## 6. Rollout Doğrulama

```powershell
kubectl -n eisa-app rollout status deploy/eisa-api    --timeout=180s
kubectl -n eisa-app rollout status deploy/eisa-portal --timeout=120s

kubectl -n eisa-app get pods -o wide
kubectl -n eisa-app get svc,ingress
kubectl -n eisa-app describe ingress eisa-app
```

Logları takip:

```powershell
kubectl -n eisa-app logs -f deploy/eisa-api
kubectl -n eisa-app logs -f deploy/eisa-portal
```

cert-manager TLS:

```powershell
kubectl -n eisa-app get certificate eisa-app-tls -o wide
kubectl -n eisa-app describe certificate eisa-app-tls
```

---

## 7. Smoke Test (curl)

### 7.1 API health

```bash
curl -fsS https://api.eisa.com.tr/healthz
# -> ok
```

### 7.2 API CORS preflight (yalnızca portal origin'i kabul edilmeli)

```bash
# İzinli origin
curl -i -X OPTIONS https://api.eisa.com.tr/api/auth/token/ \
  -H 'Origin: https://portal.eisa.com.tr' \
  -H 'Access-Control-Request-Method: POST'
# -> 200 + Access-Control-Allow-Origin: https://portal.eisa.com.tr

# İzinsiz origin
curl -i -X OPTIONS https://api.eisa.com.tr/api/auth/token/ \
  -H 'Origin: https://evil.example.com' \
  -H 'Access-Control-Request-Method: POST'
# -> Access-Control-Allow-Origin header'ı dönmemeli
```

### 7.3 Portal

```bash
curl -fsS https://portal.eisa.com.tr/healthz
# -> ok

# Runtime config kontrolü — API_BASE_URL gerçekten enjekte olmuş mu?
curl -s https://portal.eisa.com.tr/config.js
# -> window.__APP_CONFIG__ = { API_BASE_URL: "https://api.eisa.com.tr" };
```

### 7.4 TLS sertifikası

```bash
echo | openssl s_client -connect api.eisa.com.tr:443    -servername api.eisa.com.tr    2>/dev/null | openssl x509 -noout -issuer -dates
echo | openssl s_client -connect portal.eisa.com.tr:443 -servername portal.eisa.com.tr 2>/dev/null | openssl x509 -noout -issuer -dates
```

---

## 8. Sorun Giderme

| Belirti | Kontrol |
| --- | --- |
| `CrashLoopBackOff` (API) | `kubectl -n eisa-app logs deploy/eisa-api --previous` — `DJANGO_SECRET_KEY < 50 char`, eksik `DB_PASSWORD` veya `CORS_ALLOWED_ORIGINS` HTTPS değil. |
| `migrate` init takılı | PgBouncer → Postgres bağlantısı: `kubectl -n eisa-app run pg-test --rm -it --image=postgres:16-alpine -- psql "host=10.200.201.10 port=6432 dbname=eisa_db user=eisa"` |
| Portal 404 / boş sayfa | `kubectl -n eisa-app exec deploy/eisa-portal -- cat /usr/share/nginx/html/config.js` ile runtime config'i doğrula. |
| TLS Pending | `kubectl -n eisa-app describe order` — Let's Encrypt HTTP-01 challenge için 80/tcp Traefik üzerinden açık olmalı. |
| 502 Bad Gateway | API readiness probe başarısız → `kubectl -n eisa-app describe pod -l app.kubernetes.io/name=eisa-api`. |

---

## 9. Geri Alma & Yeni Sürüm

```powershell
# Yeni sürüm
$NEW_TAG = "1.1.0"
kubectl -n eisa-app set image deploy/eisa-api    api=$REGISTRY/eisa/eisa-api:$NEW_TAG
kubectl -n eisa-app set image deploy/eisa-portal portal=$REGISTRY/eisa/eisa-portal:$NEW_TAG
kubectl -n eisa-app rollout status deploy/eisa-api

# Geri alma
kubectl -n eisa-app rollout undo deploy/eisa-api
kubectl -n eisa-app rollout undo deploy/eisa-portal
```

---

## 10. Güvenlik Notları

- Tüm container'lar non-root (`runAsNonRoot: true`), capabilities drop ALL.
- TLS yalnızca Ingress/Traefik üzerinde sonlandırılır; container içinde HTTP 8080.
- API CORS allow-list: yalnızca `https://portal.eisa.com.tr`.
- DB_PASSWORD, S3 access/secret key sadece `eisa-app-secrets` içinde — repo'da, ConfigMap'te veya image'da bulunmaz.
- Local disk state yok: media/upload doğrudan RustFS S3 (`eisa-files`) bucket'ına gider.
- `CONN_MAX_AGE=0` → PgBouncer transaction-pool ile uyumlu (uzun süreli connection açılmaz).
