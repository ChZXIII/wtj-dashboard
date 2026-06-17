import os
import time
import hmac
import hashlib
import requests
import json
import datetime
import re
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Load configurations
load_dotenv()
BITKUB_API_KEY = os.getenv('BITKUB_API_KEY')
BITKUB_API_SECRET = os.getenv('BITKUB_API_SECRET')
BINANCE_TH_API_KEY = os.getenv('BINANCE_TH_API_KEY')
BINANCE_TH_API_SECRET = os.getenv('BINANCE_TH_API_SECRET')

# ค้นหาตำแหน่งโฟลเดอร์หลักของโปรเจกต์แบบไดนามิก
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

# Spreadsheet IDs
PORTFOLIO_SPREADSHEET_ID = '1yWxTiVglJsWhVBSlB7UPu7MXGRQ_vti5IjqxWTCFJK0'
TOKEN_PATH = os.path.join(PROJECT_ROOT, 'credentials', 'token_sheets.json')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
STATE_FILE = os.path.join(PROJECT_ROOT, 'credentials', 'trade_sync_state.json')

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {'processed_orders': []}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def get_bitkub_trades(symbol='KUB_THB'):
    base_url = 'https://api.bitkub.com'
    endpoint = '/api/v3/market/my-order-history'
    try:
        server_time = requests.get(f'{base_url}/api/v3/servertime').text
    except Exception as e:
        print(f"Warning: Failed to fetch Bitkub servertime ({e}), falling back to local time.")
        server_time = str(int(time.time() * 1000))
    import urllib.parse
    params = {'sym': symbol, 'p': 1, 'lmt': 10}
    query_string = urllib.parse.urlencode(params)
    payload = server_time + 'GET' + endpoint + '?' + query_string
    signature = hmac.new(BITKUB_API_SECRET.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-BTK-APIKEY': BITKUB_API_KEY,
        'X-BTK-SIGN': signature,
        'X-BTK-TIMESTAMP': server_time
    }
    res = requests.get(f'{base_url}{endpoint}?{query_string}', headers=headers)
    if res.status_code == 200:
        return res.json().get('result', [])
    return []

