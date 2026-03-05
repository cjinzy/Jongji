"""애플리케이션 설정 모듈.

pydantic-settings를 사용하여 환경 변수 및 .env 파일에서 설정을 로드합니다.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 전역 설정.

    환경 변수 또는 .env 파일에서 값을 읽어옵니다.
    """

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://jongji:jongji@localhost:5432/jongji"

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # App
    APP_NAME: str = "Jongji"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
