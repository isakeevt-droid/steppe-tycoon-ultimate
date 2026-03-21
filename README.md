# Steppe Tycoon v10.0

Основа собрана на твоих текущих файлах с сохранением существующих механик и интерфейса.

## Что добавлено
- поддержка `DATABASE_URL` для PostgreSQL
- безопасный fallback на SQLite для локального запуска
- вкладка **Рабочие**
- найм, улучшение и **увольнение** работников
- защита от 500 при быстрых тапах в шахте:
  - последовательная обработка кликов на backend
  - антиспам на frontend
- сохранён Telegram auth без тихого fallback на другой профиль внутри Telegram

## Структура
- `backend/` — FastAPI backend
- `frontend/` — HTML/CSS/JS
- `data/steppe_tycoon.db` — твоя текущая SQLite база как локальный backup
- `requirements.txt`
- `.env.example`

## Локальный запуск
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Открыть:
- `http://127.0.0.1:8000/`

## PostgreSQL для деплоя
Задай переменные окружения:
- `DATABASE_URL=postgresql://...`
- `TELEGRAM_BOT_TOKEN=...`

Проект сам нормализует `postgres://` и `postgresql://` в драйвер `psycopg`.

## Важно
- Если `DATABASE_URL` не задан, игра запускается на локальной SQLite базе.
- Для локальной проверки можно использовать приложенную `data/steppe_tycoon.db`.
- Для продакшна лучше использовать PostgreSQL.
