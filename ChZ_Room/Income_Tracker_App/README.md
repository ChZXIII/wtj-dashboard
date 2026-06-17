# ฿ เครื่องมือบันทึกรายรับส่งตรง Google Sheets (Income Tracker Web App)

สวัสดีแก! เครื่องมือตัวนี้เป็นเว็บแอปหน้าต่างบันทึกธุรกรรมรายรับสำหรับตัวแกเอง ช่วยให้แกคีย์ข้อมูลรายรับทั่วไป และรายได้วิ่ง Grab ลงตาราง Google Sheets ของแกได้อย่างรวดเร็วและปลอดภัยจากหน้าเว็บคลีนๆ ไม่ต้องพิมพ์จดโน้ตแล้วรอระบบซิงค์เที่ยงคืนอีกต่อไปจ้า!

เว็บแอปนี้เขียนขึ้นด้วย **HTML/CSS/JS** ล้วนๆ ทำให้เป็น **Static Web App** ที่แกสามารถดับเบิ้ลคลิกไฟล์ `index.html` เพื่อเปิดใช้งานบนเบราว์เซอร์ได้ทันทีโดยไม่ต้องรันเซิร์ฟเวอร์ใดๆ ทิ้งไว้ในเครื่องเบื้องหลัง (ปลอดภัยและลดภาระ CPU เครื่อง Mac ของแก)

---

## 🛠️ ขั้นตอนผูก Google Sheets ด้วย Google Apps Script (ทำครั้งเดียว)

เพื่อให้เบราว์เซอร์สามารถส่งข้อมูลไปคีย์ลงชีตของแกตรงๆ ได้ ให้แกติดตั้งโค้ดตัวกลางนี้ลงในชีตของแกตามขั้นตอนนี้นะแก:

### ขั้นตอนที่ 1: เข้าสู่หน้าเว็บเขียนสคริปต์
1. เปิดเอกสาร Google Sheets ที่แกใช้บันทึกรายได้ของแก
2. กดเลือกเมนูด้านบน: **ส่วนขยาย (Extensions)** > **Apps Script**

### ขั้นตอนที่ 2: วางโค้ด Apps Script
1. ลบโค้ดเริ่มต้นในหน้าจอ Apps Script ออกทั้งหมด (ลบฟังก์ชัน `myFunction` ทิ้ง)
2. คัดลอกโค้ดด้านล่างนี้ทั้งหมดไปวางแทนที่:

