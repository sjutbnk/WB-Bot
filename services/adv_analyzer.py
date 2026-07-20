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
