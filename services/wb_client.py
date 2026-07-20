import logging
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class WBClient:
    """Клиент для работы с API Wildberries (Контент, Статистика, Продвижение)."""
    
    def __init__(self, api_token: Optional[str] = None, adv_token: Optional[str] = None):
        self.api_token = api_token
        self.adv_token = adv_token
        
        # Определяем, работаем ли мы в режиме моков (демо-режим)
        self.is_mock = not self.api_token or self.api_token.startswith("your_") or "mock" in self.api_token.lower()
        if self.is_mock:
            logger.warning("Wildberries API работает в ДЕМО-режиме (генерация мок-данных)")

    def _get_headers(self, token_type: str = "api") -> Dict[str, str]:
        token = self.adv_token if token_type == "adv" else self.api_token
        return {
            "Authorization": f"{token}",
            "Content-Type": "application/json"
        }

    # --- Метод сбора общих заказов и продаж ---

    async def get_orders(self, days_ago: int = 14) -> List[Dict[str, Any]]:
        """Получает заказы из API Статистики."""
        if self.is_mock:
            # Возвращаем имитацию заказов за последние дни
            return self._generate_mock_orders(days_ago)

        date_from = (datetime.utcnow() - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
        url = f"https://statistics-api.wildberries.ru/api/v1/supplier/orders?dateFrom={date_from}"
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=self._get_headers("api"))
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    logger.warning("Превышен лимит запросов к API статистики WB.")
                    return self._generate_mock_orders(days_ago) # Fallback на мок при лимитах
                else:
                    logger.error(f"Ошибка получения заказов с WB API: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Исключение при запросе заказов: {e}")
            return []

    async def get_sales(self, days_ago: int = 14) -> List[Dict[str, Any]]:
        """Получает продажи (выкупы) из API Статистики."""
        if self.is_mock:
            return self._generate_mock_sales(days_ago)

        date_from = (datetime.utcnow() - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
        url = f"https://statistics-api.wildberries.ru/api/v1/supplier/sales?dateFrom={date_from}"
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=self._get_headers("api"))
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Ошибка получения продаж с WB API: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Исключение при запросе продаж: {e}")
            return []

    # --- Метод сбора остатков ---

    async def get_stocks(self) -> List[Dict[str, Any]]:
        """Получает текущие остатки на складах из API Статистики."""
        if self.is_mock:
            return self._generate_mock_stocks()

        # Дата в прошлом для получения актуальных остатков (обычно берут дату начала работы кабинета)
        date_from = "2023-01-01T00:00:00Z"
        url = f"https://statistics-api.wildberries.ru/api/v1/supplier/stocks?dateFrom={date_from}"
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=self._get_headers("api"))
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Ошибка получения остатков с WB API: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Исключение при запросе остатков: {e}")
            return []

    # --- Методы для работы с карточками (Контент API) ---

    async def get_cards(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получает список карточек продавца через API контента."""
        if self.is_mock:
            return self._generate_mock_cards()

        url = "https://content-api.wildberries.ru/content/v2/get/cards/list"
        payload = {
            "settings": {
                "cursor": {
                    "limit": limit
                },
                "filter": {
                    "withPhoto": -1
                }
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=self._get_headers("api"), json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("cards", [])
                else:
                    logger.error(f"Ошибка получения карточек с WB API: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Исключение при запросе карточек: {e}")
            return []

    async def update_card(self, card_payload: Dict[str, Any]) -> bool:
        """Обновляет описание/характеристики карточки товара."""
        if self.is_mock:
            return True

        url = "https://content-api.wildberries.ru/content/v2/cards/update"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=self._get_headers("api"), json=card_payload)
                if response.status_code == 200:
                    return True
                else:
                    logger.error(f"Ошибка обновления карточки WB: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Исключение при обновлении карточки: {e}")
            return False

    # --- Методы для работы с рекламой (Продвижение API) ---

    async def get_ad_campaigns(self) -> List[Dict[str, Any]]:
        """Получает список рекламных кампаний кабинета."""
        if self.is_mock:
            return self._generate_mock_campaigns()

        url = "https://advert-api.wildberries.ru/adv/v1/api/list"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=self._get_headers("adv"))
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Ошибка получения кампаний рекламы: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Исключение при запросе кампаний рекламы: {e}")
            return []

    async def get_campaign_full_stats(self, campaign_ids: List[int]) -> List[Dict[str, Any]]:
        """Получает подробную статистику по списку ID рекламных кампаний."""
        if self.is_mock:
            return self._generate_mock_campaign_stats(campaign_ids)

        # Полная статистика получается через метод /adv/v2/fullstats
        url = "https://advert-api.wildberries.ru/adv/v2/fullstats"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # API требует передавать список ID в теле запроса
                response = await client.post(url, headers=self._get_headers("adv"), json=campaign_ids)
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Ошибка получения статистики РК: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Исключение при запросе статистики РК: {e}")
            return []

    # --- Публичный парсинг конкурентов (без API ключа) ---

    async def get_competitor_data(self, sku: str) -> Optional[Dict[str, Any]]:
        """Получает данные по любому артикулу Wildberries через публичный API каталога."""
        # Обращаемся напрямую к публичному API WB, токен не нужен
        url = f"https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={sku}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    products = data.get("data", {}).get("products", [])
                    if products:
                        prod = products[0]
                        # Собираем полезные данные
                        price_u = prod.get("priceU", 0)  # Цена до скидок
                        sale_price_u = prod.get("salePriceU", 0)  # Цена со скидкой (в копейках)
                        
                        # Расчет цены в рублях
                        price = price_u / 100 if price_u else 0
                        sale_price = sale_price_u / 100 if sale_price_u else 0

                        # Получаем остатки по всем складам
                        total_stock = 0
                        sizes = prod.get("sizes", [])
                        for size in sizes:
                            stocks = size.get("stocks", [])
                            for stock in stocks:
                                total_stock += stock.get("qty", 0)

                        return {
                            "sku": sku,
                            "name": prod.get("name"),
                            "brand": prod.get("brand"),
                            "price": price,
                            "sale_price": sale_price,
                            "rating": prod.get("rating", 0),
                            "feedbacks": prod.get("feedbacks", 0),
                            "stock": total_stock,
                            "supplier": prod.get("supplier"),
                            "pics_count": prod.get("pics", 0)
                        }
        except Exception as e:
            logger.error(f"Ошибка при парсинге конкурента {sku}: {e}")
            
        # Fallback для мок-конкурента, если нет сети или ошибка
        if self.is_mock:
            import random
            return {
                "sku": sku,
                "name": f"Конкурентный Товар {sku}",
                "brand": "Competitor Brand",
                "price": 1500.0,
                "sale_price": 890.0,
                "rating": 4.7,
                "feedbacks": random.randint(50, 450),
                "stock": random.randint(100, 1000),
                "supplier": "ИП Конкурентов",
                "pics_count": 5
            }
        return None

    # --- Генераторы мок-данных для разработки/тестирования ---

    def _generate_mock_orders(self, days_ago: int) -> List[Dict[str, Any]]:
        import random
        orders = []
        base_skus = ["100001", "100002", "100003"]
        now = datetime.utcnow()
        for i in range(days_ago * 5): # В среднем 5 заказов в день
            order_time = now - timedelta(hours=random.randint(1, days_ago * 24))
            sku = random.choice(base_skus)
            price = 1200 if sku == "100001" else (950 if sku == "100002" else 1500)
            orders.append({
                "date": order_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "lastChangeDate": order_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "warehouseName": random.choice(["Коледино", "Казань", "Электросталь"]),
                "countryName": "Россия",
                "oblastOkrugName": "Московская обл",
                "nmId": int(sku),
                "barcode": f"bar_{sku}",
                "category": "Одежда",
                "subject": "Футболка",
                "brand": "Maria Brand",
                "techSize": "S" if random.random() > 0.5 else "M",
                "cancelDate": "0001-01-01T00:00:00Z" if random.random() > 0.1 else (order_time + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "isCancel": random.random() < 0.1,
                "gNumber": f"g_{random.randint(100000, 999999)}",
                "priceWithDisc": price,
                "finishedPrice": price * 0.95
            })
        return orders

    def _generate_mock_sales(self, days_ago: int) -> List[Dict[str, Any]]:
        import random
        sales = []
        base_skus = ["100001", "100002", "100003"]
        now = datetime.utcnow()
        for i in range(days_ago * 4): # 4 выкупа в день (процент выкупа ~80%)
            sale_time = now - timedelta(hours=random.randint(1, days_ago * 24))
            sku = random.choice(base_skus)
            price = 1200 if sku == "100001" else (950 if sku == "100002" else 1500)
            sales.append({
                "date": sale_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "lastChangeDate": sale_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "warehouseName": random.choice(["Коледино", "Казань", "Электросталь"]),
                "countryName": "Россия",
                "oblastOkrugName": "Московская обл",
                "nmId": int(sku),
                "barcode": f"bar_{sku}",
                "category": "Одежда",
                "subject": "Футболка",
                "brand": "Maria Brand",
                "techSize": "S" if random.random() > 0.5 else "M",
                "gNumber": f"g_{random.randint(100000, 999999)}",
                "priceWithDisc": price,
                "finishedPrice": price * 0.95,
                "forPay": price * 0.70, # Чистая оплата после вычета комиссий WB
                "finishedPrice": price * 0.95,
                "isRealization": True
            })
        return sales

    def _generate_mock_stocks(self) -> List[Dict[str, Any]]:
        import random
        stocks = []
        base_skus = ["100001", "100002", "100003"]
        warehouses = ["Коледино", "Казань", "Электросталь", "Краснодар", "Екатеринбург"]
        
        # Генерируем остатки по складам
        for sku in base_skus:
            for wh in warehouses:
                qty = random.randint(0, 150)
                qty_show = qty
                in_way_to_client = random.randint(0, 15)
                in_way_from_client = random.randint(0, 5)
                stocks.append({
                    "lastChangeDate": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "warehouseName": wh,
                    "nmId": int(sku),
                    "barcode": f"bar_{sku}",
                    "quantity": qty_show,
                    "inWayToClient": in_way_to_client,
                    "inWayFromClient": in_way_from_client,
                    "quantityFull": qty_show + in_way_to_client + in_way_from_client,
                    "category": "Одежда",
                    "subject": "Футболка",
                    "brand": "Maria Brand",
                    "techSize": "M",
                    "Price": 1500,
                    "Discount": 30
                })
        return stocks

    def _generate_mock_cards(self) -> List[Dict[str, Any]]:
        return [
            {
                "nmId": 100001,
                "vendorCode": "TSHIRT-MARIA-01",
                "title": "Стильная оверсайз футболка хлопковая",
                "description": "Базовая оверсайз футболка из плотного 100% хлопка. Отлично садится на любую фигуру, подходит для повседневной носки. Прочный трикотаж выдерживает многочисленные стирки.",
                "sizes": [{"techSize": "S"}, {"techSize": "M"}, {"techSize": "L"}],
                "photos": [{"big": "https://images.wbstatic.net/c516x688/new/100000/100001-1.jpg"}],
                "characteristics": [
                    {"name": "Состав", "value": ["Хлопок 100%"]},
                    {"name": "Цвет", "value": ["Черный"]},
                    {"name": "Рисунок", "value": ["Без рисунка"]}
                ]
            },
            {
                "nmId": 100002,
                "vendorCode": "TSHIRT-MARIA-02",
                "title": "Футболка женская с принтом",
                "description": "Женская футболка прямого кроя с минималистичным принтом на груди. Мягкая ткань кулирная гладь приятна к телу. Идеально для летнего гардероба.",
                "sizes": [{"techSize": "XS"}, {"techSize": "S"}, {"techSize": "M"}],
                "photos": [{"big": "https://images.wbstatic.net/c516x688/new/100000/100002-1.jpg"}],
                "characteristics": [
                    {"name": "Состав", "value": ["Хлопок 95%", "Лайкра 5%"]},
                    {"name": "Цвет", "value": ["Белый"]},
                    {"name": "Рисунок", "value": ["Принт"]}
                ]
            },
            {
                "nmId": 100003,
                "vendorCode": "PANTS-MARIA-01",
                "title": "Брюки женские классические широкие",
                "description": "Широкие классические брюки палаццо с высокой посадкой. Ткань костюмная, приятная на ощупь, практически не мнется. Создают элегантный силуэт.",
                "sizes": [{"techSize": "XS"}, {"techSize": "S"}, {"techSize": "M"}, {"techSize": "L"}],
                "photos": [{"big": "https://images.wbstatic.net/c516x688/new/100000/100003-1.jpg"}],
                "characteristics": [
                    {"name": "Состав", "value": ["Полиэстер 70%", "Вискоза 25%", "Эластан 5%"]},
                    {"name": "Цвет", "value": ["Бежевый"]},
                    {"name": "Размерная сетка", "value": ["Не заполнено"]} # Имитируем отсутствие размерной сетки!
                ]
            }
        ]

    def _generate_mock_campaigns(self) -> List[Dict[str, Any]]:
        return [
            {
                "advertId": 5001,
                "name": "РК Футболка Оверсайз Поиск",
                "type": 6, # 6 - Поиск
                "status": 9, # 9 - Идут показы
                "changeTime": "2026-07-20T10:00:00Z"
            },
            {
                "advertId": 5002,
                "name": "РК Футболка с принтом Авто",
                "type": 8, # 8 - Автоматическая
                "status": 9,
                "changeTime": "2026-07-20T10:00:00Z"
            },
            {
                "advertId": 5003,
                "name": "РК Брюки палаццо РСЯ/Внешняя",
                "type": 9, # 9 - Поиск + Каталог
                "status": 11, # 11 - Пауза
                "changeTime": "2026-07-19T18:00:00Z"
            }
        ]

    def _generate_mock_campaign_stats(self, campaign_ids: List[int]) -> List[Dict[str, Any]]:
        import random
        stats = []
        for cid in campaign_ids:
            # Имитируем воронку
            views = random.randint(10000, 50000)
            clicks = int(views * random.uniform(0.015, 0.045)) # CTR 1.5% - 4.5%
            atc = int(clicks * random.uniform(0.08, 0.15)) # Конверсия в корзину 8-15%
            orders = int(atc * random.uniform(0.15, 0.35)) # Конверсия в заказ из корзины 15-35%
            spend = random.randint(1200, 6000)
            
            stats.append({
                "advertId": cid,
                "views": views,
                "clicks": clicks,
                "ctr": (clicks / views * 100) if views else 0,
                "cpc": (spend / clicks) if clicks else 0,
                "atc": atc,
                "orders": orders,
                "spend": spend,
                "cr_to_cart": (atc / clicks * 100) if clicks else 0,
                "cr_to_order": (orders / clicks * 100) if clicks else 0,
                "cpo": (spend / orders) if orders else 0
            })
        return stats
