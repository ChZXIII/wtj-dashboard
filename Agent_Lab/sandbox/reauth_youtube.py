import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
client_secret_path = os.path.join(PROJECT_ROOT, 'credentials', 'client_secret.json')
token_path = os.path.join(PROJECT_ROOT, 'credentials', 'token_youtube.json')

print(f"📍 Project root: {PROJECT_ROOT}")
print(f"📂 client_secret.json path: {client_secret_path}")
print(f"💾 token_youtube.json path: {token_path}")

creds = None
if os.path.exists(token_path):
    print("🔍 พบไฟล์ token_youtube.json เดิม กำลังตรวจสอบสิทธิ์...")
    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    except Exception as e:
        print(f"⚠️ เกิดข้อผิดพลาดในการโหลด token: {e}")

if creds and creds.valid:
    print("✅ Token เก่ายังใช้งานได้ตามปกติ ไม่ต้องทำอะไรเพิ่ม!")
else:
    if creds and creds.expired and creds.refresh_token:
        try:
            print("🔄 Token หมดอายุ กำลังพยายามรีเฟรชโดยใช้ Refresh Token...")
            creds.refresh(Request())
            with open(token_path, 'w', encoding='utf-8') as token_file:
                token_file.write(creds.to_json())
            print("✅ รีเฟรชและอัปเดตไฟล์ token_youtube.json สำเร็จ!")
        except Exception as e:
            print(f"⚠️ การรีเฟรชล้มเหลว: {e}")
            creds = None

    if not creds:
        print("\n🔑 เริ่มต้นการเข้าสู่ระบบใหม่ผ่านเบราว์เซอร์...")
        if not os.path.exists(client_secret_path):
            print(f"❌ Error: ไม่พบไฟล์ client_secret.json ที่ {client_secret_path}")
            print("กรุณาดาวน์โหลด client_secret.json จาก Google Cloud Console มาวางที่โฟลเดอร์หลักก่อนนะแก!")
            sys.exit(1)
            
        try:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
            with open(token_path, 'w', encoding='utf-8') as token_file:
                token_file.write(creds.to_json())
            print("🎉 สำเร็จ! สร้างและบันทึกไฟล์ token_youtube.json เรียบร้อยแล้วแก!")
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในขั้นตอนล็อกอิน: {e}")
