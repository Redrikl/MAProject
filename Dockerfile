FROM python:3.10-slim

# отключаем буферизацию логов
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# зависимости
COPY auth_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# код
COPY auth_service ./auth_service

# переменные окружения (можно переопределить)
ENV FLASK_ENV=production
ENV PORT=5000

EXPOSE 5000

# ВАЖНО: запуск как модуля
CMD ["python", "-m", "auth_service.app"]
