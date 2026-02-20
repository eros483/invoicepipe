# ----- importable configurations @ src/core/config.py -----
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

load_dotenv()

class Settings(BaseSettings):
    """
    Central management for settings and configurations
    Reads .env file
    - Groq api key
    - Groq vision model name
    - Output file path for approved invoices CSV
    - Output file path for manual review log
    - Rounding tolerance for validation logic
    """
    GROQ_API_KEY: str=os.getenv("GROQ_API_KEY")
    GROQ_MODEL_NAME: str=os.getenv("GROQ_MODEL_NAME", "meta-llama/llama-4-scout-17b-16e-instruct")
    PATH_APPROVED_CSV: str=os.getenv("PATH_APPROVED_CSV", "approved_invoices.csv")
    PATH_REVIEW_TXT: str=os.getenv("PATH_REVIEW_TXT", "manual_review_needed.txt")
    ROUNDING_TOLERANCE: float=float(os.getenv("ROUNDING_TOLERANCE", "0.01"))

settings = Settings()