/**
 * GHN168 Google Sheets Accounting Sync Apps Script (Generic v3.0)
 * วัตถุประสงค์: สคริปต์กลางสำหรับซิงค์ข้อมูลบัญชีลง Google Sheets แบบ Generic
 * สคริปต์นี้จะเป็น Dumb Receiver ที่คอยรับอาร์เรย์ค่าข้อมูลแถวจากฝั่ง Client และทำการบันทึก
 * ทำให้แกสามารถแก้ไขหัวตาราง โครงสร้าง ทศนิยม หรือการจัดประเภทบน Client ได้เลยโดยไม่ต้อง deploy สคริปต์ใหม่ทุกครั้ง!
 */

var INCOME_HEADERS = [
  "วันที่บันทึก (Record Date)",
  "วันที่ตามใบเสร็จ/ใบกำกับภาษี (Tax Invoice Date)",
  "เลขที่ใบกำกับภาษี / ใบเสร็จรับเงิน (Receipt / Tax Invoice No.)",
  "เลขที่ใบวางบิล (Invoice No.)",
  "ชื่อลูกค้า (Customer Name)",
  "เลขประจำตัวผู้เสียภาษีลูกค้า (Customer Tax ID)",
  "ที่อยู่ลูกค้า (Customer Address)",
  "รหัสสาขาลูกค้า (Customer Branch)",
  "รายละเอียดงาน / โครงการ (Description / Project)",
  "ยอดก่อนภาษีมูลค่าเพิ่ม (Pre-VAT Amount)",
  "ภาษีมูลค่าเพิ่ม 7% (VAT 7%)",
  "ยอดรวมภาษีมูลค่าเพิ่ม (Gross Amount)",
  "ภาษีถูกหัก ณ ที่จ่าย % (WHT Rate %)",
  "ยอดภาษีถูกหัก ณ ที่จ่าย (WHT Amount)",
  "ยอดเงินที่ได้รับจริง (Net Received)",
  "บัญชีธนาคารที่รับเงิน (Receiving Bank)",
  "สถานะการชำระเงิน (Payment Status)",
  "วันที่ได้รับเงินจริง (Actual Payment Date)",
  "สัดส่วนผู้รับผลประโยชน์ (Profit Share Distribution)",
  "ลิงก์เอกสาร Google Drive (PDF Link)",
  "ผู้บันทึกรายการ (Recorded By)",
  "หมายเหตุ (Remarks)"
];

var EXPENSE_HEADERS = [
  "วันที่บันทึก (Record Date)",
  "วันที่ตามใบเสร็จ/ใบกำกับภาษี (Tax Invoice Date)",
  "เลขที่ใบกำกับภาษี / ใบเสร็จรับเงิน (Supplier Invoice No.)",
  "ชื่อผู้ให้บริการ / คู่ค้า (Supplier Name)",
  "เลขประจำตัวผู้เสียภาษีคู่ค้า (Supplier Tax ID)",
  "ที่อยู่คู่ค้า (Supplier Address)",
  "รหัสสาขาคู่ค้า (Supplier Branch)",
  "หมวดหมู่ค่าใช้จ่าย (Expense Category)",
  "รายละเอียดค่าใช้จ่าย (Description)",
  "ยอดก่อนภาษีมูลค่าเพิ่ม (Pre-VAT Amount)",
  "ภาษีมูลค่าเพิ่ม 7% (VAT 7%)",
  "ยอดรวมภาษีมูลค่าเพิ่ม (Gross Amount)",
  "อัตราภาษีหัก ณ ที่จ่าย % (WHT Rate %)",
  "ยอดหักภาษี ณ ที่จ่าย (WHT Amount)",
  "ประเภทยื่นภาษีหัก ณ ที่จ่าย (WHT Form Type)",
  "ยอดจ่ายเงินสุทธิ (Net Paid)",
  "ช่องทางการชำระเงิน (Payment Method)",
  "สถานะการชำระเงิน (Payment Status)",
  "วันที่จ่ายเงินจริง (Actual Paid Date)",
  "เลขที่ใบรับรองหัก ณ ที่จ่าย (50 Bis No.)",
  "ลิงก์เอกสาร Google Drive (PDF Link)",
  "สถานะการยื่นภาษี (Tax Filing Status)",
  "โครงการที่ผูก (Project Link)",
  "หมายเหตุ (Remarks)"
];

