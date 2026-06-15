from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    database_url: str = ""
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:8501"
    model_path: str = "./ml/model.pkl"
    integrity_model_path: str = "./ml/integrity_model.pkl"

    model_config = SettingsConfigDict(
        # Look for .env in parent directory (project root)
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding='utf-8',
        # Allow extra fields in .env (like frontend variables)
        extra='ignore',
        # Case insensitive environment variable names
        case_sensitive=False
    )


settings = Settings()
