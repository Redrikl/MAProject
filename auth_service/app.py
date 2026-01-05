# auth_service/app.py
import os
from datetime import datetime
from functools import wraps
from passlib.context import CryptContext

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)

from passlib.context import CryptContext

# ---------- Config ----------
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-to-a-secret-key")
SESSION_COOKIE_NAME = "user_platform_session"

pwd_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = SECRET_KEY
app.config["SESSION_COOKIE_NAME"] = SESSION_COOKIE_NAME

# ---------- In-memory user store ----------
# Structure: users[username] = {id, username, email, password_hash, created_at, status}
users = {}
_next_id = 1


def _generate_id():
    global _next_id
    val = _next_id
    _next_id += 1
    return val


# ---------- Helpers ----------
def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_ctx.verify(password, password_hash)


def get_user_by_username(username: str):
    return users.get(username)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            flash("Требуется авторизация", "warning")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)

    return wrapper


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

        # Basic validation
        if not username or not password:
            flash("Имя пользователя и пароль обязательны.", "danger")
            return redirect(url_for("register"))

        if password != password2:
            flash("Пароли не совпадают.", "danger")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Пароль должен быть не короче 6 символов.", "danger")
            return redirect(url_for("register"))

        if get_user_by_username(username):
            flash("Пользователь с таким именем уже существует.", "danger")
            return redirect(url_for("register"))

        # Create user
        pw_hash = hash_password(password)
        user = {
            "id": _generate_id(),
            "username": username,
            "email": email,
            "password_hash": pw_hash,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "status": "active",
        }
        users[username] = user

        # Auto-login
        session["username"] = username
        flash("Регистрация успешна. Вы вошли в систему.", "success")
        return redirect(url_for("profile"))

    return render_template("register.html")


@app.route("/auth/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Введите логин и пароль.", "danger")
            return redirect(url_for("login"))

        user = get_user_by_username(username)
        if not user or not verify_password(password, user["password_hash"]):
            flash("Неверный логин или пароль.", "danger")
            return redirect(url_for("login"))

        session["username"] = username
        flash("Успешный вход.", "success")
        next_page = request.args.get("next") or url_for("profile")
        return redirect(next_page)

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
    user = get_user_by_username(username)
    if not user:
        flash("Пользователь не найден.", "danger")
        return redirect(url_for("index"))

    # Don't send password_hash to the template
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    return render_template("profile.html", user=safe_user)


# ---------- Simple health check endpoints ----------
@app.route("/health/live")
def health_live():
    return "OK", 200


@app.route("/health/ready")
def health_ready():
    # For now just return OK; later check DB/redis/etc.
    return "READY", 200


# ---------- Run ----------
if __name__ == "__main__":
    # For local dev only; in Docker / k8s use gunicorn/uvicorn, etc.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
