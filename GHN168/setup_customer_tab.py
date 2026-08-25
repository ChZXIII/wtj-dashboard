#!/usr/bin/env python3
"""
================================================================================
GHN168 - Google Sheets Customer Tab Setup Script
================================================================================
Author: Q (Lead Backend Developer, ChZ Agent Corp)
Purpose:
  1. Authenticate via OAuth Token in credentials/token_sheets.json
  2. Connect to GHN168 Master Spreadsheet ID: 1vIc7kxO9q_FN2mmgyAYf8aly9lMdPRp7onqRaGx8y20
  3. Create or verify 'ข้อมูลลูกค้า' tab
  4. Write standard 10-column headers:
     - รหัสลูกค้า (Customer ID)
     - ชื่อบริษัท / ลูกค้า (Customer Name)
     - เลขประจำตัวผู้เสียภาษี (Tax ID)
     - รหัสสาขา (Branch Code)
     - ที่อยู่จดทะเบียน (Address)
     - เบอร์โทรศัพท์ (Phone)
     - อีเมล (Email)
     - ผู้ติดต่อ (Contact Person)
     - วันที่บันทึก (Created Date)
     - หมายเหตุ (Remarks)
  5. Apply professional styling:
     - Header background: Indigo #3730a3 (RGB: 55, 48, 163)
     - Header text: White #ffffff, Bold, Font: Prompt / Inter
     - Freeze top row (Frozen Header)
     - Row height: 36px header, 28px data
     - Column auto-resizing / optimal width
     - Alternating row background (#ffffff / #f8fafc)
     - Light gray grid borders (#e2e8f0)
  6. Insert initial sample customer records (TW Systems, Beyond Media, Chiang Mai Media, River Hotel)
================================================================================
"""

import os
import sys
from pathlib import Path
from datetime import datetime

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Configuration Paths
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
CREDENTIALS_DIR = ROOT_DIR / "credentials"
TOKEN_PATH = CREDENTIALS_DIR / "token_sheets.json"

SPREADSHEET_ID = "1vIc7kxO9q_FN2mmgyAYf8aly9lMdPRp7onqRaGx8y20"
TAB_NAME = "ข้อมูลลูกค้า"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# 10 Standard Columns
CUSTOMER_HEADERS = [
    "รหัสลูกค้า (Customer ID)",
    "ชื่อบริษัท / ลูกค้า (Customer Name)",
    "เลขประจำตัวผู้เสียภาษี (Tax ID)",
    "รหัสสาขา (Branch Code)",
    "ที่อยู่จดทะเบียน (Address)",
    "เบอร์โทรศัพท์ (Phone)",
    "อีเมล (Email)",
    "ผู้ติดต่อ (Contact Person)",
    "วันที่บันทึก (Created Date)",
    "หมายเหตุ (Remarks)"
]