def get_binance_th_trades(symbol='BTCTHB'):
    base_url = 'https://api.binance.th'
    endpoint = '/api/v1/allOrders'
    timestamp = int(time.time() * 1000)
    query_string = f'symbol={symbol}&timestamp={timestamp}'
    signature = hmac.new(BINANCE_TH_API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    headers = {'X-MBX-APIKEY': BINANCE_TH_API_KEY}
    res = requests.get(f'{base_url}{endpoint}?{query_string}&signature={signature}', headers=headers)
    if res.status_code == 200:
        return res.json()
    return []

def get_target_tab(trade):
    if trade['coin'] == 'KUB':
        return 'Thyme'
    elif trade['coin'] == 'BTC':
        # กฎเหล็ก: ออเดอร์ซื้อ BTC ทุกไม้ต้องถูกแยกคัดกรองแบบรายไม้
        # ยอด <= 300 บาท -> Mod, ยอด > 300 บาท -> BTC
        return 'Mod' if trade['amount_thb'] <= 300 else 'BTC'
    else:
        return trade['coin']

def write_to_sheet(service, trade, sheet_metadata):
    tab_name = get_target_tab(trade)
    if not tab_name: return False
    print(f"Writing {trade['coin']} trade to tab {tab_name}...")
    sheet_id = None
    for s in sheet_metadata.get('sheets', []):
        if s['properties']['title'] == tab_name:
            sheet_id = s['properties']['sheetId']; break
    if sheet_id is None: return False

    if tab_name == 'BTC':
        result = service.spreadsheets().values().get(spreadsheetId=PORTFOLIO_SPREADSHEET_ID, range=f'{tab_name}!A1:A50').execute()
        rows = result.get('values', [])
        target_day = str(int(trade['date'].split('/')[0]))
        target_row_idx = None
        for i, row in enumerate(rows):
            if row and row[0] == target_day:
                target_row_idx = i + 1; break
        if target_row_idx:
            body = {'values': [[target_day, trade['amount_thb'], trade['price'], trade['amount_crypto']]]}
            service.spreadsheets().values().update(spreadsheetId=PORTFOLIO_SPREADSHEET_ID, range=f"{tab_name}!A{target_row_idx}:D{target_row_idx}", valueInputOption="USER_ENTERED", body=body).execute()
            return True
    else:
        result = service.spreadsheets().values().get(spreadsheetId=PORTFOLIO_SPREADSHEET_ID, range=f'{tab_name}!A1:E50').execute()
        rows = result.get('values', [])
        target_row_idx = None
        last_week = 0
        for i, row in enumerate(rows):
            row_str = " ".join(row).replace(" ", "")
            if 'ราคาเฉลี่ย' in row_str or 'ยอดเงินที่' in row_str:
                target_row_idx = i; break
            if len(row) > 1 and str(row[1]).isdigit():
                last_week = int(row[1])
        if target_row_idx is not None:
            requests_body = [{"insertDimension": {"range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": target_row_idx, "endIndex": target_row_idx + 1}, "inheritFromBefore": False}}]
            service.spreadsheets().batchUpdate(spreadsheetId=PORTFOLIO_SPREADSHEET_ID, body={'requests': requests_body}).execute()
            if tab_name in ['Thyme', 'Mod']:
                body = {'values': [[trade['date'], last_week + 1, trade['amount_thb'], trade['price'], trade['amount_crypto']]]}
                range_str = f"{tab_name}!A{target_row_idx + 1}:E{target_row_idx + 1}"
            else:
                body = {'values': [[trade['date'], trade['amount_thb'], trade['price'], trade['amount_crypto']]]}
                range_str = f"{tab_name}!A{target_row_idx + 1}:D{target_row_idx + 1}"
            service.spreadsheets().values().update(spreadsheetId=PORTFOLIO_SPREADSHEET_ID, range=range_str, valueInputOption="USER_ENTERED", body=body).execute()
            
            # Apply beautiful high-end row styling for Thyme and Mod
            if tab_name in ['Thyme', 'Mod']:
                ACCENT_BG = {'red': 0.2, 'green': 0.239, 'blue': 0.227}
                PLATINUM = {'red': 0.894, 'green': 0.894, 'blue': 0.918}
                ROW_BG = {'red': 0.973, 'green': 0.988, 'blue': 0.980}
                BORDER_COLOR = {'red': 0.298, 'green': 0.376, 'blue': 0.349}
                LEFT_BORDER = {'red': 0.0, 'green': 0.694, 'blue': 0.459}
                ri = target_row_idx
                
                fmt_reqs = [
                    {'repeatCell': {
                        'range': {'sheetId': sheet_id, 'startRowIndex': ri, 'endRowIndex': ri+1, 'startColumnIndex': 0, 'endColumnIndex': 1},
                        'cell': {'userEnteredFormat': {
                            'backgroundColor': ACCENT_BG,
                            'textFormat': {'foregroundColor': PLATINUM, 'bold': True, 'fontSize': 9, 'fontFamily': 'Google Sans Code'},
                            'horizontalAlignment': 'CENTER',
                            'borders': {'left': {'style': 'SOLID_MEDIUM', 'color': LEFT_BORDER}, 'right': {'style': 'SOLID', 'color': BORDER_COLOR}, 'top': {'style': 'SOLID', 'color': BORDER_COLOR}, 'bottom': {'style': 'SOLID', 'color': BORDER_COLOR}},
                            'numberFormat': {'type': 'DATE', 'pattern': 'dd/mm/yyyy'}
                        }},
                        'fields': 'userEnteredFormat'
                    }},
                    {'repeatCell': {
                        'range': {'sheetId': sheet_id, 'startRowIndex': ri, 'endRowIndex': ri+1, 'startColumnIndex': 1, 'endColumnIndex': 2},
                        'cell': {'userEnteredFormat': {
                            'backgroundColor': ACCENT_BG,
                            'textFormat': {'foregroundColor': PLATINUM, 'bold': True, 'fontSize': 9, 'fontFamily': 'Google Sans Code'},
                            'horizontalAlignment': 'CENTER',
                            'borders': {'left': {'style': 'SOLID', 'color': BORDER_COLOR}, 'right': {'style': 'SOLID', 'color': BORDER_COLOR}, 'top': {'style': 'SOLID', 'color': BORDER_COLOR}, 'bottom': {'style': 'SOLID', 'color': BORDER_COLOR}},
                            'numberFormat': {'type': 'NUMBER', 'pattern': '0'}
                        }},
                        'fields': 'userEnteredFormat'
                    }},
                    {'repeatCell': {
                        'range': {'sheetId': sheet_id, 'startRowIndex': ri, 'endRowIndex': ri+1, 'startColumnIndex': 2, 'endColumnIndex': 4},
                        'cell': {'userEnteredFormat': {
                            'backgroundColor': ROW_BG,
                            'textFormat': {'foregroundColor': {'red': 0.15, 'green': 0.2, 'blue': 0.18}, 'fontSize': 10, 'fontFamily': 'Google Sans Code'},
                            'horizontalAlignment': 'CENTER',
                            'borders': {'left': {'style': 'SOLID', 'color': BORDER_COLOR}, 'right': {'style': 'SOLID', 'color': BORDER_COLOR}, 'top': {'style': 'SOLID', 'color': BORDER_COLOR}, 'bottom': {'style': 'SOLID', 'color': BORDER_COLOR}},
                            'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0.00'}
                        }},
                        'fields': 'userEnteredFormat'
                    }},
                    {'repeatCell': {
                        'range': {'sheetId': sheet_id, 'startRowIndex': ri, 'endRowIndex': ri+1, 'startColumnIndex': 4, 'endColumnIndex': 5},
                        'cell': {'userEnteredFormat': {
                            'backgroundColor': ROW_BG,
                            'textFormat': {'foregroundColor': {'red': 0.15, 'green': 0.2, 'blue': 0.18}, 'fontSize': 10, 'fontFamily': 'Google Sans Code'},
                            'horizontalAlignment': 'CENTER',
                            'borders': {'left': {'style': 'SOLID', 'color': BORDER_COLOR}, 'right': {'style': 'SOLID', 'color': BORDER_COLOR}, 'top': {'style': 'SOLID', 'color': BORDER_COLOR}, 'bottom': {'style': 'SOLID', 'color': BORDER_COLOR}},
                            'numberFormat': {'type': 'NUMBER', 'pattern': '0.00000000'}
                        }},
                        'fields': 'userEnteredFormat'
                    }}
                ]
                service.spreadsheets().batchUpdate(spreadsheetId=PORTFOLIO_SPREADSHEET_ID, body={'requests': fmt_reqs}).execute()
            return True
    return False

