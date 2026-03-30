# app/utils/config.py
# ──────────────────────────────────────────────────────────────
# Centralised application configuration.
# Values are loaded from environment variables (or a .env file).
# All other modules import `settings` from here — never os.environ.
# ──────────────────────────────────────────────────────────────

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Anthropic ────────────────────────────────────────────
    ANTHROPIC_API_KEY: str

    # ── MongoDB ──────────────────────────────────────────────
    MONGODB_URI:     str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "novel_generator"

    # ── App ──────────────────────────────────────────────────
    APP_ENV:  str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # ── Claude model ─────────────────────────────────────────
    # Using claude-sonnet-4-20250514 as the generation model.
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    CLAUDE_MAX_TOKENS: int = 4096

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# Module-level singleton — import this everywhere
settings = Settings()
