# 🔍 CODE AUDIT REPORT — Slide 4 Financial Document Items Table & Calculations
ผู้ตรวจสอบ: น้องออม (Aom) | ผู้เขียนโค้ด: น้องคิว | วันที่: 2026-07-02

## 🟢 ผ่าน (Pass)
1. **โครงสร้างตาราง 3 คอลัมน์ (3-Column Items Table):** 
   - ตารางแสดงรายการสินค้าในหน้าพรีวิว A4 (`.preview-items-table`) ได้รับการปรับแต่งให้มี 3 คอลัมน์ (ลำดับ, รายละเอียด, จำนวนเงิน) อย่างถูกต้อง ทั้งส่วนของส่วนหัวตาราง HTML (`<thead>`) และส่วนสร้างแถวตารางแบบไดนามิกใน Javascript (`updateA4Preview`)
   - มีการจัดสัดส่วนความกว้างคอลัมน์ (10%, 70%, 20%) และการจัดตำแหน่งข้อความ (กึ่งกลาง, ชิดซ้าย, ชิดขวา) สอดคล้องตรงกันดี เลย์เอาต์สวยงามไม่ทับซ้อนหรือโย้เย้
2. **ลอจิกการคำนวณเงินสด (Financial Calculations Logic):**
   - การหาค่า Subtotal ของรายการสินค้าทุกแถวทำงานได้ถูกต้อง และระบบกรองค่า `parseFloat(item.amount) || 0` ช่วยป้องกันค่า NaN หรือข้อผิดพลาดกรณีฟิลด์ว่างเปล่า
   - มีการใช้ `Math.max(0, subtotal - discountVal)` ช่วยควบคุมไม่ให้ยอดหลังหักส่วนลดติดลบ ปลอดภัย 100%
   - การคิดภาษีหัก ณ ที่จ่าย 3% คำนวณจากยอดที่หักส่วนลดแล้ว ซึ่งสอดคล้องตามหลักการบัญชีของไทย
3. **ระบบจัดการหน้ากระดาษ PDF (Dynamic PDF Height & Page Clamp):**
   - โค้ดในส่วนส่งออก PDF ได้ใช้การหาความสูงเอกสารจริง `scrollHeight` แล้วหารคูณหน้า `$N = \text{Math.ceil}(\text{scrollHeight} / 1122.5)$` เพื่อจำกัดความสูงที่ `$N \times 295\text{mm}$` และสั่ง `overflow: hidden`
   - การจัดสไตล์ชั่วคราวนี้ถูกเรียกคืนสไตล์เดิมผ่านบล็อก `finally` ซึ่งประมวลผลครอบคลุมทั้งกรณีสคริปต์ทำงานสำเร็จหรือล้มเหลว (ดักจับ Error ทั่วถึง) ทำให้ไม่มีปัญหาหน้ากระดาษ A4 เปล่าล้น หรือแถบระบบหัวกระดาษ/ท้ายกระดาษติดเข้าไปในไฟล์ PDF
4. **ความสอดคล้องต่อนโยบายความสวยงามและการใช้ฟอนต์ (UI CI Compliance):**
   - ไม่มีอักขระ Emoji ในหน้า Slide 4 (ปุ่มลบใช้เครื่องหมายคูณ `×` แทนปุ่มอีโมจิ ❌ หรือถังขยะ) ตรงตามกฎ *No Emoji in UI*
   - การใช้ฟอนต์ภาษาไทยและอังกฤษสอดคล้องตาม CI และไม่มีการดึงฟอนต์ 'Share Tech Mono' มาแสดงในข้อความทั่วไป (ใช้แสดงแค่ในส่วนของ Log Box เท่านั้น ซึ่งถือเป็นข้อมูลแบบ Code/Data สะอาดตา)