def record_portfolio_snapshot_and_update_dashboard(service):
    print("Fetching totals and recording snapshot...")
    try:
        r = requests.get('https://api.binance.th/api/v1/ticker/allPrices')
        prices = {p['symbol']: float(p['price']) for p in r.json()}
    except:
        r = requests.get('https://api.binance.com/api/v3/ticker/price')
        all_p = r.json()
        prices = {p['symbol'].replace('USDT','THB'): float(p['price']) * 35 for p in all_p if p['symbol'].endswith('USDT')}

    rk = requests.get('https://api.bitkub.com/api/market/ticker')
    bk_ticker = rk.json()
    prices['KUBTHB'] = bk_ticker.get('THB_KUB', {}).get('last', 0)
    prices['BTCTHB_BK'] = bk_ticker.get('THB_BTC', {}).get('last', 0)

    tabs = ['BTC', 'BNB', 'ASTER', 'XRP', 'SOL', 'ETH', 'Thyme', 'Mod']
    pnl_data = []
    bC_data = []
    bkC_data = []
    tC_v = 0
    
    for tab in tabs:
        res = service.spreadsheets().values().get(spreadsheetId=PORTFOLIO_SPREADSHEET_ID, range=f'{tab}!A1:F100').execute()
        rows = res.get('values', [])
        cost = 0; amt = 0; found = False
        
        for i, row in enumerate(rows):
            if any(isinstance(c, str) and ('ราคาเฉลี่ย' in c or 'ยอดเงินที่' in c) for c in row):
                if i + 1 < len(rows):
                    data_row = rows[i+1]
                    try:
                        if tab in ['Thyme', 'Mod']:
                            cost = float(str(data_row[2]).replace(',','')) if len(data_row) > 2 else 0
                            amt = float(str(data_row[4]).replace(',','')) if len(data_row) > 4 else 0
                        else:
                            cost = float(str(data_row[1]).replace(',','')) if len(data_row) > 1 else 0
                            amt = float(str(data_row[3]).replace(',','')) if len(data_row) > 3 else 0
                        found = True
                    except: pass
                    break

        if found and cost > 0:
            sym = tab + 'THB'
            if tab == 'Mod': sym = 'BTCTHB_BK'
            elif tab == 'Thyme': sym = 'KUBTHB'
            elif tab == 'BTC': sym = 'BTCTHB'
            
            market_price = prices.get(sym, 0)
            current_val = amt * market_price
            pnl_pct = (current_val - cost) / cost * 100
            pnl_data.append(round(pnl_pct, 2))
            
            tC_v += cost
            
            if tab in ['Thyme', 'Mod']:
                bkC_data.append({"tab": tab, "coin": "KUB" if tab=="Thyme" else "BTC", "amt": round(amt, 8), "cost": round(cost, 2), "val": 0})
            else:
                bC_data.append({"coin": tab, "amt": round(amt, 8), "cost": round(cost, 2), "val": 0})
        else:
            pnl_data.append(0)

    # 3. Append to Portfolio_History (Only on the 1st of the month)
    now_str = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    final_row = [now_str] + pnl_data
    if datetime.datetime.now().day == 1:
        service.spreadsheets().values().append(
            spreadsheetId=PORTFOLIO_SPREADSHEET_ID, 
            range='Portfolio_History!A1', 
            valueInputOption='USER_ENTERED', 
            body={'values': [final_row]}
        ).execute()
        print(f"Monthly Snapshot recorded: {final_row}")
    else:
        print(f"Skipped saving to Portfolio_History (today is not the 1st of the month). Live snapshot: {final_row}")

    # 4. Export JSON
    try:
        res_all = service.spreadsheets().values().get(spreadsheetId=PORTFOLIO_SPREADSHEET_ID, range='Portfolio_History!A1:I500').execute()
        all_rows = res_all.get('values', [])
        if len(all_rows) > 1:
            history_json = {
                'labels': [r[0] for r in all_rows[1:]],
                'data': {
                    'BTC': [float(r[1]) if len(r)>1 and str(r[1]).replace('.','',1).replace('-','',1).isdigit() else 0 for r in all_rows[1:]],
                    'BNB': [float(r[2]) if len(r)>2 and str(r[2]).replace('.','',1).replace('-','',1).isdigit() else 0 for r in all_rows[1:]],
                    'ASTER': [float(r[3]) if len(r)>3 and str(r[3]).replace('.','',1).replace('-','',1).isdigit() else 0 for r in all_rows[1:]],
                    'XRP': [float(r[4]) if len(r)>4 and str(r[4]).replace('.','',1).replace('-','',1).isdigit() else 0 for r in all_rows[1:]],
                    'SOL': [float(r[5]) if len(r)>5 and str(r[5]).replace('.','',1).replace('-','',1).isdigit() else 0 for r in all_rows[1:]],
                    'ETH': [float(r[6]) if len(r)>6 and str(r[6]).replace('.','',1).replace('-','',1).isdigit() else 0 for r in all_rows[1:]],
                    'Thyme_KUB': [float(r[7]) if len(r)>7 and str(r[7]).replace('.','',1).replace('-','',1).isdigit() else 0 for r in all_rows[1:]],
                    'Mod_BTC': [float(r[8]) if len(r)>8 and str(r[8]).replace('.','',1).replace('-','',1).isdigit() else 0 for r in all_rows[1:]]
                }
            }
            js_path = os.path.join(PROJECT_ROOT, 'Personal_Assistance_HQ', 'Personal_Assistance_Team', 'M', 'html', 'history_data.js')
            with open(js_path, 'w') as f:
                f.write('const historyData = ' + json.dumps(history_json) + ';')
    except Exception as e:
        print(f"Error exporting JSON: {e}")

    # 5. Update HTML Dashboard
    html_path = os.path.join(PROJECT_ROOT, 'Personal_Assistance_HQ', 'Personal_Assistance_Team', 'M', 'html', 'portfolio_dashboard.html')
    if os.path.exists(html_path):
        try:
            with open(html_path, 'r') as f:
                html_content = f.read()

            bC_str = "[\n            " + ",\n            ".join([json.dumps(x) for x in bC_data]) + "\n        ]"
            bkC_str = "[\n            " + ",\n            ".join([json.dumps(x) for x in bkC_data]) + "\n        ]"
            
            html_content = re.sub(r'const\s+bC\s*=\s*\[.*?\];', f'const bC = {bC_str};', html_content, flags=re.DOTALL)
            html_content = re.sub(r'const\s+bkC\s*=\s*\[.*?\];', f'const bkC = {bkC_str};', html_content, flags=re.DOTALL)
            html_content = re.sub(r'const\s+tC_v\s*=\s*[\d\.]+;', f'const tC_v = {round(tC_v, 2)};', html_content)

            with open(html_path, 'w') as f:
                f.write(html_content)
            print("HTML Dashboard updated successfully.")
        except Exception as e:
            print(f"Error updating HTML: {e}")
    else:
        print("HTML Dashboard file does not exist, skipping update.")

