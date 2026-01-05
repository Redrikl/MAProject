# auth_service/app.py
import os
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash

from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError

# локальная конфигурация
from .config import DATABASE_URL, SECRET_KEY as CONFIG_SECRET_KEY
from .db import Session, engine
from .models import Base, User

# ---------- Config ----------
SECRET_KEY = os.environ.get("SECRET_KEY", CONFIG_SECRET_KEY)
SESSION_COOKIE_NAME = "user_platform_session"

pwd_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = SECRET_KEY
app.config["SESSION_COOKIE_NAME"] = SESSION_COOKIE_NAME

# ---------- Helpers ----------
def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_ctx.verify(password, password_hash)


def login_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            flash("Требуется авторизация", "warning")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)

    return wrapper


def create_db_tables():
    """Только для быстрой локальной разработки.
    В продакшне/при миграциях используйте alembic upgrade head."""
    Base.metadata.create_all(bind=engine)


# ---------- Routes ----------
@app.route("/")
def index():
    logged_in = "username" in session
    username = session.get("username")
    return render_template("index.html", logged_in=logged_in, username=username)


@app.route("/auth/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        if not username or not password:
            flash("Имя пользователя и пароль обязательны.", "danger")
            return redirect(url_for("register"))

        if password != password2:
            flash("Пароли не совпадают.", "danger")
            return redirect(url_for("register"))

        # длина пароля — серверная проверка (не обрезаем)
        if len(password.encode("utf-8")) > 4096:
            flash("Пароль слишком длинный.", "danger")
            return redirect(url_for("register"))

        pw_hash = hash_password(password)

        db = Session()
        try:
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                flash("Пользователь с таким именем уже существует.", "danger")
                return redirect(url_for("register"))

            user = User(username=username, email=email, password_hash=pw_hash)
            db.add(user)
            db.commit()
            db.refresh(user)
            session["username"] = user.username
            flash("Регистрация успешна. Вы вошли в систему.", "success")
            return redirect(url_for("profile"))
        except IntegrityError:
            db.rollback()
            flash("Ошибка при создании пользователя. Попробуйте другое имя.", "danger")
            return redirect(url_for("register"))
        finally:
            db.close()

    return render_template("register.html")


@app.route("/auth/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Введите логин и пароль.", "danger")
            return redirect(url_for("login"))

        db = Session()
        try:
            user = db.query(User).filter(User.username == username).first()
            if not user or not verify_password(password, user.password_hash):
                flash("Неверный логин или пароль.", "danger")
                return redirect(url_for("login"))

            session["username"] = user.username
            flash("Успешный вход.", "success")
            next_page = request.args.get("next") or url_for("profile")
            return redirect(next_page)
        finally:
            db.close()

    return render_template("login.html")


@app.route("/auth/logout", methods=["POST", "GET"])
def logout():
    session.pop("username", None)
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("index"))


@app.route("/profile")
@login_required
def profile():
    username = session.get("username")
    db = Session()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            flash("Пользователь не найден.", "danger")
            return redirect(url_for("index"))
        safe_user = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at,
            "status": user.status,
        }
        return render_template("profile.html", user=safe_user)
    finally:
        db.close()


# ---------- health ----------
@app.route("/health/live")
def health_live():
    return "OK", 200


@app.route("/health/ready")
def health_ready():
    # сюда в будущем добавим проверки DB/Redis
    return "READY", 200


# ---------- Run ----------
if __name__ == "__main__":
    # Для локальной разработки можно создать таблицы автоматически.
    # В CI/production используем alembic миграции и тогда этот вызов можно убрать.
    create_db_tables()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