```javascript
// โค้ดรับส่งข้อมูลจากเว็บแอปมาคีย์ลงตาราง Google Sheets อัตโนมัติ
function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.tryLock(10000); // ป้องกันปัญหาคีย์ชนกัน โดยรอคิวสูงสุด 10 วินาที
  
  try {
    var data = JSON.parse(e.postData.contents);
    var sheetType = data.type; // "general", "expense", "grab" หรือ "fetch_summary"
    var spreadsheetId = data.spreadsheetId; // ID ของ Google Sheets ที่ส่งมาจากเว็บแอป
    
    if (!spreadsheetId) {
      return ContentService.createTextOutput(JSON.stringify({
        "status": "error",
        "message": "ไม่พบ Spreadsheet ID ในชุดข้อมูลที่ส่งมานะแก!"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    var activeSpreadsheet = SpreadsheetApp.openById(spreadsheetId);
    
    // 1. รองรับการดึงสรุปข้อมูลยอดสะสม 12 เดือน (fetch_summary)
    if (sheetType === "fetch_summary") {
      var months = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'];
      var summaryData = [];
      
      for (var m = 0; m < months.length; m++) {
        var mName = months[m];
        var mSheet = activeSpreadsheet.getSheetByName(mName);
        
        if (mSheet) {
          // ค้นหาแถวยอดรวมโดยการค้นหาข้อความ "ยอดรวมทั้งเดือน" ในคอลัมน์ A (เพื่อรองรับเดือนที่มีจำนวนวันต่างกันอย่างไดนามิก)
          var lastRow = mSheet.getLastRow();
          var colAValues = mSheet.getRange("A1:A" + lastRow).getValues();
          var totalRowIdx = -1;
          for (var r = 0; r < colAValues.length; r++) {
            if (colAValues[r][0] && colAValues[r][0].toString().trim() === "ยอดรวมทั้งเดือน") {
              totalRowIdx = r + 1; // แปลงเป็น 1-indexed
              break;
            }
          }
          
          var totalIncome = 0;
          var totalExpense = 0;
          var netProfit = 0;
          var totalSavings = 0;
          var fixedCosts = [];
          
          if (totalRowIdx !== -1) {
            // แถวยอดรวมทั้งเดือน คอลัมน์ C: รายรับ, E: รายจ่าย
            totalIncome = parseFloat(mSheet.getRange("C" + totalRowIdx).getValue() || 0);
            totalExpense = parseFloat(mSheet.getRange("E" + totalRowIdx).getValue() || 0);
            
            // รายได้สุทธิ อยู่ถัดจากแถวยอดรวมไป 1 แถว (คอลัมน์ C)
            netProfit = parseFloat(mSheet.getRange("C" + (totalRowIdx + 1)).getValue() || (totalIncome - totalExpense));
            
            // ยอดรวมเงินเก็บสะสม 10% อยู่ถัดจากแถวยอดรวมไป 2 แถว (คอลัมน์ C)
            totalSavings = parseFloat(mSheet.getRange("C" + (totalRowIdx + 2)).getValue() || (totalIncome * 0.1));
            
            // ดึงข้อมูลรายการ Fix Cost จากตารางชีต (ตั้งแต่แถว 2 จนถึงแถวก่อนแถวยอดรวม คอลัมน์ D และ E)
            var maxDataRow = totalRowIdx - 2; // แถวก่อนแถวว่างและแถวยอดรวม
            if (maxDataRow >= 2) {
              var dValues = mSheet.getRange("D2:E" + maxDataRow).getValues();
              for (var r = 0; r < dValues.length; r++) {
                var desc = dValues[r][0];
                var amt = parseFloat(dValues[r][1] || 0);
                if (desc && desc.toString().trim() !== "" && amt > 0) {
                  fixedCosts.push({
                    desc: desc.toString().trim(),
                    amount: amt
                  });
                }
              }
            }
          }
          
          summaryData.push({
            month: mName,
            income: totalIncome,
            expense: totalExpense,
            profit: netProfit,
            savings: totalSavings,
            fixedCosts: fixedCosts
          });
        } else {
          summaryData.push({
            month: mName,
            income: 0,
            expense: 0,
            profit: 0,
            savings: 0,
            fixedCosts: []
          });
        }
      }
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "data": summaryData
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // ดึงข้อมูลวันที่ และฟอร์แมตให้อยู่ในรูปต่างๆ
    var dateParts = data.date.split('/'); // คาดหวัง DD/MM/YYYY
    var dayStr = dateParts[0].padStart(2, '0');
    var monthStr = dateParts[1].padStart(2, '0');
    var yearStr = dateParts[2];
    
    var monthsTh = {
      '01': 'ม.ค.', '02': 'ก.พ.', '03': 'มี.ค.', '04': 'เม.ย.',
      '05': 'พ.ค.', '06': 'มิ.ย.', '07': 'ก.ค.', '08': 'ส.ค.',
      '09': 'ก.ย.', '10': 'ต.ค.', '11': 'พ.ย.', '12': 'ธ.ค.'
    };
    var tabName = monthsTh[monthStr];
    var sheet = activeSpreadsheet.getSheetByName(tabName);
    
    if (!sheet) {
      return ContentService.createTextOutput(JSON.stringify({
        "status": "error",
        "message": "ไม่พบแท็บเดือน " + tabName + " ใน Google Sheet"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    if (sheetType === "grab") {
      var dateKey = dayStr + "/" + monthStr;
      
      // ค้นหาแถววันที่ในคอลัมน์ A (แถวที่ 3 ถึง 33)
      var range = sheet.getRange("A3:A33");
      var values = range.getDisplayValues();
      var targetRow = null;
      
      for (var i = 0; i < values.length; i++) {
        var val = values[i][0];
        if (val && val.toString().indexOf(dateKey) !== -1) {
          // ตรวจสอบว่าช่องเวลายังว่างอยู่ไหม ป้องกันการเขียนทับซ้ำ
          var existingTime = sheet.getRange("B" + (i + 3)).getValue();
          if (existingTime && existingTime.toString().trim() !== "") {
            return ContentService.createTextOutput(JSON.stringify({
              "status": "error",
              "message": "ข้อมูล Grab ของวันที่ " + dateKey + " มีการบันทึกอยู่แล้วในตารางชีตนะแก!"
            })).setMimeType(ContentService.MimeType.JSON);
          }
          targetRow = i + 3;
          break;
        }
      }
      
      if (!targetRow) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "ไม่พบแถวสำหรับวันที่ " + dateKey + " ในตารางจ้า"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      var timeVal = data.time || "";
      var battVal = data.battery || "0-0";
      var distVal = data.distance || "0";
      var incVal = parseFloat(data.amount || 0);
      var tipVal = parseFloat(data.tip || 0);
      
      var battFormula = "=(" + battVal + ")/100";
      var distFormula = "=" + distVal;
      
      // จัดวางข้อมูลลงคอลัมน์ B ถึง N ตามกฎเหล็กและสูตรออโต้ของน้องเจน
      var rowValues = [
        timeVal,                                      // B (เวลา)
        battFormula,                                  // C (แบตเตอรี่ที่ใช้)
        distFormula,                                  // D (ระยะทาง)
        incVal,                                       // E (รายได้ Grab)
        '',                                           // F
        tipVal,                                       // G (Tip)
        "=sum(E" + targetRow + ":G" + targetRow + ")",  // H (ยอดรวมวัน)
        "=IFERROR(H" + targetRow + "/D" + targetRow + ", 0)", // I (บาท/กิโล)
        "=IFERROR(H" + targetRow + "/(B" + targetRow + "*1440)*60, 0)", // J (บาท/ชั่วโมง)
        "=IF(I" + targetRow + ">0, 1, 0)",            // K (ตัวนับวันวิ่ง)
        "",                                           // L
        "=H" + targetRow + "*10%",                    // M (หัก VAT 10% ออโต้)
        "=D" + targetRow + "*2"                       // N (Double Dist ออโต้)
      ];
      
      sheet.getRange("B" + targetRow + ":N" + targetRow).setValues([rowValues]);
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "message": "บันทึกข้อมูล Grab ลงแท็บ " + tabName + " แถวที่ " + targetRow + " สำเร็จแล้วจ้า!"
      })).setMimeType(ContentService.MimeType.JSON);
      
    } else if (sheetType === "general" || sheetType === "expense") {
      // บันทึกรายรับ/รายจ่ายลงในแท็บปฏิทินรายวันของแผ่นงานรายรับ-รายจ่ายทั่วไป Feltz Studio
      var dateKey = dayStr + "/" + monthStr + "/" + yearStr;
      
      // ค้นหาแถววันที่ในคอลัมน์ A (แถวที่ 2 ถึง 32)
      var range = sheet.getRange("A2:A32");
      var values = range.getDisplayValues();
      var targetRow = null;
      
      for (var i = 0; i < values.length; i++) {
        var val = values[i][0];
        if (val && val.toString().indexOf(dateKey) !== -1) {
          // ตรวจสอบข้อมูลซ้ำเพื่อป้องกันการบันทึกทับโดยไม่ตั้งใจ
          if (sheetType === "general") {
            var existingDesc = sheet.getRange("B" + (i + 2)).getValue();
            if (existingDesc && existingDesc.toString().trim() !== "") {
              return ContentService.createTextOutput(JSON.stringify({
                "status": "error",
                "message": "ข้อมูลรายรับของวันที่ " + dateKey + " มีการบันทึกอยู่แล้วในตารางชีตนะแก!"
              })).setMimeType(ContentService.MimeType.JSON);
            }
          } else { // expense
            var existingDesc = sheet.getRange("D" + (i + 2)).getValue();
            if (existingDesc && existingDesc.toString().trim() !== "") {
              return ContentService.createTextOutput(JSON.stringify({
                "status": "error",
                "message": "ข้อมูลรายจ่ายของวันที่ " + dateKey + " มีการบันทึกอยู่แล้วในตารางชีตนะแก!"
              })).setMimeType(ContentService.MimeType.JSON);
            }
          }
          targetRow = i + 2;
          break;
        }
      }
      
      if (!targetRow) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "ไม่พบแถวสำหรับวันที่ " + dateKey + " ในตารางจ้า"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      if (sheetType === "general") {
        var genDescVal = data.genDesc || "";
        var amountVal = data.amount;
        var hasTax = data.hasTaxWithholding || false;
        
        // เขียนข้อมูลลงคอลัมน์ B (รายละเอียดงาน) และ C (รายรับ)
        sheet.getRange("B" + targetRow).setValue(genDescVal);
        if (typeof amountVal === 'string' && amountVal.indexOf('=') === 0) {
          sheet.getRange("C" + targetRow).setFormula(amountVal);
        } else {
          sheet.getRange("C" + targetRow).setValue(parseFloat(amountVal || 0));
        }
        
        // บันทึก/คำนวณ หัก ณ ที่จ่าย 3% ลงคอลัมน์ F
        if (hasTax) {
          sheet.getRange("F" + targetRow).setFormula("=C" + targetRow + "*3%");
        } else {
          sheet.getRange("F" + targetRow).setValue("");
        }
        
        return ContentService.createTextOutput(JSON.stringify({
          "status": "success",
          "message": "บันทึกรายรับ Feltz Studio ลงแท็บ " + tabName + " แถวที่ " + targetRow + " สำเร็จแล้วจ้า!"
        })).setMimeType(ContentService.MimeType.JSON);
      } else { // expense
        var expDescVal = data.expDesc || "";
        var amountVal = data.amount;
        
        // เขียนข้อมูลลงคอลัมน์ D (รายละเอียดรายจ่าย) และ E (รายจ่าย)
        sheet.getRange("D" + targetRow).setValue(expDescVal);
        if (typeof amountVal === 'string' && amountVal.indexOf('=') === 0) {
          sheet.getRange("E" + targetRow).setFormula(amountVal);
        } else {
          sheet.getRange("E" + targetRow).setValue(parseFloat(amountVal || 0));
        }
        
        return ContentService.createTextOutput(JSON.stringify({
          "status": "success",
          "message": "บันทึกรายจ่าย Feltz Studio ลงแท็บ " + tabName + " แถวที่ " + targetRow + " สำเร็จแล้วจ้า!"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
    } else {
      return ContentService.createTextOutput(JSON.stringify({
        "status": "error",
        "message": "ไม่รองรับประเภทธุรกรรม " + sheetType + " นะแก"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      "status": "error",
      "message": "เกิดข้อผิดพลาดในการเขียนชีต: " + error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}

// ฟังก์ชันบันทึกรายจ่ายประจำเดือนอัตโนมัติ ทุกวันที่ 1 ของเดือน
function autoRecordMonthlyFixedCosts() {
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  var configSheet = spreadsheet.getSheetByName("ตั้งค่า Fix Cost");
  if (!configSheet) {
    Logger.log("ไม่พบแท็บ 'ตั้งค่า Fix Cost' นะแก!");
    return;
  }
  
  // ดึงข้อมูลรายการจาก A2:B7 (หรือจนสุดที่มีข้อมูล)
  var lastRow = configSheet.getLastRow();
  if (lastRow < 2) {
    Logger.log("ไม่มีข้อมูลรายการในแท็บ 'ตั้งค่า Fix Cost' นะแก!");
    return;
  }
  
  var range = configSheet.getRange(2, 1, lastRow - 1, 2);
  var data = range.getValues();
  
  var descriptions = [];
  var amounts = [];
  
  for (var i = 0; i < data.length; i++) {
    var item = data[i][0];
    var amount = data[i][1];
    if (item && item.toString().trim() !== "") {
      descriptions.push(item.toString().trim());
      amounts.push(amount || 0);
    }
  }
  
  if (descriptions.length === 0) {
    Logger.log("ไม่พบรายการ Fix Cost");
    return;
  }
  
  var descText = descriptions.join("\n");
  var amountFormula = "=" + amounts.join("+");
  
  // ค้นหาแท็บของเดือนปัจจุบัน
  var now = new Date();
  var monthStr = (now.getMonth() + 1).toString().padStart(2, '0');
  var monthsTh = {
    '01': 'ม.ค.', '02': 'ก.พ.', '03': 'มี.ค.', '04': 'เม.ย.',
    '05': 'พ.ค.', '06': 'มิ.ย.', '07': 'ก.ค.', '08': 'ส.ค.',
    '09': 'ก.ย.', '10': 'ต.ค.', '11': 'พ.ย.', '12': 'ธ.ค.'
  };
  var tabName = monthsTh[monthStr];
  var sheet = spreadsheet.getSheetByName(tabName);
  if (!sheet) {
    Logger.log("ไม่พบแท็บเดือน " + tabName);
    return;
  }
  
  // วันที่ 1 ของเดือนคือวันที่เป้าหมาย ค้นหาในคอลัมน์ A (แถวที่ 2 ถึง 32)
  var dayStr = "01";
  var yearStr = now.getFullYear().toString();
  var dateKey = dayStr + "/" + monthStr + "/" + yearStr;
  
  var aRange = sheet.getRange("A2:A32");
  var aValues = aRange.getDisplayValues();
  var targetRow = null;
  
  for (var i = 0; i < aValues.length; i++) {
    var val = aValues[i][0];
    if (val && val.toString().indexOf(dateKey) !== -1) {
      targetRow = i + 2;
      break;
    }
  }
  
  if (!targetRow) {
    Logger.log("ไม่พบแถวสำหรับวันที่ " + dateKey);
    return;
  }
  
  // เขียนข้อมูลลงคอลัมน์ D (รายละเอียดรายจ่าย) และ E (รายจ่าย)
  sheet.getRange("D" + targetRow).setValue(descText);
  sheet.getRange("E" + targetRow).setFormula(amountFormula);
  Logger.log("บันทึก Fix Cost อัตโนมัติในแท็บ " + tabName + " แถวที่ " + targetRow + " สำเร็จแล้วแก!");
}
```

