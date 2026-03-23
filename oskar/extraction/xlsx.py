import logging
from pathlib import Path

import openpyxl
import pandas as pd

logger = logging.getLogger(__name__)


def extract_text_from_xlsx(xlsx_path: Path) -> str:
    try:
        wb = openpyxl.load_workbook(str(xlsx_path), data_only=True)
        text = []
        for sheet in wb.worksheets:
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.value:
                        text.append(str(cell.value))
        return "\n".join(text)
    except Exception as e:
        logger.error(f"Error extracting XLSX {xlsx_path}: {e}")
        return ""


def extract_text_from_xls(xls_path: Path) -> str:
    try:
        sheets = pd.read_excel(str(xls_path), sheet_name=None, engine='xlrd')
        text_lines = []
        for sheet_name, df in sheets.items():
            for col in df.columns:
                for val in df[col]:
                    if pd.notnull(val):
                        text_lines.append(str(val))
        return "\n".join(text_lines)
    except Exception as e:
        logger.error(f"Error extracting XLS {xls_path}: {e}")
        return ""
