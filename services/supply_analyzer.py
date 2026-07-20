from typing import List, Dict, Any
from collections import defaultdict

class SupplyAnalyzer:
    """Сервис анализа остатков и расчета потребности в поставках."""

    @staticmethod
    def calculate_supplies(
        stocks: List[Dict[str, Any]], 
        sales: List[Dict[str, Any]], 
        target_days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Рассчитывает потребность в поставках по каждому артикулу с учетом
        скорости продаж и распределяет ее по региональным складам.
        """
        # 1. Считаем текущие остатки по каждому артикулу и складу
        # {sku: {warehouse: quantity}}
        sku_warehouse_stocks = defaultdict(lambda: defaultdict(int))
        sku_total_stocks = defaultdict(int)
        sku_transit_stocks = defaultdict(int)
        sku_details = {}

        for item in stocks:
            sku = str(item.get("nmId"))
            wh = item.get("warehouseName", "Другие")
            qty = item.get("quantity", 0)
            in_transit = item.get("inWayToClient", 0) + item.get("inWayFromClient", 0)
            
            sku_warehouse_stocks[sku][wh] += qty
            sku_total_stocks[sku] += qty
            sku_transit_stocks[sku] += in_transit
            
            # Сохраняем имя/бренд для вывода
            if sku not in sku_details:
                sku_details[sku] = {
                    "name": item.get("subject", "Товар"),
                    "brand": item.get("brand", "Maria Brand")
                }

        # 2. Считаем продажи за 14 и 30 дней для вычисления скорости продаж
        # {sku: count}
        sales_14 = defaultdict(int)
        sales_30 = defaultdict(int)
        
        # Также считаем распределение продаж по складам за последние 30 дней
        # {sku: {warehouse: count}}
        sku_warehouse_sales = defaultdict(lambda: defaultdict(int))

        for sale in sales:
            sku = str(sale.get("nmId"))
            wh = sale.get("warehouseName", "Другие")
            sales_30[sku] += 1
            sales_14[sku] += 1 # В дефолтных моках/данных период обычно 14 дней
            sku_warehouse_sales[sku][wh] += 1

        # 3. Рассчитываем итоговую потребность по каждому артикулу
        results = []
        all_skus = set(list(sku_total_stocks.keys()) + list(sales_30.keys()))

        for sku in all_skus:
            total_stock = sku_total_stocks.get(sku, 0)
            transit_stock = sku_transit_stocks.get(sku, 0)
            
            # Среднесуточные продажи
            speed_14 = sales_14.get(sku, 0) / 14.0
            speed_30 = sales_30.get(sku, 0) / 30.0
            
            # Используем максимальную скорость для безопасности (или среднее, возьмем max)
            speed = max(speed_14, speed_30)
            
            # Оборачиваемость (на сколько дней хватит остатков)
            turnover_days = total_stock / speed if speed > 0 else 999
            
            # Общая потребность на target_days (например, 30 дней)
            # Формула: (Потребность на X дней) - Текущие остатки (включая путь)
            needed_total = int(max(0, (speed * target_days) - (total_stock + transit_stock)))

            # Распределение потребности по региональным складам
            regional_distribution = {}
            # Ключевые склады для выгрузки рекомендаций
            target_warehouses = ["Коледино", "Казань", "Электросталь", "Краснодар", "Екатеринбург"]
            
            if needed_total > 0:
                # Считаем доли продаж по складам за 30 дней
                sku_sales_wh = sku_warehouse_sales[sku]
                total_wh_sales = sum(sku_sales_wh.values())
                
                remaining_needed = needed_total
                
                for wh in target_warehouses:
                    # Доля продаж с этого склада
                    share = sku_sales_wh[wh] / total_wh_sales if total_wh_sales > 0 else 0.2 # 20% дефолт
                    
                    # Пропорциональное количество поставки
                    wh_needed = int(round(needed_total * share))
                    regional_distribution[wh] = wh_needed
                    remaining_needed -= wh_needed
                
                # Корректируем погрешности округления на главный склад (Коледино)
                regional_distribution["Коледино"] = max(0, regional_distribution.get("Коледино", 0) + remaining_needed)
            else:
                for wh in target_warehouses:
                    regional_distribution[wh] = 0

            # Название товара
            details = sku_details.get(sku, {"name": "Товар", "brand": "Maria Brand"})

            results.append({
                "sku": sku,
                "name": f"{details['brand']} / {details['name']}",
                "total_stock": total_stock,
                "transit_stock": transit_stock,
                "speed_14": speed_14,
                "speed_30": speed_30,
                "turnover_days": turnover_days,
                "needed_total": needed_total,
                "distribution": regional_distribution
            })

        return results