3. กดเซฟโครงการ (คลิกรูป **แผ่นบันทึกข้อมูล/Disk** หรือกด `Cmd + S` บน Mac)

### ขั้นตอนที่ 3: เปิดการติดตั้งใช้งาน (Deploy Web App)
1. กดปุ่มสีน้ำเงินด้านขวาบนเลือก **การใช้งานได้จริง (Deploy)** > **การติดตั้งใช้งานใหม่ (New deployment)**
2. คลิกรูป **ฟันเฟือง (Gear)** ข้างคำว่าเลือกประเภท (Select type) แล้วเลือก **เว็บแอป (Web app)**
3. ตั้งค่าหน้าต่าง Deploy ดังนี้:
   - **คำอธิบาย:** บันทึกรายรับ v1.0
   - **เรียกใช้ในฐานะ (Execute as):** เลือก **ฉัน (อีเมลบัญชีของแกเอง)**
   - **ผู้มีสิทธิ์เข้าถึง (Who has access):** เลือก **ทุกคน (Anyone)** *(สำคัญมาก! หากไม่เลือกเป็นทุกคน ตัวเบราว์เซอร์ภายในเครื่องจะยิง API เข้ามาบันทึกไม่ได้เนื่องจากติดสิทธิ์ล็อกอิน)*
