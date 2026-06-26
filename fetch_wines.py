# =================================================================================
# 
# 專案名稱：電子酒單&庫存前後端管理系統
# 開發設計：Sommelier Yannick "Y.K." Liu
# 版權所有 (c) 2026 Yannick "Y.K." Liu. 保留所有權利。
#
# =================================================================================

import pandas as pd
import json
import requests
from io import StringIO

# 試算表ID
SHEET_ID = "107NpWDkYD0lhIoC-ewLHZouWJoAfd8GTifBa8YTDMSQ"

# 只抓取指定的兩個分頁
TARGET_SHEETS = ["By the Glass", "Wine List"]

# 順序Index
CATEGORY_ORDER = {
    "By the Glass": 1,
    "Sparkling": 2,
    "Rosé": 3,
    "White Wine": 4,
    "Red Wine": 5,
    "Sweet Wine": 6,
    "Fortified Wine": 7,
    "Sake": 8,
    "Spirits & Liquors": 9,
    "Beer & Cocktails": 10,
    "Alcohol Free & Soft Drinks": 11,
    "Others": 12
}

# 定義國家形容詞對照表
COUNTRY_TO_ADJECTIVE = {
    "france": "French",
    "italy": "Italian",
    "spain": "Spanish",
    "australia": "Australian",
    "germany": "German",
    "chile": "Chilean",
    "new zealand": "New Zealand",
    "south africa": "South African",
    "america": "American",
    "united states": "American",
    "usa": "American",
    "japan": "Japanese"
}

def classify_wine_dynamic(row, sheet_name="Wine List"):
    """
    動態判定大分類與子分類 (修正：Champagne 直接由 C 欄 Type 判定)
    row.iloc[2] = C欄 (Type)
    row.iloc[3] = D欄 (Country)
    """
    type_val = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
    country_val = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ""
    
    type_lower = type_val.lower()
    country_lower = country_val.lower()
    
    # 獲取國家形容詞
    country_adj = COUNTRY_TO_ADJECTIVE.get(country_lower, country_val.capitalize() if country_val else "Others")

    # 1. By the Glass 分頁獨立判定
    if sheet_name == "By the Glass":
        big_cat = "By the Glass"
        if "spirit" in type_lower or "liquor" in type_lower or any(x in type_lower for x in ["whisky", "whiskey", "brandy", "cognac", "gin", "vodka", "rum", "tequila"]):
            sub_cat = "Spirits & Liquor"
        elif "sake" in type_lower:
            sub_cat = "Sake"
        else:
            sub_cat = "Wine"
        return big_cat, sub_cat

    # 2. Champagne 獨立邏輯 (直接檢查 C 欄 Type)
    if type_lower in ["champagne", "champagen"]:
        return "Sparkling", "Champagne"

    # 3. Sparkling (其他氣泡酒)
    elif type_val == "Sparkling":
        return "Sparkling", f"{country_adj} Sparkling"

    # 4. Rosé
    elif type_val in ["Rosé", "Rose"]:
        return "Rosé", f"{country_adj} Rosé"

    # 5. White Wine
    elif type_val in ["White", "White Wine"]:
        return "White Wine", f"{country_adj} White"

    # 6. Red Wine
    elif type_val in ["Red", "Red Wine"]:
        return "Red Wine", f"{country_adj} Red"

    # 7. Sweet Wine
    elif type_val in ["Sweet", "Sweet Wine", "Dessert", "Sauternes", "Tokaji", "Ice Wine"]:
        return "Sweet Wine", f"{country_adj} Sweet"

    # 8. Fortified Wine
    elif type_val in ["Sherry", "Port", "Madeira", "Fortified", "Fortified Wine"]:
        return "Fortified Wine", f"{country_adj} Fortified"

    # 9. Sake
    elif type_val in ["Sake", "Nihonshu"]:
        return "Sake", "Sake"

    # 10. Spirits & Liquors
    spirits_types = ["Spirits", "Single Malt Whisky", "Blended Whisky", "Brandy", "Cognac", "Armagnac", "Calvado", "Rum", "Vodka", "Gin", "Tequila", "Liquor"]
    if type_val in spirits_types:
        return "Spirits & Liquors", type_val

    # 11. Beer & Cocktails
    beer_cocktail_types = ["Beer", "Bottled Beer", "Draft Beer", "Cocktail", "Draft Cocktail"]
    if type_val in beer_cocktail_types:
        return "Beer & Cocktails", type_val

    # 12. Alcohol Free & Soft Drinks
    soft_types = ["Alcohol Free", "Alccohol Free", "Soft Drink", "Juice", "Tea", "Coffee", "Mocktail"]
    if type_val in soft_types:
        clean_type = "Alcohol Free" if type_val == "Alccohol Free" else type_val
        return "Alcohol Free & Soft Drinks", clean_type

    # 13. Others
    return "Others", type_val if type_val else "Others"
    
def fetch_and_clean():
    """
    核心抓取、清洗與排序函式
    """
    all_wines = []      # 酒款總表
    
    base_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

    # 僅針對指定的兩個有效分頁進行抓取
    for name in TARGET_SHEETS:
        try:
            url = f"{base_url}&sheet={requests.utils.quote(name)}"
            response = requests.get(url)
            response.encoding = 'utf-8'
            
            # 讀取 CSV 並跳過前 2 列（Row 1 & Row 2 為抬頭與說明欄）
            df = pd.read_csv(StringIO(response.text), skiprows=2, header=None)
            
            # 對接 21 欄結構：若不足 21 欄（A~U）則補滿空字串
            for col_idx in range(21):
                if col_idx not in df.columns:
                    df[col_idx] = ""
            
            # 只取前 21 欄
            df = df.iloc[:, :21]
            
            # 清除 Index 6 (Column G - Item Name) 為空的無效列
            df = df[df[6].notnull() & (df[6].astype(str).str.strip() != "")]
            
            # 清除儲存格前後空格與格化式調整
            def clean_cell(val):
                if pd.isna(val):
                    return ""
                if isinstance(val, float):
                    if val.is_integer():
                        return str(int(val))
                    return str(val)
                return str(val).strip()

            for col in df.columns:
                df[col] = df[col].apply(clean_cell)
            
            # 開始將 DataFrame 轉為二維陣列進行精密分類加工
            rows = df.values.tolist()
            processed_rows = []
            
            for row in rows:
                # 依據最新複雜邏輯計算大分類與子分類
                big_cat, sub_cat = parse_categories(name, row)
                
                # 替換 row[2] 為動態計算出的子分類，方便前端框架直接沿用
                row[2] = sub_cat
                
                # 將「大分類名稱」附加到陣列的最後面（Index 21）
                row.append(big_cat)
                
                processed_rows.append(row)
                
            all_wines.extend(processed_rows)
            print(f"Successfully synced sheet: [{name}] -> Processed {len(processed_rows)} items.")
            
        except Exception as e:
            print(f"[Warning] Failed to sync sheet {name}. Reason: {e}")

    # 依照 CATEGORY_ORDER 字典定義的權重順序進行全酒款精準排序
    # x[21] 代表剛附加進去的最尾端「大分類」
    all_wines.sort(key=lambda x: CATEGORY_ORDER.get(x[21], 99))

    # 封裝輸出數據
    output_data = {
        "wines": all_wines,
        "categories": TARGET_SHEETS
    }

    # 匯出前端可讀取的 JSON 檔案
    with open('wine_data.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    print(f"\n[Complete] {len(all_wines)} items have been parsed, sorted and successfully exported to 'wine_data.json'.")

if __name__ == "__main__":
    fetch_and_clean()
