"""
Comprehensive settings configuration for Fluxion backend
"""

from typing import Any, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application settings"""

    APP_NAME: str = Field(default="Fluxion API")
    VERSION: str = Field(default="2.0.0")  # Changed from APP_VERSION to VERSION
    APP_DESCRIPTION: str = Field(default="Production-ready DeFi Supply Chain Platform")
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    WORKERS: int = Field(default=1)
    API_V1_PREFIX: str = Field(default="/api/v1")
    DOCS_URL: Optional[str] = Field(default="/docs")
    REDOC_URL: Optional[str] = Field(default="/redoc")
    LOG_LEVEL: str = Field(default="INFO")
    ALLOWED_ORIGINS: List[str] = Field(default=["*"])
    ALLOWED_HOSTS: List[str] = Field(default=["*"])

    @field_validator("WORKERS")
    @classmethod
    def validate_workers(cls, v: int, info) -> int:
        if info.data.get("ENVIRONMENT") == "production" and v < 2:
            return 4
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


class DatabaseSettings(BaseSettings):
    """Database settings"""

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://fluxion:fluxion@localhost:5432/fluxion"
    )
    DATABASE_READ_URL: Optional[str] = Field(default=None)
    DB_POOL_SIZE: int = Field(default=20)
    DB_MAX_OVERFLOW: int = Field(default=30)
    DB_POOL_TIMEOUT: int = Field(default=30)
    DB_POOL_RECYCLE: int = Field(default=3600)
    DB_ECHO: bool = Field(default=False)


class RedisSettings(BaseSettings):
    """Redis settings"""

    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_DB: int = Field(default=0)
    REDIS_MAX_CONNECTIONS: int = Field(default=20)
    CACHE_TTL: int = Field(default=3600)
    SESSION_TTL: int = Field(default=86400)


class SecuritySettings(BaseSettings):
    """Security settings"""

    SECRET_KEY: str = Field(
        default="development-secret-key-change-in-production-min-32-chars-long"
    )
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    PASSWORD_MIN_LENGTH: int = Field(default=8)
    PASSWORD_REQUIRE_UPPERCASE: bool = Field(default=True)
    PASSWORD_REQUIRE_LOWERCASE: bool = Field(default=True)
    PASSWORD_REQUIRE_NUMBERS: bool = Field(default=True)
    PASSWORD_REQUIRE_SPECIAL: bool = Field(default=True)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    RATE_LIMIT_BURST: int = Field(default=100)
    CORS_ORIGINS: List[str] = Field(default=["*"])
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    ENCRYPTION_KEY: Optional[str] = Field(default=None)
    FIELD_ENCRYPTION_ENABLED: bool = Field(default=False)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v


class BlockchainSettings(BaseSettings):
    """Blockchain settings"""

    ETH_RPC_URL: str = Field(default="http://localhost:8545")
    ETH_WEBSOCKET_URL: Optional[str] = Field(default=None)
    ETH_CHAIN_ID: int = Field(default=1)
    POLYGON_RPC_URL: Optional[str] = Field(default=None)
    POLYGON_CHAIN_ID: int = Field(default=137)
    BSC_RPC_URL: Optional[str] = Field(default=None)
    BSC_CHAIN_ID: int = Field(default=56)
    GAS_PRICE_STRATEGY: str = Field(default="medium")
    MAX_GAS_PRICE: int = Field(default=100)
    SUPPLY_CHAIN_ADDRESS: Optional[str] = Field(default=None)
    LIQUIDITY_POOL_ADDRESS: Optional[str] = Field(default=None)
    SYNTHETIC_ASSET_ADDRESS: Optional[str] = Field(default=None)
    GOVERNANCE_TOKEN_ADDRESS: Optional[str] = Field(default=None)
    ASSET_VAULT_ADDRESS: Optional[str] = Field(default=None)
    ETHERSCAN_API_KEY: Optional[str] = Field(default=None)
    POLYGONSCAN_API_KEY: Optional[str] = Field(default=None)


class ComplianceSettings(BaseSettings):
    """Compliance settings"""

    KYC_ENABLED: bool = Field(default=False)
    KYC_PROVIDER: str = Field(default="jumio")
    KYC_API_KEY: Optional[str] = Field(default=None)
    KYC_API_SECRET: Optional[str] = Field(default=None)
    AML_ENABLED: bool = Field(default=False)
    AML_PROVIDER: str = Field(default="chainalysis")
    AML_API_KEY: Optional[str] = Field(default=None)
    TRANSACTION_MONITORING_ENABLED: bool = Field(default=False)
    SUSPICIOUS_AMOUNT_THRESHOLD: float = Field(default=10000.0)
    DAILY_TRANSACTION_LIMIT: float = Field(default=50000.0)
    REGULATORY_REPORTING_ENABLED: bool = Field(default=False)
    AUDIT_LOG_RETENTION_DAYS: int = Field(default=2555)


class MonitoringSettings(BaseSettings):
    """Monitoring and logging settings"""

    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")
    METRICS_ENABLED: bool = Field(default=True)
    METRICS_PORT: int = Field(default=8001)
    HEALTH_CHECK_INTERVAL: int = Field(default=30)
    SENTRY_DSN: Optional[str] = Field(default=None)
    SENTRY_ENVIRONMENT: Optional[str] = Field(default=None)


class ExternalServicesSettings(BaseSettings):
    """External services settings"""

    NOTIFICATION_SERVICE_URL: Optional[str] = Field(default=None)
    ANALYTICS_SERVICE_URL: Optional[str] = Field(default=None)


class Settings(BaseSettings):
    """Main settings class combining all setting groups"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    app: AppSettings = AppSettings()
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    security: SecuritySettings = SecuritySettings()
    blockchain: BlockchainSettings = BlockchainSettings()
    compliance: ComplianceSettings = ComplianceSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    external: ExternalServicesSettings = ExternalServicesSettings()


settings = Settings()


def get_settings() -> Settings:
    """Get settings instance"""
    return settings