4. กดปุ่ม **การติดตั้งใช้งาน (Deploy)** สีน้ำเงินด้านล่าง
5. หาก Google โหลดหน้าต่างขอสิทธิ์การเข้าถึงข้อมูล (Authorize Access) ให้แกกดให้สิทธิ์ และหากมีหน้าต่างเตือนความปลอดภัยขึ้นมา ให้เลือก **Advanced (ขั้นสูง)** > **Go to ... (ปลอดภัย/เข้าสู่ลิงก์สคริปต์)**
6. เมื่อดีพลอยเสร็จสิ้น ระบบจะให้ URL มา ให้แกทำการคัดลอก **URL ของเว็บแอป (Web app URL)** (ลิงก์จะยาวๆ ลงท้ายด้วย `/exec`)

### ขั้นตอนที่ 4: นำ URL มากรอกในตัวแอป
1. ดับเบิ้ลคลิกเปิดไฟล์ `index.html` ของเว็บแอปในเบราว์เซอร์
2. ไปที่เมนูด้านซ้าย เลือกแท็บ **การตั้งค่าเชื่อมต่อ**
3. วางลิงก์ URL ที่ก็อปปี้มาลงในช่อง **Google Apps Script Web App URL**
4. กดปุ่ม **บันทึกการตั้งค่าลิงก์** สีส้ม
5. เสร็จเรียบร้อยจ้า! หลังจากนี้แกจะบันทึก Grab หรือ บันทึกรายรับทั่วไป ข้อมูลก็จะยิงตรงลงคอลัมน์และคำนวณสูตรอัปเดตแผ่นชีตให้ทันทีแก!

