"""Validated service configuration. Error rendering must never include secret values."""

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", hide_input_in_errors=True)
    app_origin: str = "http://localhost:8080"
    cookie_secure: bool = False
    guest_cookie_secret: SecretStr
    livekit_url: str
    livekit_api_key: SecretStr
    livekit_api_secret: SecretStr
    livekit_agent_name: str = "workplace-english-tutor"
    conversation_model: str = "google/gemini-3.5-flash"
    transcription_model: str = "deepgram/nova-3"
    transcription_language: str = "en"
    assessment_model: str = "google/gemini-3.5-flash"
    tts_model: str = "cartesia/sonic-3"
    tts_voice: str = "30894953-bcce-41fe-892c-15ce19c843ff"
    tts_speed: float = Field(default=0.8, ge=0.6, le=1.5)
    redis_url: SecretStr = SecretStr("redis://redis:6379/0")
    session_ttl_seconds: int = Field(default=86400, ge=60, le=86400)
    voice_lease_seconds: int = Field(default=15, ge=10, le=60)
    max_active_sessions: int = Field(default=4, ge=1, le=32)
    assessment_timeout_seconds: int = Field(default=30, ge=5, le=60)
    log_level: str = "INFO"

    @field_validator("guest_cookie_secret", "livekit_api_key", "livekit_api_secret")
    @classmethod
    def required_secret(cls, value: SecretStr, info):
        if not value.get_secret_value().strip():
            raise ValueError(f"{info.field_name.upper()} must be configured")
        if info.field_name == "guest_cookie_secret" and len(value.get_secret_value()) < 32:
            raise ValueError("GUEST_COOKIE_SECRET must contain at least 32 characters")
        return value

    @field_validator("livekit_url")
    @classmethod
    def cloud_url(cls, value: str):
        if not value.startswith("wss://"):
            raise ValueError("LIVEKIT_URL must be a wss:// LiveKit Cloud URL")
        return value

    @field_validator("app_origin")
    @classmethod
    def origin(cls, value: str):
        from urllib.parse import urlsplit

        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.path:
            raise ValueError("APP_ORIGIN must be an HTTP(S) origin without a trailing slash")
        return value


@lru_cache
def settings() -> Settings:
    return Settings()
