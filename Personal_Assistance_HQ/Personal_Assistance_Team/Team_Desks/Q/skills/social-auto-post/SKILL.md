---
name: social-auto-post
description: Prerequisites, setup guide, and API troubleshooting for auto-posting Facebook Video/Reels, YouTube Shorts, and TikTok.
---

# Skill: Social Media Auto-Post Setup & Troubleshooting Guide

คู่มือสำหรับตรวจสอบและตั้งค่าความพร้อมล่วงหน้า (Prerequisites) รวมถึงวิธีแก้ปัญหาในการทำระบบออโต้โพสต์คลิปสั้นและวิดีโอไปยัง **Facebook Reels/Video, YouTube Shorts** และ **TikTok**

---

## 🔴 1. YouTube Shorts (YouTube Data API v3)
หากจะทำระบบออโต้โพสต์ขึ้นช่อง YouTube ต้องตั้งค่าโปรเจกต์ Google Cloud (GCP) และสิทธิ์เข้าถึงดังนี้:

### 🔍 สิ่งที่ต้องจัดเตรียมก่อนรัน (Prerequisites)
1. **เจ้าของสิทธิ์โปรเจกต์:** การสร้างคีย์ใน Google Cloud Console จะต้องใช้ **Email หลักที่ใช้เปิด/ควบคุมช่อง YouTube (หรือบัญชีแบรนด์)** เท่านั้น
2. **เปิดใช้งาน API:** ค้นหาและกด **Enable** ตัว **`YouTube Data API v3`** ในโปรเจกต์ GCP
3. **OAuth Consent Screen (หน้าจอความยินยอม):**
   * ตั้งค่า User Type เป็น **External**
   * ตั้งค่า Publishing Status เป็น **Testing** (ถ้าตั้งเป็น Production จะถูกกูเกิลบังคับส่งตรวจแอปยาว)
   * **สำคัญมาก:** แอด Email หลักของตนเองเข้าไปที่หน้าจอ **`Audience` (Test users)** ด้วย ไม่งั้นกูเกิลจะบล็อกการยินยอมสิทธิ์
4. **สร้างและดาวน์โหลดไฟล์คีย์:** 
   * ไปที่เมนู **Credentials (หรือ Clients)**
   * สร้างคีย์ประเภท **OAuth client ID** ➔ เลือก **Desktop App**
   * ดาวน์โหลดไฟล์ JSON มาเปลี่ยนชื่อเป็น `client_secret.json` วางไว้ที่รูทของโปรเจกต์
5. **เข้าสู่ระบบครั้งแรก (First Auth):**
   * ลบไฟล์ `token_youtube.json` ตัวเก่าออก
   * รันสคริปต์อัปโหลดหรือสคริปต์ทดสอบ ตัวอย่างเช่น:
     ```bash
     ./venv/bin/python scratch/test_youtube_api.py
     ```
   * ระบบจะเด้งบราวเซอร์ขึ้นมา ให้คลิกเลือก **บัญชีแบรนด์ (Brand Account)** หรือชื่อช่อง YouTube ตัวที่ต้องการโพสต์จริง (อย่าเลือกบัญชีส่วนตัว) จากนั้นกดยืนยันยอมรับสิทธิ์ ระบบจะบันทึก `token_youtube.json` ใหม่และใช้งานได้ยาวๆ

---

## 🔵 2. Facebook Reels & Video (Meta Graph API)
สำหรับ Facebook Page หากจะโพสต์คลิป Reels หรืออัปโหลดวิดีโอยาว จะใช้ Access Token แฟนเพจที่มีสิทธิ์บริหารจัดการโพสต์ (`pages_manage_posts` และ `pages_read_engagement`):

### 🎬 การอัปโหลด Facebook Reels (3-Step API)
การโพสต์ Reels จะยิงผ่าน Endpoint `/{page-id}/video_reels` ด้วย 3 ขั้นตอนดังนี้:

* **Step 1: Start (เริ่มต้น Session)**
  * ยิง `POST` ไปที่ `https://graph.facebook.com/v19.0/{PAGE_ID}/video_reels?upload_phase=start&access_token={PAGE_TOKEN}`
  * ดึงค่า `video_id` และ `upload_url` จาก Response กลับมา
* **Step 2: Upload (ส่งไฟล์วิดีโอ)**
  * ยิง `POST` ไปยัง `upload_url` ที่ได้รับจากขั้นแรก (โฮสต์จะเปลี่ยนเป็น `rupload.facebook.com`)
  * **กฎเหล็กของระบบอัปโหลด (จุดที่มักพลาด):** ต้องส่ง Headers ไปให้ครบดังนี้:
    ```python
    headers = {
        'Authorization': 'OAuth {PAGE_ACCESS_TOKEN}',
        'offset': '0',                       # ห้ามขาด! หากไม่มี offset ระบบจะตอบกลับ 400 Bad Request
        'file_size': str(video_size_bytes),  # ขนาดของไฟล์วิดีโอเป็นหน่วยไบต์
        'Content-Type': 'application/octet-stream'
    }
    ```
    *(หากลืมส่ง `offset` เซิร์ฟเวอร์ของ Meta จะฟ้องว่า `Header Offset not convertable to unsigned long` และปัดตกทันที)*
