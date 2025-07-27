# Используем минимальный Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Устанавливаем системные зависимости (если нужно Pillow, psycopg2 и т.п.)
RUN apt-get update && apt-get install -y \
    gcc libpq-dev python3-dev musl-dev \
    && apt-get clean

# Копируем зависимости и устанавливаем
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Открываем порт (если нужно)
EXPOSE 8000

# Устанавливаем переменные окружения (будут переопределяться в docker run)
ENV PYTHONUNBUFFERED=1

# Стартовый скрипт
CMD ["python", "run_bot.py"]
