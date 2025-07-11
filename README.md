# AutoNotify Bot

Telegram бот для автоматического отслеживания и публикации информации о:
- Бесплатных раздачах в Epic Games Store
- Больших скидках в Steam

## Возможности

- Автоматическая публикация новых раздач из EGS
- Отслеживание скидок в Steam (минимальный процент скидки можно настроить в settings.cfg)
- Поиск игр в Steam по названию
- Создание постов по ссылке на игру
- Поддержка цен в разных валютах (RUB, KZT)

## Команды

- `/start`, `/help` - Список команд
- `/post` - Предпросмотр и публикация раздач Epic Games
- `/steam_search [название]` - Поиск игры в Steam
- `/steam_url [ссылка]` - Создание поста по ссылке на игру Steam

Также бот поддерживает прямой поиск по названию игры и созданию постов по ссылкам Steam без использования команд.

# Installation
1. Fill `.env`
2. Install `uv`: `pip install uv`
3. Run command:
```shell
uv venv && source .venv/bin/activate && uv pip install -r requirements.txt && uv run main.py
```
