import requests
import json
from datetime import datetime

def create_game_info(game, offer, status, available_in_russia=None):
    """Создает словарь с информацией об игре"""
    price_info = {
        "discount": 0,
        "RUB": {"original": -1, "current": -1},
        "USD": {"original": -1, "current": -1}
    }
    
    if game.get('price'):
        total_price = game['price'].get('totalPrice', {})
        discount = offer['discountSetting']['discountPercentage']
        
        original_price = total_price.get('originalPrice', 0) / 100
        current_price = total_price.get('discountPrice', original_price) / 100
        
        currency = total_price.get('currencyCode', 'USD')
        if currency in price_info:
            price_info[currency] = {
                "original": original_price,
                "current": current_price
            }
            price_info["discount"] = discount

    url = "https://store.epicgames.com/ru/p/" + game['catalogNs']['mappings'][0]['pageSlug']

    return {
        'title': game['title'],
        'publisher': game.get('seller', {}).get('name'),
        'status': status,
        'start_date': offer['startDate'],
        'end_date': offer['endDate'],
        'url': url,
        'image_url': game.get('keyImages', [{}])[0].get('url'),
        'price': price_info,
        'available_in_russia': available_in_russia
    }

def process_offers(game, offers, status, available_in_russia=None):
    """Обрабатывает предложения"""
    games_list = []
    if offers:
        for offer in offers[0].get('promotionalOffers', []):
            if offer['discountSetting']['discountPercentage'] == 0:
                games_list.append(create_game_info(game, offer, status, available_in_russia))
    return games_list

def get_free_games_for_region(region):
    """Получает список бесплатных игр для конкретного региона"""
    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
    params = {
        "locale": "en-US",
        "country": region,
        "allowCountries": region
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        games = []
        for game in data['data']['Catalog']['searchStore']['elements']:
            if not game.get('promotions'):
                continue
                
            promotional_offers = game['promotions'].get('promotionalOffers', [])
            upcoming_offers = game['promotions'].get('upcomingPromotionalOffers', [])
            
            games.extend(process_offers(game, promotional_offers, 'active', None))
            games.extend(process_offers(game, upcoming_offers, 'upcoming', None))
            
        return games
        
    except requests.exceptions.RequestException as e:
        error_msg = "Ошибка при получении данных для региона " + region + ": " + str(e)
        print(error_msg)
        return None

def get_free_games():
    """Основная функция получения и сравнения списков игр"""
    us_games = get_free_games_for_region('US')
    ru_games = get_free_games_for_region('RU')
    
    if not us_games or not ru_games:
        return None
        
    us_titles = {game['title']: game for game in us_games}
    
    final_games = []
    for ru_game in ru_games:
        ru_game['available_in_russia'] = ru_game['title'] in us_titles
        if ru_game['title'] in us_titles:
            us_price = us_titles[ru_game['title']]['price']['USD']
            ru_game['price']['USD'] = us_price
        final_games.append(ru_game)
    
    for us_game in us_games:
        if not any(game['title'] == us_game['title'] for game in ru_games):
            us_game['available_in_russia'] = False
            final_games.append(us_game)
    
    return final_games

if __name__ == "__main__":
    games = get_free_games()
    if games:
        print("Найдено " + str(len(games)) + " бесплатных игр")
        for game in games:
            print("\nНазвание: " + game['title'])
            print("Статус: " + ('Активна' if game['status'] == 'active' else 'Скоро'))
            print("Период: " + game['start_date'] + " - " + game['end_date'])
            print("Доступно в России: " + ('Да' if game['available_in_russia'] else 'Нет'))
