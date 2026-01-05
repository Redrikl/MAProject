# auth_service/config.py
import os

# Для локальной разработки по умолчанию SQLite в файле
DEFAULT_DB = "sqlite:///./dev_db.sqlite3"

DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DB)
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-prod")
