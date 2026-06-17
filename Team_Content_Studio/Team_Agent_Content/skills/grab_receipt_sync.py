import os
import os.path
import subprocess
import re
import datetime

# ค้นหาตำแหน่งโฟลเดอร์หลักของโปรเจกต์แบบไดนามิก
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)
import calendar
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = '1Uhpj9avRUogJLE6pplkhNsMvTgYFLtX93vqe5CPNjE0'
SAVINGS_SPREADSHEET_ID = '1YkKiRQ0eRzH9gMr-wM8TwfLv8BdTxoT04GSruG9aQ9s'

MONTHS_TH = {
    '01': 'ม.ค.', '02': 'ก.พ.', '03': 'มี.ค.', '04': 'เม.ย.',
    '05': 'พ.ค.', '06': 'มิ.ย.', '07': 'ก.ค.', '08': 'ส.ค.',
    '09': 'ก.ย.', '10': 'ต.ค.', '11': 'พ.ย.', '12': 'ธ.ค.'
}

def col_num_to_letter(n):
    string = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string

def get_data_from_notes():
    script = '''
    tell application "Notes"
        set noteList to notes whose name contains "Grab Data"
        if (count of noteList) > 0 then
            set targetNote to item 1 of noteList
            return body of targetNote
        else
            return "Note not found"
        end if
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    body = result.stdout
    
    if "Note not found" in body or not body.strip():
        return None

    clean_text = re.sub('<[^<]+>', '\n', body)
    
    def sum_string_values(s):
        if not s: return "0"
        # Extract all numbers and sum them
        nums = re.findall(r'\d+', s)
        return str(sum(int(n) for n in nums))

    date_match = re.search(r'(\d{1,2}/\d{1,2})', clean_text)
    time_match = re.search(r'เวลา\s*([\d:]+)', clean_text)
    batt_match = re.search(r'แบตเตอรี่ที่ใช้\s*([\d-]+)', clean_text)
    dist_match = re.search(r'ระยะทาง\s*([\d\+]+)', clean_text)
    inc_match = re.search(r'รายได้\s*Grab\s*([\d\+\s]+)', clean_text)
    tip_match = re.search(r'Tip\s*([\d\+\s]+)', clean_text)
    
    if not date_match or not time_match or not inc_match:
        return None 
        
    date_val = date_match.group(1)
    time_val = time_match.group(1)
    batt_val = batt_match.group(1) if batt_match else "0-0"
    dist_val = dist_match.group(1) if dist_match else "0"
    inc_val = sum_string_values(inc_match.group(1))
    tip_val = sum_string_values(tip_match.group(1))

    day_str, month_str = date_val.split('/')
    month_str = month_str.zfill(2)
    day_str = day_str.zfill(2)
    
    return [f"{day_str}/{month_str}", time_val, batt_val, dist_val, inc_val, tip_val]

def setup_new_month_sheet(service, spreadsheet_id, new_month_num, new_year, all_sheets):
    new_tab_name = MONTHS_TH[new_month_num]
    prev_sheet_id = all_sheets[-1]['properties']['sheetId']
    prev_tab_name = all_sheets[-1]['properties']['title']

    print(f"Creating new tab '{new_tab_name}' in Grab Sheet by duplicating sheet ID {prev_sheet_id}...")

    body = {
        "requests": [
            {
                "duplicateSheet": {
                    "sourceSheetId": prev_sheet_id,
                    "insertSheetIndex": len(all_sheets),
                    "newSheetName": new_tab_name
                }
            }
        ]
    }
    response = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
    new_sheet_id = response['replies'][0]['duplicateSheet']['properties']['sheetId']

    # Clear เฉพาะ data rows (B-N) ไม่แตะ summary
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=f"'{new_tab_name}'!B3:N33"
    ).execute()

    num_days = calendar.monthrange(int(new_year), int(new_month_num))[1]

    # ใส่วันที่เดือนใหม่ใน col A (row 3 ถึง 3+num_days-1)
    dates = [[f"{day:02d}/{new_month_num}/{new_year}"] for day in range(1, num_days + 1)]
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{new_tab_name}'!A3:A{3 + num_days - 1}",
        valueInputOption='USER_ENTERED',
        body={'values': dates}
    ).execute()

    # Clear เฉพาะ data rows ส่วนเกิน (ถ้าเดือนน้อยกว่า 31 วัน)
    # หยุดที่ row 36 เพื่อไม่ทับ summary rows ที่ 38+
    if num_days < 31:
        clear_start = 3 + num_days
        clear_end = 36  # summary rows เริ่มที่ 38 เว้น buffer ไว้ที่ 37
        if clear_start <= clear_end:
            service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=f"'{new_tab_name}'!A{clear_start}:N{clear_end}"
            ).execute()

    # ดึง summary template จาก tab เดือนก่อนหน้า แล้วใส่ใน tab ใหม่ (row 38-45)
    try:
        r_summary = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{prev_tab_name}'!A38:N45"
        ).execute()
        prev_summary = r_summary.get('values', [])

        # สร้าง summary template พร้อม formula ที่อ้างอิงข้อมูลเดือนใหม่
        data_end_row = 3 + num_days - 1  # แถวสุดท้ายของข้อมูล
        row38 = [''] * 14
        row38[10] = f'=IFERROR(SUM(K3:K{data_end_row}),0)'  # นับวันที่วิ่ง
        # เก็บ target dist จาก tab เดือนก่อน (col L=index 11)
        row38[11] = prev_summary[0][11] if prev_summary and len(prev_summary[0]) > 11 else '2000'

        summary_rows = [
            row38,
            ['', '', 'เฉลี่ยแบต 1% วิ่งได้', '', '', '', '', 'ยอดรวมทั้งเดือน', '', 'เฉลี่ยทั้งเดือน', '', '', '', ''],
            ['', '', f'=IFERROR(SUM(D3:D{data_end_row})/(SUM(C3:C{data_end_row})*100),0)', '', '', '', '',
             f'=IFERROR(SUM(H3:H{data_end_row}),0)',
             f'=IFERROR(AVERAGEIF(H3:H{data_end_row},">0"),0)',
             f'=IFERROR(H40/K38,0)', '', '', '', ''],
            ['', '', '', '', '', '', '', '', 'เฉลี่ยทั้งเดือน', '', '', '', '', ''],
            ['', '', '', '', '', '', '', '', f'=IFERROR(H40/COUNTIF(K3:K{data_end_row},"=1"),0)', '', '', '', '', ''],
            [''] * 14,
            ['', '', '', '', '', '', '', 'คำนวน Vat', '', 'คำนวน 10%', '', '', '', ''],
            [''] * 14,
        ]

        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{new_tab_name}'!A38:N45",
            valueInputOption='USER_ENTERED',
            body={'values': summary_rows}
        ).execute()
        print(f"Summary rows 38-45 restored for '{new_tab_name}' ✅")
    except Exception as e:
        print(f"Warning: Could not restore summary rows: {e}")

    print(f"New month '{new_tab_name}' setup successfully in Grab sheet.")
    return new_tab_name

def link_savings_sheet(service, spreadsheet_id, tab_name):
    current_year = str(datetime.datetime.now().year)
    print(f"Linking new month '{tab_name}' to Savings Sheet year {current_year}...")
    
    # Check if year tab exists in Savings Sheet
    meta = service.spreadsheets().get(spreadsheetId=SAVINGS_SPREADSHEET_ID).execute()
    titles = [s.get("properties", {}).get("title", "") for s in meta.get('sheets', [])]
    
    if current_year not in titles:
        print(f"Warning: Tab '{current_year}' not found in Savings Sheet. Please create it manually.")
        return

    # Read row 2 to find length
    result = service.spreadsheets().values().get(
        spreadsheetId=SAVINGS_SPREADSHEET_ID,
        range=f"'{current_year}'!A2:ZZ2"
    ).execute()
    row_2 = result.get('values', [[]])[0]
    col_len = len(row_2)
    
    # Calculate column letters for the 2 new columns
    col1 = col_num_to_letter(col_len + 1)
    col2 = col_num_to_letter(col_len + 2)
    
    photo_formula = f'=IMPORTRANGE("https://docs.google.com/spreadsheets/d/12DqpiZEWBX74hweRY7YOgAIAsWIGr-cquvc3vKcmINc/edit?usp=sharing","{tab_name}!p3:p33")'
    grab_formula = f'=IMPORTRANGE("https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit?usp=sharing","{tab_name}!M3:M33")'
    
    body = {
        'values': [
            ['Photo', 'Grab'],
            [photo_formula, grab_formula]
        ]
    }
    
    # Write to Row 2 and 3 at new columns
    update_range = f"'{current_year}'!{col1}2:{col2}3"
    service.spreadsheets().values().update(
        spreadsheetId=SAVINGS_SPREADSHEET_ID,
        range=update_range,
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
    print(f"Savings Sheet linked successfully at columns {col1} and {col2} in tab '{current_year}'!")

def get_or_create_spreadsheet(service, year):
    # Search for a spreadsheet named 'Grab {year}'
    # Note: We need the Drive API for searching by name
    from googleapiclient.discovery import build as build_drive
    drive_service = build_drive('drive', 'v3', credentials=service._http.credentials)
    
    query = f"name = 'Grab {year}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
    results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = results.get('files', [])
    
    if files:
        print(f"Found existing spreadsheet: {files[0]['name']} (ID: {files[0]['id']})")
        return files[0]['id']
    else:
        print(f"Spreadsheet for {year} not found. Creating 'Grab {year}'...")
        # For simplicity, we create a new one. In a real scenario, we might copy a template ID.
        spreadsheet = {
            'properties': {
                'title': f'Grab {year}'
            }
        }
        spreadsheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
        new_id = spreadsheet.get('spreadsheetId')
        print(f"Created new spreadsheet for {year} with ID: {new_id}")
        return new_id

def clear_notes_data(next_date_str):
    """ล้างข้อมูลใน Note และวาง Template ของวันใหม่"""
    template = f"""<div>Grab Data</div>
<div>{next_date_str}</div>
<div><br></div>
<div><object><table cellspacing="0" cellpadding="0" style="border-collapse: collapse; direction: ltr">
<tbody>
<tr><td valign="top" style="border-style: solid; border-width: 1.0px 1.0px 1.0px 1.0px; border-color: #ccc; padding: 3.0px 5.0px 3.0px 5.0px; min-width: 70px"><div>เวลา </div>
</td><td valign="top" style="border-style: solid; border-width: 1.0px 1.0px 1.0px 1.0px; border-color: #ccc; padding: 3.0px 5.0px 3.0px 5.0px; min-width: 70px"><br></td></tr>
<tr><td valign="top" style="border-style: solid; border-width: 1.0px 1.0px 1.0px 1.0px; border-color: #ccc; padding: 3.0px 5.0px 3.0px 5.0px; min-width: 70px"><div>แบตเตอรี่ที่ใช้ </div>
</td><td valign="top" style="border-style: solid; border-width: 1.0px 1.0px 1.0px 1.0px; border-color: #ccc; padding: 3.0px 5.0px 3.0px 5.0px; min-width: 70px"><br></td></tr>
<tr><td valign="top" style="border-style: solid; border-width: 1.0px 1.0px 1.0px 1.0px; border-color: #ccc; padding: 3.0px 5.0px 3.0px 5.0px; min-width: 70px"><div>ระยะทาง </div>
</td><td valign="top" style="border-style: solid; border-width: 1.0px 1.0px 1.0px 1.0px; border-color: #ccc; padding: 3.0px 5.0px 3.0px 5.0px; min-width: 70px"><br></td></tr>
<tr><td valign="top" style="border-style: solid; border-width: 1.0px 1.0px 1.0px 1.0px; border-color: #ccc; padding: 3.0px 5.0px 3.0px 5.0px; min-width: 70px"><div>รายได้ Grab </div>
</td><td valign="top" style="border-style: solid; border-width: 1.0px 1.0px 1.0px 1.0px; border-color: #ccc; padding: 3.0px 5.0px 3.0px 5.0px; min-width: 70px"><br></td></tr>
<tr><td valign="top" style="border-style: solid; border-width: 1.0px 1.0px 1.0px 1.0px; border-color: #ccc; padding: 3.0px 5.0px 3.0px 5.0px; min-width: 70px"><div>Tip </div>
</td><td valign="top" style="border-style: solid; border-width: 1.0px 1.0px 1.0px 1.0px; border-color: #ccc; padding: 3.0px 5.0px 3.0px 5.0px; min-width: 70px"><br></td></tr>
</tbody>
</table></object><br></div>"""
    
    # Escape double quotes and newlines for AppleScript
    template_escaped = template.replace('"', '\\"').replace('\n', '\\n')
    
    script = f'''
    tell application "Notes"
        set noteList to notes whose name contains "Grab Data" or name contains "TEST"
        if (count of noteList) > 0 then
            set targetNote to item 1 of noteList
            set body of targetNote to "{template_escaped}"
            return "Clear successful"
        else
            return "Note not found"
        end if
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error resetting Note: {result.stderr.strip()}")
    else:
        print(f"Note reset successfully: {result.stdout.strip()}")
        print(f"Note reset with template for {next_date_str}")

