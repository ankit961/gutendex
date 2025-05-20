from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

# ✅ Load the .env file from root (one level up from app/)
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    DATABASE_URL: str
    LLM_MODEL_PATH: str 

    class Config:
        env_file = env_path

settings = Settings()
print("✅ Loaded LLM_MODEL_PATH:", settings.LLM_MODEL_PATH)


print("✅ Loaded DATABASE_URL:", settings.DATABASE_URL)  # Debug