* **Step 3: Publish (สั่งเผยแพร่)**
  * ยิง `POST` ไปที่ `https://graph.facebook.com/v19.0/{PAGE_ID}/video_reels?upload_phase=finish&video_id={VIDEO_ID}&access_token={PAGE_TOKEN}&video_state=PUBLISHED&description={TEXT_CAPTION}`

### 🎞️ การอัปโหลด Facebook Page Video (วิดีโอยาวปกติ)
หากเป็นคลิปยาวปานกลางหรือยาวปกติ (เช่น คิว `FB_Videos_3-5Min`)
* ให้ใช้ Endpoint สำหรับอัปโหลดวิดีโอโดยตรง:
  `POST https://graph-video.facebook.com/v19.0/{PAGE_ID}/videos`
  *(หมายเหตุ: ต้องเปลี่ยนโฮสต์เป็น `graph-video.facebook.com` เท่านั้น ไม่ใช่โฮสต์ graph ปกติ)*
* ส่งข้อมูลผ่านบอทโดยระบุฟิลด์ `source` (ข้อมูลไบนารีของไฟล์) และ `description`

---

## ⚫ 3. TikTok (Content Posting API v2) คู่มือตั้งค่าและแก้ไขปัญหาที่พบบ่อย (Troubleshooting)

ปัญหาการขอสิทธิ์โพสต์วิดีโอของ TikTok มักซับซ้อนและมีจุดกับดักเยอะมาก ให้ทำตามคู่มือนี้เพื่อไม่ให้เสียเวลาแก้บั๊กเป็นชั่วโมง:

### ⚠️ ข้อจำกัดสำคัญและวิธีแก้ไข (Troubleshooting)

#### 1. สิทธิ์ `video.publish` และ `video.upload` ไม่ขึ้นมาให้เลือกตอนกด Add Scopes
* **สาเหตุ:** สิทธิ์เหล่านี้จะยังไม่โผล่ขึ้นมาให้เราเลือกจนกว่าเราจะเปิดสวิตช์ฟีเจอร์โพสต์ตรงเสียก่อน
* **วิธีแก้:** ไปที่เมนู **Products** ➔ มองหา **Content Posting API** ➔ เปิดสวิตช์ **Direct Post** ให้เป็น **ON (สีเขียว)** จากนั้นเลื่อนไปด้านล่าง สิทธิ์ทั้งสองตัวจะถูกแอดเข้าเครื่องอัตโนมัติเองโดยไม่ต้องกดแอดแมนนวล

#### 2. ใส่ Redirect URI ในแท็บ Web* ของ Login Kit แล้วเจอฟ้องสีแดงเตือน https://
* **อาการ:** TikTok บังคับให้ Web Redirect URI ต้องเป็น `https://` และเป็นโดเมนจริงเท่านั้น ไม่ยอมรับ IP `http://127.0.0.1` หรือ `http://localhost`
* **วิธีแก้ (GitHub Pages Callback Bridge):**
  1. เราสร้างหน้าเว็บ `callback.html` ขึ้นบนโดเมน GitHub Pages ของเราที่เป็น HTTPS จริง (เช่น `https://chzxiii.github.io/wtj-dashboard/callback.html`)
  2. หน้าเว็บนี้มีสคริปต์ JavaScript สั้นๆ คอยดึงรหัส `code` และ `state` จาก URL Query แล้วทำหาร Redirect ส่งต่อกลับมายังเครื่องโลคอลของเราที่ `http://localhost:5000/callback` แบบออโต้
  3. นำลิงก์ HTTPS ของ GitHub Pages ไปใส่ในช่อง **Redirect URI** ของแท็บ **`Web*`**
  4. **สำคัญมาก:** ต้องกดปุ่ม **`+ Add a URI`** สีขาวใต้ช่องกรอก เพื่อให้ลิงก์ย้ายขึ้นไปอยู่ในแถบลิสต์ (ที่มีเครื่องหมายลบ `-` ด้านขวา) ไม่งั้นตอนกด Save ระบบจะไม่บันทึกและเกิดปัญหา `redirect_uri` ไม่ตรงกัน

