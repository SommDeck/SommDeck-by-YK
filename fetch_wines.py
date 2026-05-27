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

# 核心雲端試算表來源ID
SHEET_ID = "107NpWDkYD0lhIoC-ewLHZouWJoAfd8GTifBa8YTDMSQ"

def parse_categories(sheet_name):
    """
    【雙層分類】
    大分類 (big_category) 與子項目名稱 (sub_category)。
    """
    name_lower = sheet_name.lower()
    
    # 1. By the Glass 子項目名稱
    if "glass" in name_lower:
        big_cat = "By the Glass"
        if "wine" in name_lower:
            sub_cat = "Wine"
        elif "spirits" in name_lower or "liquor" in name_lower:
            sub_cat = "Spirits & Liquor"
        else:
            sub_cat = "Wine" # 安全預設值
        return big_cat, sub_cat
        
    # 2. 烈酒與利口酒大類 (非單杯)
    elif "spirits" in name_lower or "liquor" in name_lower:
        return "Spirits & Liquor", sheet_name
        
    # 3. 氣泡系列
    elif "champagne" in name_lower or "sparkling" in name_lower:
        return "Champagne & Sparkling", sheet_name
        
    # 4. 粉紅酒
    elif "rosé" in name_lower or "rose" in name_lower:
        return "Rosé", sheet_name
        
    # 5. 白葡萄酒
    elif "white" in name_lower:
        return "White Wine", sheet_name
        
    # 6. 紅葡萄酒
    elif "red" in name_lower:
        return "Red Wine", sheet_name
        
    # 7. 例外安全機制
    else:
        return "Others", sheet_name

def fetch_and_clean():
    all_wines = []
    categories = []
    
    # 透過GSA獲取試算表分頁結構
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

    for name in sheet_names:
        # 排除後臺與日誌分頁
        if "REC" in name or "CRM" in name or "Setup" in name or "User_Config" in name:
            continue
            
        try:
            url = f"{base_url}&sheet={requests.utils.quote(name)}"
            response = requests.get(url)
            response.encoding = 'utf-8'
            
            df = pd.read_csv(StringIO(response.text), skiprows=2, header=None)
            
            # 將資料補滿至16欄 (索引0~15，對應A-P欄)
            for col_idx in range(16):
                if col_idx not in df.columns:
                    df[col_idx] = ""
            
            df = df.iloc[:, :16]
            
            # 清除酒名(Index 5)為空的無效列
            df = df[df[5].notnull() & (df[5].astype(str).str.strip() != "")]
            
            # 清洗儲存格內容
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
            
            # 大分類與子分類名稱
            big_cat, sub_cat = parse_categories(name)
            
            df[16] = sub_cat  # Index 16: 前台子項目名稱 (例: "Spirits & Liquor")
            df[17] = big_cat  # Index 17: 側邊欄大分類名稱 (例: "By the Glass")
            
            all_wines.extend(df.values.tolist())
            categories.append(name)
            print(f"成功同步並優化分頁: [{big_cat: <21} -> {sub_cat: <18} (原分頁名: {name})]")
            
        except Exception as e:
            print(f"【警告】同步分頁 {name} 失敗。原因: {e}")

    output_data = {
        "wines": all_wines,
        "categories": categories
    }

    with open('wine_data.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print("\n[完成] JSON 任務成功。")

if __name__ == "__main__":
    fetch_and_clean()