# 10 Real Customers from QT / IV / RE Documents
ALL_10_CUSTOMERS = [
    [
        "CUST-001",
        "บริษัท เชียงใหม่มีเดีย จำกัด",
        "'0505560000123",
        "'00000'",
        "123 ถ.ห้วยแก้ว ต.ช้างเผือก อ.เมือง จ.เชียงใหม่ 50300",
        "081-1111111",
        "contact@cmmedia.co.th",
        "คุณสมชาย",
        "01/01/2026",
        "ลูกค้าประจำ งานผลิตคลิปวิดีโอโปรโมทสินค้าและสตูดิโอ"
    ],
    [
        "CUST-002",
        "บริษัท นอร์ทเทิร์น อินโนเวชั่น แล็บ จำกัด",
        "'0505566001234",
        "'00000'",
        "88/9 หมู่ 5 ต.ช้างเผือก อ.เมือง จ.เชียงใหม่ 50300",
        "081-987-6543",
        "contact@northernlab.co.th",
        "คุณนิวัฒน์",
        "15/01/2026",
        "ลูกค้างานผลิตคลิปวิดีโอโปรโมทสินค้าและสื่อโฆษณาออนไลน์"
    ],
    [
        "CUST-003",
        "บริษัท ไอเด็กซ์ ไมซ์ จำกัด",
        "'0505555007201",
        "'00000'",
        "500/60 หมู่ที่ 2 ต.แม่เหียะ อ.เมือง จ.เชียงใหม่ 50100",
        "053-888999",
        "contact@idexmice.com",
        "คุณนวพร (คุณหอม)",
        "25/06/2026",
        "ลูกค้าประจำ งานอีเวนต์, ถ่ายทำวิดีโอ 2 กล้อง, ภาพนิ่ง และเช่าอุปกรณ์"
    ],
    [
        "CUST-004",
        "บริษัท อินดีด ครีเอชั่น จำกัด",
        "'0505545004373",
        "'00000'",
        "500/61 หมู่ที่ 2 ต.แม่เหียะ อ.เมือง จ.เชียงใหม่ 50100",
        "081-2345678",
        "contact@indeedcreation.co.th",
        "คุณเอกชัย",
        "02/07/2026",
        "ลูกค้างานเช่าไฟสตูดิโอ intercon และอุปกรณ์กองถ่าย"
    ],
    [
        "CUST-005",
        "บริษัท ลานนา ครีเอทีฟ สตูดิโอ จำกัด",
        "'0505560000456",
        "'00000'",
        "88 ถ.นิมมานเหมินท์ ต.สุเทพ อ.เมือง จ.เชียงใหม่ 50200",
        "082-2222222",
        "contact@lannacreative.co.th",
        "คุณลานนา",
        "03/07/2026",
        "ลูกค้างานบริการตัดต่อและเกรดสีภาพยนตร์สั้น"
    ],
    [
        "CUST-006",
        "บริษัท แคทไซคลิ่ง จำกัด",
        "'0505565009988",
        "'00000'",
        "123 ถ.เชียงใหม่-ลำพูน ต.วัดเกต อ.เมือง จ.เชียงใหม่ 50000",
        "053-111222",
        "contact@catcycling.co.th",
        "คุณกมล",
        "27/06/2026",
        "ลูกค้างานถ่าย VDO สัมภาษณ์ 2 กล้อง พร้อมตัดต่อ"
    ],
    [
        "CUST-007",
        "บริษัท พิงค์นคร พร็อพเพอร์ตี้ จำกัด",
        "'0505560000789",
        "'00000'",
        "99 ถ.ซุปเปอร์ไฮเวย์ ต.หนองป่าครั่ง อ.เมือง จ.เชียงใหม่ 50000",
        "083-3333333",
        "contact@pinknakorn.co.th",
        "คุณชัชชัย",
        "18/08/2026",
        "ลูกค้างานผลิตวิดีโอ Virtual Tour โครงการบ้านหรู"
    ],
    [
        "CUST-008",
        "โรงแรม เดอะริเวอร์ เชียงใหม่",
        "'0505560000888",
        "'00000'",
        "12 ถ.เจริญราษฎร์ ต.วัดเกต อ.เมือง จ.เชียงใหม่ 50000",
        "084-4444444",
        "riverhotel@cmriver.com",
        "คุณธารา",
        "18/01/2026",
        "ลูกค้างานถ่ายทำภาพนิ่งและ Reels โรงแรม"
    ],
    [
        "CUST-009",
        "บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด",
        "'0505568016475",
        "'00000'",
        "21/6 หมู่ 2 ต.ริมใต้ อ.แม่ริม จ.เชียงใหม่ 50180",
        "092-419-3953",
        "m-cool-house@hotmail.com",
        "คุณเอกรินทร์",
        "10/02/2026",
        "คู่ค้า/ลูกค้าประจำ งานออแกไนซ์และอีเวนต์สตูดิโอ"
    ],
    [
        "CUST-010",
        "บริษัท ล้านนา ช็อปปิ้ง จำกัด",
        "'0505569008888",
        "'00000'",
        "99 ถ.นิมมานเหมินท์ ต.สุเทพ อ.เมือง จ.เชียงใหม่ 50200",
        "084-5556677",
        "contact@lannashopping.co.th",
        "คุณนฤมล",
        "22/08/2026",
        "ลูกค้างานบริการถ่ายภาพนิ่งและ Reels โซเชียลมีเดีย"
    ]
]
SAMPLE_CUSTOMERS = ALL_10_CUSTOMERS


