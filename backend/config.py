import os
from dotenv import load_dotenv

load_dotenv("backend/.env")

class Config:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    MODEL_PATH: str = os.getenv("MODEL_PATH", "models/forecaster.pkl")
    WEATHER_CITY: str = os.getenv("WEATHER_CITY", "Singapore")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

config = Config()