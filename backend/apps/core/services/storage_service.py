"""Singleton RustFS depolama servisi."""

from __future__ import annotations

import hashlib
import io
import os
import threading
import uuid
from datetime import timedelta

from django.conf import settings
from minio import Minio


class StorageService:
    """Uygulama yaşam döngüsünde tek RustFS client örneği üretir."""

    _instance: "StorageService | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "StorageService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self.endpoint = settings.RUSTFS_ENDPOINT
        self.access_key = settings.RUSTFS_ACCESS_KEY
        self.secret_key = settings.RUSTFS_SECRET_KEY
        self.bucket_name = settings.RUSTFS_BUCKET_NAME
        self.secure = settings.RUSTFS_SECURE

        self.client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )
        self._ensure_bucket()
        self._initialized = True

    def _ensure_bucket(self) -> None:
        """Servis ilk ayağa kalktığında bucket yoksa otomatik oluştur."""
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)

    def upload_file(self, uploaded_file, object_name: str | None = None, prefix: str = "") -> str:
        """Django uploaded file nesnesini RustFS'e yükler."""
        ext = os.path.splitext(uploaded_file.name)[1].lower() or ".bin"
        if not object_name:
            object_name = f"{uuid.uuid4().hex}{ext}"

        clean_prefix = prefix.strip("/")
        if clean_prefix:
            object_name = f"{clean_prefix}/{object_name}"

        uploaded_file.seek(0)
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            data=uploaded_file,
            length=uploaded_file.size,
            content_type=uploaded_file.content_type or "application/octet-stream",
        )
        return object_name

    def upload_file_with_checksum(
        self,
        uploaded_file,
        object_name: str | None = None,
        prefix: str = "",
    ) -> tuple[str, str]:
        """Django uploaded file nesnesini yükler; (object_key, sha256_checksum) döndürür.

        SHA-256, 64 KB chunk'larla stream okunarak hesaplanır — büyük dosyalar için
        tüm içeriği RAM'e almaz. İki geçiş:
          Pass 1: SHA-256 hash (64KB chunk stream)
          Pass 2: seek(0) → MinIO put_object (SDK kendi chunk stream'ini yönetir)

        Storage'a yazılan baytlar kaynakla özdeştir (seek test ile doğrulanabilir).
        Her çağrı benzersiz UUID key üretir; aynı key üzerine yazılmaz.
        Dönen checksum formatı: ``sha256:<hex>``
        """
        ext = os.path.splitext(uploaded_file.name)[1].lower() or ".bin"
        if not object_name:
            object_name = f"{uuid.uuid4().hex}{ext}"

        clean_prefix = prefix.strip("/")
        if clean_prefix:
            object_name = f"{clean_prefix}/{object_name}"

        # Pass 1: SHA-256 hash — 64KB chunk, RAM'e tam okuma yok
        uploaded_file.seek(0)
        hasher = hashlib.sha256()
        chunk_size = 64 * 1024
        while True:
            chunk = uploaded_file.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
        checksum = f"sha256:{hasher.hexdigest()}"

        # Pass 2: stream to storage
        uploaded_file.seek(0)
        content_type = uploaded_file.content_type or "application/octet-stream"
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            data=uploaded_file,
            length=uploaded_file.size,
            content_type=content_type,
        )
        return object_name, checksum

    def public_url(self, object_key: str) -> str:
        """Obje için kalıcı (süresiz) public URL döndürür.

        URL formatı: ``S3_PUBLIC_BASE_URL/<object_key>``

        ``S3_PUBLIC_BASE_URL`` bucket adını içermelidir, örn.:
          ``https://files.eisa.com.tr/eisa-files``
          → ``https://files.eisa.com.tr/eisa-files/ads/abc123.mp4``

        Boş bırakılırsa ``DOOH_PERSISTENT_MEDIA_URL=True`` ortamında
        ``ImproperlyConfigured`` üretilir.
        """
        from django.core.exceptions import ImproperlyConfigured

        base = getattr(settings, "S3_PUBLIC_BASE_URL", "").rstrip("/")
        if not base:
            raise ImproperlyConfigured(
                "S3_PUBLIC_BASE_URL kalici medya URL uretimi icin zorunludur. "
                "Bucket adini dahil edin: https://<endpoint>/<bucket> "
                "(orn. https://files.eisa.com.tr/eisa-files)"
            )
        return f"{base}/{object_key}"

    def upload_bytes(
        self,
        data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Bytes verisini RustFS'e yükler."""
        byte_stream = io.BytesIO(data)
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            data=byte_stream,
            length=len(data),
            content_type=content_type,
        )
        return object_name

    def read_object(self, object_name: str) -> bytes:
        """Objeyi okuyup ham byte olarak döner."""
        response = self.client.get_object(self.bucket_name, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_object(self, object_name: str) -> None:
        """Objeyi bucket'tan siler."""
        self.client.remove_object(self.bucket_name, object_name)

    def get_object_url(self, object_name: str, expires_minutes: int | None = None) -> str:
        """Objeye erişim için presigned URL üretir."""
        ttl_minutes = expires_minutes or settings.RUSTFS_PRESIGNED_URL_TTL_MINUTES
        return self.client.presigned_get_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            expires=timedelta(minutes=ttl_minutes),
        )
