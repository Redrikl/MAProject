# auth_service/config.py
import os

# Если переменная окружения не задана, используем локальный SQLite (dev fallback)
DEFAULT_DB = "sqlite:///./dev_db.sqlite3"

DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DB)
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-prod")
PORT = int(os.environ.get("PORT", 5000))
