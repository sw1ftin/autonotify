import locale
import sys

# Альтернативный вариант настройки кодировки
if sys.platform == 'win32':
    try:
        locale.setlocale(locale.LC_ALL, 'Russian_Russia.1251')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '')  # Системная локаль по умолчанию
else:
    try:
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '')

from datetime import datetime
import json
from typing import Dict, List, Tuple
import pytz
from parsers.epicgames import get_free_games

def get_discord_timestamp(date_str: str, format_type: str = 'F') -> str:
    """Преобразует дату в Discord timestamp
    Форматы:
    t - 16:20
    T - 16:20:30
    d - 20/04/2021
    D - 20 April 2021
    f - 20 April 2021 16:20
    F - Tuesday, 20 April 2021 16:20
    R - relative time
    """
    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    unix_ts = int(dt.timestamp())
    return f"<t:{unix_ts}:{format_type}>"

def get_telegram_timestamp(date_str: str) -> str:
    """Преобразует дату в человекочитаемый формат для Telegram"""
    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    msk = pytz.timezone('Europe/Moscow')
    dt = dt.astimezone(msk)
    formatted_date = dt.strftime("%d.%m.%Y %H:%M (МСК)")
    return escape_markdown_v2(formatted_date)

def format_price(price_data: Dict) -> str:
    """Форматирует цену игры"""
    if price_data["RUB"]["original"] != -1:
        return f"{price_data['RUB']['original']} ₽"
    return f"${price_data['USD']['original']}"

def escape_markdown_v2(text: str) -> str:
    """Экранирует специальные символы для Telegram MarkdownV2"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    escaped_text = text
    for char in special_chars:
        escaped_text = escaped_text.replace(char, f'\\{char}')
    return escaped_text

def generate_game_post(game: Dict, platform: str = 'discord') -> Tuple[str, str]:
    """Генерирует пост для одной игры с учетом платформы (discord/telegram)"""
    if platform == 'discord':
        template = f""":video_game: **{game['title']}**
*От разработчика: {game['publisher']}*

:alarm_clock: **Период раздачи:**
:white_small_square: Начало: {get_discord_timestamp(game['start_date'], 'f')}
:white_small_square: Конец: {get_discord_timestamp(game['end_date'], 'f')}
:white_small_square: Заканчивается {get_discord_timestamp(game['end_date'], 'R')}

:moneybag: **Обычная цена:** {format_price(game['price'])}
:inbox_tray: **Сейчас:** Хватай бесплатно! :URA:

:link: **Забрать игру:**
<{game['url']}>

*{'Доступно' if game['available_in_russia'] else 'Недоступно'} на аккаунтах с регионом Россия {':URA:' if game['available_in_russia'] else ':SAJ:'}*"""
    else:
        title = escape_markdown_v2(game['title'])
        publisher = escape_markdown_v2(game['publisher'])
        price = escape_markdown_v2(format_price(game['price']))
        url = game['url']
        start_date = get_telegram_timestamp(game['start_date'])
        end_date = get_telegram_timestamp(game['end_date'])
        
        template = f"""🎮 *{title}*
_От разработчика: {publisher}_

⏰ *Период раздачи:*
▫️ Начало: {start_date}
▫️ Конец: {end_date}

💰 *Обычная цена:* {price}
📥 *Сейчас:* Хватай бесплатно\\! 🎉

🔗 *Забрать игру:*
{url}

_{'Доступно' if game['available_in_russia'] else 'Недоступно'} на аккаунтах с регионом Россия {'🎉' if game['available_in_russia'] else '😢'}_"""

    return template, game['image_url']

def generate_posts(platform: str = 'all') -> Dict[str, Dict[str, str]]:
    """Генерирует посты для игр в выбранном формате
    
    Args:
        platform: 'all', 'discord' или 'telegram'
    """
    games = get_free_games()
    if not games:
        raise Exception("Не удалось получить данные об играх")
    
    posts = {}
    for game in games:
        post_key = f"epic_games_{game['title'].lower().replace(' ', '_')}"
        posts[post_key] = {"image": game['image_url']}
        
        if platform in ['all', 'discord']:
            discord_text, _ = generate_game_post(game, 'discord')
            posts[post_key]["discord_text"] = discord_text
            
        if platform in ['all', 'telegram']:
            telegram_text, _ = generate_game_post(game, 'telegram')
            posts[post_key]["telegram_text"] = telegram_text
    
    return posts

def save_posts_to_file(posts: Dict[str, Dict[str, str]], filename: str = "generated_posts.txt"):
    """Сохраняет посты в файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        for key, post_data in posts.items():
            f.write(f"\n=== {key} ===\n\n")
            
            if 'discord_text' in post_data:
                f.write("=== DISCORD POST ===\n")
                f.write(post_data['discord_text'])
                f.write("\n\n")
                
            if 'telegram_text' in post_data:
                f.write("=== TELEGRAM POST ===\n")
                f.write(post_data['telegram_text'])
                f.write("\n\n")
                
            f.write("=== IMAGE URL ===\n")
            f.write(post_data['image'])
            f.write("\n\n" + "="*50 + "\n")

if __name__ == "__main__":
    try:
        posts = generate_posts('all')
        for key, post_data in posts.items():
            print(f"\n=== {key} ===\n")
            
            if 'discord_text' in post_data:
                print("=== DISCORD POST ===")
                print(post_data['discord_text'])
                print()
                
            if 'telegram_text' in post_data:
                print("=== TELEGRAM POST ===")
                print(post_data['telegram_text'])
                print()
                
            print("=== IMAGE URL ===")
            print(post_data['image'])
            print("\n" + "="*50)
        
        save_posts_to_file(posts)
        print("\nПосты успешно сохранены в generated_posts.txt")
        
    except Exception as e:
        print(f"Произошла ошибка: {e}")
