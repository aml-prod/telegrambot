FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Кириллица и Pillow-зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core fonts-dejavu-extra fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY bot /app/bot
COPY pyproject.toml /app/

# Директория для файлов/БД
RUN mkdir -p /app/storage
VOLUME ["/app/storage"]

# По умолчанию ничего не запускаем: команду задаёт compose