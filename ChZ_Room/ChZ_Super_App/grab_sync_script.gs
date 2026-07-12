/**
 * Grab Income Sync Script (v1.0)
 * วัตถุประสงค์: ซิงค์ข้อมูลรายได้ Grab (โครงสร้าง 6 คอลัมน์) สำหรับ Grab Spreadsheet
 * พัฒนาโดย: น้องคิว (q_developer)
 */

var THAI_MONTHS = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'];

function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.tryLock(10000); // Lock script 10 seconds to prevent race conditions
  
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return createJsonResponse({
        "status": "error",
        "message": "ไม่พบ Payload หรือข้อมูลที่ส่งเข้ามานะแก!"
      });
    }

    var data = JSON.parse(e.postData.contents);
    var spreadsheetId = data.spreadsheetId || data.grabSpreadsheetId;
    
    if (!spreadsheetId) {
      return createJsonResponse({
        "status": "error",
        "message": "ไม่พบ Spreadsheet ID หรือ grabSpreadsheetId ในพารามิเตอร์ที่ส่งเข้ามานะแก!"
      });
    }
    
    var activeSpreadsheet = SpreadsheetApp.openById(spreadsheetId);
    
    // type === 'grab'
    if (data.type === 'grab') {
      var date = data.date; // DD/MM/YYYY
      var distance = parseFloat(data.distance) || 0;
      var amount = parseFloat(data.amount) || 0;
      var tip = parseFloat(data.tip) || 0;
      var battery = parseFloat(data.battery) || 0;
      var workingHours = data.workingHours || '0:00';
      
      var sheetName = getMonthNameFromDateStr(date);
      var grabSheet = activeSpreadsheet.getSheetByName(sheetName);
      
      var parts = date.split('/');
      var day = parseInt(parts[0], 10);
      var month = parseInt(parts[1], 10);
      var year = parseInt(parts[2], 10);
      
      if (!grabSheet) {
        grabSheet = activeSpreadsheet.insertSheet(sheetName);
        var headers = ["วันที่", "ระยะทาง", "ยอดวิ่ง", "ทิป", "แบตเตอรี่", "เวลาทำงาน", "รายได้รวม", "เงินเก็บ 10%", "บาท/Km", "บาท/hrs"];
        grabSheet.appendRow(headers);
        
        var daysInMonth = new Date(year, month, 0).getDate();
        var rowsData = [];
        for (var d = 1; d <= daysInMonth; d++) {
          var dayStr = (d < 10 ? '0' : '') + d;
          var monthStr = (month < 10 ? '0' : '') + month;
          var dateFormatted = dayStr + '/' + monthStr + '/' + year;
          var rowNum = d + 1;
          var formulaG = "=C" + rowNum + "+D" + rowNum;
          var formulaH = "=G" + rowNum + "*0.1";
          var formulaI = "=IF(B" + rowNum + ">0, G" + rowNum + "/B" + rowNum + ", 0)";
          var formulaJ = "=IF(F" + rowNum + ">0, G" + rowNum + "/(F" + rowNum + "*24), 0)";
          rowsData.push([dateFormatted, "", "", "", "", "", formulaG, formulaH, formulaI, formulaJ]);
        }
        grabSheet.getRange(2, 1, daysInMonth, 10).setValues(rowsData);
        
        // เพิ่มแถวว่างและแถวสรุปผลท้ายเดือน
        grabSheet.getRange(daysInMonth + 2, 1, 1, 10).setValues([["", "", "", "", "", "", "", "", "", ""]]);
        grabSheet.getRange(daysInMonth + 3, 1, 1, 10).setValues([["", "รวมระยะทาง", "เฉลี่ยแบต 1% วิ่งได้", "", "", "", "ยอดรวมทั้งเดือน", "รวมเงินเก็บ 10%", "เฉลี่ย บาท/Km", "เฉลี่ย บาท/ชม."]]);
        
        var lastDayRow = daysInMonth + 1;
        var formulaB = "=SUM(B2:B" + lastDayRow + ")";
        var formulaC = "=IF(SUM(E2:E" + lastDayRow + ")>0, SUM(B2:B" + lastDayRow + ")/SUM(E2:E" + lastDayRow + "), 0)";
        var formulaG = "=SUM(G2:G" + lastDayRow + ")";
        var formulaH = "=SUM(H2:H" + lastDayRow + ")";
        var formulaI_summary = "=IF(SUM(B2:B" + lastDayRow + ")>0, SUM(G2:G" + lastDayRow + ")/SUM(B2:B" + lastDayRow + "), 0)";
        var formulaJ_summary = "=IF(SUM(F2:F" + lastDayRow + ")>0, SUM(G2:G" + lastDayRow + ")/(SUM(F2:F" + lastDayRow + ")*24), 0)";
        grabSheet.getRange(daysInMonth + 4, 1, 1, 10).setValues([["", formulaB, formulaC, "", "", "", formulaG, formulaH, formulaI_summary, formulaJ_summary]]);
        
        beautifyGrabSheet(grabSheet);
      }
      
      var targetRow = day + 1; // เขียนตรงตามวัน (แถว 2 = วันที่ 1)
      grabSheet.getRange(targetRow, 2, 1, 5).setValues([[
        distance,
        amount,
        tip,
        battery,
        workingHours
      ]]);
      
      return createJsonResponse({ "status": "success" });
    }
    
    // type === 'init_grab_sheet'
    else if (data.type === 'init_grab_sheet') {
      initGrabSpreadsheet(spreadsheetId);
      return createJsonResponse({ "status": "success" });
    }
    
    // INVALID TYPE
    else {
      return createJsonResponse({
        "status": "error",
        "message": "ประเภทธุรกรรม '" + data.type + "' ไม่ถูกต้องสำหรับบอร์ด Grab นะแก!"
      });
    }
    
  } catch (error) {
    return createJsonResponse({
      "status": "error",
      "message": "เกิดข้อผิดพลาด: " + error.toString()
    });
  } finally {
    lock.releaseLock();
  }
}