MONTHS_TH = {
    1: 'ม.ค.', 2: 'ก.พ.', 3: 'มี.ค.', 4: 'เม.ย.',
    5: 'พ.ค.', 6: 'มิ.ย.', 7: 'ก.ค.', 8: 'ส.ค.',
    9: 'ก.ย.', 10: 'ต.ค.', 11: 'พ.ย.', 12: 'ธ.ค.'
}

def check_and_rollover_btc_tab(service):
    """ตรวจวัดการเปลี่ยนเดือนของแท็บ BTC อัตโนมัติทุกวันที่ 1"""
    try:
        now = datetime.datetime.now()
        current_month = MONTHS_TH.get(now.month)
        if not current_month:
            return

        # อ่านค่าใน B1 เพื่อดูว่าบิลเดือนไหนที่ยังเปิดใช้งานอยู่
        res = service.spreadsheets().values().get(
            spreadsheetId=PORTFOLIO_SPREADSHEET_ID,
            range='BTC!B1'
        ).execute()
        res_val = res.get('values', [])
        active_month = res_val[0][0].strip() if res_val and res_val[0] else ''

        if active_month and active_month != current_month:
            print(f"[Auto Month Rollover] เปลี่ยนเดือนจาก '{active_month}' เป็น '{current_month}' สำหรับแท็บ BTC...")
            
            # 1. ดึงยอดสรุปของเดือนเก่า (Row 36)
            res_totals = service.spreadsheets().values().get(
                spreadsheetId=PORTFOLIO_SPREADSHEET_ID,
                range='BTC!B36:D36'
            ).execute()
            totals_val = res_totals.get('values', [])
            totals = totals_val[0] if totals_val and totals_val[0] else [0, 0, 0]
            
            def parse_float(val):
                try:
                    return float(str(val).replace(',', '').strip())
                except:
                    return 0.0
            
            thb_total = parse_float(totals[0]) if len(totals) > 0 else 0.0
            avg_price = parse_float(totals[1]) if len(totals) > 1 else 0.0
            btc_total = parse_float(totals[2]) if len(totals) > 2 else 0.0
            
            # 2. ค้นหาแถวของเดือนเก่าในประวัติการ DCA (คอลัมน์ F)
            res_history = service.spreadsheets().values().get(
                spreadsheetId=PORTFOLIO_SPREADSHEET_ID,
                range='BTC!F1:F30'
            ).execute()
            history_rows = res_history.get('values', [])
            
            old_month_row_idx = None
            for idx, row in enumerate(history_rows):
                if row and row[0].strip() == active_month:
                    old_month_row_idx = idx + 1
                    break
                    
            if not old_month_row_idx:
                print(f"Warning: ไม่พบแถวของเดือน '{active_month}' ในประวัติ ค้นหาตำแหน่งว่างแทน...")
                # ค้นหาตำแหน่งว่างแรกถัดจากปี 2026
                for idx, row in enumerate(history_rows):
                    if idx >= 5 and (not row or not row[0].strip()):
                        old_month_row_idx = idx + 1
                        break
            
            if old_month_row_idx:
                # 3. แปลงค่าผลลัพธ์เดือนเก่าให้เป็น Static
                service.spreadsheets().values().update(
                    spreadsheetId=PORTFOLIO_SPREADSHEET_ID,
                    range=f'BTC!F{old_month_row_idx}:I{old_month_row_idx}',
                    valueInputOption='USER_ENTERED',
                    body={'values': [[active_month, thb_total, avg_price, btc_total]]}
                ).execute()
                print(f"กู้คืน/เขียนประวัติ '{active_month}' เป็นค่าคงที่เรียบร้อย")

                # 4. เขียนแถวประวัติเดือนใหม่ (เช่น มิ.ย.) อิงสูตรสรุปยอด
                new_month_row_idx = old_month_row_idx + 1
                service.spreadsheets().values().update(
                    spreadsheetId=PORTFOLIO_SPREADSHEET_ID,
                    range=f'BTC!F{new_month_row_idx}:I{new_month_row_idx}',
                    valueInputOption='USER_ENTERED',
                    body={'values': [[current_month, '=B36', '=C36', '=D36']]}
                ).execute()
                print(f"สร้างแถวใหม่สำหรับเดือน '{current_month}' เรียบร้อย")
                
                # 5. จัดการหน้าตา เส้นขอบตาราง (Borders) และสีของเดือนใหม่และเดือนเก่า
                meta = service.spreadsheets().get(spreadsheetId=PORTFOLIO_SPREADSHEET_ID).execute()
                btc_sheet_id = None
                for s in meta['sheets']:
                    if s['properties']['title'] == 'BTC':
                        btc_sheet_id = s['properties']['sheetId']
                        break
                
                if btc_sheet_id is not None:
                    DARK_BG = {'red': 0.21960784, 'green': 0.23921569, 'blue': 0.27450982}
                    LIGHT_BG = {'red': 0.94509804, 'green': 0.94509804, 'blue': 0.9607843}
                    TEXT_LIGHT = {'red': 0.89411765, 'green': 0.89411765, 'blue': 0.91764706}
                    TEXT_DARK = {'red': 0.2, 'green': 0.2, 'blue': 0.24705882}
                    GOLD_BORDER = {'red': 0.7176471, 'green': 0.5803922, 'blue': 0.23529412}
                    GREY_BORDER = {'red': 0.29803923, 'green': 0.32941177, 'blue': 0.3764706}
                    
                    fmt_reqs = [
                        # เปลี่ยนขอบล่างของแถวเดิมให้เป็นเส้นบาง
                        {
                            'updateBorders': {
                                'range': {
                                    'sheetId': btc_sheet_id,
                                    'startRowIndex': old_month_row_idx - 1,
                                    'endRowIndex': old_month_row_idx,
                                    'startColumnIndex': 5,
                                    'endColumnIndex': 9
                                },
                                'bottom': {'style': 'SOLID', 'color': GREY_BORDER}
                            }
                        },
                        # จัดฟอร์แมตแถวใหม่ (F: คอลัมน์เดือน)
                        {
                            'repeatCell': {
                                'range': {
                                    'sheetId': btc_sheet_id,
                                    'startRowIndex': new_month_row_idx - 1,
                                    'endRowIndex': new_month_row_idx,
                                    'startColumnIndex': 5,
                                    'endColumnIndex': 6
                                },
                                'cell': {
                                    'userEnteredFormat': {
                                        'backgroundColor': DARK_BG,
                                        'textFormat': {
                                            'foregroundColor': TEXT_LIGHT,
                                            'fontFamily': 'Google Sans Code',
                                            'fontSize': 10,
                                            'bold': True
                                        },
                                        'horizontalAlignment': 'CENTER',
                                        'borders': {
                                            'left': {'style': 'SOLID_MEDIUM', 'color': GOLD_BORDER},
                                            'right': {'style': 'SOLID', 'color': GREY_BORDER},
                                            'top': {'style': 'SOLID', 'color': GREY_BORDER},
                                            'bottom': {'style': 'SOLID_MEDIUM', 'color': GOLD_BORDER}
                                        }
                                    }
                                },
                                'fields': 'userEnteredFormat'
                            }
                        },
                        # จัดฟอร์แมตแถวใหม่ (G: ยอดเงิน)
                        {
                            'repeatCell': {
                                'range': {
                                    'sheetId': btc_sheet_id,
                                    'startRowIndex': new_month_row_idx - 1,
                                    'endRowIndex': new_month_row_idx,
                                    'startColumnIndex': 6,
                                    'endColumnIndex': 7
                                },
                                'cell': {
                                    'userEnteredFormat': {
                                        'backgroundColor': LIGHT_BG,
                                        'textFormat': {
                                            'foregroundColor': TEXT_DARK,
                                            'fontFamily': 'Google Sans Code',
                                            'fontSize': 10
                                        },
                                        'horizontalAlignment': 'CENTER',
                                        'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0.00'},
                                        'borders': {
                                            'left': {'style': 'SOLID', 'color': GREY_BORDER},
                                            'right': {'style': 'SOLID', 'color': GREY_BORDER},
                                            'top': {'style': 'SOLID', 'color': GREY_BORDER},
                                            'bottom': {'style': 'SOLID_MEDIUM', 'color': GOLD_BORDER}
                                        }
                                    }
                                },
                                'fields': 'userEnteredFormat'
                            }
                        },
                        # จัดฟอร์แมตแถวใหม่ (H: ราคาเฉลี่ย)
                        {
                            'repeatCell': {
                                'range': {
                                    'sheetId': btc_sheet_id,
                                    'startRowIndex': new_month_row_idx - 1,
                                    'endRowIndex': new_month_row_idx,
                                    'startColumnIndex': 7,
                                    'endColumnIndex': 8
                                },
                                'cell': {
                                    'userEnteredFormat': {
                                        'backgroundColor': LIGHT_BG,
                                        'textFormat': {
                                            'foregroundColor': TEXT_DARK,
                                            'fontFamily': 'Google Sans Code',
                                            'fontSize': 10
                                        },
                                        'horizontalAlignment': 'CENTER',
                                        'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0'},
                                        'borders': {
                                            'left': {'style': 'SOLID', 'color': GREY_BORDER},
                                            'right': {'style': 'SOLID', 'color': GREY_BORDER},
                                            'top': {'style': 'SOLID', 'color': GREY_BORDER},
                                            'bottom': {'style': 'SOLID_MEDIUM', 'color': GOLD_BORDER}
                                        }
                                    }
                                },
                                'fields': 'userEnteredFormat'
                            }
                        },
                        # จัดฟอร์แมตแถวใหม่ (I: จำนวน BTC)
                        {
                            'repeatCell': {
                                'range': {
                                    'sheetId': btc_sheet_id,
                                    'startRowIndex': new_month_row_idx - 1,
                                    'endRowIndex': new_month_row_idx,
                                    'startColumnIndex': 8,
                                    'endColumnIndex': 9
                                },
                                'cell': {
                                    'userEnteredFormat': {
                                        'backgroundColor': LIGHT_BG,
                                        'textFormat': {
                                            'foregroundColor': TEXT_DARK,
                                            'fontFamily': 'Google Sans Code',
                                            'fontSize': 10
                                        },
                                        'horizontalAlignment': 'CENTER',
                                        'numberFormat': {'type': 'NUMBER', 'pattern': '0.00000000'},
                                        'borders': {
                                            'left': {'style': 'SOLID', 'color': GREY_BORDER},
                                            'right': {'style': 'SOLID_MEDIUM', 'color': GOLD_BORDER},
                                            'top': {'style': 'SOLID', 'color': GREY_BORDER},
                                            'bottom': {'style': 'SOLID_MEDIUM', 'color': GOLD_BORDER}
                                        }
                                    }
                                },
                                'fields': 'userEnteredFormat'
                            }
                        }
                    ]
                    service.spreadsheets().batchUpdate(spreadsheetId=PORTFOLIO_SPREADSHEET_ID, body={'requests': fmt_reqs}).execute()
                    print("จัดขอบและสีทองของแถวประวัติเรียบร้อย")

                # 6. ล้างข้อมูลตาราง B3:D33
                service.spreadsheets().values().clear(
                    spreadsheetId=PORTFOLIO_SPREADSHEET_ID,
                    range='BTC!B3:D33'
                ).execute()
                print("ล้างข้อมูลตาราง B3:D33 เรียบร้อย")

                # 7. เขียนชื่อเดือนใหม่ใน B1
                service.spreadsheets().values().update(
                    spreadsheetId=PORTFOLIO_SPREADSHEET_ID,
                    range='BTC!B1',
                    valueInputOption='USER_ENTERED',
                    body={'values': [[current_month]]}
                ).execute()
                print(f"เปลี่ยนหัวกระดาษเป็นเดือน '{current_month}' เรียบร้อยแล้ว")
                
    except Exception as e:
        print(f"Error during BTC Auto Rollover: {e}")

