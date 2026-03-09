from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Voucher Backend"
    app_env: str = "dev"
    debug: bool = True
    api_prefix: str = ""

    database_url: str = "sqlite:///./data/app.db"

    storage_provider: str = "local"
    local_storage_root: str = "./data/storage"

    ocr_provider: str = "rapidocr"
    rapidocr_text_score: float = 0.5
    rapidocr_use_det: bool = True
    rapidocr_use_cls: bool = True
    rapidocr_use_rec: bool = True

    max_upload_mb: int = 15

    auth_secret_key: str = "change-me-in-production"
    auth_issuer: str = "voucher-backend"
    auth_token_expire_minutes: int = 1440

    wechat_app_id: str | None = None
    wechat_app_secret: str | None = None
    wechat_login_timeout_seconds: int = 8
    wechat_login_mock_enabled: bool = False
    wechat_login_mock_prefix: str = "dev-"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def local_storage_path(self) -> Path:
        return Path(self.local_storage_root).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
