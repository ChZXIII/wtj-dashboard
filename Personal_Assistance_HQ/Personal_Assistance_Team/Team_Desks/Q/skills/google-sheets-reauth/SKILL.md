---
name: google-sheets-reauth
description: How to check, refresh, and re-authenticate Google Sheets API tokens when credentials expire or libraries are missing. Trigger when spreadsheet synchronization fails due to token/credential issues.
---

# Skill: Google Sheets API Re-authentication & Token Renewal

ใช้เมื่อระบบซิงค์ชีต (Grab หรือ Crypto) เกิดปัญหา Credentials/Token หมดอายุ หรือต้องการต่ออายุ API Token

---

## 🔍 วิธีตรวจสอบปัญหา (Diagnostic Steps)
1. **เช็ค Log ของบอท:** หากบอท (Jane, Win) รันไม่ผ่านและฟ้อง Error เกี่ยวกับ OAuth หรือ Authentication:
   - `google.auth.exceptions.RefreshError`
   - `Token has been expired or revoked`
   - `invalid_grant: Bad Request`
2. **เช็คพิกัดไฟล์ Token:** ในโฟลเดอร์หลักของโปรเจกต์จะต้องมี:
   - `client_secret.json` (คีย์หลักที่ดาวน์โหลดจาก Google Cloud Console)
   - `token_sheets.json` (ตัว Token ที่ได้หลังการ Login ครั้งแรก)

---

## 🛠️ ขั้นตอนการแก้ไขและต่ออายุ (Re-auth Steps)

### 1. ตรวจสอบ dependencies ใน Virtual Environment
ต้องมั่นใจว่าใน `venv` ของโปรเจกต์มีแพ็กเกจเหล่านี้ติดตั้งครบถ้วน:
```bash
pip install google-auth-oauthlib google-api-python-client
```

### 2. โค้ดสำหรับดึงคีย์และรัน Re-auth (Python)
บอทจะเรียกหน้าต่างล็อกอินขึ้นมาผ่าน Local Server flow:
```python
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
token_path = 'token_sheets.json'
client_secret_path = 'client_secret.json'

creds = None
if os.path.exists(token_path):
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        try:
            print("Refreshing credentials...")
            creds.refresh(Request())
        except Exception as e:
            print(f"Refresh failed: {e}. Attempting full re-authentication...")
            creds = None
            
    if not creds:
        print("Opening browser for authentication...")
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        print("New token generated successfully!")
```

### 3. ขั้นตอนยืนยันสิทธิ์สำหรับผู้ใช้ (User Action)
- เมื่อสคริปต์เปิดเบราว์เซอร์อัตโนมัติ ให้ผู้ใช้คลิกเลือกบัญชี Google ที่เชื่อมโยงกับ Google Sheet
- หากเจอด่านคำเตือน **"Google hasn't verified this app"** ให้กดคลิก **Advanced** และเลือก **Go to [Project Name] (unsafe)** เพื่ออนุมัติสิทธิ์เข้าถึง Sheets API
- หลังล็อกอินเสร็จ สคริปต์จะบันทึกผลลัพธ์เป็นไฟล์ `token_sheets.json` ใหม่โดยอัตโนมัติ

---

## 🧪 การทดสอบสิทธิ์หลังทำเสร็จ (Verification Check)
รันสคริปต์ทดสอบดึงแถวแรกของชีตเพื่อเช็คความพร้อม:
```python
from googleapiclient.discovery import build
service = build('sheets', 'v4', credentials=creds)
sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
print("Connected successfully! Sheet Title:", sheet_metadata.get('properties', {}).get('title'))
```
