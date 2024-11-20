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
        button_text = str(i+1) + ". " + game['name']
        callback_data = "steam_select_" + str(game['id'])
        builder.button(
            text=button_text,
            callback_data=callback_data
        )
        builder.adjust(1)
    
    prev_callback = "steam_page_" + str(page-1) if page > 0 else "steam_page_none"
    next_callback = "steam_page_" + str(page+1) if (page + 1) * items_per_page < len(games) else "steam_page_none"
    page_text = "📄 " + str(page + 1) + "/" + str((len(games) + items_per_page - 1) // items_per_page)
    
    nav_buttons = [
        InlineKeyboardButton(
            text="◀️" if page > 0 else "　",
            callback_data=prev_callback
        ),
        InlineKeyboardButton(
            text=page_text,
            callback_data="steam_page_current"
        ),
        InlineKeyboardButton(
            text="▶️" if (page + 1) * items_per_page < len(games) else "　",
            callback_data=next_callback
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
            rub_price = str(game_info['price']['RUB']['current']) + " ₽"
            if game_info['price']['discount'] > 0:
                rub_price = rub_price + " (-" + str(game_info['price']['discount']) + "%)"
            prices.append(rub_price)
        else:
            prices.append("Неизвестно")
            
        if game_info['price']['KZT']['current'] != -1:
            kzt_price = str(game_info['price']['KZT']['current']) + " ₸"
            if game_info['price']['discount'] > 0:
                kzt_price = kzt_price + " (-" + str(game_info['price']['discount']) + "%)"
            prices.append(kzt_price)
        else:
            prices.append("Неизвестно")
            
        price_text = "RUB: " + prices[0] + "\nKZT: " + prices[1]
    
    developer_text = "От разработчика: " + game_info['developers'][0]
    url = "https://store.steampowered.com/app/" + str(game_info['steam_appid']) + "/"
    
    text = [
        "🎮 " + hbold(game_info['title']),
        hitalic(developer_text),
        "",
        "💰 " + hbold('Цена:') + "\n" + price_text,
        "",
        "🔗 " + hbold('Страница игры:'),
        url,
        "",
        hitalic(game_info['description']),
        "",
        "#steam"
    ]
    
    return "\n".join(text) 