import os
import os.path
import calendar
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ค้นหาตำแหน่งโฟลเดอร์หลักของโปรเจกต์แบบไดนามิก
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

MONTHS_TH = {
    '01': 'ม.ค.', '02': 'ก.พ.', '03': 'มี.ค.', '04': 'เม.ย.',
    '05': 'พ.ค.', '06': 'มิ.ย.', '07': 'ก.ค.', '08': 'ส.ค.',
    '09': 'ก.ย.', '10': 'ต.ค.', '11': 'พ.ย.', '12': 'ธ.ค.'
}

def get_sheets_service():
    creds = None
    token_path = os.path.join(PROJECT_ROOT, 'credentials', 'token_sheets.json')
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("ไม่พบไฟล์สิทธิ์การเชื่อมต่อ Google Sheets ที่ใช้ได้ กรุณารีออโธไรซ์ใหม่")
    return build('sheets', 'v4', credentials=creds)

def main():
    print("กำลังเริ่มต้นการเชื่อมต่อ Google Sheets API...")
    try:
        service = get_sheets_service()
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึงสิทธิ์เชื่อมต่อ: {e}")
        return

    # 1. ตรวจสอบว่ามีการส่ง ID สเปรดชีตมาหรือไม่
    import sys
    spreadsheet_id = None
    if len(sys.argv) > 1:
        spreadsheet_id = sys.argv[1]
        
    is_existing = False
    if spreadsheet_id:
        print(f"พบ ID สเปรดชีตเดิมจากอาร์กิวเมนต์: {spreadsheet_id} แก กำลังทำการเชื่อมต่อ...")
        try:
            meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            is_existing = True
            print("เชื่อมต่อสเปรดชีตเดิมสำเร็จแล้วแก! จะทำการแก้ไขในชีตเดิมนะ")
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการดึงข้อมูลชีตเดิม: {e}")
            print("ระบบจะทำการสร้างชีตใหม่แทน...")
            spreadsheet_id = None

    if not spreadsheet_id:
        # สร้าง Google Spreadsheet ใหม่ชื่อ "รายรับ รายจ่าย Feltz Studio 2026"
        spreadsheet_body = {
            'properties': {
                'title': 'รายรับ รายจ่าย Feltz Studio 2026'
            }
        }
        print("กำลังสร้าง Spreadsheet ใหม่...")
        spreadsheet = service.spreadsheets().create(body=spreadsheet_body, fields='spreadsheetId').execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')
        print(f"สร้างสำเร็จแล้วแก! Spreadsheet ID: {spreadsheet_id}")
        print(f"ลิงก์สำหรับเข้าดู: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")

    # 2. ตรวจสอบและสร้างแท็บที่ยังไม่มี
    print("กำลังตรวจสอบแท็บใน Spreadsheet...")
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = meta.get('sheets', [])
    existing_titles = {s['properties']['title'] for s in sheets}
    
    requests = []
    months_keys = sorted(list(MONTHS_TH.keys())) # ['01', '02', ..., '12']
    
    first_sheet_id = sheets[0]['properties']['sheetId'] if sheets else 0
    first_sheet_title = sheets[0]['properties']['title'] if sheets else 'Sheet1'
    
    # ถ้า ม.ค. ยังไม่มี และมีแผ่นงานแรกที่ชื่ออื่น (เช่น Sheet1) เราจะเปลี่ยนชื่อแผ่นงานแรกเป็น ม.ค.
    if 'ม.ค.' not in existing_titles:
        requests.append({
            'updateSheetProperties': {
                'properties': {
                    'sheetId': first_sheet_id,
                    'title': 'ม.ค.'
                },
                'fields': 'title'
            }
        })
        existing_titles.add('ม.ค.')
        if first_sheet_title in existing_titles:
            existing_titles.remove(first_sheet_title)

    for m_num in months_keys:
        m_title = MONTHS_TH[m_num]
        if m_title not in existing_titles:
            requests.append({
                'addSheet': {
                    'properties': {
                        'title': m_title
                    }
                }
            })
            
    if 'ตั้งค่า Fix Cost' not in existing_titles:
        requests.append({
            'addSheet': {
                'properties': {
                    'title': 'ตั้งค่า Fix Cost'
                }
            }
        })
        
    if requests:
        print("กำลังสร้าง/เปลี่ยนชื่อแท็บที่ขาดไป...")
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={'requests': requests}).execute()

    # ดึง metadata เพื่อหา sheetId ของแต่ละแท็บเพื่อส่งฟอร์แมตในขั้นตอนถัดไป
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = meta.get('sheets', [])
    sheet_map = {s['properties']['title']: s['properties']['sheetId'] for s in sheets}

    # 3. หยอดข้อมูลปฏิทินรายวันและสูตรคำนวณลงในแต่ละแท็บ
    print("กำลังเติมตารางปฏิทินรายวันและสูตรคำนวณอัตโนมัติในทุกแท็บ...")
    
    format_requests = []
    
    for m_num in months_keys:
        m_title = MONTHS_TH[m_num]
        sheet_id = sheet_map[m_title]
        num_days = calendar.monthrange(2026, int(m_num))[1]
        
        # ดึงข้อมูลเดิมที่มีอยู่แล้วในแท็บนี้ (ถ้ามี) เพื่อถนอมข้อมูลบันทึกของแก (ดึงสูตรดิบมาใช้)
        existing_values = []
        if is_existing:
            try:
                res = service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{m_title}'!A1:G100",
                    valueRenderOption='FORMULA'
                ).execute()
                existing_values = res.get('values', [])
            except Exception:
                pass
        
        # เตรียมตารางข้อมูล
        values = [
            ['วันที่', 'รายละเอียดงาน', 'รายรับ (บาท)', 'รายละเอียดรายจ่าย', 'รายจ่าย (บาท)', 'หัก ณ ที่จ่าย 3% (บาท)', 'เงินเก็บ 10% (บาท)']
        ]
        
        # เติมข้อมูลรายวัน
        for day in range(1, num_days + 1):
            row_idx = day + 1 # row index (1-based, index 1 คือ header)
            date_str = f"{day:02d}/{m_num}/2026"
            
            # ถนอมค่าเดิมที่แกคีย์ไว้
            orig_desc = ''
            orig_income = ''
            orig_exp_desc = ''
            orig_expense = ''
            orig_tax = f"=C{row_idx}*3%"
            orig_savings = f"=C{row_idx}*10%"
            
            if len(existing_values) > day: # row_idx - 1
                row_data = existing_values[day]
                if len(row_data) > 1: orig_desc = row_data[1]
                if len(row_data) > 2: orig_income = row_data[2]
                if len(row_data) > 3: orig_exp_desc = row_data[3]
                if len(row_data) > 4: orig_expense = row_data[4]
                if len(row_data) > 5: orig_tax = row_data[5]
                if len(row_data) > 6: orig_savings = row_data[6]
                
            values.append([date_str, orig_desc, orig_income, orig_exp_desc, orig_expense, orig_tax, orig_savings])
            
        # เติมแถวว่าง 1 แถวเพื่อเว้นระยะ
        values.append(['', '', '', '', '', '', ''])
        
        # แถวยอดสรุปท้ายเดือน
        summary_row_idx = num_days + 3
        total_income_formula = f"=SUM(C2:C{num_days+1})"
        total_expense_formula = f"=SUM(E2:E{num_days+1})"
        total_tax_formula = f"=SUM(F2:F{num_days+1})"
        total_savings_formula = f"=SUM(G2:G{num_days+1})"
        
        # แถวแรก: ยอดรวมทั้งเดือน
        values.append(['ยอดรวมทั้งเดือน', '', total_income_formula, '', total_expense_formula, total_tax_formula, total_savings_formula])
        
        # แถวสอง: ค่าคอมมิชชัน (เขียนสูตรลงคอลัมน์ E รายจ่าย)
        commission_formula = f"=IF(C{summary_row_idx}<=70000, C{summary_row_idx}*10%, IF(C{summary_row_idx}<=100000, C{summary_row_idx}*15%, C{summary_row_idx}*20%))"
        values.append(['ค่าคอมมิชชัน', '', '', '', commission_formula, '', ''])
        
        # แถวสาม: รายได้สุทธิ (สูตรแบบใหม่ C_Total - E_Total - E_Commission เขียนลงคอลัมน์ C)
        net_income_formula = f"=C{summary_row_idx}-E{summary_row_idx}-E{summary_row_idx+1}"
        values.append(['รายได้สุทธิ', '', net_income_formula, '', '', '', ''])
        
        # แถวสี่: ยอดรวมเงินเก็บสะสม 10% (สูตรเดิมดึงจาก G_Total เขียนลงคอลัมน์ C)
        values.append(['ยอดรวมเงินเก็บสะสม 10%', '', f"=G{summary_row_idx}", '', '', '', ''])
        
        # แถวห้า: ยอดยกมาจากเดือนก่อน (เขียนลงคอลัมน์ C)
        if m_num == '01':
            carryover_formula = "0"
        else:
            prev_m_num = months_keys[months_keys.index(m_num) - 1]
            prev_m_title = MONTHS_TH[prev_m_num]
            prev_num_days = calendar.monthrange(2026, int(prev_m_num))[1]
            carryover_formula = f"='{prev_m_title}'!C{prev_num_days + 8}"
        values.append(['ยอดยกมาจากเดือนก่อน', '', carryover_formula, '', '', '', ''])
        
        # แถวหก: รายได้สุทธิสะสมรวม (เขียนลงคอลัมน์ C)
        accum_net_formula = f"=C{summary_row_idx+2}+C{summary_row_idx+4}"
        values.append(['รายได้สุทธิสะสมรวม', '', accum_net_formula, '', '', '', ''])
        
        # อัปเดตข้อมูลลงชีตในแท็บเดือนนั้นๆ
        update_range = f"'{m_title}'!A1:G{len(values)}"
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=update_range,
            valueInputOption='USER_ENTERED',
            body={'values': values}
        ).execute()

        # 4. เพิ่มคำขอจัดแต่งรูปแบบ (Formatting Requests) ให้ตารางดูสวยงาม พรีเมียม
        # ตั้งค่าฟอนต์ Google Sans Code เป็นมาตรฐานทั้งแผ่น
        format_requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id
                },
                'cell': {
                    'userEnteredFormat': {
                        'textFormat': {
                            'fontFamily': 'Google Sans Code'
                        }
                    }
                },
                'fields': 'userEnteredFormat.textFormat.fontFamily'
            }
        })

        # ฟอร์แมต Header (Bold, Slate Background, White Text)
        format_requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                    'startColumnIndex': 0,
                    'endColumnIndex': 7
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.09, 'green': 0.15, 'blue': 0.27}, # Slate 800 (#172554 equivalent)
                        'textFormat': {
                            'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0},
                            'bold': True,
                            'fontSize': 10,
                            'fontFamily': 'Google Sans Code'
                        },
                        'horizontalAlignment': 'CENTER'
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
            }
        })
        
        # 1. จัดสีพื้นหลังให้แต่ละกลุ่มคอลัมน์ (Column Group Backgrounds)
        # คอลัมน์ A: วันที่ (Slate 50)
        format_requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 1,
                    'endRowIndex': num_days + 1,
                    'startColumnIndex': 0,
                    'endColumnIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.97, 'green': 0.98, 'blue': 0.99}
                    }
                },
                'fields': 'userEnteredFormat.backgroundColor'
            }
        })
        
        # คอลัมน์ B & C: รายรับ (Emerald 50)
        format_requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 1,
                    'endRowIndex': num_days + 1,
                    'startColumnIndex': 1,
                    'endColumnIndex': 3
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.93, 'green': 0.99, 'blue': 0.96}
                    }
                },
                'fields': 'userEnteredFormat.backgroundColor'
            }
        })
        
        # คอลัมน์ D & E: รายจ่าย (Red 50)
        format_requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 1,
                    'endRowIndex': num_days + 1,
                    'startColumnIndex': 3,
                    'endColumnIndex': 5
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 1.0, 'green': 0.96, 'blue': 0.96}
                    }
                },
                'fields': 'userEnteredFormat.backgroundColor'
            }
        })
        
        # คอลัมน์ F & G: หัก ณ ที่จ่าย & เงินเก็บ (Sky 50)
        format_requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 1,
                    'endRowIndex': num_days + 1,
                    'startColumnIndex': 5,
                    'endColumnIndex': 7
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.94, 'green': 0.98, 'blue': 1.0}
                    }
                },
                'fields': 'userEnteredFormat.backgroundColor'
            }
        })
        
        # 2. ไฮไลต์แถบสรุปท้ายตาราง (Summary Rows Background - Slate 100)
        format_requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': summary_row_idx - 1,
                    'endRowIndex': summary_row_idx + 6,
                    'startColumnIndex': 0,
                    'endColumnIndex': 7
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.95, 'green': 0.96, 'blue': 0.98}
                    }
                },
                'fields': 'userEnteredFormat.backgroundColor'
            }
        })

        # 3. ตีเส้นตารางสีเทาบางเฉียบ (Explicit Thin Gridlines)
        format_requests.append({
            'updateBorders': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': num_days + 8,
                    'startColumnIndex': 0,
                    'endColumnIndex': 7
                },
                'top': {'style': 'SOLID', 'width': 1, 'color': {'red': 0.88, 'green': 0.91, 'blue': 0.94}},
                'bottom': {'style': 'SOLID', 'width': 1, 'color': {'red': 0.88, 'green': 0.91, 'blue': 0.94}},
                'left': {'style': 'SOLID', 'width': 1, 'color': {'red': 0.88, 'green': 0.91, 'blue': 0.94}},
                'right': {'style': 'SOLID', 'width': 1, 'color': {'red': 0.88, 'green': 0.91, 'blue': 0.94}},
                'innerHorizontal': {'style': 'SOLID', 'width': 1, 'color': {'red': 0.88, 'green': 0.91, 'blue': 0.94}},
                'innerVertical': {'style': 'SOLID', 'width': 1, 'color': {'red': 0.88, 'green': 0.91, 'blue': 0.94}}
            }
        })
        
        # จัดตัวหนังสือคอลัมน์ A (วันที่) ให้อยู่กึ่งกลาง
        format_requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 1,
                    'endRowIndex': num_days + 1,
                    'startColumnIndex': 0,
                    'endColumnIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'horizontalAlignment': 'CENTER'
                    }
                },
                'fields': 'userEnteredFormat(horizontalAlignment)'
            }
        })

        # ฟอร์แมตตัวเลขสกุลเงินสำหรับรายได้ (คอลัมน์ C)
        format_requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 1,
                    'endRowIndex': num_days + 8,
                    'startColumnIndex': 2,
                    'endColumnIndex': 3
                },
                'cell': {
                    'userEnteredFormat': {
                        'numberFormat': {
                            'type': 'NUMBER',
                            'pattern': '#,##0.00'
                        }
                    }
                },
                'fields': 'userEnteredFormat.numberFormat'
            }
        })

        # ฟอร์แมตตัวเลขสกุลเงินสำหรับรายจ่าย, หักภาษี และเงินเก็บ (คอลัมน์ E, F, G)
        format_requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 1,
                    'endRowIndex': num_days + 8,
                    'startColumnIndex': 4,
                    'endColumnIndex': 7
                },
                'cell': {
                    'userEnteredFormat': {
                        'numberFormat': {
                            'type': 'NUMBER',
                            'pattern': '#,##0.00'
                        }
                    }
                },
                'fields': 'userEnteredFormat.numberFormat'
            }
        })

        # ฟอร์แมตแถวยอดรวม (ทำให้หนา)
        format_requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': summary_row_idx - 1,
                    'endRowIndex': summary_row_idx + 6,
                    'startColumnIndex': 0,
                    'endColumnIndex': 7
                },
                'cell': {
                    'userEnteredFormat': {
                        'textFormat': {
                            'bold': True
                        }
                    }
                },
                'fields': 'userEnteredFormat.textFormat.bold'
            }
        })
        
    # ดึงข้อมูลเดิมของแท็บ ตั้งค่า Fix Cost
    fix_cost_title = 'ตั้งค่า Fix Cost'
    fix_cost_sheet_id = sheet_map[fix_cost_title]
    fix_cost_existing_values = []
    if is_existing:
        try:
            res = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{fix_cost_title}'!A1:B20"
            ).execute()
            fix_cost_existing_values = res.get('values', [])
        except Exception:
            pass
            
    if len(fix_cost_existing_values) > 1:
        fix_cost_values = fix_cost_existing_values
        fix_cost_values[0] = ['รายการ', 'จำนวนเงิน (บาท)'] # ตอกย้ำหัวตารางให้ตรง
    else:
        fix_cost_values = [
            ['รายการ', 'จำนวนเงิน (บาท)'],
            ['ค่า Adobe Photography Plan', 380],
            ['Drop Box', 500],
            ['Internet', 1400],
            ['เงินกู้สตูดิโอ', 9000],
            ['เงินเดือนเก่ง', 25000],
            ['เงินเดือนมด', 10000]
        ]
    
    update_range = f"'{fix_cost_title}'!A1:B{len(fix_cost_values)}"
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=update_range,
        valueInputOption='USER_ENTERED',
        body={'values': fix_cost_values}
    ).execute()

    # ตั้งค่าฟอนต์ Google Sans Code เป็นมาตรฐานทั้งแผ่นสำหรับแท็บตั้งค่า Fix Cost
    format_requests.append({
        'repeatCell': {
            'range': {
                'sheetId': fix_cost_sheet_id
            },
            'cell': {
                'userEnteredFormat': {
                    'textFormat': {
                        'fontFamily': 'Google Sans Code'
                    }
                }
            },
            'fields': 'userEnteredFormat.textFormat.fontFamily'
        }
    })

    # ฟอร์แมต Header สำหรับแท็บ 'ตั้งค่า Fix Cost'
    format_requests.append({
        'repeatCell': {
            'range': {
                'sheetId': fix_cost_sheet_id,
                'startRowIndex': 0,
                'endRowIndex': 1,
                'startColumnIndex': 0,
                'endColumnIndex': 2
            },
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': {'red': 0.09, 'green': 0.15, 'blue': 0.27},
                    'textFormat': {
                        'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0},
                        'bold': True,
                        'fontSize': 10,
                        'fontFamily': 'Google Sans Code'
                    },
                    'horizontalAlignment': 'CENTER'
                }
            },
            'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
        }
    })
    
    # ฟอร์แมตตัวเลขคอลัมน์ B สำหรับแท็บ 'ตั้งค่า Fix Cost'
    format_requests.append({
        'repeatCell': {
            'range': {
                'sheetId': fix_cost_sheet_id,
                'startRowIndex': 1,
                'endRowIndex': 7,
                'startColumnIndex': 1,
                'endColumnIndex': 2
            },
            'cell': {
                'userEnteredFormat': {
                    'numberFormat': {
                        'type': 'NUMBER',
                        'pattern': '#,##0.00'
                    }
                }
            },
            'fields': 'userEnteredFormat.numberFormat'
        }
    })

    # ยิงจัดฟอร์แมตทั้งหมดในรอบเดียว
    if format_requests:
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={'requests': format_requests}).execute()
        
    print("จัดแต่งสีสันและฟอร์แมตตัวเลขตารางรายรับและแท็บตั้งค่า Fix Cost เสร็จสิ้นเรียบร้อยแล้วแก! ✅")
    print(f"\nสรุปข้อมูลชีตรายรับตัวใหม่ของแก:")
    print(f"ID ชีตทั่วไป: {spreadsheet_id}")

if __name__ == '__main__':
    main()