def sync_trades():
    print(f"🕒 Starting Trade Sync: {datetime.datetime.now()}")
    state = load_state()
    processed_orders = state.get('processed_orders', [])
    all_trades = []
    
    for sym in ['KUB_THB']:
        trades = get_bitkub_trades(sym)
        for t in trades:
            order_id = str(t.get('txn_id'))
            if t.get('side') == 'buy' and order_id not in processed_orders:
                amount_thb = float(t['amount']); price = float(t['rate'])
                amount_crypto = amount_thb / price if price > 0 else 0
                dt = datetime.datetime.fromtimestamp(t['ts'] / 1000)
                all_trades.append({'order_id': order_id, 'exchange': 'Bitkub', 'date': dt.strftime('%d/%m/%Y'), 'coin': sym.split('_')[0], 'amount_thb': amount_thb, 'price': price, 'amount_crypto': amount_crypto})
                
    for sym in ['BTCTHB', 'ETHTHB', 'SOLTHB', 'BNBTHB', 'XRPTHB', 'ASTERTHB']:
        orders = get_binance_th_trades(sym)
        for o in orders:
            order_id = str(o.get('orderId'))
            if o.get('status') == 'FILLED' and o.get('side') == 'BUY' and order_id not in processed_orders:
                amount_thb = float(o.get('cumulativeQuoteQty', 0))
                amount_crypto = float(o.get('executedQty', 0))
                price = amount_thb / amount_crypto if amount_crypto > 0 else float(o.get('price', 0))
                dt = datetime.datetime.fromtimestamp(o['time'] / 1000)
                all_trades.append({'order_id': order_id, 'exchange': 'Binance TH', 'date': dt.strftime('%d/%m/%Y'), 'coin': sym.replace('THB', ''), 'amount_thb': amount_thb, 'price': price, 'amount_crypto': amount_crypto})
                
    all_trades.sort(key=lambda x: datetime.datetime.strptime(x['date'], '%d/%m/%Y'))
    
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing credentials...")
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials in Trade Sync: {e}")
                return
        else:
            print("Credentials invalid or missing. Run Jane's agent manually to re-authenticate.")
            return

    service = build('sheets', 'v4', credentials=creds)
    
    # --- Auto Month Rollover: แท็บ BTC ---
    check_and_rollover_btc_tab(service)

    if all_trades:
        print(f"✅ Found {len(all_trades)} NEW trades to process!")
        sheet_metadata = service.spreadsheets().get(spreadsheetId=PORTFOLIO_SPREADSHEET_ID).execute()
        success_count = 0
        for t in all_trades:
            if write_to_sheet(service, t, sheet_metadata):
                processed_orders.append(t['order_id'])
                success_count += 1
        if success_count > 0:
            state['processed_orders'] = processed_orders
            save_state(state)
            print("✅ Sync complete and state saved.")
        else:
            print("⚠️ Trades found but none were successfully written.")
    else:
        print("📭 No new trades found.")

    record_portfolio_snapshot_and_update_dashboard(service)

if __name__ == "__main__":
    sync_trades()
