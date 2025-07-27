# Инструкция по запуску GameChebService

## Предварительные требования

1. Установлен Python 3.13+
2. Активировано виртуальное окружение
3. Установлены зависимости: `pip install -r requirements.txt`
4. Настроен файл `.env` с токеном бота

## Запуск системы

### 1. Запуск Django сервера

```bash
# Активируем виртуальное окружение
source venv/bin/activate

# Запускаем Django сервер на порту 8000
python manage.py runserver 8000
```

Django сервер будет доступен по адресу: http://localhost:8000/

### 2. Запуск Telegram бота

В новом терминале:

```bash
# Активируем виртуальное окружение
source venv/bin/activate

# Запускаем бота в режиме polling
python run_polling.py
```

### 3. Альтернативный запуск через run_bot.py

Для запуска Django + бота в одном процессе:

```bash
source venv/bin/activate
python run_bot.py
```

## Проверка работы

1. **Django сервер**: Откройте http://localhost:8000/ в браузере
2. **Telegram бот**: Найдите бота в Telegram и отправьте команду `/start`

## Остановка

Для остановки процессов используйте `Ctrl+C` в соответствующих терминалах.

## Структура после рефакторинга

- `bot/base_handlers.py` - базовый класс для обработчиков
- `bot/point_handlers.py` - обработчики точек маршрута
- `bot/route_handlers.py` - обработчики маршрутов
- `bot/handlers.py` - главный файл объединения
- `bot/admin_commands.py` - административные команды
- `run_polling.py` - запуск бота в режиме polling
- `run_bot.py` - запуск Django + бота

## Логи

- Django логи выводятся в терминал с сервером
- Логи бота выводятся в терминал с `run_polling.py` 