def get_sheets_service():
    """สร้าง Google Sheets service โดยใช้ token จาก credentials/"""
    creds = None
    token_path = os.path.join(PROJECT_ROOT, 'credentials', 'token_sheets.json')
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing credentials...")
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
                if os.path.exists(token_path):
                    try:
                        os.remove(token_path)
                        print(f"Deleted invalid token file at: {token_path}")
                    except Exception as re:
                        print(f"Failed to delete invalid token file: {re}")
                return None
        else:
            print("Credentials invalid or missing. Opening browser to re-auth...")
            flow = InstalledAppFlow.from_client_secrets_file(os.path.join(PROJECT_ROOT, 'credentials', 'client_secret.json'), SCOPES)
            creds = flow.run_local_server(port=0)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
    return build('sheets', 'v4', credentials=creds)

def check_and_create_new_month_tab(service, spreadsheet_id):
    """ถ้าวันนี้คือวันที่ 1 ของเดือน และ tab เดือนนี้ยังไม่มี ให้สร้างอัตโนมัติ"""
    now = datetime.datetime.now()
    if now.day != 1:
        return
    
    current_month_str = f"{now.month:02d}"
    current_month_tab = MONTHS_TH.get(current_month_str)
    if not current_month_tab:
        return
    
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    all_sheets = sheet_metadata.get('sheets', [])
    sheet_titles = [s.get('properties', {}).get('title', '') for s in all_sheets]
    
    if current_month_tab not in sheet_titles:
        print(f"[Auto Month Rollover] วันที่ 1 ของเดือน - ยังไม่มี tab '{current_month_tab}' กำลังสร้าง...")
        new_tab = setup_new_month_sheet(service, spreadsheet_id, current_month_str, str(now.year), all_sheets)
        link_savings_sheet(service, spreadsheet_id, new_tab)
        print(f"[Auto Month Rollover] สร้าง tab '{current_month_tab}' เรียบร้อยแล้ว ✅")
    else:
        print(f"[Auto Month Rollover] tab '{current_month_tab}' มีอยู่แล้ว ไม่ต้องสร้างใหม่")