var PETTY_CASH_HEADERS = [
  "เลขที่ใบสำคัญ (Voucher No.)",
  "วันที่เบิกเงิน (Date)",
  "ชื่อผู้ขอเบิก (Requester Name)",
  "หมวดหมู่ค่าใช้จ่าย (Expense Category)",
  "รายละเอียด (Description)",
  "ยอดจ่ายจริง (Amount Paid)",
  "ยอดคงเหลือ (Petty Cash Balance)",
  "ผู้อนุมัติ (Approver Name)",
  "ลิงก์ใบเสร็จ (Receipt Link)",
  "หมายเหตุ (Remarks)"
];

var PAYROLL_HEADERS = [
  "รหัสรอบจ่าย (Payroll ID)",
  "รหัสพนักงาน (Employee ID)",
  "ชื่อพนักงาน (Employee Name)",
  "เลขบัตรประชาชน (Employee Tax ID)",
  "เงินเดือน (Base Salary)",
  "ค่าตำแหน่ง/โบนัส (Allowances & Bonus)",
  "ยอดรวมรายได้ (Total Earnings)",
  "หักประกันสังคม (Social Security)",
  "หักภาษี ณ ที่จ่าย (WHT PND1)",
  "เงินหักอื่นๆ (Other Deductions)",
  "ยอดโอนจริง (Net Pay Amount)",
  "เลขบัญชี (Employee Bank Account)",
  "สถานะ (Payment Status)",
  "ลิงก์สลิป (Pay Slip Link)"
];

var BANK_REC_HEADERS = [
  "รหัสรายงาน (Reconciliation ID)",
  "รอบประจำเดือน (Statement Period)",
  "รหัสบัญชีธนาคาร (Bank Account Code)",
  "ยอด Statement ธนาคาร (Bank Statement Balance)",
  "ยอดในระบบ (Book Balance)",
  "เงินฝากระหว่างทาง (Deposit in Transit)",
  "เช็คค้างจ่าย (Outstanding Cheques)",
  "ค่าธรรมเนียมค้างบันทึก (Bank Charges)",
  "ยอดปรับปรุง Statement (Adjusted Statement Balance)",
  "ยอดปรับปรุงระบบ (Adjusted Book Balance)",
  "ส่วนต่าง (Difference Unreconciled)",
  "ผู้กระทบยอด (Reconciled By)"
];

