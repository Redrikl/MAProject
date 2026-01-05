# auth_service/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .config import DATABASE_URL

# Для SQLite: check_same_thread аргумент нужен при использовании многопоточности с SQLite
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Опция scoped_session для безопасности в многопоточном сервере (gunicorn)
Session = scoped_session(SessionLocal)

def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
