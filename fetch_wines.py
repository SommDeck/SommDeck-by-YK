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

# 順序Index
CATEGORY_ORDER = {
    "By the Glass": 1,
    "Sparkling": 2,
    "Rosé": 3,
    "White Wine": 4,
    "Red Wine": 5,
    "Sweer Wine": 6,
    "Fortified Wine": 7,
    "Sake": 8,
    "Spirits & Liquor": 9,
    "Draft & Cocktails": 10,
    "Alcohol Free & Soft Drinks": 11,
    "Others": 12
}

def parse_categories(sheet_name):
    """
    分類
    依據分頁名稱關鍵字，進行分類
    """
    name_lower = sheet_name.lower()
    
    # 1. By the Glass
    if "glass" in name_lower:
        big_cat = "By the Glass"
        if "wine" in name_lower:
            sub_cat = "Wine"
        elif "spirits" in name_lower or "liquor" in name_lower:
            sub_cat = "Spirits & Liquor"
        else:
            sub_cat = "Wine" # 安全預設值
        return big_cat, sub_cat
        
    # 2. Sparkling
    elif "champagne" in name_lower or "sparkling" in name_lower:
        return "Champagne & Sparkling", sheet_name
        
    # 3. Rosé
    elif "rosé" in name_lower or "rose" in name_lower:
        return "Rosé", sheet_name
        
    # 4. White Wine
    elif "white" in name_lower:
        return "White Wine", sheet_name
        
    # 5. Red Wine
    elif "red" in name_lower:
        return "Red Wine", sheet_name
        
    # 6. Sweet Wine
    elif "sweet" in name_lower or "dessert" in name_lower or "sauternes" in name_lower or "tokaji" in name_lower or "ice wine" in name_lower:
        return "Sweet Wine", sheet_name
        
    # 7. Fortified Wine
    elif "fortified" in name_lower or "port" in name_lower or "sherry" in name_lower:
        return "Fortified Wine", sheet_name

    # 8. Sake
    elif "sake" in name_lower or "nihonshu" in name_lower:
        return "Sake", sheet_name
        
    # 9. Spirits & Liquor
    elif "spirits" in name_lower or "liquor" in name_lower:
        return "Spirits & Liquor", sheet_name
        
    # 10. Draft & Cocktails
    elif "draft" in name_lower or "cocktail" in name_lower or "beer" in name_lower:
        return "Draft & Cocktails", sheet_name
        
    # 11. Alcohol Free & Soft Drinks
    elif "alcohol free" in name_lower or "soft drink" in name_lower or "mocktail" in name_lower or "juice" in name_lower or "soda" in name_lower or "tea" in name_lower or "coffee" in name_lower:
        return "Alcohol Free & Soft Drinks", sheet_name
        
    # 12. Others
    else:
        return "Others", sheet_name

def fetch_and_clean():
    """
    核抓取、排序函式
    """
    all_wines = []      # 酒款總表
    raw_categories = []  # 分頁原始名稱
    
    # 透過 GSA (Google Visualization API) 獲取試算表分頁
    meta_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:json"
    
    try:
        res = requests.get(meta_url)
        start_idx = res.text.find("{")
        end_idx = res.text.rfind("}") + 1
        meta_data = json.loads(res.text[start_idx:end_idx])
        sheet_names = [sheet['name'] for sheet in meta_data.get('table', {}).get('parsedParams', {}).get('sheets', [])]
    except Exception as e:
        print(f"【錯誤】動態獲取分頁結構失敗: {e}")
        return

    base_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

    # 遍歷每個有效分頁
    for name in sheet_names:
        # 排除後臺與日誌分頁
        if "REC" in name or "CRM" in name or "Setup" in name or "User_Config" in name:
            continue
            
        try:
            url = f"{base_url}&sheet={requests.utils.quote(name)}"
            response = requests.get(url)
            response.encoding = 'utf-8'
            
            # 讀取CSV並跳過前2列
            df = pd.read_csv(StringIO(response.text), skiprows=2, header=None)
            
            # 【防呆】將資料補滿至16欄，防止前端調用時Undefined
            for col_idx in range(16):
                if col_idx not in df.columns:
                    df[col_idx] = ""
            
            df = df.iloc[:, :16]
            
            # 清除Index 5為空的無效列
            df = df[df[5].notnull() & (df[5].astype(str).str.strip() != "")]
            
            # 清除儲存格前後空格
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
            
            # 大分類與子分類名稱貼標
            big_cat, sub_cat = parse_categories(name)
            
            df[16] = sub_cat  # Index 16: 前台子項目名稱
            df[17] = big_cat  # Index 17: 側邊欄/大分類名稱
            
            all_wines.extend(df.values.tolist())
            raw_categories.append(name)
            print(f"成功同步分頁: [{big_cat: <26} -> {sub_cat: <18} (原分頁名: {name})]")
            
        except Exception as e:
            print(f"【警告】同步分頁 {name} 失敗。原因: {e}")

    # CATEGORY_ORDER 排序酒款
    all_wines.sort(key=lambda x: CATEGORY_ORDER.get(x[17], 99))
    
    # categories 排序
    sorted_categories = list(set(raw_categories))
    sorted_categories.sort(key=lambda name: CATEGORY_ORDER.get(parse_categories(name)[0], 99))

    # 封裝
    output_data = {
        "wines": all_wines,
        "categories": sorted_categories
    }

    # 匯出 JSON
    with open('wine_data.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print(f"\n[完成] 完美的 {len(all_wines)} 款酒水已按照指定酒單順序排序並匯出。")

if __name__ == "__main__":
    fetch_and_clean()
