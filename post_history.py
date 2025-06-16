import json
from datetime import datetime, timezone
import os
from typing import Optional

HISTORY_FILE = 'data/post_history.json'

def ensure_history_file():
    """Создает файл истории, если он не существует"""
    os.makedirs('data', exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def load_history():
    """Загружает историю постов"""
    ensure_history_file()
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []

def save_history(history):
    """Сохраняет историю постов"""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def add_to_history(game_info: dict, post_type: str = 'auto', chat_id: Optional[int] = None, message_id: Optional[int] = None):
    """Добавляет пост в историю"""
    history = load_history()
    now = datetime.now(timezone.utc).isoformat()
    title = game_info.get('title') or ''
    status = game_info.get('status') or 'active'
    start_date = game_info.get('start_date') or now
    end_date = game_info.get('end_date') or now
    entry = {
        'title': title,
        'status': status,
        'post_time': now,
        'post_type': post_type,
        'chat_id': chat_id,
        'message_id': message_id,
        'start_date': start_date,
        'end_date': end_date
    }
    save_history(history + [entry])

def is_game_posted(game_title: str) -> bool:
    """Проверяет, был ли уже пост об этой игре"""
    try:
        history = load_history()
        return any(post['title'].lower() == game_title.lower() for post in history)
    except Exception as e:
        print(f"Ошибка при проверке истории: {e}")
        return False

def remove_from_history(game_title: str):
    """Удаляет игру из истории"""
    try:
        history = load_history()
        history = [post for post in history if post['title'].lower() != game_title.lower()]
        save_history(history)
    except Exception as e:
        print(f"Ошибка при удалении из истории: {e}")

def get_posted_games() -> list:
    """Возвращает список всех опубликованных игр"""
    try:
        history = load_history()
        return history
    except Exception as e:
        print(f"Ошибка при получении истории: {e}")
        return []