def main():
    now = datetime.datetime.now()
    tomorrow = now + datetime.timedelta(days=1)
    tomorrow_str = f"{tomorrow.day:02d}/{tomorrow.month:02d}"
    
    current_year = str(now.year)
    target_spreadsheet_id = SPREADSHEET_ID  # default 2026

    # --- Auto Month Rollover: ขึ้น tab เดือนใหม่อัตโนมัติทุกวันที่ 1 ---
    if now.day == 1:
        service_early = get_sheets_service()
        if service_early:
            if current_year == '2026':
                rollover_sheet_id = SPREADSHEET_ID
            else:
                try:
                    rollover_sheet_id = get_or_create_spreadsheet(service_early, current_year)
                except:
                    rollover_sheet_id = SPREADSHEET_ID
            check_and_create_new_month_tab(service_early, rollover_sheet_id)

    # ดึงข้อมูลจาก Note
    row_data = get_data_from_notes()
    
    if not row_data:
        print("No valid data found in Notes.")
        
        # ค้นหาวันที่ใน Note เพื่อเช็คว่าต้องอัปเดตไหม
        script = 'tell application "Notes" to get body of item 1 of (notes whose name contains "Grab Data")'
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        body = result.stdout
        if "Note not found" not in body:
            clean_text = re.sub('<[^<]+>', '\n', body)
            date_match = re.search(r'(\d{1,2}/\d{1,2})', clean_text)
            if date_match:
                note_date = date_match.group(1)
                day_n, month_n = note_date.split('/')
                note_date_fmt = f"{day_n.zfill(2)}/{month_n.zfill(2)}"
                
                # ถ้าวันที่ใน Note ยังไม่ใช่พรุ่งนี้ ให้รันไปเป็นพรุ่งนี้เลย (เพราะรันตอน 23:00)
                if note_date_fmt != tomorrow_str:
                    print(f"Note date {note_date_fmt} is old. Rolling over to tomorrow: {tomorrow_str}")
                    clear_notes_data(tomorrow_str)
            else:
                print("No date found in Note. Resetting with tomorrow's template...")
                clear_notes_data(tomorrow_str)
        return
        
    date_val, time_val, batt_val, dist_val, inc_val, tip_val = row_data
    
    # ถ้าวันที่ใน Note เป็นของพรุ่งนี้ไปแล้ว (รันซ้ำ) ให้ข้าม
    if date_val == tomorrow_str:
        print(f"Note is already set for tomorrow ({tomorrow_str}). Skipping.")
        return

    day_str, month_str = date_val.split('/')
    tab_name = MONTHS_TH.get(month_str.zfill(2))
    
    if not tab_name:
        print(f"Invalid month parsed: {month_str}")
        return

    service = get_sheets_service()
    if not service:
        return
    
    # Dynamically find or create the Grab Spreadsheet for the current year
    if current_year == '2026':
        target_spreadsheet_id = SPREADSHEET_ID
    else:
        try:
            target_spreadsheet_id = get_or_create_spreadsheet(service, current_year)
        except Exception as e:
            print(f"Drive API access failed, using fallback ID: {e}")
            target_spreadsheet_id = SPREADSHEET_ID
    
    sheet_metadata = service.spreadsheets().get(spreadsheetId=target_spreadsheet_id).execute()
    all_sheets = sheet_metadata.get('sheets', '')
    sheet_titles = [s.get("properties", {}).get("title", "") for s in all_sheets]
    
    if tab_name not in sheet_titles:
        tab_name = setup_new_month_sheet(service, target_spreadsheet_id, month_str, current_year, all_sheets)
        link_savings_sheet(service, target_spreadsheet_id, tab_name)
        
    result = service.spreadsheets().values().get(
        spreadsheetId=target_spreadsheet_id,
        range=f"'{tab_name}'!A1:B100"
    ).execute()
    values = result.get('values', [])
    
    target_row = None
    for i, row in enumerate(values):
        if row and date_val in row[0]:
            if len(row) > 1 and row[1].strip():
                print(f"Data for {date_val} already exists. Rolling over note to {tomorrow_str}.")
                clear_notes_data(tomorrow_str)
                return
            target_row = i + 1
            break
            
    if not target_row:
        print(f"Could not find date {date_val} in column A of tab '{tab_name}'")
        return
        
    batt_formula = f"=({batt_val})/100"
    dist_formula = f"={dist_val}"
    
    # เจนจะรักษาช่อง M (=H*10%) และ N (=D*2) และ K (ตัวนับ) ไว้เสมอค่ะ
    row_values = [
        time_val,                     # B
        batt_formula,                 # C
        dist_formula,                 # D
        inc_val,                      # E
        '',                           # F
        tip_val,                      # G
        f"=sum(E{target_row}:G{target_row})", # H
        f"=IFERROR(H{target_row}/D{target_row}, 0)", # I
        f"=IFERROR(H{target_row}/(B{target_row}*1440)*60, 0)", # J
        f"=IF(I{target_row}>0, 1, 0)", # K (Count)
        "",                            # L
        f"=H{target_row}*10%",         # M
        f"=D{target_row}*2"            # N
    ]
    
    print(f"Updating row {target_row} in tab '{tab_name}'...")
    service.spreadsheets().values().update(
        spreadsheetId=target_spreadsheet_id,
        range=f"'{tab_name}'!B{target_row}:N{target_row}",
        valueInputOption='USER_ENTERED',
        body={'values': [row_values]}
    ).execute()
    
    print("Update successful!")
    # หลังอัปเดตสำเร็จ ให้ล้างข้อมูลใน Note และวาง Template ของวันถัดไป
    clear_notes_data(tomorrow_str)

if __name__ == '__main__':
    os.chdir(PROJECT_ROOT)
    main()
