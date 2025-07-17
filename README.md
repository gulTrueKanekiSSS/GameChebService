# GameCheb

**GameCheb** — это backend API-сервис для веб-приложения и Telegram-бота. Проект позволяет создавать и управлять маршрутами с медиа-точками (фото, видео, аудио) через Telegram, а также предоставляет REST API для фронтенда, который отображает маршруты пользователям.

---

## 📌 Возможности

- Создание маршрутов и точек через Telegram-бот
- Хранение медиафайлов в Яндекс Object Storage (S3)
- REST API для фронтенда
- Поддержка текстовых описаний, аудио, фото, видео
- Интеграция с Render для автодеплоя

---

## 🛠️ Стек технологий

- Python
- Django 5.2
- Django REST Framework
- aiogram 3.20 (Telegram bot)
- PostgreSQL
- Yandex Object Storage
- Render (деплой)

---

## 🚀 Разворачивание

Проект автоматически деплоится на [Render](https://render.com) при каждом коммите.  
Запуск включает:
- `run_bot.py` — Telegram-бот
- Web-сервер aiohttp для обхода ограничений бесплатного тарифа Render

### Запуск вручную

```bash
git clone https://github.com/yourusername/gamecheb.git
cd gamecheb

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
python manage.py migrate

# Запуск Django-сервера
python manage.py runserver

# Отдельно запустить Telegram-бота
python run_bot.py
```
### ⚙️ Переменные окружения
#### Создай файл .env и добавь туда:

env

AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
ADMIN_GROUP_ID=...
ADMIN_IDS=...
DATABASE_URL=postgres://user:pass@host:port/dbname
DEBUG=True
DJANGO_SECRET_KEY=your_secret_key
PYTHON_VERSION=3.12
TELEGRAM_BOT_TOKEN=your_bot_token
WEBHOOK_URL=https://yourdomain.com/webhook/

---

core - основные настройки проекта

api - REST api

bot - логика бота

quest_bot - Django для работы с ботом