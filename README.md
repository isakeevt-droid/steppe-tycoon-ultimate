# Steppe Tycoon v10.2

Полная версия проекта с backend + frontend.

## Что включено
- полный проект в папках `backend/` и `frontend/`
- фиксы по сундуку, дирхамам и питомцу из сундука
- защита от потери Telegram-сессии после сворачивания
- сохранение последней открытой вкладки и фильтра зданий
- мобильные улучшения интерфейса:
  - более плотные карточки
  - быстрые кнопки количества для каравана: `25% / 50% / Макс`
  - одна колонка для быстрых действий на узких экранах
  - более удобные размеры кнопок и полей на телефоне
- `run_local.bat` для запуска на Windows

## Структура
- `backend/` — FastAPI backend
- `frontend/` — HTML/CSS/JS
- `data/` — сюда создастся локальная SQLite база
- `requirements.txt`
- `.env.example`
- `run_local.bat`

## Быстрый запуск
### Windows
Запусти `run_local.bat`

### Вручную
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Открыть в браузере:
- `http://127.0.0.1:8000/`

## Для Telegram WebApp
Нужна переменная окружения:
- `TELEGRAM_BOT_TOKEN=...`

## Для деплоя на PostgreSQL
Задай:
- `DATABASE_URL=postgresql://...`
- `TELEGRAM_BOT_TOKEN=...`

Если `DATABASE_URL` не задан, проект сам запустится на SQLite.
