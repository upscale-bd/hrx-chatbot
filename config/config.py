"""Configuration with Consul fallback for HRX Chatbot."""
import os
import json
import logging
import re
from typing import Optional, Dict, Any

import consul
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConsulKVLoader:
    """Load .env-style key/value pairs from Consul."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        key_name: str = "hrx-chatbot",
        require_consul: bool = False,
    ):
        host = host or os.getenv("CONSUL_HOST", "consul")
        port = port or int(os.getenv("CONSUL_PORT", "8500"))
        self.key_name = key_name
        self.require_consul = require_consul
        self.consul_client = None

        try:
            token = os.getenv("CONSUL_TOKEN")
            self.consul_client = consul.Consul(host=host, port=port, token=token)
            self.consul_client.agent.self()
            logger.info(f"Consul connected at {host}:{port}")
        except Exception as e:
            if require_consul:
                raise RuntimeError(f"Consul required but unavailable: {e}")
            # Consul is optional; prefer environment variables if it is not reachable.
            logger.debug(f"Consul unavailable ({e}); falling back to env/.env")
            self.consul_client = None

    @staticmethod
    def _parse_env_value(value: str) -> Any:
        value = value.strip()
        if "#" in value:
            value = value.split("#")[0].strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        if re.fullmatch(r"-?\d+", value):
            return int(value)
        if re.fullmatch(r"-?\d+\.\d+", value):
            return float(value)
        if (value.startswith("{") and value.endswith("}")) or (
            value.startswith("[") and value.endswith("]")
        ):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value

    def get_consul_values(self) -> Dict[str, Any]:
        if not self.consul_client:
            return {}
        try:
            _, data = self.consul_client.kv.get(self.key_name)
            if not data or not data.get("Value"):
                return {}
            value_str = data["Value"].decode("utf-8")
            env_config: Dict[str, Any] = {}
            pair_pattern = re.compile(
                r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>\"(?:[^\"\\]|\\.)*\"|\'(?:[^\'\\]|\\.)*\'|\{.*?\}|\[.*?\]|[^\n\r]*)",
                re.DOTALL,
            )
            matches = list(pair_pattern.finditer(value_str))
            if matches:
                for m in matches:
                    key = m.group("key").strip()
                    raw_val = m.group("value").strip()
                    env_config[key] = self._parse_env_value(raw_val)
                return env_config

            for line in value_str.strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                env_config[key.strip()] = self._parse_env_value(val)
            return env_config
        except Exception as e:
            logger.error(f"Failed loading Consul key {self.key_name}: {e}")
            return {}


class Settings(BaseSettings):
    # Application
    APP_SECRET_KEY: str = "dev-secret"
    APP_DATABASE_URL: str = "sqlite:///./chat.db"
    HRX_BASE_URL: str = "http://localhost:8000/mock/hrx"
    HRX_BEARER_TOKEN: Optional[str] = None
    REPORT_DIR: str = os.getenv("TMPDIR", "/tmp")

    # Celery / cache
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 3600

    # Gemini
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_TOP_P: float = 0.9
    GEMINI_TOP_K: int = 40
    GEMINI_TEMPERATURE: float = 0.1
    GEMINI_RETRY_DELAY: float = 5.0
    GEMINI_MAX_RETRIES: int = 3
    GEMINI_MAX_TOKENS: int = 4096
    GEMINI_TIMEOUT: int = 30
    GEMINI_MAX_TOKENS_EXTENDED: int = 8192
    GEMINI_TIMEOUT_EXTENDED: int = 120

    # MinIO (optional)
    MINIO_ACCESS_KEY: Optional[str] = None
    MINIO_SECRET_KEY: Optional[str] = None
    MINIO_BUCKET_ENDPOINT: Optional[str] = None
    MINIO_BUCKET_PORT: Optional[int] = None
    MINIO_BUCKET_NAME: Optional[str] = None
    MINIO_BUCKET_USE_SSL: bool = True

    # Consul
    USE_CONSUL: bool = False
    CONSUL_HOST: str = "consul"
    CONSUL_PORT: int = 8500
    CONSUL_PREFIX: str = "hrx-chatbot"
    CONSUL_KEY: str = "hrx-chatbot"

    # Model selections
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    LANGUAGE_MODEL: str = "gemini-2.5-flash"

    # Dataset mapping (optional JSON)
    DATASET_MAPPING: Dict[str, str] = {}

    @field_validator("DATASET_MAPPING", mode="before")
    @classmethod
    def parse_dataset_mapping(cls, v):
        if isinstance(v, dict):
            return v
        if isinstance(v, str) and v.strip():
            try:
                return json.loads(v)
            except Exception as e:
                raise ValueError(f"Invalid DATASET_MAPPING JSON: {e}")
        return {}

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings: Optional[Settings] = None


def load_settings_from_consul(
    consul_host: Optional[str] = None,
    consul_port: Optional[int] = None,
    consul_key: Optional[str] = None,
    require_consul: Optional[bool] = None,
) -> Settings:
    consul_host = consul_host or os.getenv("CONSUL_HOST") or "consul"
    consul_port = consul_port or int(os.getenv("CONSUL_PORT", "8500"))
    consul_key = consul_key or os.getenv("CONSUL_KEY") or "hrx-chatbot"
    require_consul = (
        require_consul
        if require_consul is not None
        else os.getenv("CONSUL_REQUIRE", "false").lower() == "true"
    )

    loader = ConsulKVLoader(
        host=consul_host,
        port=consul_port,
        key_name=consul_key,
        require_consul=require_consul,
    )
    consul_values = loader.get_consul_values()
    consul_keys = {"USE_CONSUL", "CONSUL_HOST", "CONSUL_PORT", "CONSUL_KEY", "CONSUL_PREFIX", "CONSUL_REQUIRE"}
    filtered = {k: v for k, v in consul_values.items() if k not in consul_keys}

    if require_consul and not filtered:
        raise RuntimeError("Consul required but returned no config values")

    if filtered:
        logger.info(f"Loaded {len(filtered)} settings from Consul")
        return Settings(**filtered)
    return Settings()


def init_settings() -> Settings:
    global settings
    use_consul = os.getenv("USE_CONSUL", "false").lower() == "true"
    if use_consul:
        settings = load_settings_from_consul()
    else:
        settings = Settings()
    return settings


# Initialize on import (safe defaults); callers can re-init if needed
try:
    init_settings()
except Exception as e:
    logger.warning(f"Settings initialization failed on import: {e}")