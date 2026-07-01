from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    PORT: int = 8001
    HOST: str = "0.0.0.0"
    MOCK_MODE: bool = True
    SOLVER_TIME_LIMIT_DAILY_MS: int = 30000
    SOLVER_TIME_LIMIT_RECOVERY_MS: int = 5000
    LOG_LEVEL: str = "INFO"

    LOW_VOLUME_SKIP_PENALTY: int = 100
    MANDATORY_PENALTY: int = 1_000_000
    
settings = Settings()