from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "ConsumerDost"
    demo_mode: bool = True
    timezone: str = "Asia/Kolkata"

    # Telegram
    telegram_bot_token: str = ""

    # Gnani Speech APIs
    gnani_api_key: str = ""
    gnani_stt_url: str = "https://api.vachana.ai/stt/v3"
    gnani_tts_url: str = "https://api.vachana.ai/api/v1/tts/inference"

    # LLM Providers
    gemini_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    primary_llm_provider: str = "gemini"
    llm_model: str = "gemini-3.8-flash"

    # Database
    database_url: str = "sqlite+aiosqlite:///data/consumerdost.db"

    # Directory Paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    data_dir: Path = base_dir / "data"
    assets_dir: Path = base_dir / "assets"
    fonts_dir: Path = assets_dir / "fonts"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
