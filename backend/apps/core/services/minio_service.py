"""Singleton MinIO servisi."""

from __future__ import annotations

import io
import os
import threading
import uuid
from datetime import timedelta

from django.conf import settings
from minio import Minio


class MinioService:
    """Uygulama yaşam döngüsünde tek MinIO client örneği üretir."""

    _instance: "MinioService | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "MinioService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self.secure = settings.MINIO_SECURE

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
        """Django uploaded file nesnesini MinIO'ya yükler."""
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

    def upload_bytes(
        self,
        data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Bytes verisini MinIO'ya yükler."""
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
        ttl_minutes = expires_minutes or settings.MINIO_PRESIGNED_URL_TTL_MINUTES
        return self.client.presigned_get_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            expires=timedelta(minutes=ttl_minutes),
        )