#### 3. ปัญหา local HTTP server บายด์พอร์ตไม่ผ่าน (Errno 49 Can't assign requested address)
* **อาการ:** เมื่อรันสคริปต์ `tiktok_publisher.py` ในโหมดขอสิทธิ์ (OAuth) ครั้งแรก สคริปต์จะพยายามแกะตัวแปร `TIKTOK_REDIRECT_URI` เพื่อไปบายด์พอร์ตเซิร์ฟเวอร์ และจะโยน Error 49 ออกมาเพราะพยายามไปบายด์พอร์ตบนโฮสต์ GitHub Pages (`chzxiii.github.io`)
* **วิธีแก้:** ในโค้ด [tiktok_publisher.py](file:///Users/chz/Desktop/ChZ_Agent_Corp/WTJ_Content_Studio/Team_Agent_Content/skills/tiktok_publisher.py) ได้รับการปรับปรุงให้ตรวจสอบว่า หากตัวแปร Redirect URI ไม่ใช่ localhost/127.0.0.1 ให้ตั้งค่าเซิร์ฟเวอร์โลคอลไปบายด์ที่ `127.0.0.1` พอร์ต `5000` เสมอ เพื่อรอรับสายดีดกลับจากหน้าเว็บ GitHub Pages

#### 4. บุ่มเซฟหรือตั้งค่าทั้งหมดกลายเป็นสีเทา กดอะไรไม่ได้ (Locked)
* **อาการ:** หลังจากกดปุ่ม **Submit for review** ด้านขวาบน หน้าเว็บคอนโซลจะล็อกการตั้งค่าทั้งหมดทำให้แก้ไขข้อมูลหรือปรับแต่ง Redirect URI ไม่ได้
* **วิธีแก้:** นี่เป็นเรื่องปกติของระบบ TikTok ในระหว่างการรีวิว (In review) ห้ามกดยกเลิก (Recall) ให้รอรีวิวผ่าน 1-3 วันทำการ

#### 5. สิทธิ์ API บล็อกการโพสต์ขึ้นบัญชีสาธารณะ (Error 403: unaudited_client)
* **อาการ:** ในระหว่างที่แอปยังไม่ผ่านการอนุมัติ (Unaudited / In review) TikTok จะไม่อนุญาตให้ API โพสต์คลิปไปเป็นสาธารณะ หากฝืนโพสต์จะเจอ Error: `unaudited_client_can_only_post_to_private_accounts`
* **วิธีแก้:** 
  * ในระหว่างที่รอการตรวจสอบนี้ บอทจะทำการตั้งค่าความเป็นส่วนตัวของคลิป TikTok ที่ส่งขึ้นไปเป็น **`SELF_ONLY` (Private / เฉพาะฉัน)** เพื่อให้เราทดสอบโพสต์วิดีโอเดโมและระบบรันผ่านได้โดยไม่ถูกปฏิเสธสิทธิ์
  * เมื่อแอปผ่านการอนุมัติรีวิวแล้ว ระบบจะสามารถตั้งค่าเป็น **`PUBLIC_TO_EVERYONE`** เพื่อโพสต์เป็นคลิปสาธารณะให้ผู้ชมเห็นได้ทันที

#### 6. โดนปฏิเสธการรีวิวทันที (Not approved) เพราะหาหน้า Terms of Service หรือ Privacy Policy ไม่เจอ
* **อาการ:** TikTok ปฏิเสธการอัปเดตแอปอย่างรวดเร็วพร้อมขึ้นแจ้งเตือน: `Missing Terms of Service, ToS needs to be easily accessible from the homepage. Missing Privacy Policy, PP needs to be easily accessible from the homepage. Website must be fully developed.`
* **สาเหตุ:** ถึงแม้เราจะกรอกลิงก์หน้า `privacy.html` และ `terms.html` แยกไปให้ในฟอร์มของแอปแล้ว แต่ทาง TikTok มีเกณฑ์ว่าลิงก์กฎหมายทั้งสองตัวนี้จะต้องแสดงอยู่บน **หน้าแรกสุดของเว็บไซต์ (Homepage / Landing page)** ที่ผู้ใช้เข้าถึงด้วย เพื่อให้ผู้ใช้สามารถกดคลิกอ่านนโยบายได้ตลอดเวลา
* **วิธีแก้:**
  1. เข้าไปแก้ไขไฟล์หน้าแรกสุดของแดชบอร์ด ([`index.html`](file:///Users/chz/Desktop/ChZ_Agent_Corp/WTJ_Content_Studio/Team_Agent_Content/WTJ_Story_Project/dashboard/index.html)) เพื่อเพิ่มกล่อง Footer ท้ายหน้าเว็บที่มีลิงก์ชี้ไปยังหน้า `/privacy.html` และ `/terms.html`
  2. สั่งรัน git เพื่อดันโค้ดขึ้นระบบ GitHub Pages (เช่น `https://chzxiii.github.io/wtj-dashboard/`)
  3. ไปที่แดชบอร์ดผู้พัฒนาของ TikTok กดปุ่ม **Return to Draft** ➔ ตรวจสอบข้อมูลฟอร์ม ➔ กด **Save** ➔ กด **Submit for review** เพื่อส่งตรวจใหม่อีกรอบ

---


## 💾 สรุปการตั้งค่าไฟล์ .env ของบอท TikTok
ภายในไฟล์ [`.env`](file:///Users/chz/Desktop/ChZ_Agent_Corp/.env) ที่รูทของโปรเจกต์ ต้องตั้งค่าตัวแปรดังนี้:
```ini
TIKTOK_CLIENT_KEY="sbawsptlnucpajwh3d"
TIKTOK_CLIENT_SECRET="COYzAsOjYsSjQykkiZ8LhAs44TaXJfv2"
TIKTOK_REDIRECT_URI="https://chzxiii.github.io/wtj-dashboard/callback.html"
```