// Helper: Response JSON
function createJsonResponse(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
                       .setMimeType(ContentService.MimeType.JSON);
}

// Helper: Extract Month Name from DD/MM/YYYY
function getMonthNameFromDateStr(dateStr) {
  if (!dateStr) return THAI_MONTHS[0];
  var parts = dateStr.split('/');
  if (parts.length < 2) return THAI_MONTHS[0];
  var mIdx = parseInt(parts[1], 10) - 1;
  return getMonthName(mIdx);
}

// Helper: Get Month Name from index
function getMonthName(monthIndex) {
  if (monthIndex >= 0 && monthIndex < 12) {
    return THAI_MONTHS[monthIndex];
  }
  return THAI_MONTHS[0];
}

// Helper: Beautify Grab Sheet with Batch formatting
function beautifyGrabSheet(sheet) {
  var lastCol = sheet.getLastColumn();
  if (lastCol === 0) return;
  var headers = sheet.getRange(1, 1, 1, lastCol);
  headers.setFontWeight("bold")
         .setBackground("#1e293b") // สีน้ำเงินเข้ม Slate/Navy
         .setFontColor("#ffffff") // ฟอนต์สีขาว
         .setHorizontalAlignment("center")
         .setVerticalAlignment("middle")
         .setFontSize(10)
         .setFontFamily("Google Sans Code"); // เปลี่ยนเป็น Google Sans Code ตามคำสั่งเพิ่มเติม
  
  sheet.setRowHeight(1, 30);
  sheet.setFrozenRows(1);
  
  var lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    if (lastCol >= 10 && lastRow > 4) {
      // โครงสร้างชีตแบบใหม่ (10 คอลัมน์ มีแถวสรุป)
      var daysInMonth = lastRow - 4;
      var dataRange = sheet.getRange(2, 1, daysInMonth, lastCol);
      dataRange.setFontFamily("Google Sans Code")
               .setFontSize(10)
               .setVerticalAlignment("middle")
               .setHorizontalAlignment("right");
      sheet.setRowHeights(2, daysInMonth, 24);
      
      var backgrounds = [];
      for (var r = 2; r <= daysInMonth + 1; r++) {
        var rowBg = [];
        for (var c = 1; c <= lastCol; c++) {
          var bg;
          if (c === 1) {
            bg = (r % 2 === 0) ? "#f8fafc" : "#ffffff";
          } else if (c <= 6) {
            bg = (r % 2 === 0) ? "#f0fdf4" : "#ffffff";
          } else {
            bg = (r % 2 === 0) ? "#f8fafc" : "#ffffff";
          }
          rowBg.push(bg);
        }
        backgrounds.push(rowBg);
      }
      dataRange.setBackgrounds(backgrounds);
      dataRange.setBorder(true, true, true, true, true, true, "#cbd5e1", SpreadsheetApp.BorderStyle.SOLID);
      
      // เซ็ต NumberFormat ของคอลัมน์แบตเตอรี่, เวลาทำงาน, ยอดวิ่ง, ทิป และเฉลี่ย
      sheet.getRange(2, 3, daysInMonth, 2).setNumberFormat("#,##0.00"); // ยอดวิ่ง, ทิป
      sheet.getRange(2, 5, daysInMonth, 1).setNumberFormat('0" %"');
      sheet.getRange(2, 6, daysInMonth, 1).setNumberFormat('[hh]:mm:ss');
      sheet.getRange(2, 7, daysInMonth, 4).setNumberFormat("#,##0.00"); // รายได้รวม, เงินเก็บ 10%, บาท/Km, บาท/hrs
      
      // แถวหัวข้อสรุป (daysInMonth + 3)
      var summaryHeaderRow = daysInMonth + 3;
      var summaryHeaderRange = sheet.getRange(summaryHeaderRow, 1, 1, lastCol);
      summaryHeaderRange.setBackground("#e0f2f1")
                         .setFontColor("#004d40")
                         .setFontWeight("bold")
                         .setFontFamily("Google Sans Code")
                         .setFontSize(10)
                         .setVerticalAlignment("middle")
                         .setHorizontalAlignment("center");
      sheet.setRowHeight(summaryHeaderRow, 24);
      
      // แถวค่าสรุป (daysInMonth + 4)
      var summaryValueRow = daysInMonth + 4;
      var summaryValueRange = sheet.getRange(summaryValueRow, 1, 1, lastCol);
      summaryValueRange.setBackground("#ffffff")
                       .setFontColor("#0f172a")
                       .setFontWeight("bold")
                       .setFontFamily("Google Sans Code")
                       .setFontSize(10)
                       .setVerticalAlignment("middle")
                       .setHorizontalAlignment("center");
      sheet.setRowHeight(summaryValueRow, 24);
      
      // จัดฟอร์แมตตัวเลขในแถวสรุป
      sheet.getRange(summaryValueRow, 2).setNumberFormat("#,##0.00"); // รวมระยะทาง
      sheet.getRange(summaryValueRow, 3).setNumberFormat("0.00"); // เฉลี่ยแบต
      sheet.getRange(summaryValueRow, 7, 1, 4).setNumberFormat("#,##0.00"); // ยอดรวม, รวมเงินเก็บ 10%, เฉลี่ย Km, เฉลี่ย ชม.
      
      // ใส่เส้นขอบล้อมรอบโซนสรุปด้วยสี #cbd5e1
      var summaryZone = sheet.getRange(daysInMonth + 3, 1, 2, lastCol);
      summaryZone.setBorder(true, true, true, true, true, true, "#cbd5e1", SpreadsheetApp.BorderStyle.SOLID);
    } else {
      // โครงสร้างชีตแบบเก่า (6 คอลัมน์ ไม่มีแถวสรุป)
      var dataRange = sheet.getRange(2, 1, lastRow - 1, lastCol);
      dataRange.setFontFamily("Google Sans Code")
               .setFontSize(10)
               .setVerticalAlignment("middle")
               .setHorizontalAlignment("right");
      sheet.setRowHeights(2, lastRow - 1, 24);
      
      var backgrounds = [];
      for (var r = 2; r <= lastRow; r++) {
        var rowBg = [];
        for (var c = 1; c <= lastCol; c++) {
          var bg;
          if (c === 1) {
            bg = (r % 2 === 0) ? "#f8fafc" : "#ffffff";
          } else {
            bg = (r % 2 === 0) ? "#f0fdf4" : "#ffffff";
          }
          rowBg.push(bg);
        }
        backgrounds.push(rowBg);
      }
      dataRange.setBackgrounds(backgrounds);
      dataRange.setBorder(true, true, true, true, true, true, "#cbd5e1", SpreadsheetApp.BorderStyle.SOLID);
    }
  }
  headers.setBorder(null, null, true, null, null, null, "#cbd5e1", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  var sheetName = sheet.getName();
  if (sheetName === "ม.ค.") {
    // ห้ามสคริปต์ไปขยับหรือแตะต้องความกว้างคอลัมน์ของ ม.ค. เด็ดขาด
  } else {
    var ss = sheet.getParent();
    var templateSheet = ss.getSheetByName("ม.ค.");
    if (templateSheet) {
      for (var c = 1; c <= lastCol; c++) {
        var templateW = templateSheet.getColumnWidth(c);
        sheet.setColumnWidth(c, templateW);
      }
    } else {
      sheet.autoResizeColumns(1, lastCol);
      for (var c = 1; c <= lastCol; c++) {
        var w = sheet.getColumnWidth(c);
        if (w < 90) sheet.setColumnWidth(c, 90);
      }
    }
  }
}