### ขั้นตอนที่ 5: ตั้งค่าทริกเกอร์บันทึก Fix Cost อัตโนมัติรายเดือน
เพื่อให้ระบบสามารถรันฟังก์ชัน `autoRecordMonthlyFixedCosts()` เพื่อคีย์ค่าใช้จ่ายประจำเดือน (Fix Cost) ลงในชีตของแกอัตโนมัติในวันที่ 1 ของทุกเดือน ให้ทำดังนี้จ้า:
1. ในหน้า **Apps Script** ด้านซ้ายมือ ให้คลิกไอคอน **ทริกเกอร์ (Triggers)** (รูปนาฬิกาปลุก ⏰)
2. คลิกปุ่ม **+ เพิ่มทริกเกอร์ (+ Add Trigger)** ที่มุมขวาล่าง
3. ตั้งค่าทริกเกอร์ในหน้าต่างใหม่ดังนี้:
   - **เลือกฟังก์ชันที่จะรัน (Choose which function to run):** เลือก `autoRecordMonthlyFixedCosts`
   - **เลือกการใช้ในการจัดเตรียมการใช้งาน (Choose which deployment should run):** เลือก `Head`
   - **เลือกแหล่งที่มาของเหตุการณ์ (Select event source):** เลือก **ตามเวลา (Time-driven)**
   - **เลือกประเภททริกเกอร์ตามเวลา (Select type of time based trigger):** เลือก **ทริกเกอร์รายเดือน (Month timer)**
   - **เลือกวันในแต่ละเดือน (Select day of month):** เลือก **1**
   - **เลือกเวลาของวัน (Select time of day):** แนะนำช่วง **เที่ยงคืนถึงตี 1 (Midnight to 1 AM)** หรือตามที่แกสะดวก
