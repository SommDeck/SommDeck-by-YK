# =================================================================================
# 
# 專案名稱：電子酒單&庫存前後端管理系統 (GSA 動態二級架構版)
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

def get_big_category(sheet_name):
    """
    【分類漏斗】
    根據試算表分頁名稱(Tabs)，動態運算出最外層側邊欄的摺疊大分類。
    支援未來任意拆分或擴充子分頁。
    """
    name_lower = sheet_name.lower()
    
    # 1. 優先過濾單杯格式
    if "glass" in name_lower:
        return "By the Glass"
    # 2. 過濾型態（氣泡與粉紅）
    elif "champagne" in name_lower or "sparkling" in name_lower:
        return "Champagne & Sparkling"
    elif "rosé" in name_lower or "rose" in name_lower:
        return "Rosé"
    # 3. 根據產地+紅白進行大類歸納
    elif "white" in name_lower:
        return "White Wine"
    elif "red" in name_lower:
        return "Red Wine"
    # 4. 例外機制
    else:
        return "Others"

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
        
        # 解析試算表內分頁名稱
        sheet_names = [sheet['name'] for sheet in meta_data.get('table', {}).get('parsedParams', {}).get('sheets', [])]
    except Exception as e:
        print(f"【錯誤】動態獲取分頁結構失敗: {e}")
        return

    base_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

    # 對各分頁進行二維矩陣對齊
    for name in sheet_names:
        # 排除後臺分頁
        if "REC" in name or "CRM" in name:
            continue
            
        try:
            url = f"{base_url}&sheet={requests.utils.quote(name)}"
            response = requests.get(url)
            response.encoding = 'utf-8'
            
            #  (skiprows=2)
            df = pd.read_csv(StringIO(response.text), skiprows=2, header=None)
            
            # 將資料補滿至12欄 (索引 0~11，對應 A-L 欄)
            # 防止Pandas自動裁切造成位移
            for col_idx in range(12):
                if col_idx not in df.columns:
                    df[col_idx] = ""
            
            # 保留基礎12欄資料捨棄雜訊欄
            df = df.iloc[:, :12]
            
            # 清除酒名(Index 4)為空或純空白鍵的無效無登錄橫列
            df = df[df[4].notnull() & (df[4].astype(str).str.strip() != "")]
            
            # 防止年份、REF等字串失效
            def clean_cell(val):
                if pd.isna(val):
                    return ""
                if isinstance(val, float):
                    if val.is_integer():
                        return str(int(val))  # 2026.0 -> "2026"
                    return str(val)
                return str(val).strip()

            for col in df.columns:
                df[col] = df[col].apply(clean_cell)
            
            # 雙層選單路由節點
            big_cat = get_big_category(name)
            df[12] = name     # Index 12: 子分頁名稱 (例如: "Burgundy Red")
            df[13] = big_cat  # Index 13: 側邊欄折疊大分類 (例如: "Red Wine")
            
            # 合併至全域資料集
            all_wines.extend(df.values.tolist())
            categories.append(name)
            print(f"成功動態同步分頁: [{big_cat: <21} -> {name}]")
            
        except Exception as e:
            print(f"【警告】同步分頁 {name} 失敗，已略過該分頁。錯誤原因: {e}")

    # 輸出契合前端JSON格式
    output_data = {
        "wines": all_wines,
        "categories": categories
    }

    # 寫入靜態JSON
    with open('wine_data.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print("\n[完成] JSON 數據模型已自動化對齊，雙層側邊欄選單已無縫就緒。")

if __name__ == "__main__":
    fetch_and_clean()
