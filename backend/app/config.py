from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = Field(..., validation_alias="OPENAI_API_KEY")
    model_name: str = "gpt-3.5-turbo"
    max_tokens: int = 900
    temperature: float = 0.2
    audit_history_max_files: int = Field(default=50, validation_alias="QA_AUDIT_HISTORY_MAX_FILES")
    audit_history_max_age_days: int = Field(default=14, validation_alias="QA_AUDIT_HISTORY_MAX_AGE_DAYS")
    allowed_execution_root: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2],
        validation_alias="QA_ALLOWED_EXECUTION_ROOT",
    )

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[1] / ".env"),
        env_file_encoding="utf-8",
    )


settings = Settings()
