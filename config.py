"""Application configuration loaded from environment variables."""
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/careerpilot.db"))
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = PROJECT_ROOT / DATABASE_PATH

HIREBASE_API_URL = os.getenv("HIREBASE_API_URL", "https://api.hirebase.com/v1/jobs")
HIREBASE_API_KEY = os.getenv("HIREBASE_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
if GEMINI_MODEL in {
    "gemini-1.5-flash",
    "models/gemini-1.5-flash",
    "gemini-2.5-flash",
    "models/gemini-2.5-flash",
    "gemini-3.8-flash",
    "models/gemini-3.8-flash",
    "gemini-3.5-flash-lite",
}:
    GEMINI_MODEL = "gemini-3.5-flash"
