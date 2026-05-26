# =================================================================================
# 
# 專案名稱：電子酒單&庫存前後端管理系統
# 開發設計：Sommelier Yannick "Y.K." Liu
# 版權所有 (c) 2026 Yannick "Y.K." Liu. 保留所有權利。
#
# 【商用授權聲明】
# 本程式碼之邏輯、架構及演算法均屬原開發者 Yannick "Y.K." Liu 個人財產。
# 僅供獲得正式授權之合作單位使用。未經版權所有者書面同意，禁止任何形式之
# 轉售、散佈、複製或二次開發。
#
# =================================================================================

import pandas as pd
import json
import requests
from io import StringIO

SHEET_ID = "107NpWDkYDOlhIoC-ewLHZouWJoAfd8GTifBa8YTDMSQ"

# GAS同步對應A到P欄位的0-based索引
COL = {
    "bin": 0,          # A 欄：庫位
    "ref": 1,          # B 欄：編號
    "country": 2,      # C 欄：國家
    "region": 3,       # D 欄：大產區
    "sub_region": 4,   # E 欄：子產區
    "item": 5,         # F 欄：品項名稱
    "vintage": 6,      # G 欄：年份
    "volume": 7,       # H 欄：容量
    "price": 8,        # I 欄：價格
    "opening": 9,      # J 欄：期初
    "usage": 10,       # K 欄：消耗
    "ending": 11,      # L 欄：期末庫存
    "varieties": 12,   # M 欄：品種
    "tag": 13,         # N 欄：標籤
    "description": 14, # O 欄：風味描述
    "url": 15          # P 欄：圖片連結
}

# 前端大項目
MASTER_CATEGORIES = [
    "By The Glass",
    "Champagne & Sparkling",
    "White Wine",
    "Red Wine",
    "Sweet Wine",
    "Spirit & Liquor",
    "Draft & Cocktail",
    "Alcohol Free & Soft Drink"
]

def get_menu_category(tab_name):
    """
    智能分類映射器
    分析Google Sheets分頁名稱自動對應到大項
    """
    name_lower = tab_name.lower().strip()
    
    if "glass" in name_lower or "btg" in name_lower or "單杯" in name_lower:
        return "By The Glass"
    elif "champagne" in name_lower or "sparkling" in name_lower or "氣泡" in name_lower or "香檳" in name_lower:
        return "Champagne & Sparkling"
    elif "sweet" in name_lower or "dessert" in name_lower or "甜酒" in name_lower or "貴腐" in name_lower:
        return "Sweet Wine"
    elif "spirit" in name_lower or "liquor" in name_lower or "whisky" in name_lower or "烈酒" in name_lower:
        return "Spirit & Liquor"
    elif "draft" in name_lower or "cocktail" in name_lower or "調酒" in name_lower or "汲飲" in name_lower:
        return "Draft & Cocktail"
    elif "free" in name_lower or "soft" in name_lower or "無酒精" in name_lower or "軟性" in name_lower:
        return "Alcohol Free & Soft Drink"
    elif "red" in name_lower or "紅" in name_lower:
        return "Red Wine"
    elif "white" in name_lower or "白" in name_lower:
        return "White Wine"
    
    return "White Wine" # 防呆預設

def fetch_and_clean():
    # 確保JSON初始化
    output_database = {cat: {} for cat in MASTER_CATEGORIES}

    # Gviz API分頁名稱
    meta_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:json"
    try:
        res = requests.get(meta_url)
        start_idx = res.text.find("{")
        end_idx = res.text.rfind("}") + 1
        meta_data = json.loads(res.text[start_idx:end_idx])
        sheet_names = [sheet['name'] for sheet in meta_data.get('table', {}).get('parsedParams', {}).get('sheets', [])]
    except Exception as e:
        print(f"[-] 動態獲取分頁結構失敗: {e}")
        return

    base_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

    # 分頁與歸類
    for tab_name in sheet_names:
        if "REC" in tab_name or "CRM" in tab_name:
            continue
            
        target_category = get_menu_category(tab_name)
        print(f"[*] 偵測到分頁 [{tab_name}] ➔ 自動歸流至前端大項: {target_category}")
            
        try:
            url = f"{base_url}&sheet={requests.utils.quote(tab_name)}"
            response = requests.get(url)
            response.encoding = 'utf-8'
            
            # 讀取CSV
            df = pd.read_csv(StringIO(response.text), skiprows=2, header=None)
            
            # 防止因GS欄未填導致的IndexError/KeyError
            df = df.reindex(columns=range(16), fillvalue="")
            
            # 過濾無效列
            df = df.fillna("")
            df = df[df[COL["item"]].astype(str).str.strip() != ""]
            
            if df.empty:
                continue

            # 逐列迭代
            for _, row in df.iterrows():
                row_list = list(row)
                
                # 地理防呆
                country = str(row_list[COL["country"]]).strip() or "Others"
                region = str(row_list[COL["region"]]).strip() or "Generic"
                sub_region = str(row_list[COL["sub_region"]]).strip() or "Generic"
                
                # 即時庫存
                ending_str = str(row_list[COL["ending"]]).replace(",", "").strip()
                try:
                    is_sold_out = True if not ending_str or float(ending_str) <= 0 else False
                except ValueError:
                    is_sold_out = False 

                # 酒款規格
                wine_obj = {
                    "bin": str(row_list[COL["bin"]]).strip(),
                    "ref": str(row_list[COL["ref"]]).strip(),
                    "item": str(row_list[COL["item"]]).strip(),
                    "vintage": str(row_list[COL["vintage"]]).strip(),
                    "volume": str(row_list[COL["volume"]]).strip(),
                    "price": str(row_list[COL["price"]]).strip(),
                    "opening": str(row_list[COL["opening"]]).strip(),
                    "usage": str(row_list[COL["usage"]]).strip(),
                    "ending": ending_str,
                    "varieties": str(row_list[COL["varieties"]]).strip(),
                    "tag": str(row_list[COL["tag"]]).strip(),
                    "description": str(row_list[COL["description"]]).strip(),
                    "url": str(row_list[COL["url"]]).strip(),
                    "original_tab": tab_name,
                    "is_sold_out": is_sold_out
                }
                
                # 使用setdefault鏈式語法
                output_database[target_category] \
                    .setdefault(country, {}) \
                    .setdefault(region, {}) \
                    .setdefault(sub_region, []) \
                    .append(wine_obj)
                
            print(f"[+] 成功同步並歸流分頁資料: {tab_name}")
            
        except Exception as e:
            print(f"[-] 同步分頁 {tab_name} 失敗: {e}")

    # 過濾掉空項目
    final_database = {cat: data for cat, data in output_database.items() if data}
    active_categories = list(final_database.keys())

    # 封裝前端對接規格JSON
    final_json = {
        "menu_types": active_categories,  
        "database": final_database
    }

    # 本地輸出
    with open('wine_data.json', 'w', encoding='utf-8') as f:
        json.dump(final_json, f, ensure_ascii=False, indent=4)
        
    print("\n[完成] wine_data.json 對接前端Tabs")

if __name__ == "__main__":
    fetch_and_clean()
