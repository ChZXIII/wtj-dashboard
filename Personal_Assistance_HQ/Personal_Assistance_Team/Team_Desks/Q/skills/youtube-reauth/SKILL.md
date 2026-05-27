---
name: youtube-reauth
description: How to check, refresh, and re-authenticate YouTube API upload tokens when credentials expire or uploads fail due to OAuth issues. Trigger when YouTube uploading or publishing script fails.
---

# Skill: YouTube API Re-authentication & Token Renewal

ใช้เมื่อระบบอัปโหลดวิดีโอ YouTube (Reels/Shorts หรือคลิปยาว) เกิดปัญหา Credentials/Token หมดอายุ หรือตัวต่ออายุอัตโนมัติ (Refresh Token) ใช้งานไม่ได้

---

## 🔍 วิธีตรวจสอบปัญหา (Diagnostic Steps)
1. **เช็ค Log ของบอท:** หากสคริปต์อัปโหลด (`youtube_publisher.py` หรือ `wtj_auto_poster.py`) รันล้มเหลวและฟ้องข้อความแนวนี้:
   - `google.auth.exceptions.RefreshError`
   - `Token has been expired or revoked`
   - `invalid_grant: Bad Request`
   - `Request had insufficient authentication scopes`
2. **เช็คพิกัดไฟล์ Token:** ในรูทโปรเจกต์ ChZ_Agent_Corp จะต้องมี:
   - `client_secret.json` (คีย์หลักที่ดาวน์โหลดจาก Google Cloud Console สิทธิ์เข้าถึง API)
   - `token_youtube.json` (ตัว Token สิทธิ์ `youtube.upload` ที่ระบบอัปเดตให้อัตโนมัติ)

---

## 🛠️ ขั้นตอนการแก้ไขและต่ออายุ (Re-auth Steps)

### 1. เรียกใช้งานสคริปต์ต่ออายุอัตโนมัติ
เราเตรียมสคริปต์ [reauth_youtube.py](file:///Users/chz/Desktop/ChZ_Agent_Corp/Agent_Lab/sandbox/reauth_youtube.py) ไว้ในห้องแล็บเพื่อช่วยตรวจเช็คและกู้คืนสิทธิ์ให้โดยไม่ต้องเปิดเบราว์เซอร์หากตัว Refresh Token ยังทำงานได้:

```bash
./venv/bin/python Agent_Lab/sandbox/reauth_youtube.py
```

### 2. ขั้นตอนกรณีต้องการล็อกอินใหม่ทางหน้าต่างเบราว์เซอร์ (User Action Required)
หากตัว Refresh Token ถูกยกเลิก (Revoke) หรือหมดอายุไปแล้ว สคริปต์จะเปิดเบราว์เซอร์อัตโนมัติเพื่อให้คนล็อกอินใหม่:
1. คลิกเลือกบัญชี Google ที่เชื่อมโยงกับช่อง YouTube
2. หากเจอด่านคำเตือน **"Google hasn't verified this app"** ให้คลิกที่ **Advanced** และเลือก **Go to [Project Name] (unsafe)** เพื่ออนุมัติสิทธิ์เข้าถึง
3. กดยอมรับสิทธิ์อัปโหลดวิดีโอขึ้น YouTube
4. หลังจากล็อกอินสำเร็จ หน้าเว็บจะขึ้นแจ้งเตือน และสคริปต์จะบันทึกผลลัพธ์ลงไฟล์ `token_youtube.json` ใหม่ในรูทโปรเจกต์ ChZ_Agent_Corp อัตโนมัติ

---

## 🧪 การทดสอบสิทธิ์หลังทำเสร็จ (Verification Check)
รันสคริปต์ออโต้โพสต์แบบ Dry-Run เพื่อจำลองการเชื่อมต่อและตรวจเช็คความถูกต้องโดยไม่ทำการอัปโหลดคลิปจริงขึ้นหน้าช่อง:

```bash
./venv/bin/python WTJ_Content_Studio/Team_Agent_Content/skills/wtj_auto_poster.py -q Reels_Under1Min --dry-run
```

หากผลลัพธ์ขึ้นว่า `YouTube: ✅ สำเร็จ` แสดงว่าโทเคนพร้อมใช้งานเรียบร้อยแล้ว!
