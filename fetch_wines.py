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
SHEET_ID = "1Yq8_ZA73THLrd1qSyAL9BwXnEwzpefXHPqxRKf_60Rs"

# 指定分頁
TARGET_SHEETS = ["By the Glass", "Wine List"]

# Index
CATEGORY_ORDER = {
    "By the Glass": 1,
    "Sparkling Wine": 2,
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

# 國家名詞
COUNTRY_TO_NOUN = {
    "france": "France",
    "italy": "Italy",
    "spain": "Spain",
    "australia": "Australia",
    "germany": "Germany",
    "chile": "Chile",
    "new zealand": "New Zealand",
    "south africa": "South Africa",
    "america": "America",
    "united states": "America",
    "usa": "America",
    "japan": "Japan"
}

def classify_wine_dynamic(row, sheet_name="Wine List"):
    """
    分類
    row[2] = C欄 (Type)
    row[3] = D欄 (Country)
    """
    type_val = str(row[2]).strip() if len(row) > 2 and pd.notna(row[2]) else ""
    country_val = str(row[3]).strip() if len(row) > 3 and pd.notna(row[3]) else ""
    
    type_lower = type_val.lower()
    country_lower = country_val.lower()
    
    # 國家名詞
    country_noun = COUNTRY_TO_NOUN.get(country_lower, country_val.capitalize() if country_val else "Others")

    # 1. By the Glass
    if sheet_name == "By the Glass":
        big_cat = "By the Glass"
        if "spirit" in type_lower or "liquor" in type_lower or any(x in type_lower for x in ["whisky", "whiskey", "brandy", "cognac", "gin", "vodka", "rum", "tequila", "shochu"]):
            sub_cat = "Spirits & Liquor"
        elif "sake" in type_lower:
            sub_cat = "Sake"
        else:
            sub_cat = "Wine"
        return big_cat, sub_cat

    # 若Type為空
    if type_val == "":
        return "Others", ""

    # 2. Champagne
    if type_lower in ["champagne", "champagen"]:
        return "Sparkling Wine", "Champagne"

    # 3. Sparkling Wine
    if type_val == "Sparkling" or any(x in type_val for x in ["Sparkling Wine", "Prosecco", "Cava", "Crémant", "Franciacorta"]):
        return "Sparkling Wine", country_noun

    # 4. Rosé
    if type_val in ["Rosé", "Rose"]:
        return "Rosé", country_noun

    # 5. White Wine
    if type_val in ["White", "White Wine"]:
        return "White Wine", country_noun

    # 6. Red Wine
    if type_val in ["Red", "Red Wine"]:
        return "Red Wine", country_noun

    # 7. Sweet Wine
    if type_val in ["Sweet", "Sweet Wine", "Dessert", "Sauternes", "Tokaji", "Ice Wine"]:
        return "Sweet Wine", country_noun

    # 8. Fortified Wine
    if type_val in ["Sherry", "Port", "Madeira", "Fortified", "Fortified Wine"]:
        return "Fortified Wine", country_noun

    # 9. Sake
    if type_val in ["Sake", "Nihonshu"] or "sake" in type_lower:
        return "Sake", ""

    # 10. Spirits & Liquors
    spirits_types = ["Spirits", "Single Malt Whisky", "Blended Whisky", "Brandy", "Cognac", "Armagnac", "Calvado", "Rum", "Vodka", "Gin", "Tequila", "Liquor", "Shochu"]
    if type_val in spirits_types or "shochu" in type_lower or "whisky" in type_lower or "whiskey" in type_lower:
        specific_sub = "Shochu" if (type_val == "Shochu" or "shochu" in type_lower) else type_val
        return "Spirits & Liquors", specific_sub

    # 11. Beer & Cocktails
    if "beer" in type_lower or "cocktail" in type_lower:
        sub_cat = "Cocktails" if "cocktail" in type_lower else "Beer"
        return "Beer & Cocktails", sub_cat

    # 12. Alcohol Free & Soft Drinks
    soft_types = ["Alcohol Free", "Alccohol Free", "Soft Drink", "Juice", "Tea", "Coffee", "Mocktail"]
    if type_val in soft_types or any(x in type_lower for x in ["free", "drink", "juice", "tea", "coffee", "mocktail"]):
        sub_cat = "Alcohol Free" if ("free" in type_lower) else "Soft Drinks"
        return "Alcohol Free & Soft Drinks", sub_cat

    # 13. Others
    return "Others", ""
    
def fetch_and_clean():
    """
    排序
    """
    all_wines = []      # 酒款總表
    base_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

    # 指定分頁
    for name in TARGET_SHEETS:
        try:
            url = f"{base_url}&sheet={requests.utils.quote(name)}"
            response = requests.get(url)
            response.encoding = 'utf-8'
            
            # 跳過前2列
            df = pd.read_csv(StringIO(response.text), skiprows=2, header=None)
            
            # 21欄結構
            for col_idx in range(21):
                if col_idx not in df.columns:
                    df[col_idx] = ""
            
            # 只取前21欄
            df = df.iloc[:, :21]
            
            # Index 6(Column G)為空
            df = df[df[6].notnull() & (df[6].astype(str).str.strip() != "")]
            
            # 格式化調整
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
            
            # DataFrame
            rows = df.values.tolist()
            processed_rows = []
            
            for row in rows:
                big_cat, sub_cat = classify_wine_dynamic(row, name)
                
                # row[2] (Column C)
                row[2] = sub_cat
                
                # （Index 21）
                row.append(big_cat)
                processed_rows.append(row)
                
            all_wines.extend(processed_rows)
            print(f"Successfully synced sheet: [{name}] -> Processed {len(processed_rows)} items.")
            
        except Exception as e:
            print(f"[Warning] Failed to sync sheet {name}. Reason: {e}")

    # CATEGORY_ORDER
    # x[21]「大分類」
    all_wines.sort(key=lambda x: CATEGORY_ORDER.get(x[21], 99))

    # 封裝
    output_data = {
        "wines": all_wines,
        "categories": TARGET_SHEETS
    }

    # 匯出JSON
    with open('wine_data.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    print(f"\n[Complete] {len(all_wines)} items have been parsed, sorted and successfully exported to 'wine_data.json'.")

if __name__ == "__main__":
    fetch_and_clean()
