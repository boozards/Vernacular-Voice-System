import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App General
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    SERVICE_NAME: str = "voicekart_shared"
    SECRET_KEY: str = "super-secret-voicekart-key-2026"

    # WhatsApp Cloud API Configuration
    WHATSAPP_PHONE_NUMBER_ID: str = "mock_phone_number_id"
    WHATSAPP_ACCESS_TOKEN: str = "mock_whatsapp_access_token"
    WHATSAPP_VERIFY_TOKEN: str = "voicekart_verify_token_123"
    WHATSAPP_APP_SECRET: str = "voicekart_app_secret_abc"
    WHATSAPP_API_VERSION: str = "v19.0"

    # OpenAI API Configuration
    OPENAI_API_KEY: str = "mock_openai_api_key"
    OPENAI_MODEL: str = "gpt-4o"
    WHISPER_MODEL: str = "whisper-1"

    # ElevenLabs API Configuration
    ELEVENLABS_API_KEY: str = "mock_elevenlabs_api_key"
    ELEVENLABS_DEFAULT_VOICE: str = "21m00Tcm4TlvDq8ikWAM"  # Default fallback voice ID
    ELEVENLABS_CACHE_ENABLED: bool = True
    ELEVENLABS_QUOTA_ALERT_THRESHOLD_PCT: float = 20.0

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    SESSION_TTL_SECONDS: int = 1800  # 30 minutes sliding window

    # PostgreSQL Configuration
    POSTGRES_USER: str = "voicekart"
    POSTGRES_PASSWORD: str = "voicekart_pass"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "voicekart_db"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Elasticsearch Configuration
    ELASTICSEARCH_HOST: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX: str = "voicekart_products"
    ELASTICSEARCH_USER: str = "elastic"
    ELASTICSEARCH_PASSWORD: str = "elastic_pass"

    # MinIO / AWS S3 Configuration
    S3_ENDPOINT_URL: Optional[str] = "http://localhost:9000"
    S3_BUCKET_NAME: str = "voicekart-audio"
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    AWS_SECRET_ACCESS_KEY: str = "minioadmin"
    AWS_REGION: str = "ap-south-1"

    # Service Inter-communication URLs
    GATEWAY_SERVICE_URL: str = "http://localhost:8001"
    ORCHESTRATOR_SERVICE_URL: str = "http://localhost:8002"
    TTS_SERVICE_URL: str = "http://localhost:8003"
    STT_SERVICE_URL: str = "http://localhost:8004"
    CATALOG_SERVICE_URL: str = "http://localhost:8005"
    ORDER_SERVICE_URL: str = "http://localhost:8006"

    # Razorpay Payment Integration
    RAZORPAY_KEY_ID: str = "rzp_test_mockkey123"
    RAZORPAY_KEY_SECRET: str = "rzp_secret_mock456"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
