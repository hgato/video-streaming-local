from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGO_URL: str = "mongodb://localhost:27017"
    MONGO_DB: str = "videos"
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"


settings = Settings()
