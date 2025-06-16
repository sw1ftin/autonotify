import requests
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

class SteamParser:
    def __init__(self):
        self.base_url = "https://store.steampowered.com/api"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def search_games(self, query: str) -> List[Dict]:
        """Поиск игр в Steam по названию"""
        if not query or query.strip().lower() in ('free', 'бесплатно'):
            return self.search_free_games()
        
        url = f"{self.base_url}/storesearch/"
        params = {
            'term': query,
            'l': 'russian',
            'cc': 'RU',
            'page': 1,
            'page_size': 100,
            'infinite': 1
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            items = data.get('items', [])
            
            items.sort(key=lambda x: x.get('name', '').lower().startswith(query.lower()), reverse=True)
            
            print(f"Found {len(items)} items before limit")
            
            return items[:100]
        except Exception as e:
            print(f"Error searching games: {e}")
            return []

    def search_free_games(self) -> List[Dict]:
        """Поиск бесплатных игр в Steam по ссылке фильтрации"""
        url = "https://store.steampowered.com/search/"
        params = {
            'maxprice': 'free',
            'specials': '1',
            'ndl': '1',
            'as-discount-percent': '100-',
            'l': 'russian',
            'cc': 'RU'
        }
        try:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.select('a.search_result_row')
            items = []
            for row in rows:
                app_id = row.get('data-ds-appid')
                title_elem = row.select_one('span.title')
                if not app_id or not title_elem:
                    continue
                items.append({
                    'id': int(app_id),
                    'name': title_elem.text.strip(),
                    'url': row.get('href')
                })
            print(f"Found {len(items)} free games")
            return items
        except Exception as e:
            print(f"Error searching free games: {e}")
            return []

    def get_app_id_from_url(self, url: str) -> Optional[str]:
        """Извлекает app_id из URL игры"""
        match = re.search(r'/app/(\d+)/', url)
        return match.group(1) if match else None

    def get_game_details(self, app_id: str, currency: str = "RUB") -> Optional[Dict]:
        """Получает информацию об игре через Steam API"""
        url = f"{self.base_url}/appdetails"
        params = {
            "appids": app_id,
            "cc": currency,
            "l": "russian"
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json().get(str(app_id), {}).get("data", {})
            return data if data else None
        except Exception as e:
            print(f"Error getting game details: {e}")
            return None

    def format_game_info(self, game_data: Dict) -> Dict:
        """Форматирует информацию об игре в единый формат"""
        is_free = game_data.get("is_free", False)
        
        ru_data = self.get_game_details(game_data['steam_appid'], 'RU')
        kz_data = self.get_game_details(game_data['steam_appid'], 'KZ')
        
        ru_price_info = ru_data.get("price_overview", {}) if ru_data else {}
        kz_price_info = kz_data.get("price_overview", {}) if kz_data else {}
        
        price = {
            "discount": 0,
            "RUB": {
                "original": -1,
                "current": -1
            },
            "KZT": {
                "original": -1,
                "current": -1
            }
        }
        
        if ru_price_info:
            try:
                initial = ru_price_info.get("initial", 0)
                final = ru_price_info.get("final", 0)
                
                if initial > 0:
                    price["RUB"]["original"] = initial / 100
                if final > 0:
                    price["RUB"]["current"] = final / 100
                price["discount"] = ru_price_info.get("discount_percent", 0)
            except (TypeError, ValueError) as e:
                print(f"Error processing RUB price for game {game_data.get('name')}: {e}")
        
        if kz_price_info:
            try:
                initial = kz_price_info.get("initial", 0)
                final = kz_price_info.get("final", 0)
                
                if initial > 0:
                    price["KZT"]["original"] = initial / 100
                if final > 0:
                    price["KZT"]["current"] = final / 100
            except (TypeError, ValueError) as e:
                print(f"Error processing KZT price for game {game_data.get('name')}: {e}")
        
        return {
            "title": game_data.get("name", ""),
            "publisher": game_data.get("publishers", [""])[0],
            "developers": game_data.get("developers", [""]),
            "release_date": game_data.get("release_date", {}).get("date", ""),
            "description": game_data.get("short_description", ""),
            "is_free": is_free,
            "price": price,
            "image_url": game_data.get("header_image", ""),
            "steam_appid": game_data.get("steam_appid", ""),
            "categories": [cat.get("description") for cat in game_data.get("categories", [])],
            "genres": [genre.get("description") for genre in game_data.get("genres", [])]
        }

    def get_game_by_url(self, url: str) -> Optional[Dict]:
        """Получает полную информацию об игре по URL"""
        app_id = self.get_app_id_from_url(url)
        if not app_id:
            return None
            
        game_data = self.get_game_details(app_id)
        if not game_data:
            return None
            
        return self.format_game_info(game_data)

    def get_game_by_id(self, app_id: str) -> Optional[Dict]:
        """Получает полную информацию об игре по ID"""
        game_data = self.get_game_details(app_id)
        if not game_data:
            return None
            
        return self.format_game_info(game_data)