// Function to initialize Grab spreadsheet sheets and default row templates for 12 months in 2026
function initGrabSpreadsheet(grabSpreadsheetId) {
  var ss = SpreadsheetApp.openById(grabSpreadsheetId);
  var year = new Date().getFullYear();
  
  for (var i = 0; i < THAI_MONTHS.length; i++) {
    var sheetName = THAI_MONTHS[i];
    var sheet = ss.getSheetByName(sheetName);
    if (!sheet) {
      sheet = ss.insertSheet(sheetName);
    } else {
      sheet.clear();
    }
    
    var headers = ["วันที่", "ระยะทาง", "ยอดวิ่ง", "ทิป", "แบตเตอรี่", "เวลาทำงาน", "รายได้รวม", "เงินเก็บ 10%", "บาท/Km", "บาท/hrs"];
    sheet.appendRow(headers);
    
    var monthIndex = i;
    var daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
    
    var rowsData = [];
    for (var d = 1; d <= daysInMonth; d++) {
      var dayStr = (d < 10 ? '0' : '') + d;
      var monthStr = ((monthIndex + 1) < 10 ? '0' : '') + (monthIndex + 1);
      var dateFormatted = dayStr + '/' + monthStr + '/' + year;
      var rowNum = d + 1;
      var formulaG = "=C" + rowNum + "+D" + rowNum;
      var formulaH = "=G" + rowNum + "*0.1";
      var formulaI = "=IF(B" + rowNum + ">0, G" + rowNum + "/B" + rowNum + ", 0)";
      var formulaJ = "=IF(F" + rowNum + ">0, G" + rowNum + "/(F" + rowNum + "*24), 0)";
      rowsData.push([dateFormatted, "", "", "", "", "", formulaG, formulaH, formulaI, formulaJ]);
    }
    
    sheet.getRange(2, 1, daysInMonth, 10).setValues(rowsData);
    
    // เพิ่มแถวว่างและแถวสรุปผลท้ายเดือน
    sheet.getRange(daysInMonth + 2, 1, 1, 10).setValues([["", "", "", "", "", "", "", "", "", ""]]);
    sheet.getRange(daysInMonth + 3, 1, 1, 10).setValues([["", "รวมระยะทาง", "เฉลี่ยแบต 1% วิ่งได้", "", "", "", "ยอดรวมทั้งเดือน", "รวมเงินเก็บ 10%", "เฉลี่ย บาท/Km", "เฉลี่ย บาท/ชม."]]);
    
    var lastDayRow = daysInMonth + 1;
    var formulaB = "=SUM(B2:B" + lastDayRow + ")";
    var formulaC = "=IF(SUM(E2:E" + lastDayRow + ")>0, SUM(B2:B" + lastDayRow + ")/SUM(E2:E" + lastDayRow + "), 0)";
    var formulaG = "=SUM(G2:G" + lastDayRow + ")";
    var formulaH = "=SUM(H2:H" + lastDayRow + ")";
    var formulaI_summary = "=IF(SUM(B2:B" + lastDayRow + ")>0, SUM(G2:G" + lastDayRow + ")/SUM(B2:B" + lastDayRow + "), 0)";
    var formulaJ_summary = "=IF(SUM(F2:F" + lastDayRow + ")>0, SUM(G2:G" + lastDayRow + ")/(SUM(F2:F" + lastDayRow + ")*24), 0)";
    sheet.getRange(daysInMonth + 4, 1, 1, 10).setValues([["", formulaB, formulaC, "", "", "", formulaG, formulaH, formulaI_summary, formulaJ_summary]]);
    
    beautifyGrabSheet(sheet);
  }
  
  var defaultSheet = ss.getSheetByName("Sheet1");
  if (defaultSheet) {
    var lastRow = defaultSheet.getLastRow();
    var lastCol = defaultSheet.getLastColumn();
    if (lastRow <= 1 && lastCol <= 1) {
      var val = defaultSheet.getRange(1, 1).getValue();
      if (val === "") {
        try {
          ss.deleteSheet(defaultSheet);
        } catch (e) {}
      }
    }
  }
}
