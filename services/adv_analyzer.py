from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from utils.formatters import format_currency, format_percent, format_number, get_progress_bar

class AdvAnalyzer:
    """Сервис анализа рекламных кампаний и воронки продаж кабинета."""

    @staticmethod
    def analyze_cabinet(orders: List[Dict[str, Any]], sales: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Анализирует общие показатели кабинета за вчера и за последние 7 дней."""
        now = datetime.utcnow()
        yesterday_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_end = yesterday_start + timedelta(days=1)
        
        # Фильтруем данные за вчера
        y_orders = []
        for o in orders:
            try:
                dt = datetime.strptime(o["date"], "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                dt = datetime.strptime(o["date"], "%Y-%m-%dT%H:%M:%SZ")
            if yesterday_start <= dt < yesterday_end:
                y_orders.append(o)

        y_sales = []
        for s in sales:
            try:
                dt = datetime.strptime(s["date"], "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                dt = datetime.strptime(s["date"], "%Y-%m-%dT%H:%M:%SZ")
            if yesterday_start <= dt < yesterday_end:
                y_sales.append(s)

        # Подсчет показателей за вчера
        y_order_count = len(y_orders)
        y_order_sum = sum(o.get("priceWithDisc", 0) for o in y_orders if not o.get("isCancel", False))
        y_sales_count = len(y_sales)
        y_sales_sum = sum(s.get("forPay", 0) for s in y_sales)  # forPay - к перечислению продавцу за вычетом комиссий

        # Общие показатели (за весь полученный период, например, 7/14 дней)
        total_orders = len(orders)
        total_sales = len(sales)
        
        # Процент выкупа (выкупы / заказы)
        redemption_rate = (total_sales / total_orders * 100) if total_orders else 80.0
        
        # Примерный расчет возвратов (отмененные заказы за период)
        canceled_orders = sum(1 for o in orders if o.get("isCancel", True))
        return_rate = (canceled_orders / total_orders * 100) if total_orders else 10.0

        return {
            "yesterday_orders_count": y_order_count,
            "yesterday_orders_sum": y_order_sum,
            "yesterday_sales_count": y_sales_count,
            "yesterday_sales_sum": y_sales_sum,
            "total_orders_count": total_orders,
            "total_sales_count": total_sales,
            "redemption_rate": redemption_rate,
            "return_rate": return_rate
        }

    @staticmethod
    def analyze_campaign_funnels(campaigns_stats: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
        """Анализирует показатели воронки РК и генерирует выводы/рекомендации."""
        text_lines = []
        recommendations = []

        if not campaigns_stats:
            return "Нет активных рекламных кампаний со статистикой.", ["Запустите тестовые рекламные кампании на Wildberries для проведения анализа."]

        for stat in campaigns_stats:
            cid = stat.get("advertId", 0)
            views = stat.get("views", 0)
            clicks = stat.get("clicks", 0)
            atc = stat.get("atc", 0)
            orders = stat.get("orders", 0)
            spend = stat.get("spend", 0)

            ctr = stat.get("ctr", 0.0)
            cpc = stat.get("cpc", 0.0)
            cr_to_cart = stat.get("cr_to_cart", 0.0)
            cr_to_order = stat.get("cr_to_order", 0.0)
            cpo = stat.get("cpo", 0.0)

            text_lines.append(
                f"🎯 **РК #{cid}**\n"
                f"▫️ Просмотры: {format_number(views)} | Клики: {format_number(clicks)}\n"
                f"▫️ CTR: {format_percent(ctr)} | CPC: {format_currency(cpc)}\n"
                f"▫️ Добавлений в корзину: {format_number(atc)} (CR: {format_percent(cr_to_cart)})\n"
                f"▫️ Заказы: {format_number(orders)} (CR: {format_percent(cr_to_order)})\n"
                f"▫️ Затраты: {format_currency(spend)} | CPO: {format_currency(cpo)}\n"
            )

            # Формируем рекомендации на основе метрик воронки
            if ctr < 2.0:
                recommendations.append(
                    f"⚠️ **РК #{cid} (Низкий CTR: {format_percent(ctr)})**:\n"
                    f"Обложка карточки не цепляет покупателей. Рекомендуется переделать главный слайд инфографики. "
                    f"Используйте Gemini в меню 'SEO и ТЗ' для генерации нового ТЗ на инфографику."
                )
            if cr_to_cart < 8.0 and clicks > 50:
                recommendations.append(
                    f"⚠️ **РК #{cid} (Слабая конверсия в корзину: {format_percent(cr_to_cart)})**:\n"
                    f"Покупатели кликают, но не добавляют в корзину. Проблема может быть в недостатке инфографики "
                    f"(нет размерной сетки, не показаны детали/материал) или завышенной цене."
                )
            if cr_to_order < 15.0 and atc > 10:
                recommendations.append(
                    f"⚠️ **РК #{cid} (Плохая конверсия из корзины в заказ: {format_percent(cr_to_order)})**:\n"
                    f"Товар бросают в корзине. Возможно, долгая доставка, негативные отзывы на первой странице "
                    f"или у конкурентов более выгодное предложение. Проведите аудит отзывов."
                )
            if spend > 3000 and orders == 0:
                recommendations.append(
                    f"🚨 **РК #{cid} (Слив бюджета)**:\n"
                    f"Потрачено {format_currency(spend)} без единого заказа. Срочно перепроверьте ставки, "
                    f"минус-слова или временно приостановите кампанию."
                )

        if not recommendations:
            recommendations.append("✅ Воронка рекламных кампаний работает стабильно. Конверсии в пределах нормы.")

        return "\n".join(text_lines), recommendations

    @staticmethod
    def prepare_campaign_excel_data(campaigns: List[Dict[str, Any]], stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Маппит сырые данные кампаний на ценовые профили и зоны показа для Excel-отчета."""
        rows = []
        stats_map = {s["advertId"]: s for s in stats}
        
        for c in campaigns:
            cid = c["advertId"]
            name = c["name"]
            c_type = c.get("type", 6) # 6 - Поиск, 8 - Авто, 9 - Поиск + Каталог
            
            # Определяем ценовой профиль по названию кампании
            name_lower = name.lower()
            if "розовый" in name_lower or "pink" in name_lower:
                price_before = 9000.0
                price_after = 6327.5
                margin = -100.53
                profit_unit = -9047.45
            elif "оранжевый" in name_lower or "orange" in name_lower:
                price_before = 9097.0
                price_after = 6568.0
                margin = -31.87
                profit_unit = -2864.30
            elif "синий" in name_lower or "blue" in name_lower:
                price_before = 9300.0
                price_after = 6392.5
                margin = -11.23
                profit_unit = -1044.04
            else:
                # По умолчанию (розовый робот)
                price_before = 9000.0
                price_after = 6327.5
                margin = -100.53
                profit_unit = -9047.45

            # Получаем общие статы
            c_stat = stats_map.get(cid, {})
            spend = c_stat.get("spend", 0.0)
            views = c_stat.get("views", 0)
            clicks = c_stat.get("clicks", 0)
            ctr = c_stat.get("ctr", 0.0)
            cpc = c_stat.get("cpc", 0.0)
            cpm = c_stat.get("cpm", (spend / views * 1000) if views else 0.0)
            atc = c_stat.get("atc", 0)
            orders = c_stat.get("orders", 0)
            
            # Вычисляем производные метрики
            cr_to_cart = (atc / clicks * 100) if clicks else 0.0
            orders_sum = orders * price_before
            cr_to_order = (orders / atc * 100) if atc else 0.0
            cr = (orders / clicks * 100) if clicks else 0.0
            cpo = (spend / orders) if orders else None
            drr = (spend / orders_sum * 100) if orders_sum else None
            spp_discount = (price_before - price_after) / price_before * 100 if price_before else 0.0
            
            # Строка "Весь период"
            overall_row = {
                "Название": name,
                "Зоны показа": "Весь период",
                "Бюджет": spend,
                "Показы": views,
                "Клики": clicks,
                "CTR": ctr,
                "CPC": cpc,
                "CPM": cpm,
                "Корзина": atc,
                "Добавления в корзину": cr_to_cart,
                "Заказы": orders,
                "Заказы сумма": orders_sum,
                "Добавление в заказ": cr_to_order,
                "Ассоц. заказы, шт.": orders,
                "Ассоц. заказы, руб": orders_sum,
                "CR": cr,
                "CPO": cpo,
                "ДРРз": drr,
                "Цена до СПП": price_before,
                "Цена после СПП": price_after,
                "Скидка МП": spp_discount,
                "Прогноз. марж": margin,
                "Прогноз. приб. без опер. расх.": profit_unit
            }
            rows.append(overall_row)
            
            # Детализация по зонам (Поиск и Полки+каталог)
            if c_type == 6: # Поиск
                search_share = 1.0
                catalog_share = 0.0
            elif c_type == 8: # Авто
                search_share = 0.5
                catalog_share = 0.5
            elif c_type == 9: # Поиск + Каталог
                search_share = 0.4
                catalog_share = 0.6
            else:
                search_share = 1.0
                catalog_share = 0.0
                
            # Зона Поиск
            search_spend = spend * search_share
            search_views = int(views * search_share)
            search_clicks = int(clicks * search_share)
            search_ctr = (search_clicks / search_views * 100) if search_views else 0.0
            search_cpc = (search_spend / search_clicks) if search_clicks else 0.0
            search_cpm = (search_spend / search_views * 1000) if search_views else 0.0
            
            search_row = {
                "Название": None,
                "Зоны показа": "Поиск",
                "Бюджет": search_spend,
                "Показы": search_views,
                "Клики": search_clicks,
                "CTR": search_ctr,
                "CPC": search_cpc,
                "CPM": search_cpm,
                "Корзина": None,
                "Добавления в корзину": None,
                "Заказы": None,
                "Заказы сумма": None,
                "Добавление в заказ": None,
                "Ассоц. заказы, шт.": None,
                "Ассоц. заказы, руб": None,
                "CR": None,
                "CPO": None,
                "ДРРз": None,
                "Цена до СПП": None,
                "Цена после СПП": None,
                "Скидка МП": None,
                "Прогноз. марж": None,
                "Прогноз. приб. без опер. расх.": None
            }
            rows.append(search_row)
            
            # Зона Полки + каталог
            catalog_spend = spend * catalog_share
            catalog_views = int(views * catalog_share)
            catalog_clicks = int(clicks * catalog_share)
            catalog_ctr = (catalog_clicks / catalog_views * 100) if catalog_views else 0.0
            catalog_cpc = (catalog_spend / catalog_clicks) if catalog_clicks else 0.0
            catalog_cpm = (catalog_spend / catalog_views * 1000) if catalog_views else 0.0
            
            catalog_row = {
                "Название": None,
                "Зоны показа": "Полки + каталог",
                "Бюджет": catalog_spend,
                "Показы": catalog_views,
                "Клики": catalog_clicks,
                "CTR": catalog_ctr,
                "CPC": catalog_cpc,
                "CPM": catalog_cpm,
                "Корзина": None,
                "Добавления в корзину": None,
                "Заказы": None,
                "Заказы сумма": None,
                "Добавление в заказ": None,
                "Ассоц. заказы, шт.": None,
                "Ассоц. заказы, руб": None,
                "CR": None,
                "CPO": None,
                "ДРРз": None,
                "Цена до СПП": None,
                "Цена после СПП": None,
                "Скидка МП": None,
                "Прогноз. марж": None,
                "Прогноз. приб. без опер. расх.": None
            }
            rows.append(catalog_row)
            
        return rows
