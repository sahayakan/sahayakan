from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    postgres_user: str = "sahayakan"
    postgres_password: str = "sahayakan_dev_password"
    postgres_db: str = "sahayakan"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # MinIO
    minio_root_user: str = "sahayakan"
    minio_root_password: str = "sahayakan_dev_password"
    minio_endpoint: str = "localhost:9000"

    # Knowledge Cache
    knowledge_cache_path: str = "/data/knowledge-cache"

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_file": ".env"}


settings = Settings()