function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.tryLock(10000); // ล็อกสคริปต์ 10 วินาทีป้องกันสัญญานยิงชนกัน
  
  try {
    var data = JSON.parse(e.postData.contents);
    var spreadsheetId = data.spreadsheetId;
    
    if (!spreadsheetId) {
      return ContentService.createTextOutput(JSON.stringify({
        "status": "error",
        "message": "ไม่พบ Spreadsheet ID ในพารามิเตอร์ที่ส่งเข้ามานะแก!"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    var activeSpreadsheet = SpreadsheetApp.openById(spreadsheetId);
    
    // ----------------------------------------------------
    // CASE 1: ซิงค์แถวข้อมูลลงแท็บใดๆ แบบ Generic
    // ----------------------------------------------------
    if (data.type === "sync") {
      var sheetName = data.sheetName;
      if (!sheetName) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "ไม่ระบุชื่อแท็บชีต (sheetName) นะแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      var sheet = activeSpreadsheet.getSheetByName(sheetName);
      if (!sheet) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "ไม่พบแท็บชีตชื่อ '" + sheetName + "' บน Google Sheets นะแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      // บันทึกหลายแถวพร้อมกัน (กรณี Split Items ในรายรับ)
      if (data.rows && Array.isArray(data.rows) && data.rows.length > 0) {
        var numRows = data.rows.length;
        var numCols = data.rows[0].length;
        sheet.getRange(sheet.getLastRow() + 1, 1, numRows, numCols).setValues(data.rows);
        beautifySheet(sheet, sheetName);
        
        return ContentService.createTextOutput(JSON.stringify({
          "status": "success",
          "message": "ซิงค์ข้อมูล " + numRows + " แถว ลงแท็บ '" + sheetName + "' เรียบร้อยแล้วแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      } 
      // บันทึกแถวเดี่ยว
      else if (data.values && Array.isArray(data.values) && data.values.length > 0) {
        sheet.appendRow(data.values);
        beautifySheet(sheet, sheetName);
        
        return ContentService.createTextOutput(JSON.stringify({
          "status": "success",
          "message": "ซิงค์ข้อมูลลงแท็บ '" + sheetName + "' เรียบร้อยแล้วแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      } 
      else {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "ไม่พบข้อมูลแถว (rows/values) ในพารามิเตอร์นะแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      }
    }
    
    // ----------------------------------------------------
    // CASE 2: เตรียมโครงสร้าง 5 แท็บหลักอัตโนมัติ (Initialize)
    // ----------------------------------------------------
    else if (data.type === "initialize") {
      var sheetsInfo = [
        { name: "รายรับ", headers: INCOME_HEADERS },
        { name: "รายจ่าย", headers: EXPENSE_HEADERS },
        { name: "เงินสดย่อย", headers: PETTY_CASH_HEADERS },
        { name: "เงินเดือน", headers: PAYROLL_HEADERS },
        { name: "กระทบยอดธนาคาร", headers: BANK_REC_HEADERS }
      ];
      
      var createdSheets = [];
      var checkedSheets = [];
      
      for (var i = 0; i < sheetsInfo.length; i++) {
        var info = sheetsInfo[i];
        var sheetName = info.name;
        var headers = info.headers;
        var sheet = activeSpreadsheet.getSheetByName(sheetName);
        
        if (!sheet) {
          sheet = activeSpreadsheet.insertSheet(sheetName);
          sheet.appendRow(headers);
          beautifySheet(sheet, sheetName);
          createdSheets.push(sheetName);
        } else {
          migrateSheetIfNeeded(sheet, headers);
          beautifySheet(sheet, sheetName);
          checkedSheets.push(sheetName);
        }
      }
      
      // ล้างข้อมูลแถวเก่าที่มีปัญหาทศนิยมยาว/ไม่มี VAT ในแท็บ "รายจ่าย"
      var expenseSheet = activeSpreadsheet.getSheetByName("รายจ่าย");
      var deletedBuggyRows = 0;
      if (expenseSheet) {
        var lastRow = expenseSheet.getLastRow();
        if (lastRow > 1) {
          var values = expenseSheet.getRange(1, 1, lastRow, expenseSheet.getLastColumn()).getValues();
          for (var r = lastRow - 1; r >= 1; r--) {
            var row = values[r];
            if (row.length > 8) {
              var desc = row[8] || "";
              if (desc.indexOf("ซื้อกล้อง") !== -1 || desc.indexOf("ค่าอาหารกองถ่ายวันนี้") !== -1) {
                expenseSheet.deleteRow(r + 1);
                deletedBuggyRows++;
              }
            }
          }
        }
      }
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "message": "เตรียมโครงสร้างชีตสำเร็จแล้วแก! (สร้างแท็บใหม่: " + createdSheets.join(", ") + " | ตรวจทานแท็บเดิม: " + checkedSheets.join(", ") + " | ล้างแถวมีปัญหาออก: " + deletedBuggyRows + " แถว)"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // INVALID TYPE
    else {
      return ContentService.createTextOutput(JSON.stringify({
        "status": "error",
        "message": "ประเภทธุรกรรม '" + data.type + "' ไม่ถูกต้องนะแก!"
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

/**
 * ฟังก์ชันช่วยตรวจสอบและไมเกรตโครงสร้างตารางข้อมูลเป็นระบบ 22/24 คอลัมน์โดยไม่ทำลายข้อมูลเดิม
 */
function migrateSheetIfNeeded(sheet, targetHeaders) {
  var lastCol = sheet.getLastColumn();
  if (lastCol === 0) {
    sheet.appendRow(targetHeaders);
    return;
  }
  
  var currentHeaders = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  var needsMigration = false;
  if (currentHeaders.length !== targetHeaders.length) {
    needsMigration = true;
  } else {
    for (var i = 0; i < targetHeaders.length; i++) {
      if (currentHeaders[i] !== targetHeaders[i]) {
        needsMigration = true;
        break;
      }
    }
  }

  if (needsMigration) {
    var lastRow = sheet.getLastRow();
    var oldValues = [];
    if (lastRow > 1) {
      oldValues = sheet.getRange(2, 1, lastRow - 1, lastCol).getValues();
    }
    
    var newValues = [];
    for (var r = 0; r < oldValues.length; r++) {
      var oldRow = oldValues[r];
      var newRow = new Array(targetHeaders.length).fill("");
      
      if (targetHeaders.length === 22) { // แท็บรายรับ (Income)
        if (lastCol === 14) {
          newRow[0] = oldRow[0]; // Record Date
          newRow[1] = oldRow[0]; // Tax Invoice Date
          newRow[2] = oldRow[1]; // Receipt No.
          newRow[3] = "-";       // Invoice No.
          newRow[4] = oldRow[2]; // Client Name
          newRow[5] = oldRow[3]; // Tax ID
          newRow[6] = "-";       // Address
          newRow[7] = "00000";   // Branch
          newRow[8] = oldRow[4]; // Detail / Project
          newRow[9] = oldRow[5]; // Pre-VAT
          newRow[10] = oldRow[6]; // VAT
          newRow[11] = (parseFloat(oldRow[5]) || 0) + (parseFloat(oldRow[6]) || 0); // Gross
          newRow[12] = 0;        // WHT Rate
          newRow[13] = oldRow[7]; // WHT Amount
          var preVat = parseFloat(oldRow[5]) || 0;
          var whtAmt = parseFloat(oldRow[7]) || 0;
          if (preVat > 0) {
            newRow[12] = Math.round((whtAmt / preVat) * 100);
          }
          newRow[14] = oldRow[8]; // Net Received
          newRow[15] = "KBank";  // Receiving Bank
          newRow[16] = "ชำระเงินแล้ว"; // Payment Status
          newRow[17] = oldRow[0]; // Actual Payment Date
          newRow[18] = "คนดีล: " + oldRow[9] + " (" + oldRow[10] + "%)";
          newRow[19] = oldRow[13]; // Google Drive PDF Link
          newRow[20] = "System (Migrated)"; // Recorded By
          newRow[21] = "ยอดเข้า บ.: " + oldRow[11] + ", จ่ายคนดีล: " + oldRow[12]; // Remarks
        } else {
          for (var c = 0; c < Math.min(lastCol, targetHeaders.length); c++) {
            newRow[c] = oldRow[c];
          }
        }
      } else if (targetHeaders.length === 24) { // แท็บรายจ่าย (Expense)
        if (lastCol === 9) {
          newRow[0] = oldRow[0]; // Record Date
          newRow[1] = oldRow[0]; // Tax Invoice Date
          newRow[2] = oldRow[1]; // Supplier Invoice No / WHT No
          newRow[3] = oldRow[2]; // Supplier Name
          newRow[4] = oldRow[3]; // Supplier Tax ID
          newRow[5] = "-";       // Address
          newRow[6] = "00000";   // Branch
          newRow[7] = "ค่าบริการจ้างทำของ"; // Category
          newRow[8] = oldRow[4]; // Description
          newRow[9] = oldRow[5]; // Pre-VAT
          newRow[10] = 0;        // VAT
          newRow[11] = oldRow[5]; // Gross Amount
          newRow[12] = 0;        // WHT %
          newRow[13] = oldRow[6]; // WHT Amount
          var grossVal = parseFloat(oldRow[5]) || 0;
          var whtVal = parseFloat(oldRow[6]) || 0;
          if (grossVal > 0) {
            newRow[12] = Math.round((whtVal / grossVal) * 100);
          }
          newRow[14] = whtVal > 0 ? "ภ.ง.ด.3" : "ไม่เข้าเกณฑ์"; // WHT Form Type
          newRow[15] = oldRow[7]; // Net Paid
          newRow[16] = "KBank";  // Payment Method
          newRow[17] = "จ่ายเงินแล้ว"; // Payment Status
          newRow[18] = oldRow[0]; // Actual Paid Date
          newRow[19] = oldRow[1]; // 50 Bis Certificate No.
          newRow[20] = oldRow[8]; // Google Drive PDF Link
          newRow[21] = "ยื่นแล้ว"; // Tax Filing Status
          newRow[22] = "";       // Project Link
          newRow[23] = "Migrated from 9-column layout";
        } else if (lastCol === 12) {
          newRow[0] = oldRow[0]; // Record Date
          newRow[1] = oldRow[0]; // Tax Invoice Date
          newRow[2] = oldRow[1]; // Supplier Invoice No / WHT No
          newRow[3] = oldRow[2]; // Supplier Name
          newRow[4] = oldRow[3]; // Supplier Tax ID
          newRow[5] = "-";       // Address
          newRow[6] = "00000";   // Branch
          newRow[7] = "ค่าบริการจ้างทำของ"; // Category
          newRow[8] = oldRow[4]; // Description
          newRow[9] = oldRow[5]; // Pre-VAT
          newRow[10] = oldRow[6]; // VAT
          newRow[11] = (parseFloat(oldRow[5]) || 0) + (parseFloat(oldRow[6]) || 0); // Gross Amount
          newRow[12] = 0;        // WHT %
          newRow[13] = oldRow[7]; // WHT Amount
          var grossVal = parseFloat(oldRow[5]) || 0;
          var whtVal = parseFloat(oldRow[7]) || 0;
          if (grossVal > 0) {
            newRow[12] = Math.round((whtVal / grossVal) * 100);
          }
          newRow[14] = oldRow[10]; // WHT Form Type
          newRow[15] = oldRow[8]; // Net Paid
          newRow[16] = "KBank";  // Payment Method
          newRow[17] = "จ่ายเงินแล้ว"; // Payment Status
          newRow[18] = oldRow[0]; // Actual Paid Date
          newRow[19] = oldRow[1]; // 50 Bis Certificate No.
          newRow[20] = oldRow[9]; // Google Drive PDF Link
          newRow[21] = "ยื่นแล้ว"; // Tax Filing Status
          newRow[22] = oldRow[11]; // Project Link
          newRow[23] = "Migrated from 12-column layout";
        } else {
          for (var c = 0; c < Math.min(lastCol, targetHeaders.length); c++) {
            newRow[c] = oldRow[c];
          }
        }
      }
      newValues.push(newRow);
    }
    
    sheet.clear();
    sheet.appendRow(targetHeaders);
    if (newValues.length > 0) {
      sheet.getRange(2, 1, newValues.length, targetHeaders.length).setValues(newValues);
    }
    
    beautifySheet(sheet, sheet.getName());
  }
}

/**
 * ฟังก์ชันช่วยจัดแต่งความสวยงามของแท็บชีตให้พรีเมียม สแกนสายตาง่าย และดูเป็นมืออาชีพ
 */
function beautifySheet(sheet, sheetName) {
  var lastCol = sheet.getLastColumn();
  if (lastCol === 0) return;

  var headers = sheet.getRange(1, 1, 1, lastCol);
  
  // 1. ตั้งค่าสีหัวตารางและข้อความแยกตามประเภทแท็บเพื่อความสแกนง่าย
  var headerBg = "#374151"; // ค่าเริ่มต้นสี Charcoal เข้ม
  var headerText = "#ffffff";
  
  if (sheetName === "รายรับ") {
    headerBg = "#ffedd5"; // สีส้มครีมสว่าง
    headerText = "#9a3412"; // ตัวหนังสือส้มแดงเข้ม
  } else if (sheetName === "รายจ่าย") {
    headerBg = "#fee2e2"; // สีแดงอ่อน
    headerText = "#991b1b"; // ตัวหนังสือแดงเข้ม
  } else if (sheetName === "เงินสดย่อย") {
    headerBg = "#dcfce7"; // สีเขียวอ่อน
    headerText = "#166534"; // ตัวหนังสือเขียวเข้ม
  } else if (sheetName === "เงินเดือน") {
    headerBg = "#f3e8ff"; // สีม่วงอ่อน
    headerText = "#581c87"; // ตัวหนังสือม่วงเข้ม
  } else if (sheetName === "กระทบยอดธนาคาร") {
    headerBg = "#e0f2fe"; // สีฟ้าอ่อน
    headerText = "#0369a1"; // ตัวหนังสือฟ้าเข้ม
  }
  
  // จัดสไตล์หัวตาราง
  headers.setFontWeight("bold")
         .setBackground(headerBg)
         .setFontColor(headerText)
         .setHorizontalAlignment("center")
         .setVerticalAlignment("middle")
         .setFontSize(10)
         .setFontFamily("Prompt");
  
  // ตั้งความสูงของแถวแรกให้ดูโปร่งพรีเมียม (30px)
  sheet.setRowHeight(1, 30);
  
  // ตรึงแถวแรก
  sheet.setFrozenRows(1);
  
  // 2. จัดแต่งสไตล์ข้อมูลในตาราง (ถ้ามีข้อมูล)
  var lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    var dataRange = sheet.getRange(2, 1, lastRow - 1, lastCol);
    
    // ตั้งฟอนต์เนื้อหา
    dataRange.setFontFamily("Inter")
             .setFontSize(10)
             .setVerticalAlignment("middle");
             
    // ปรับความสูงแถวข้อมูลทั่วไปให้มีพื้นที่หายใจ (24px)
    sheet.setRowHeights(2, lastRow - 1, 24);
    
    // เคลียร์และใส่สีสลับแถวเพื่อให้มองง่ายขึ้น (Alternating Rows)
    for (var r = 2; r <= lastRow; r++) {
      var rowRange = sheet.getRange(r, 1, 1, lastCol);
      if (r % 2 === 0) {
        rowRange.setBackground("#fafafa");
      } else {
        rowRange.setBackground("#ffffff");
      }
    }

    // 3. จัดการเส้นตารางให้ดูเบาบางลง
    dataRange.setBorder(true, true, true, true, true, true, "#e5e7eb", SpreadsheetApp.BorderStyle.SOLID);
  }
  
  // ขีดเส้นใต้หัวตารางหนาๆ สีเทาเข้ม
  headers.setBorder(null, null, true, null, null, null, "#9ca3af", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);

  // 4. สั่งขยายขนาดความกว้างคอลัมน์อัตโนมัติให้พอดีกับข้อมูล
  sheet.autoResizeColumns(1, lastCol);
  
  // ตั้งค่ากว้างขั้นต่ำเผื่อบางคอลัมน์สั้นเกินไป
  for (var c = 1; c <= lastCol; c++) {
    var w = sheet.getColumnWidth(c);
    if (w < 85) {
      sheet.setColumnWidth(c, 85);
    }
  }
}
