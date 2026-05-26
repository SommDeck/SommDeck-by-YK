# =================================================================================
# 
# 專案名稱：電子酒單&庫存前後端管理系統 (GSA 欄位全對應優化版 v3.5)
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

SHEET_ID = "107NpWDkYD0lhIoC-ewLHZouWJoAfd8GTifBa8YTDMSQ"

# 💡 與 GAS v3.5 核心定義完全同步：精準對應 A 到 P 欄位的 0-based 索引
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

def fetch_and_clean():
    output_database = {}
    menu_types = []  # 記錄所有有效的分頁大項

    # 1. 透過 Gviz API 動態獲取試算表的所有分頁名稱
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

    # 2. 分頁歸類
    for tab_name in sheet_names:
        # 自動排除日誌(REC)與客戶管理(CRM)
        if "REC" in tab_name or "CRM" in tab_name:
            continue
            
        try:
            url = f"{base_url}&sheet={requests.utils.quote(tab_name)}"
            response = requests.get(url)
            response.encoding = 'utf-8'
            
            # 從第3列開始
            df = pd.read_csv(StringIO(response.text), skiprows=2, header=None)
            
            # 校驗：確保F欄不為空值
            df = df[df[COL["item"]].notnull() & (df[COL["item"]].astype(str).str.strip() != "")]
            df = df.fillna("") # 將所有 NaN 空值補上空字串，防止 JSON 解析破裂
            
            if df.empty:
                continue

            menu_types.append(tab_name)
            if tab_name not in output_database:
                output_database[tab_name] = {}

            # 3. 逐列迭代
            for _, row in df.iterrows():
                # 確保row至少有16欄
                row_list = list(row) + [""] * (16 - len(row))
                
                # 分類資訊
                country = str(row_list[COL["country"]]).strip() or "Others"
                region = str(row_list[COL["region"]]).strip() or "Generic"
                sub_region = str(row_list[COL["sub_region"]]).strip() or "Generic"
                
                # 動態建構：大分類(分頁) -> 國家 -> 大產區 -> 子產區
                if country not in output_database[tab_name]:
                    output_database[tab_name][country] = {}
                if region not in output_database[tab_name][country]:
                    output_database[tab_name][country][region] = {}
                if sub_region not in output_database[tab_name][country][region]:
                    output_database[tab_name][country][region][sub_region] = []

                # 庫存與售罄
                ending_str = str(row_list[COL["ending"]]).replace(",", "").strip()
                try:
                    is_sold_out = True if not ending_str or float(ending_str) <= 0 else False
                except ValueError:
                    is_sold_out = False # 若非數字則預設不售罄

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
                    "is_sold_out": is_sold_out
                }
                
                # 子產區清單
                output_database[tab_name][country][region][sub_region].append(wine_obj)
                
            print(f"[+] 成功同步分頁並完成四層巢狀歸類: {tab_name}")
            
        except Exception as e:
            print(f"[-] 同步分頁 {tab_name} 失敗: {e}")

    # 4. 封裝成標準前端規格的 JSON
    final_json = {
        "menu_types": menu_types,      # e.g., ["香檳氣泡酒", "白葡萄酒", "紅葡萄酒"]
        "database": output_database
    }

    # 寫入本地靜態檔案
    with open('wine_data.json', 'w', encoding='utf-8') as f:
        json.dump(final_json, f, ensure_ascii=False, indent=4)
    print("\n[完成] 4層結構化 wine_data.json 已自動生成，無縫對接前端 HTML Tabs！")

if __name__ == "__main__":
    fetch_and_clean()
