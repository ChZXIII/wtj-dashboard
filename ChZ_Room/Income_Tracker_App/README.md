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
    var sheetType = data.type; // "general", "expense", "grab", "fetch_summary" หรือ "upload_html" หรือ ธุรกรรมปฏิทิน
    
    // รองรับการแปลง HTML เป็น PDF และอัปโหลดขึ้น Google Drive
    if (sheetType === "upload_html") {
      var htmlContent = data.htmlContent;
      var pdfName = data.pdfName;
      var docType = data.docType;
      var parentFolderId = data.parentFolderId;
      var pdfShiftApiKey = data.pdfShiftApiKey;
      
      if (!htmlContent) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "ไม่พบ htmlContent ในข้อมูลที่ส่งเข้ามานะแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      if (!parentFolderId) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "ไม่พบ parentFolderId ในข้อมูลที่ส่งเข้ามานะแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      if (!pdfShiftApiKey) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "ไม่พบ PDFShift API Key ในข้อมูลที่ส่งเข้ามานะแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      var convertResult = convertHtmlToPdfWithPdfShift(htmlContent, pdfShiftApiKey, pdfName);
      if (!convertResult.success) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "การแปลง HTML เป็น PDF ด้วย PDFShift API ล้มเหลวนะแก! รายละเอียด: " + convertResult.error
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      var pdfBlob = convertResult.blob;
      var pdfUrl = saveBlobToFolder(pdfBlob, docType, parentFolderId);
      if (!pdfUrl) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "เซฟไฟล์ PDF ลงโฟลเดอร์ล้มเหลว (อาจเกิดจากสิทธิ์เข้าถึง หรือโฟลเดอร์ไม่ถูกต้องนะแก!)"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "message": "อัปโหลดไฟล์ PDF (ผ่าน PDFShift) ขึ้น Google Drive เรียบร้อยแล้วแก!",
        "pdfUrl": pdfUrl
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    var spreadsheetId = data.spreadsheetId; // ID ของ Google Sheets ที่ส่งมาจากเว็บแอป
    
    if (!spreadsheetId) {
      return ContentService.createTextOutput(JSON.stringify({
        "status": "error",
        "message": "ไม่พบ Spreadsheet ID ในชุดข้อมูลที่ส่งมานะแก!"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // 1. รองรับการดึงสรุปข้อมูลยอดสะสม 12 เดือน (fetch_summary)
    if (sheetType === "fetch_summary") {
      var activeSpreadsheet = SpreadsheetApp.openById(spreadsheetId);
      var months = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'];
      var summaryData = [];
      
      for (var m = 0; m < months.length; m++) {
        var mName = months[m];
        var mSheet = activeSpreadsheet.getSheetByName(mName);
        
        if (mSheet) {
          var lastRow = mSheet.getLastRow();
          var colBValues = mSheet.getRange("B1:B" + lastRow).getValues();
          var totalRowIdx = -1;
          for (var r = 0; r < colBValues.length; r++) {
            if (colBValues[r][0] && colBValues[r][0].toString().trim() === "ยอดรวมทั้งเดือน") {
              totalRowIdx = r + 1; // แปลงเป็น 1-indexed
              break;
            }
          }
          
          var totalIncome = 0;
          var totalExpense = 0;
          var netProfit = 0;
          var totalSavings = 0;
          var cumulativeProfit = 0;
          var fixedCosts = [];
          
          if (totalRowIdx !== -1) {
            totalIncome = parseFloat(mSheet.getRange("C" + totalRowIdx).getValue() || 0);
            totalExpense = parseFloat(mSheet.getRange("E" + totalRowIdx).getValue() || 0);
            netProfit = parseFloat(mSheet.getRange("C" + (totalRowIdx + 1)).getValue() || (totalIncome - totalExpense));
            totalSavings = parseFloat(mSheet.getRange("C" + (totalRowIdx + 2)).getValue() || (totalIncome * 0.1));
            cumulativeProfit = parseFloat(mSheet.getRange("C" + (totalRowIdx + 4)).getValue() || 0);
            
            var maxDataRow = totalRowIdx - 2;
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
            cumulativeProfit: cumulativeProfit,
            fixedCosts: fixedCosts
          });
        } else {
          summaryData.push({
            month: mName,
            income: 0,
            expense: 0,
            profit: 0,
            savings: 0,
            cumulativeProfit: 0,
            fixedCosts: []
          });
        }
      }
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "data": summaryData
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // 2. ดึงเหตุการณ์ในปฏิทิน (fetch_calendar_events)
    if (sheetType === "fetch_calendar_events") {
      var start = new Date(data.startDate);
      var end = new Date(data.endDate);
      var cal = CalendarApp.getDefaultCalendar();
      var events = cal.getEvents(start, end);
      var eventList = [];
      for (var i = 0; i < events.length; i++) {
        var ev = events[i];
        eventList.push({
          id: ev.getId(),
          title: ev.getTitle(),
          startTime: ev.getStartTime().toISOString(),
          endTime: ev.getEndTime().toISOString(),
          colorId: ev.getColor() || "",
          description: ev.getDescription() || ""
        });
      }
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "data": eventList
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // 3. สร้างเหตุการณ์ใหม่ (create_calendar_event)
    if (sheetType === "create_calendar_event") {
      var title = data.title;
      var start = new Date(data.startTime);
      var end = new Date(data.endTime);
      var desc = data.description || "";
      var colorId = data.colorId;
      
      var cal = CalendarApp.getDefaultCalendar();
      var event = cal.createEvent(title, start, end, {description: desc});
      if (colorId) {
        event.setColor(getEventColorEnum(colorId));
      }
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "eventId": event.getId(),
        "message": "สร้างกิจกรรมในปฏิทินสำเร็จแล้วแก!"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // 4. อัปเดตสีของเหตุการณ์โดยตรง (update_calendar_event_color)
    if (sheetType === "update_calendar_event_color") {
      var eventId = data.eventId;
      var colorId = data.colorId;
      var cal = CalendarApp.getDefaultCalendar();
      var event = cal.getEventById(eventId);
      if (event) {
        event.setColor(getEventColorEnum(colorId));
        return ContentService.createTextOutput(JSON.stringify({
          "status": "success",
          "message": "อัปเดตสีกิจกรรมในปฏิทินสำเร็จแล้วแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      } else {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "ไม่พบกิจกรรมที่ระบุนะแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      }
    }
    
    // ตรวจสอบความถูกต้องของ data.date อย่างปลอดภัยป้องกัน TypeError: split บนมือถือ
    if (!data || !data.date || typeof data.date !== 'string' || data.date.split('/').length !== 3) {
      return ContentService.createTextOutput(JSON.stringify({
        "status": "error",
        "message": "ไม่พบข้อมูลวันที่ หรือรูปแบบวันที่ผิดรูปแบบนะแก! (คาดหวัง DD/MM/YYYY)"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    var activeSpreadsheet = SpreadsheetApp.openById(spreadsheetId);
    
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
      var range = sheet.getRange("A3:A33");
      var values = range.getDisplayValues();
      var targetRow = null;
      
      for (var i = 0; i < values.length; i++) {
        var val = values[i][0];
        if (val && val.toString().indexOf(dateKey) !== -1) {
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
      
      var rowValues = [
        timeVal,
        battFormula,
        distFormula,
        incVal,
        '',
        tipVal,
        "=sum(E" + targetRow + ":G" + targetRow + ")",
        "=IFERROR(H" + targetRow + "/D" + targetRow + ", 0)",
        "=IFERROR(H" + targetRow + "/(B" + targetRow + "*1440)*60, 0)",
        "=IF(I" + targetRow + ">0, 1, 0)",
        "",
        "=H" + targetRow + "*10%",
        "=D" + targetRow + "*2"
      ];
      
      sheet.getRange("B" + targetRow + ":N" + targetRow).setValues([rowValues]);
      autoResizeSheetColumns(sheet);
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "message": "บันทึกข้อมูล Grab ลงแท็บ " + tabName + " แถวที่ " + targetRow + " สำเร็จแล้วจ้า!"
      })).setMimeType(ContentService.MimeType.JSON);
      
    } else if (sheetType === "general" || sheetType === "expense") {
      var dateKey = dayStr + "/" + monthStr + "/" + yearStr;
      var range = sheet.getRange("A2:A32");
      var values = range.getDisplayValues();
      var targetRow = null;
      
      for (var i = 0; i < values.length; i++) {
        var val = values[i][0];
        if (val && val.toString().indexOf(dateKey) !== -1) {
          if (sheetType === "general") {
            var existingDesc = sheet.getRange("B" + (i + 2)).getValue();
            if (existingDesc && existingDesc.toString().trim() !== "") {
              return ContentService.createTextOutput(JSON.stringify({
                "status": "error",
                "message": "ข้อมูลรายรับของวันที่ " + dateKey + " มีการบันทึกอยู่แล้วในตารางชีตนะแก!"
              })).setMimeType(ContentService.MimeType.JSON);
            }
          } else {
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
        
        sheet.getRange("B" + targetRow).setValue(genDescVal);
        if (typeof amountVal === 'string' && amountVal.indexOf('=') === 0) {
          sheet.getRange("C" + targetRow).setFormula(amountVal);
        } else {
          sheet.getRange("C" + targetRow).setValue(parseFloat(amountVal || 0));
        }
        
        if (hasTax) {
          sheet.getRange("F" + targetRow).setFormula("=C" + targetRow + "*3%");
        } else {
          sheet.getRange("F" + targetRow).setValue("");
        }
        
        // หากมี calendarEventId ส่งเข้ามา ให้แก้ไขสีกิจกรรมเป็น Sage Green (ID 2)
        if (data.calendarEventId) {
          try {
            var cal = CalendarApp.getDefaultCalendar();
            var event = cal.getEventById(data.calendarEventId);
            if (event) {
              event.setColor(getEventColorEnum(2)); // Sage Green (ID 2)
            }
          } catch (calErr) {
            Logger.log("ไม่สามารถอัปเดตสีกิจกรรมในปฏิทินได้: " + calErr.toString());
          }
        }
        
        autoResizeSheetColumns(sheet);
        
        return ContentService.createTextOutput(JSON.stringify({
          "status": "success",
          "message": "บันทึกรายรับ Feltz Studio ลงแท็บ " + tabName + " แถวที่ " + targetRow + " สำเร็จแล้วจ้า!"
        })).setMimeType(ContentService.MimeType.JSON);
      } else {
        var expDescVal = data.expDesc || "";
        var amountVal = data.amount;
        
        sheet.getRange("D" + targetRow).setValue(expDescVal);
        if (typeof amountVal === 'string' && amountVal.indexOf('=') === 0) {
          sheet.getRange("E" + targetRow).setFormula(amountVal);
        } else {
          sheet.getRange("E" + targetRow).setValue(parseFloat(amountVal || 0));
        }
        autoResizeSheetColumns(sheet);
        
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

// ฟังก์ชันแปลง Color ID เป็นค่า Enum ของ Google Apps Script
function getEventColorEnum(colorId) {
  var cid = parseInt(colorId, 10);
  if (cid === 2) return CalendarApp.EventColor.PALE_GREEN;
  if (cid === 5) return CalendarApp.EventColor.YELLOW;
  if (cid === 11) return CalendarApp.EventColor.RED;
  return CalendarApp.EventColor.PALE_GREEN; // default
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
  autoResizeSheetColumns(sheet); // ปรับความกว้างคอลัมน์ออโต้
  Logger.log("บันทึก Fix Cost อัตโนมัติในแท็บ " + tabName + " แถวที่ " + targetRow + " สำเร็จแล้วแก!");
}

// ฟังก์ชันปรับขนาดความกว้างคอลัมน์อัจฉริยะโดยลอกเลียนแบบขนาดจากแท็บต้นแบบโดยตรง
function autoResizeSheetColumns(sheet) {
  if (!sheet) return;
  var spreadsheet = sheet.getParent();
  var lastCol = sheet.getLastColumn();
  if (lastCol <= 0) return;
  
  // ค้นหาแท็บต้นแบบเพื่อใช้อั่งอิงความกว้าง (หา "ต้นแบบ" -> "Template" -> "ม.ค." -> หรือชีตแรกสุดของแผ่นงาน)
  var templateSheet = spreadsheet.getSheetByName("ต้นแบบ") || 
                      spreadsheet.getSheetByName("Template") || 
                      spreadsheet.getSheetByName("ม.ค.") ||
                      spreadsheet.getSheets()[0];
  
  // ถ้ามีแท็บต้นแบบ และแท็บต้นแบบไม่ใช่แท็บปัจจุบันที่เรากำลังปรับขนาดอยู่
  if (templateSheet && templateSheet.getName() !== sheet.getName()) {
    // ก็อปปี้ความกว้างคอลัมน์จากแท็บต้นแบบมาใส่แท็บปัจจุบันตรงๆ เลยเพื่อความแม่นยำ
    var templateLastCol = templateSheet.getLastColumn();
    for (var c = 1; c <= Math.min(lastCol, templateLastCol); c++) {
      var templateW = templateSheet.getColumnWidth(c);
      if (templateW > 50) {
        sheet.setColumnWidth(c, templateW);
      }
    }
  } else {
    // แท็บต้นแบบจะไม่ถูกบังคับปรับขนาดคอลัมน์อัตโนมัติ เพื่อให้ผู้ใช้สามารถกำหนดขนาดความกว้างคอลัมน์ได้อย่างอิสระ
  }
}

// ฟังก์ชันสำหรับรันใน Apps Script เพื่อจัดหน้าและคัดลอกขนาดคอลัมน์จากต้นแบบไปยังทุกแท็บทันที!
function beautifyAllSheetsNow() {
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  
  var sheets = spreadsheet.getSheets();
  var count = 0;
  for (var i = 0; i < sheets.length; i++) {
    var sheet = sheets[i];
    // ข้ามหน้าการตั้งค่าที่ไม่ใช่ปฏิทินบัญชีรายเดือน
    if (sheet.getName() !== "ตั้งค่า Fix Cost") {
      autoResizeSheetColumns(sheet);
      count++;
    }
  }
  Logger.log("ปรับขนาดทุกชีตจำนวน " + count + " แท็บ โดยอิงตามต้นแบบเรียบร้อยแล้วแก!");
}

// ฟังก์ชันแปลง HTML เป็น PDF ด้วย API ของ PDFShift
function convertHtmlToPdfWithPdfShift(htmlContent, apiKey, filename) {
  var url = "https://api.pdfshift.io/v3/convert/pdf";
  var payload = {
    source: htmlContent,
    sandbox: false,
    delay: 1000
  };
  var options = {
    method: "post",
    contentType: "application/json",
    headers: {
      "X-API-Key": apiKey
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };
  try {
    var response = UrlFetchApp.fetch(url, options);
    var code = response.getResponseCode();
    var responseText = response.getContentText();
    if (code === 200 || code === 201) {
      var blob = response.getBlob();
      blob.setName(filename || "document.pdf");
      return { success: true, blob: blob };
    } else {
      return { success: false, error: "HTTP Code: " + code + ", Details: " + responseText };
    }
  } catch (e) {
    return { success: false, error: "Network/Script Exception: " + e.toString() };
  }
}

// ฟังก์ชันบันทึก Blob PDF ลงในโฟลเดอร์ Google Drive
function saveBlobToFolder(blob, docType, parentFolderId) {
  if (!blob || !parentFolderId) return null;
  var parentFolder = DriveApp.getFolderById(parentFolderId);
  if (!parentFolder) return null;
  
  var prefix = "";
  if (docType === "quotation") prefix = "01";
  else if (docType === "invoice") prefix = "02";
  else if (docType === "receipt") prefix = "03";
  
  var subFolder = null;
  var folders = parentFolder.getFolders();
  while (folders.hasNext()) {
    var folder = folders.next();
    var name = folder.getName();
    if (name.indexOf(prefix + "_") === 0 || name.indexOf(prefix + " ") === 0 || name === prefix) {
      subFolder = folder;
      break;
    }
  }
  
  var uploadFolder = subFolder || parentFolder;
  var file = uploadFolder.createFile(blob);
  try {
    file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  } catch (sharingError) {
    Logger.log("ไม่สามารถตั้งค่าการแชร์ไฟล์ได้: " + sharingError.toString());
  }
  return file.getUrl();
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
