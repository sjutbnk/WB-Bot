import os
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from typing import List, Dict, Any

class ExcelGenerator:
    """Сервис для генерации профессионально оформленных Excel отчетов."""

    @staticmethod
    def generate_supply_report(data: List[Dict[str, Any]], filepath: str) -> str:
        """Создает оформленный Excel-файл с расчетом поставок."""
        # Готовим список строк для датафрейма
        rows = []
        for item in data:
            dist = item.get("distribution", {})
            rows.append({
                "Артикул": item["sku"],
                "Товар (Бренд / Категория)": item["name"],
                "Остаток на складах": item["total_stock"],
                "Товары в пути": item["transit_stock"],
                "Продаж/день (14д)": round(item["speed_14"], 2),
                "Продаж/день (30д)": round(item["speed_30"], 2),
                "Оборачиваемость (дни)": "∞" if item["turnover_days"] == 999 else round(item["turnover_days"], 1),
                "Рекомендовано поставить": item["needed_total"],
                "Коледино": dist.get("Коледино", 0),
                "Казань": dist.get("Казань", 0),
                "Электросталь": dist.get("Электросталь", 0),
                "Краснодар": dist.get("Краснодар", 0),
                "Екатеринбург": dist.get("Екатеринбург", 0)
            })

        df = pd.DataFrame(rows)
        
        # Сохраняем в файл через ExcelWriter
        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Рекомендации поставок")
            
            # Получаем объект листа для стилизации
            workbook = writer.book
            worksheet = writer.sheets["Рекомендации поставок"]
            
            # --- Стилизация ---
            # Цветовые заливки
            header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid") # Темно-синий
            deficit_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid") # Светло-зеленый (нужна поставка)
            normal_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
            
            # Шрифты
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            data_font = Font(name="Calibri", size=10)
            bold_data_font = Font(name="Calibri", size=10, bold=True)
            
            # Выравнивание
            center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
            left_align = Alignment(horizontal="left", vertical="center")
            right_align = Alignment(horizontal="right", vertical="center")
            
            # Границы
            thin_border_side = Side(border_style="thin", color="D9D9D9")
            border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
            
            # Стилизуем шапку таблицы
            worksheet.row_dimensions[1].height = 28
            for col_idx in range(1, len(df.columns) + 1):
                cell = worksheet.cell(row=1, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = center_align
                cell.border = border
            
            # Заполняем стилями данные
            for row_idx in range(2, len(df) + 2):
                worksheet.row_dimensions[row_idx].height = 20
                needed_total = df.iloc[row_idx - 2]["Рекомендовано поставить"]
                
                # Если нужна поставка, подсветим всю строчку нежно-зеленым
                row_fill = deficit_fill if needed_total > 0 else normal_fill
                
                for col_idx in range(1, len(df.columns) + 1):
                    cell = worksheet.cell(row=row_idx, column=col_idx)
                    cell.fill = row_fill
                    cell.border = border
                    cell.font = bold_data_font if col_idx in [1, 8] else data_font
                    
                    # Выравнивание колонок
                    if col_idx in [1, 7]: # Артикул, оборачиваемость
                        cell.alignment = center_align
                    elif col_idx == 2: # Название товара
                        cell.alignment = left_align
                    else: # Цифровые значения
                        cell.alignment = right_align
                        # Форматирование чисел
                        if col_idx in [3, 4, 8, 9, 10, 11, 12, 13]:
                            cell.number_format = "#,##0"
                        elif col_idx in [5, 6]:
                            cell.number_format = "0.00"

            # Включаем сетку линий
            worksheet.views.sheetView[0].showGridLines = True
            
            # Автоматическая ширина столбцов с запасом
            for col in worksheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.value:
                        # Учитываем перенос строки в заголовках
                        lines = str(cell.value).split('\n')
                        for line in lines:
                            max_len = max(max_len, len(line))
                worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)
                
        return filepath

    @staticmethod
    def generate_campaign_report(data: List[Dict[str, Any]], filepath: str) -> str:
        """Создает детальный Excel-отчет по рекламным кампаниям в стиле предоставленного шаблона."""
        # 1. Считаем итоги для первой строчки "Итого"
        total_budget = sum(item.get("Бюджет", 0) for item in data if item.get("Зоны показа") == "Весь период")
        total_views = sum(item.get("Показы", 0) for item in data if item.get("Зоны показа") == "Весь период")
        total_clicks = sum(item.get("Клики", 0) for item in data if item.get("Зоны показа") == "Весь период")
        total_carts = sum(item.get("Корзина", 0) for item in data if item.get("Зоны показа") == "Весь период")
        total_orders = sum(item.get("Заказы", 0) for item in data if item.get("Зоны показа") == "Весь период")
        total_orders_sum = sum(item.get("Заказы сумма", 0) for item in data if item.get("Зоны показа") == "Весь период")
        total_assoc_orders = sum(item.get("Ассоц. заказы, шт.", 0) for item in data if item.get("Зоны показа") == "Весь период")
        total_assoc_sum = sum(item.get("Ассоц. заказы, руб", 0) for item in data if item.get("Зоны показа") == "Весь период")
        total_profit = sum(item.get("Прогноз. приб. без опер. расх.", 0) for item in data if item.get("Зоны показа") == "Весь период")
        
        # Расчетные метрики для Итого
        total_ctr = (total_clicks / total_views * 100) if total_views else 0.0
        total_cpc = (total_budget / total_clicks) if total_clicks else 0.0
        total_cpm = (total_budget / total_views * 1000) if total_views else 0.0
        total_cr_to_cart = (total_carts / total_clicks * 100) if total_clicks else 0.0
        total_cr_to_order = (total_orders / total_carts * 100) if total_carts else 0.0
        total_cr = (total_orders / total_clicks * 100) if total_clicks else 0.0
        total_cpo = (total_budget / total_orders) if total_orders else None
        total_drr = (total_budget / total_orders_sum * 100) if total_orders_sum else None
        
        # Средние цены по кампаниям для Итого
        c_count = sum(1 for item in data if item.get("Зоны показа") == "Весь период" and item.get("Цена до СПП"))
        avg_price_before = sum(item.get("Цена до СПП", 0) for item in data if item.get("Зоны показа") == "Весь период" and item.get("Цена до СПП")) / c_count if c_count else 0
        avg_price_after = sum(item.get("Цена после СПП", 0) for item in data if item.get("Зоны показа") == "Весь период" and item.get("Цена после СПП")) / c_count if c_count else 0
        avg_spp_discount = (avg_price_before - avg_price_after) / avg_price_before * 100 if avg_price_before else 0
        avg_margin = (total_profit / total_orders_sum * 100) if total_orders_sum else (total_profit / avg_price_before * 100 if avg_price_before else 0)

        # Создаем строчку Итого
        summary_row = {
            "Название": "Итого",
            "Зоны показа": "Весь период",
            "Бюджет": round(total_budget, 2),
            "Показы": total_views,
            "Клики": total_clicks,
            "CTR": round(total_ctr, 2),
            "CPC": round(total_cpc, 2),
            "CPM": round(total_cpm, 2),
            "Корзина": total_carts,
            "Добавления в корзину": round(total_cr_to_cart, 2),
            "Заказы": total_orders,
            "Заказы сумма": round(total_orders_sum, 2),
            "Добавление в заказ": round(total_cr_to_order, 2),
            "Ассоц. заказы, шт.": total_assoc_orders,
            "Ассоц. заказы, руб": round(total_assoc_sum, 2),
            "CR": round(total_cr, 2),
            "CPO": round(total_cpo, 2) if total_cpo is not None else None,
            "ДРРз": round(total_drr, 2) if total_drr is not None else None,
            "Цена до СПП": round(avg_price_before, 2),
            "Цена после СПП": round(avg_price_after, 2),
            "Скидка МП": round(avg_spp_discount, 2),
            "Прогноз. марж": round(avg_margin, 2),
            "Прогноз. приб. без опер. расх.": round(total_profit, 2)
        }

        # Объединяем итоговую строку со списком кампаний
        all_rows = [summary_row] + data
        df = pd.DataFrame(all_rows)

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Отчет по кампаниям")
            
            workbook = writer.book
            worksheet = writer.sheets["Отчет по кампаниям"]
            
            # --- Стилизация в стиле шаблона ---
            # Светло-серый цвет для шапки
            header_fill = PatternFill(start_color="EAEAEA", end_color="EAEAEA", fill_type="solid")
            # Светло-серый с голубым отливом для строки "Итого"
            total_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
            normal_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
            
            header_font = Font(name="Calibri", size=10, bold=True, color="000000")
            total_font = Font(name="Calibri", size=10, bold=True, color="000000")
            data_font = Font(name="Calibri", size=10)
            
            center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
            left_align = Alignment(horizontal="left", vertical="center")
            right_align = Alignment(horizontal="right", vertical="center")
            
            thin_border_side = Side(border_style="thin", color="D9D9D9")
            border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
            
            # Шапка
            worksheet.row_dimensions[1].height = 28
            for col_idx in range(1, len(df.columns) + 1):
                cell = worksheet.cell(row=1, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = center_align
                cell.border = border
            
            # Строки
            for row_idx in range(2, len(df) + 2):
                is_total = (row_idx == 2)
                row_fill = total_fill if is_total else normal_fill
                worksheet.row_dimensions[row_idx].height = 20
                
                for col_idx in range(1, len(df.columns) + 1):
                    cell = worksheet.cell(row=row_idx, column=col_idx)
                    cell.fill = row_fill
                    cell.border = border
                    cell.font = total_font if is_total else data_font
                    
                    # Выравнивание
                    if col_idx in [1, 2]: # Название, Зоны показа
                        cell.alignment = left_align
                    else:
                        cell.alignment = right_align
                    
                    # Форматирование чисел
                    val = cell.value
                    if val is not None and not isinstance(val, str):
                        # Целые числа
                        if col_idx in [4, 5, 9, 11, 14]:
                            cell.number_format = "#,##0"
                        # Вещественные (валюты и проценты)
                        else:
                            cell.number_format = "0.00"

            worksheet.views.sheetView[0].showGridLines = True
            
            # Ширина колонок
            for col in worksheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.value:
                        lines = str(cell.value).split('\n')
                        for line in lines:
                            max_len = max(max_len, len(line))
                worksheet.column_dimensions[col_letter].width = max(max_len + 3, 11)
                
        return filepath
