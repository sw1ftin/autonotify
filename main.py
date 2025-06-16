import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold, hitalic, hlink
from generate_post import generate_posts
from parsers.epicgames import get_free_games
import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
from post_history import add_to_history, is_game_posted, get_posted_games, remove_from_history
from steam_handler import (
    search_steam_games, get_steam_game_by_url,
    create_steam_search_keyboard, format_steam_post,
    steam_parser
)
import configparser
from pathlib import Path
from typing import Optional

load_dotenv()

config = configparser.ConfigParser()
config.read('settings.cfg', encoding='utf-8')

TIMEZONE = config.get('timezone', 'timezone', fallback='Europe/Moscow')
CHECK_INTERVAL = config.getint('check_interval', 'interval', fallback=3600)
STEAM_MIN_DISCOUNT = config.getint('steam', 'min_discount', fallback=50)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv('TG_BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Не установлен токен бота (TG_BOT_TOKEN)")

CHANNEL_ID = os.getenv('TG_CHANNEL_ID')
if not CHANNEL_ID:
    raise ValueError("Не установлен ID канала (TG_CHANNEL_ID)")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_post_keyboard(post_id: str, game_info: dict = None) -> Optional[InlineKeyboardMarkup]:
    """Создает клавиатуру с кнопками для поста"""
    buttons = []
    
    if post_id:
        buttons.append([
            InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"post_{post_id}"),
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_{post_id}")
        ])
    
    if game_info and game_info.get('status') == 'active':
        buttons.append([
            InlineKeyboardButton(text="🎮 Забрать игру", url=game_info['url'])
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

def format_game_post(game_info: dict) -> str:
    """Форматирует пост об игре используя HTML разметку"""
    start_date = datetime.fromisoformat(game_info['start_date'].replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(game_info['end_date'].replace('Z', '+00:00'))
    msk_tz = pytz.timezone('Europe/Moscow')
    start_date_msk = start_date.astimezone(msk_tz).strftime("%d.%m.%Y %H:%M (МСК)")
    end_date_msk = end_date.astimezone(msk_tz).strftime("%d.%m.%Y %H:%M (МСК)")
    
    price = (f"{game_info['price']['RUB']['original']} ₽" 
             if game_info['price']['RUB']['original'] != -1 
             else f"${game_info['price']['USD']['original']}")
    
    status_tags = {
        'active': '#актуально',
        'upcoming': '#скоро',
        'ended': '#завершено'
    }
    
    publisher_text = 'От разработчика: ' + game_info['publisher']
    
    text = [
        "🎮 " + hbold(game_info['title']),
        hitalic(publisher_text),
        "",
        hbold('⏰ Период раздачи:'),
        "▫️ Начало: " + start_date_msk,
        "▫️ Конец: " + end_date_msk,
        "",
        "💰 " + hbold('Обычная цена:') + " " + price,
        "📥 " + hbold('Сейчас:') + " Хватай бесплатно! 🎉",
        "",
        "🔗 " + hbold('Забрать игру:'),
        game_info['url'],
        "",
        hitalic(
            "Доступно на аккаунтах с регионом Россия 🎉" 
            if game_info['available_in_russia'] 
            else "Недоступно на аккаунтах с регионом Россия 😢"
        ),
        "",
        status_tags.get(game_info['status'], '') + " #egs"
    ]
    
    return "\n".join(text)

async def check_steam_deals():
    """Проверяет скидки в Steam"""
    try:
        search_results = steam_parser.search_games("free")
        
        for game in search_results:
            game_info = steam_parser.get_game_by_id(str(game['id']))
            if game_info and not is_game_posted(game_info['title']):
                if game_info['price']['discount'] >= STEAM_MIN_DISCOUNT:
                    formatted_text = format_steam_post(game_info)
                    await bot.send_photo(
                        chat_id=CHANNEL_ID,
                        photo=game_info['image_url'],
                        caption=formatted_text,
                        parse_mode=ParseMode.HTML
                    )
                    add_to_history(game_info, 'auto')
                    await asyncio.sleep(2)
    except Exception as e:
        logging.error("Ошибка при проверке Steam: " + str(e))

async def check_ended_giveaways():
    """Проверяет завершенные раздачи"""
    try:
        posted_games = get_posted_games()
        current_time = datetime.now(pytz.UTC)
        
        for game in posted_games:
            try:
                end_time = datetime.fromisoformat(game['end_date'].replace('Z', '+00:00'))
                if current_time > end_time:
                    game['status'] = 'ended'
                    text = [
                        "🚫 " + hbold('Раздача завершена'),
                        "",
                        "🎮 " + hbold(game['title']),
                        "",
                        "Раздача этой игры больше не доступна.",
                        "",
                        "#завершено \n#egs"
                    ]
                    
                    await bot.send_message(
                        chat_id=CHANNEL_ID,
                        text="\n".join(text),
                        parse_mode=ParseMode.HTML
                    )
                    
                    remove_from_history(game['title'])
                    logging.info("Удалена завершенная раздача: " + game['title'])
            except Exception as e:
                logging.error("Ошибка при обработке завершенной раздачи " + game['title'] + ": " + str(e))
                continue
                
    except Exception as e:
        logging.error("Ошибка при проверке завершенных раздач: " + str(e))

async def check_started_giveaways():
    """Проверяет начавшиеся раздачи"""
    try:
        posted_games = get_posted_games()
        current_time = datetime.now(pytz.UTC)
        
        for game in posted_games:
            try:
                if game['status'] == 'upcoming':
                    start_time = datetime.fromisoformat(game['start_date'].replace('Z', '+00:00'))
                    if current_time >= start_time:
                        games = get_free_games()
                        game_info = next((g for g in games if g['title'] == game['title']), None)
                        
                        if game_info and game_info['status'] == 'active':
                            formatted_text = format_game_post(game_info)
                            await bot.send_photo(
                                chat_id=CHANNEL_ID,
                                photo=game_info['image_url'],
                                caption=formatted_text,
                                parse_mode=ParseMode.HTML,
                                reply_markup=get_post_keyboard(None, game_info)
                            )
                            
                            remove_from_history(game['title'])
                            add_to_history(game_info, 'auto')
                            
                            logging.info("Обновлен статус раздачи: " + game['title'])
            except Exception as e:
                logging.error("Ошибка при обработке начавшейся раздачи " + game['title'] + ": " + str(e))
                continue
    except Exception as e:
        logging.error("Ошибка при проверке начавшихся раздач: " + str(e))

async def periodic_checks():
    """Периодическая проверка обеих платформ"""
    while True:
        try:
            logging.info("Проверка завершенных раздач")
            await check_ended_giveaways()
            
            logging.info("Проверка начавшихся раздач")
            await check_started_giveaways()
            
            logging.info("Запуск проверки Epic Games")
            games = get_free_games()
            if games:
                for game in games:
                    if not is_game_posted(game['title']):
                        formatted_text = format_game_post(game)
                        await bot.send_photo(
                            chat_id=CHANNEL_ID,
                            photo=game['image_url'],
                            caption=formatted_text,
                            parse_mode=ParseMode.HTML,
                            reply_markup=get_post_keyboard(None, game)
                        )
                        add_to_history(game, 'auto')
                        await asyncio.sleep(2)
            
            logging.info("Запуск проверки Steam")
            await check_steam_deals()
            
            logging.info("Проверки завершены, следующая через " + str(CHECK_INTERVAL) + " секунд")
            await asyncio.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            logging.error("Ошибка при выполнении периодических проверок: " + str(e))
            await asyncio.sleep(300)

@dp.message(Command("post"))
async def cmd_post(message: types.Message):
    """Команда для предпросмотра и подтверждения постов"""
    if str(message.from_user.id) != os.getenv('ADMIN_ID'):
        await message.reply("У вас нет прав для выполнения этой команды")
        return
    
    try:
        logging.info("Запрос ручной публикации постов")
        games = get_free_games()
        
        if not games:
            await message.reply("Не удалось получить данные об играх. Попробуйте позже.")
            return
        
        logging.info("Получено " + str(len(games)) + " игр для предпросмотра")
        preview_msg = await message.reply("🎮 Предпросмотр постов:")
        
        for game in games:
            try:
                post_id = f"epic_games_{game['title'].lower().replace(' ', '_')}"
                formatted_text = format_game_post(game)
                
                posted_status = "✅ Уже опубликовано" if is_game_posted(game['title']) else "⏳ Не опубликовано"
                formatted_text += f"\n\n{posted_status}"
                
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=game['image_url'],
                    caption=formatted_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_post_keyboard(post_id)
                )
                await asyncio.sleep(1)
            except Exception as e:
                error_msg = "Ошибка при отправке поста " + game['title'] + ": " + str(e)
                logging.error(error_msg)
                await message.reply(error_msg)
        
        await preview_msg.delete()
        
    except Exception as e:
        error_msg = "Ошибка при подготовке постов: " + str(e)
        logging.error(error_msg)
        await message.reply(error_msg)

@dp.callback_query()
async def process_callback(callback_query: types.CallbackQuery):
    """Обработка нажатий на кнопки"""
    try:
        if callback_query.data == "steam_search_cancel":
            await callback_query.message.delete()
            await callback_query.answer("Поиск отменен")
            return
            
        if callback_query.data.startswith('steam_page_'):
            if callback_query.data in ['steam_page_none', 'steam_page_current']:
                await callback_query.answer()
                return
                
            page = int(callback_query.data.split('_')[2])
            if not hasattr(bot, 'steam_search_results'):
                await callback_query.answer("Поиск устарел, выполните новый поиск")
                return
                
            await callback_query.message.edit_reply_markup(
                reply_markup=create_steam_search_keyboard(bot.steam_search_results, page)
            )
            await callback_query.answer()
            return
            
        if callback_query.data.startswith('steam_select_'):
            app_id = callback_query.data.split('_')[2]
            game_info = await get_steam_game_by_url(f"https://store.steampowered.com/app/{app_id}/")
            
            if game_info:
                formatted_text = format_steam_post(game_info)
                await bot.send_photo(
                    chat_id=callback_query.message.chat.id,
                    photo=game_info['image_url'],
                    caption=formatted_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_post_keyboard(f"steam_{app_id}")
                )
                await callback_query.message.delete()
            else:
                await callback_query.answer("Ошибка: игра не найдена")
            return
            
        action, post_id = callback_query.data.split('_', 1)
        
        if action == "delete":
            await callback_query.message.delete()
            await callback_query.answer("Пост удален")
            
        elif action == "post":
            if post_id.startswith('steam_'):
                app_id = post_id.replace('steam_', '')
                game_info = steam_parser.get_game_by_id(app_id)
                if game_info:
                    formatted_text = format_steam_post(game_info)
                    await bot.send_photo(
                        chat_id=CHANNEL_ID,
                        photo=game_info['image_url'],
                        caption=formatted_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=get_post_keyboard(None, game_info)
                    )
                    add_to_history(game_info, 'manual')
                    await callback_query.message.delete()
                    await callback_query.answer("Пост опубликован в канал")
            else:
                games = get_free_games()
                game_title = post_id.replace('epic_games_', '').replace('_', ' ')
                game_info = next((game for game in games if game['title'].lower() == game_title.lower()), None)
                
                if game_info:
                    formatted_text = format_game_post(game_info)
                    await bot.send_photo(
                        chat_id=CHANNEL_ID,
                        photo=game_info['image_url'],
                        caption=formatted_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=get_post_keyboard(None, game_info)
                    )
                    add_to_history(game_info, 'manual')
                    await callback_query.message.delete()
                    await callback_query.answer("Пост опубликован в канал")
                else:
                    await callback_query.answer("Ошибка: игра не найдена")
                
    except Exception as e:
        logging.error("Ошибка при обработке callback: " + str(e))
        await callback_query.answer(f"Произошла ошибка: {str(e)}")

@dp.message(Command("steam_search"))
async def cmd_steam_search(message: types.Message):
    """Поиск игры в Steam по названию"""
    if str(message.from_user.id) != os.getenv('ADMIN_ID'):
        return
        
    query = message.text.replace('/steam_search', '').strip()
    if not query:
        await message.reply("Укажите название игры после команды")
        return
        
    games = await search_steam_games(query)
    if not games:
        await message.reply("Игры не найдены")
        return
        
    await message.reply(
        "Результаты поиска:",
        reply_markup=create_steam_search_keyboard(games)
    )

@dp.message(Command("steam_url"))
async def cmd_steam_url(message: types.Message):
    """Создание поста для игры Steam по URL"""
    if str(message.from_user.id) != os.getenv('ADMIN_ID'):
        return
        
    url = message.text.replace('/steam_url', '').strip()
    if not url or 'store.steampowered.com' not in url:
        await message.reply("Укажите корректную ссылку на игру в Steam")
        return
        
    game_info = await get_steam_game_by_url(url)
    if not game_info:
        await message.reply("Не удалось получить информацию об игре")
        return
        
    formatted_text = format_steam_post(game_info)
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=game_info['header_image'],
        caption=formatted_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_post_keyboard(f"steam_{game_info['steam_appid']}")
    )

@dp.callback_query(lambda c: c.data.startswith('steam_page_'))
async def process_steam_page(callback_query: types.CallbackQuery):
    page = int(callback_query.data.split('_')[2])
    if not hasattr(bot, 'steam_search_results'):
        await callback_query.answer("Поиск устарел, выполните новый поиск")
        return
        
    await callback_query.message.edit_reply_markup(
        reply_markup=create_steam_search_keyboard(bot.steam_search_results, page)
    )

async def send_help_message(message: types.Message):
    """Отправляет сообщние с помощью"""
    help_text = [
        hbold('📋 Доступные команды:'),
        "",
        "/post - Предпросмотр и публикация раздач Epic Games",
        "/steam_search [название] - Поиск игры в Steam",
        "/steam_url [ссылка] - Создание поста по ссылке на игру Steam",
        "/help - Показать это сообщение",
        "",
        hbold('🔍 Быстрый поиск:'),
        "• Отправьте название игры для поиска в Steam",
        "• Отправьте ссылку на игру Steam для создания поста"
    ]
    
    await message.reply(
        "\n".join(help_text), 
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    if str(message.from_user.id) != os.getenv('ADMIN_ID'):
        return
    await send_help_message(message)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Показывает список доступных команд"""
    if str(message.from_user.id) != os.getenv('ADMIN_ID'):
        return
    await send_help_message(message)

@dp.message()
async def handle_message(message: types.Message):
    """Обработка обычных сообщений"""
    if str(message.from_user.id) != os.getenv('ADMIN_ID'):
        return
        
    text = message.text.strip()
    
    if 'store.steampowered.com' in text:
        game_info = await get_steam_game_by_url(text)
        if not game_info:
            await message.reply("Не удалось получить информацию об игре")
            return
            
        formatted_text = format_steam_post(game_info)
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=game_info['image_url'],
            caption=formatted_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_post_keyboard(f"steam_{game_info['steam_appid']}")
        )
    
    else:
        games = await search_steam_games(text)
        if not games:
            await message.reply("Игры не найдены")
            return
            
        bot.steam_search_results = games
        
        await message.reply(
            "Результаты поиска:",
            reply_markup=create_steam_search_keyboard(games)
        )

async def main():
    asyncio.create_task(periodic_checks())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