4. กดปุ่ม **บันทึก (Save)** สีน้ำเงินด้านขวา
5. เรียบร้อยจ้า! ทุกวันที่ 1 ของเดือนเวลาเที่ยงคืน ระบบจะไปดึงค่าในแท็บ `'ตั้งค่า Fix Cost'` มารวมเป็นสูตรบวกเลขและคีย์ลงในช่องรายจ่ายของวันที่ 1 ประจำเดือนนั้นให้แกแบบอัตโนมัติเลยนะแก!

---

## 🎨 รายละเอียดฟีเจอร์เด่น
- **สลับ Light/Dark Mode:** ระบบจำค่าโหมดสว่างและโหมดมืด (CI Sunset Glow) ไว้ในเครื่องออโต้
- **ประวัติการบันทึกเครื่อง:** แสดงประวัติการทำธุรกรรม 100 รายการล่าสุดที่กรอกผ่านหน้าต่างนี้แบบเรียลไทม์ (เซฟลงหน่วยความจำ `localStorage` ของเครื่องแกเอง ไม่รั่วไหล)
- **ระบบจัดการและเลือกด่วน Fix Cost:** สามารถจัดเก็บ จัดการ เพิ่ม หรือลบรายการ Fix Cost มาตรฐานหลายรายการได้โดยตรงผ่านหน้าการตั้งค่า และระบบจะซิงค์เป็นตัวเลือกด่วน (Select Dropdown) ที่หัวกริดฟอร์มรายจ่ายเพื่อกดป้อนข้อมูลอัตโนมัติได้ทันที
- **ระบบลบแบตเตอรี่อัจฉริยะ:** ช่องแบตเตอรี่ในหน้าฟอร์ม Grab รองรับการคำนวณเช่นกัน เช่น แกพิมพ์ `100-45` ระบบจะนำไปแปลงเป็นสูตร `=(100-45)/100` ลงชีตให้เรียบร้อยจ้า
- **รองรับการบันทึกรายจ่าย (Expense):** สามารถเลือกแท็บบันทึกรายจ่าย ป้อนรายละเอียดและจำนวนเงิน (หรือสูตรคำนวณ เช่น 200+50) เพื่อส่งข้อมูลเขียนลงคอลัมน์ D (รายละเอียดรายจ่าย) และ E (รายจ่าย) ใน Google Sheets ได้โดยตรงผ่านระบบ Apps Script ตัวเดียวกันกับรายรับ Feltz Studio จ้า