## 🔴 ต้องแก้ไข (Fail - Must Fix)
1. **ช่องโหว่การซิงค์สถานะภาษีหัก ณ ที่จ่าย (Withholding Tax Sync Bug):**
   * **จุดพิกัด:** `super_app_anime.html` บรรทัดที่ 6345 - 6354 (ฟังก์ชัน Event Listener ของแบบฟอร์มส่งออกเอกสาร PDF)
   * **ปัญหา:** วัตถุธุรกรรม `newTx` ที่ถูกสร้างขึ้นเพื่อบันทึกประวัติการเงินลง Ledger ท้องถิ่นและซิงค์ขึ้นกูเกิลชีต **ไม่มีการกำหนดแอตทริบิวต์ `hasTax`**
   * **ผลกระทบ:** เมื่อเรียกใช้ฟังก์ชัน `sendTransactionToGAS(newTx)` ฝั่งหลังบ้านกูเกิลชีตจะพยายามประเมินค่า `payload.hasTaxWithholding = tx.hasTax || ...` เนื่องจาก `newTx` ไม่มีแอตทริบิวต์นี้ และฟิลด์ `remarks` ก็ไม่ได้ใส่ข้อมูลว่ามีการหัก ณ ที่จ่าย ทำให้สถานะการหักภาษี 3% ซิงค์ขึ้นกูเกิลชีตเป็น **FALSE** ตลอดเวลา ทั้งที่เอกสารจริงและยอดเงินสุทธิมีการหักภาษีไปแล้ว ส่งผลให้ข้อมูลบัญชีคลาดเคลื่อน
   * **การแก้ไข:** ในส่วนสร้างวัตถุ `newTx` ต้องส่งต่อค่า `hasTax: hasTax3` และเพิ่มคำอธิบายในหมายเหตุ (Remarks) ให้ชัดเจนเมื่อมีการหักภาษี ณ ที่จ่าย เช่นเดียวกับลอจิกของ Slide 2

## 🟡 ข้อเสนอแนะ (Advisory)
- **การหลีกเลี่ยง HTML Injection ในรายการพรีวิว:** ในลอจิกการอัปเดตแถวตารางพรีวิว A4 มีการแทรก `${item.desc || '-'}` ลงไปใน `tr.innerHTML` ตรงๆ ถึงแม้ว่าระบบนี้จะถูกเรียกใช้งานแบบออฟไลน์ (`file://`) เฉพาะส่วนบุคคลบนเครื่องพี่เก่ง แต่ออมแนะนำให้ทำการแปลงค่าข้อความเบื้องต้น (เช่น เปลี่ยน `<` เป็น `&lt;` และ `>` เป็น `&gt;`) หรือใช้การสร้างโหนด `td` แยกพร้อม `textContent` เพื่อความปลอดภัยของข้อมูลในระยะยาวค่ะ

---

## 🏁 คำตัดสินสุดท้าย (Final Verdict)
### 🔴 REJECT (FAIL)
**เหตุผลหลัก:** ข้อมูลสถานะการหักภาษี ณ ที่จ่าย 3% (`hasTax`) ตกหล่นในลอจิกการสร้าง Object ธุรกรรมก่อนส่งไปที่ `sendTransactionToGAS` ส่งผลให้ตัวเลขยอดเงินสุทธิที่บันทึกซิงค์ขึ้นกูเกิลชีตไม่ตรงกับยอดก่อนหักภาษีจริงโดยไม่มีการลงบันทึกบันทึกกำกับภาษี

---

### 🛠️ วิธีแก้ไขเฉพาะจุดสำหรับพี่คิว (Q)

พี่คิวสามารถแก้โค้ดในฟังก์ชัน Submit Form (`super_app_anime.html` ช่วงบรรทัดที่ 6342-6355) จากเดิม:

```javascript
              // Save transaction
              if (type === 'invoice' || type === 'receipt') {
                exportLogs.innerHTML += `<br>[System] Auto-recording income transaction to ledger...`;
                const newTx = {
                  id: Date.now(),
                  date: date,
                  time: new Date().toTimeString().split(' ')[0].substring(0, 5),
                  type: 'income',
                  category: 'Feltz Studio',
                  remarks: `[${type === 'invoice' ? 'ใบวางบิล' : 'ใบเสร็จรับเงิน'}] ${docNumber} - ${client}`,
                  amount: netTotal,
                  syncStatus: 'local'
                };
```

แก้ไขให้เป็นแบบนี้ค่ะ:

```javascript
              // Save transaction
              if (type === 'invoice' || type === 'receipt') {
                exportLogs.innerHTML += `<br>[System] Auto-recording income transaction to ledger...`;
                let finalRemarks = `[${type === 'invoice' ? 'ใบวางบิล' : 'ใบเสร็จรับเงิน'}] ${docNumber} - ${client}`;
                if (hasTax3) {
                  finalRemarks += ' (หัก ณ ที่จ่าย 3%)';
                }
                const newTx = {
                  id: Date.now(),
                  date: date,
                  time: new Date().toTimeString().split(' ')[0].substring(0, 5),
                  type: 'income',
                  category: 'Feltz Studio',
                  remarks: finalRemarks,
                  amount: netTotal,
                  hasTax: hasTax3,
                  syncStatus: 'local'
                };
```