def get_sheets_service():
    """Load OAuth credentials and build Google Sheets API service."""
    if not TOKEN_PATH.is_file():
        raise FileNotFoundError(f"OAuth token file not found at: {TOKEN_PATH}")

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired OAuth token...")
            creds.refresh(Request())
            # Save the refreshed token back
            with open(TOKEN_PATH, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            print("✅ Token refreshed and saved successfully.")
        else:
            raise RuntimeError("OAuth credentials invalid and cannot be refreshed.")

    return build("sheets", "v4", credentials=creds)


def setup_customer_sheet():
    """Create and beautify 'ข้อมูลลูกค้า' tab with 10 standard columns and sample data."""
    print("=" * 70)
    print(f"🚀 GHN168 Customer Tab Setup starting on Spreadsheet: {SPREADSHEET_ID}")
    print("=" * 70)

    service = get_sheets_service()
    sheets_api = service.spreadsheets()

    # Step 1: Fetch spreadsheet metadata
    spreadsheet = sheets_api.get(spreadsheetId=SPREADSHEET_ID).execute()
    sheet_list = spreadsheet.get("sheets", [])
    print(f"📄 Connected to Spreadsheet: '{spreadsheet.get('properties', {}).get('title')}'")

    target_sheet_id = None
    existing_sheets = []
    for s in sheet_list:
        props = s.get("properties", {})
        existing_sheets.append(props.get("title"))
        if props.get("title") == TAB_NAME:
            target_sheet_id = props.get("sheetId")

    print(f"📋 Current tabs found: {', '.join(existing_sheets)}")

    # Step 2: Create 'ข้อมูลลูกค้า' tab if not present
    if target_sheet_id is None:
        print(f"➕ Tab '{TAB_NAME}' not found. Creating new tab...")
        add_sheet_request = {
            "addSheet": {
                "properties": {
                    "title": TAB_NAME,
                    "gridProperties": {
                        "frozenRowCount": 1
                    }
                }
            }
        }
        res = sheets_api.batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": [add_sheet_request]}
        ).execute()
        target_sheet_id = res["replies"][0]["addSheet"]["properties"]["sheetId"]
        print(f"✅ Created tab '{TAB_NAME}' with sheetId: {target_sheet_id}")
    else:
        print(f"ℹ️ Found existing tab '{TAB_NAME}' (sheetId: {target_sheet_id})")

    # Step 3: Populate header and sample data
    all_rows = [CUSTOMER_HEADERS] + SAMPLE_CUSTOMERS
    val_range = f"'{TAB_NAME}'!A1:J{len(all_rows)}"

    print(f"📝 Writing headers and {len(SAMPLE_CUSTOMERS)} sample rows to {val_range}...")
    sheets_api.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=val_range,
        valueInputOption="USER_ENTERED",
        body={"values": all_rows}
    ).execute()
    print("✅ Values written successfully.")

    # Step 4: Apply styling via batchUpdate
    # Indigo color #3730a3 => R: 55/255=0.2157, G: 48/255=0.1882, B: 163/255=0.6392
    header_bg_color = {"red": 55 / 255.0, "green": 48 / 255.0, "blue": 163 / 255.0}
    header_text_color = {"red": 1.0, "green": 1.0, "blue": 1.0}
    border_color = {"red": 226 / 255.0, "green": 232 / 255.0, "blue": 240 / 255.0}
    alt_row_color = {"red": 248 / 255.0, "green": 250 / 255.0, "blue": 252 / 255.0}

    total_rows = len(all_rows)
    total_cols = len(CUSTOMER_HEADERS)

    requests = [
        # 4.1 Freeze row 1
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": target_sheet_id,
                    "gridProperties": {
                        "frozenRowCount": 1
                    }
                },
                "fields": "gridProperties.frozenRowCount"
            }
        },
        # 4.2 Format Header (Row 0)
        {
            "repeatCell": {
                "range": {
                    "sheetId": target_sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": total_cols
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": header_bg_color,
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "textFormat": {
                            "foregroundColor": header_text_color,
                            "fontSize": 10,
                            "bold": True,
                            "fontFamily": "Prompt"
                        },
                        "wrapStrategy": "CLIP"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment,textFormat,wrapStrategy)"
            }
        },
        # 4.3 Set Header Row Height (36px)
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": target_sheet_id,
                    "dimension": "ROWS",
                    "startIndex": 0,
                    "endIndex": 1
                },
                "properties": {
                    "pixelSize": 36
                },
                "fields": "pixelSize"
            }
        },
        # 4.4 Set Data Rows Height (28px)
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": target_sheet_id,
                    "dimension": "ROWS",
                    "startIndex": 1,
                    "endIndex": total_rows
                },
                "properties": {
                    "pixelSize": 28
                },
                "fields": "pixelSize"
            }
        },
        # 4.5 Format Data Cells (Font Inter, Size 10, Vertical Center)
        {
            "repeatCell": {
                "range": {
                    "sheetId": target_sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": total_rows,
                    "startColumnIndex": 0,
                    "endColumnIndex": total_cols
                },
                "cell": {
                    "userEnteredFormat": {
                        "verticalAlignment": "MIDDLE",
                        "textFormat": {
                            "fontSize": 10,
                            "fontFamily": "Inter"
                        }
                    }
                },
                "fields": "userEnteredFormat(verticalAlignment,textFormat)"
            }
        },
        # 4.6 Alignments for specific columns:
        # Col 0 (Customer ID), Col 2 (Tax ID), Col 3 (Branch), Col 8 (Date) -> Center
        {
            "repeatCell": {
                "range": {
                    "sheetId": target_sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": total_rows,
                    "startColumnIndex": 0,
                    "endColumnIndex": 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat.horizontalAlignment"
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": target_sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": total_rows,
                    "startColumnIndex": 2,
                    "endColumnIndex": 4
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat.horizontalAlignment"
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": target_sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": total_rows,
                    "startColumnIndex": 8,
                    "endColumnIndex": 9
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat.horizontalAlignment"
            }
        },
        # 4.7 Grid Borders for data
        {
            "updateBorders": {
                "range": {
                    "sheetId": target_sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": total_rows,
                    "startColumnIndex": 0,
                    "endColumnIndex": total_cols
                },
                "top": {"style": "SOLID", "width": 1, "color": border_color},
                "bottom": {"style": "SOLID", "width": 1, "color": border_color},
                "left": {"style": "SOLID", "width": 1, "color": border_color},
                "right": {"style": "SOLID", "width": 1, "color": border_color},
                "innerHorizontal": {"style": "SOLID", "width": 1, "color": border_color},
                "innerVertical": {"style": "SOLID", "width": 1, "color": border_color}
            }
        },
        # 4.8 Auto-resize column widths
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": target_sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": total_cols
                }
            }
        }
    ]

    # Alternating row background colors for even rows
    for r in range(1, total_rows):
        if r % 2 == 1:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": target_sheet_id,
                        "startRowIndex": r,
                        "endRowIndex": r + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": total_cols
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": alt_row_color
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            })

    # Explicit minimum column widths for optimal readability
    col_widths = {
        0: 130,  # Customer ID
        1: 260,  # Customer Name
        2: 160,  # Tax ID
        3: 100,  # Branch Code
        4: 340,  # Address
        5: 140,  # Phone
        6: 220,  # Email
        7: 150,  # Contact Person
        8: 130,  # Created Date
        9: 250   # Remarks
    }

    for col_idx, width in col_widths.items():
        requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": target_sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": col_idx,
                    "endIndex": col_idx + 1
                },
                "properties": {
                    "pixelSize": width
                },
                "fields": "pixelSize"
            }
        })

    print(f"🎨 Applying {len(requests)} formatting requests (Indigo styling, frozen row, custom widths)...")
    sheets_api.batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={"requests": requests}
    ).execute()

    print("=" * 70)
    print(f"🎉 SUCCESS! 'ข้อมูลลูกค้า' tab is ready on Google Sheets!")
    print(f"🔗 Spreadsheet URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    print("=" * 70)
    return {
        "status": "success",
        "sheet_id": target_sheet_id,
        "spreadsheet_id": SPREADSHEET_ID,
        "tab_name": TAB_NAME,
        "total_columns": total_cols,
        "total_rows": total_rows
    }


def sync_customer_tab_via_gas():
    """Sync all 10 customer records via GAS Webhook (type: overwrite)."""
    import requests
    gas_url = os.environ.get("GAS_SCRIPT_URL", "https://script.google.com/macros/s/AKfycbylMN5ot9w2_LfD4hgwnmTz4y7dSRLKdR-__0THDVzDivW-lUeF0YG25Hj3apCf0lWx/exec")
    payload = {
        "type": "overwrite",
        "spreadsheetId": SPREADSHEET_ID,
        "sheetName": TAB_NAME,
        "headers": CUSTOMER_HEADERS,
        "rows": ALL_10_CUSTOMERS
    }
    print(f"📡 Syncing {len(ALL_10_CUSTOMERS)} customers to Google Sheets tab '{TAB_NAME}' via GAS Webhook...")
    res = requests.post(gas_url, json=payload, timeout=30)
    if res.status_code == 200:
        data = res.json()
        print(f"✅ GAS Webhook Sync Result: {data.get('message', 'Success')}")
        return {"status": "success", "message": data.get("message")}
    else:
        print(f"⚠️ GAS Webhook returned status {res.status_code}: {res.text}")
        return {"status": "error", "message": f"HTTP {res.status_code}"}


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 GHN168 CUSTOMER DATABASE SYNC PIPELINE (10 Real Customers)")
    print("=" * 70)
    try:
        res = sync_customer_tab_via_gas()
        if res.get("status") != "success":
            print("🔄 Attempting direct Google Sheets API setup...")
            setup_customer_sheet()
    except Exception as e:
        print(f"⚠️ Webhook error: {e}. Trying direct Google Sheets API...")
        try:
            setup_customer_sheet()
        except Exception as e2:
            print(f"❌ Error occurred: {e2}", file=sys.stderr)
            sys.exit(1)

