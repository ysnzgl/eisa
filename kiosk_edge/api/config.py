"""Kiosk konfigürasyonu — environment veya local config dosyasından okur."""
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Lokal veritabanı (SQLite)
    sqlite_path: str = "/var/lib/eisa/local.db"

    # Merkezi API (Django) — HTTPS zorunlu
    central_api_base: str = "https://api.e-isa.local"
    kiosk_app_key: str = ""
    kiosk_mac: str = ""

    # Lokal API (eczacı uçbiriminden QR sorgusu için paylaşılan sır)
    local_api_secret: str = ""

    # Senkronizasyon aralıkları (saniye)
    pull_interval_sec: int = 900   # 15 dk: kategoriler, sorular, reklam
    push_interval_sec: int = 300   # 5 dk:  loglar, reklam impressionları

    # Üretimde sertifika doğrulamasını zorla; sadece geliştirme için False yapılabilir
    verify_tls: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_prefix="EISA_")

    @model_validator(mode="after")
    def _required_credentials(self) -> "Settings":
        if not self.kiosk_app_key or not self.kiosk_mac:
            raise ValueError(
                "EISA_KIOSK_APP_KEY ve EISA_KIOSK_MAC environment değişkenleri zorunludur."
            )
        if not self.central_api_base.lower().startswith("https://"):
            # Yalnızca açık geliştirme ortamında http kabul edilir
            if not self.central_api_base.startswith("http://localhost") and \
               not self.central_api_base.startswith("http://127.0.0.1"):
                raise ValueError("EISA_CENTRAL_API_BASE üretimde HTTPS olmalıdır.")
        return self


settings = Settings()
