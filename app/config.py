import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    # Construct database URI dynamically
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS")
    JWT_ACCESS_TOKEN_EXPIRES = os.getenv("JWT_ACCESS_TOKEN_EXPIRES")
    REDIS_VALID_TTL = os.getenv("REDIS_VALID_TTL")
    REDIS_RATE_LIMIT_TTL = os.getenv("REDIS_RATE_LIMIT_TTL")
    JWT_REFRESH_TOKEN_EXPIRES = os.getenv("JWT_REFRESH_TOKEN_EXPIRES")
    RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL")

    OTP_VALIDITY_SECONDS = os.getenv("OTP_VALIDITY_SECONDS")
    OTP_LENGTH = os.getenv("OTP_LENGTH")
    TOKEN_VALIDITY_SECONDS = os.getenv("TOKEN_VALIDITY_SECONDS")
    RATE_LIMIT_MESSAGE = os.getenv("RATE_LIMIT_MESSAGE")
