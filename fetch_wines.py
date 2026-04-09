"""
==========================================
設計者：侍酒師 Somm Yannick "YK" Liu
© 2026. 根據 GNU GPLv3 授權。
後端：Google Sheets 轉 JSON (容錯增強版)
==========================================
"""
import pandas as pd
import json
import requests
from io import StringIO

SHEET_ID = "107NpWDkYD0lhIoC-ewLHZouWJoAfd8GTifBa8YTDMSQ"

# 對應您的分頁 GID
TABS = {
    "Sparkling": "2026459108",
    "French White": "125950905",
    "French Red": "1602098318",
    "USA White": "0",
    "USA Red": "977503732",
    "Other Regions": "292673052"
}

def fetch_and_clean():
    all_wines = []
    base_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

    for name, gid in TABS.items():
        try:
            url = f"{base_url}&gid={gid}"
            response = requests.get(url)
            response.encoding = 'utf-8'
            # 從第 3 列開始抓取 (skiprows=2)
            df = pd.read_csv(StringIO(response.text), skiprows=2, header=None)
            
            for _, r in df.iterrows():
                if len(r) > 4 and pd.notnull(r[4]) and str(r[4]).strip() != "":
                    # 依照您 GAS 的順序：0:Bin, 1:Ref, 2:產區1, 3:產區2, 4:酒名, 5:容量, 6:年份, 7:價格(Index 8), 8:庫存(Index 11), 9:描述(Index 13), 10:照片URL(Index 14)
                    wine = [
                        str(r[0]) if pd.notnull(r[0]) else "",   # 0: Bin
                        str(r[1]) if pd.notnull(r[1]) else "",   # 1: Ref
                        str(r[2]) if pd.notnull(r[2]) else "",   # 2: Region1
                        str(r[3]) if pd.notnull(r[3]) else "",   # 3: Region2
                        str(r[4]),                                # 4: Name
                        str(r[5]) if pd.notnull(r[5]) else "",   # 5: Size
                        str(r[6]) if pd.notnull(r[6]) else "",   # 6: Year
                        str(r[8]) if pd.notnull(r[8]) else "0",  # 7: Price
                        str(r[11]) if pd.notnull(r[11]) else "0",# 8: Stock
                        str(r[13]) if pd.notnull(r[13]) else "", # 9: Desc
                        str(r[14]) if pd.notnull(r[14]) else "", # 10: Photo
                        name                                      # 11: Category (額外紀錄)
                    ]
                    all_wines.append(wine)
            print(f"成功抓取: {name}")
        except Exception as e:
            print(f"抓取 {name} 失敗: {e}")

    with open('wine_data.json', 'w', encoding='utf-8') as f:
        json.dump(all_wines, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    fetch_and_clean()