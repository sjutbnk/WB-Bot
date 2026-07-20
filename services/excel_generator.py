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
