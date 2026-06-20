import pandas as pd
import numpy as np
import datetime as dt

from newsapi import NewsApiClient



from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from pathlib import Path
from datetime import datetime
import sys
import json

data = json.loads(sys.argv[1])



newsapi = NewsApiClient(api_key="875cb8982b934e1698eb61c92f44594a")
key_word = data["text_inputs"]["Key Words: e.g Nasdaq, S&P500, Brent..."]

keywords = [x.strip() for x in key_word.split(",") if x.strip()]

beginning_date = data["text_inputs"]["Beginning Date : DD/MM/YYYY"]
b_date = [x.strip() for x in beginning_date.split("/") if x.strip()]
b_day = int(b_date[0])
b_month = int(b_date[1])
b_year = int(b_date[-1])

ending_date = data["text_inputs"]["Ending Date : DD/MM/YYYY"]
e_date = [x.strip() for x in beginning_date.split("/") if x.strip()]
e_day = int(e_date[0])
e_month = int(e_date[1])
e_year = int(e_date[-1])

beginning_hour = data["button_inputs"]["Beginning Hour"]
b_hour = int(beginning_hour)

ending_hour = data["button_inputs"]["Ending Hour"]
e_hour = int(ending_hour)

article_info = pd.DataFrame(columns=["Source","Date","Title","Summary","Link"])
categories = ["business", "general", "science", "technology"]
rows = []

for keyword in keywords:
    articles = newsapi.get_everything(
        q=keyword,  # keyword just in title
        from_param=dt.datetime(b_year, b_month, b_day, b_hour , 0, 0), # 8h UTC donc 10h Pairs été
        to=dt.datetime(e_year, e_month, e_day , e_hour, 0, 0),  # 14h UTC donc 16h Paris été
        language="en",
        sort_by="publishedAt",
        page_size=100)

    for article in articles["articles"]:
        source = article["source"]["name"]
        date = pd.to_datetime(article['publishedAt'])
        title = article["title"]
        description = article["description"]
        link = article["url"]

        rows.append({"Source":source,
                    "Date":date,
                    "Title":title,
                    "Summary":description,
                    "Link":link})

article_info = pd.DataFrame(rows)
        
# Option 1 : enlever le tz au niveau pandas
article_info["Date"] = article_info["Date"].dt.tz_localize(None)


wb = Workbook()
ws1 = wb.active
ws1.title = "News"

row_num = 1
for row in dataframe_to_rows(article_info,index=False,header=True):
    ws1.append(row)

def bold_first_row(ws):
    bold = Font(bold=True)
    for cell in ws1[1]:
        cell.font = bold


def autofit_columns(ws):
    for col in ws.columns:
        max_length = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            value = cell.value
            if value is not None:
                # on convertit en str pour mesurer la longueur
                max_length = max(max_length, len(str(value)))
        # petit +2 pour respirer un peu
        ws.column_dimensions[col_letter].width = max_length + 2

bold_first_row(ws1)
autofit_columns(ws1)
from openpyxl.styles import Alignment

# Wrap sur la colonne Summary (colonne 4, sans toucher aux autres)
for row in ws1.iter_rows(min_row=2, min_col=4, max_col=4):
    for cell in row:
        cell.alignment = Alignment(wrap_text=True)

output_dir = Path("outputs")
output_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
wb.save(output_dir / f"News_Report_{timestamp}.xlsx")
#wb.save("News_Report.xlsx")
output_file = output_dir / f"News_Report_{timestamp}.xlsx"
print(str(output_file))
    
