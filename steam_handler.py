from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hbold, hitalic
from parsers.steam import SteamParser
from typing import Dict, List

steam_parser = SteamParser()

async def search_steam_games(query: str) -> List[Dict]:
    """Поиск игр в Steam по названию"""
    return steam_parser.search_games(query)

async def get_steam_game_by_url(url: str) -> Dict:
    """Получение информации об игре по URL"""
    return steam_parser.get_game_by_url(url)

def create_steam_search_keyboard(games: list, page: int = 0, items_per_page: int = 5) -> InlineKeyboardMarkup:
    """Создает клавиатуру с результатами поиска"""
    builder = InlineKeyboardBuilder()
    
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(games))
    
    for i in range(start_idx, end_idx):
        game = games[i]
        builder.button(
            text=f"{i+1}. {game['name']}",
            callback_data=f"steam_select_{game['id']}"
        )
        builder.adjust(1)
    
    nav_buttons = [
        InlineKeyboardButton(
            text="◀️" if page > 0 else "　",
            callback_data=f"steam_page_{page-1}" if page > 0 else "steam_page_none"
        ),
        InlineKeyboardButton(
            text=f"📄 {page + 1}/{(len(games) + items_per_page - 1) // items_per_page}",
            callback_data="steam_page_current"
        ),
        InlineKeyboardButton(
            text="▶️" if (page + 1) * items_per_page < len(games) else "　",
            callback_data=f"steam_page_{page+1}" if (page + 1) * items_per_page < len(games) else "steam_page_none"
        )
    ]
    
    builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="steam_search_cancel"
    ))
    
    return builder.as_markup()

def format_steam_post(game_info: Dict) -> str:
    """Форматирует пост для игры из Steam"""
    if game_info['is_free']:
        price_text = "Бесплатно!"
    else:
        prices = []
        
        if game_info['price']['RUB']['current'] != -1:
            rub_price = f"{game_info['price']['RUB']['current']} ₽"
            if game_info['price']['discount'] > 0:
                rub_price = f"{rub_price} (-{game_info['price']['discount']}%)"
            prices.append(rub_price)
        else:
            prices.append("Неизвестно")
            
        if game_info['price']['KZT']['current'] != -1:
            kzt_price = f"{game_info['price']['KZT']['current']} ₸"
            if game_info['price']['discount'] > 0:
                kzt_price = f"{kzt_price} (-{game_info['price']['discount']}%)"
            prices.append(kzt_price)
        else:
            prices.append("Неизвестно")
            
        price_text = f"RUB: {prices[0]}\nKZT: {prices[1]}"
    
    text = [
        f"🎮 {hbold(game_info['title'])}",
        f"{hitalic(f'От разработчика: {game_info['developers'][0]}')}",
        "",
        f"💰 {hbold('Цена:')}\n{price_text}",
        "",
        f"🔗 {hbold('Страница игры:')}",
        f"https://store.steampowered.com/app/{game_info['steam_appid']}/",
        "",
        hitalic(game_info['description']),
        "",
        "#steam"
    ]
    
    return "\n".join(text) 