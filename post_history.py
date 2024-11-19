import json
from datetime import datetime
import os

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

def add_to_history(game_info: dict, post_type: str = 'auto'):
    """Добавляет пост в историю"""
    try:
        history = load_history()
        history.append({
            'title': game_info['title'],
            'status': game_info['status'],
            'post_time': datetime.now().isoformat(),
            'post_type': post_type,
            'start_date': game_info['start_date'],
            'end_date': game_info['end_date']
        })
        save_history(history)
    except Exception as e:
        print(f"Ошибка при добавлении в историю: {e}")

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