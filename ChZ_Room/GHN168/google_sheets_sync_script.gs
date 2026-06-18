/**
 * GHN168 Google Sheets Accounting Sync Apps Script (Comprehensive v2.0)
 * วัตถุประสงค์: บันทึกข้อมูลรายรับ (ใบเสร็จ) และรายจ่าย (50 ทวิ/ค่าใช้จ่ายทั่วไป) ลงชีตของบริษัทแบบละเอียดสมบูรณ์
 * ติดตั้ง: ไปที่ Extensions > Apps Script ใน Google Sheet ของบริษัทแก วางโค้ดนี้ทั้งหมดแทนที่ของเดิมแล้วกด Deploy เป็น Web App
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
    // CASE 1: บันทึกข้อมูล รายรับ (จากใบเสร็จรับเงิน)
    // ----------------------------------------------------
    if (data.type === "income") {
      var sheetName = "รายรับ";
      var sheet = activeSpreadsheet.getSheetByName(sheetName);
      
      if (!sheet) {
        sheet = activeSpreadsheet.insertSheet(sheetName);
        sheet.appendRow(INCOME_HEADERS);
        sheet.getRange(1, 1, 1, INCOME_HEADERS.length).setFontWeight("bold").setBackground("#f3f4f6");
        sheet.setFrozenRows(1);
      } else {
        migrateSheetIfNeeded(sheet, INCOME_HEADERS);
      }
      
      if (data.items && Array.isArray(data.items) && data.items.length > 0) {
        // วนลูปบันทึกแยกรายรายการสินค้า/บริการ (Itemized split rows)
        for (var i = 0; i < data.items.length; i++) {
          var item = data.items[i];
          var rowData = [
            data.recordDate || data.date,          // วันที่บันทึก
            data.date,                              // วันที่ตามใบเสร็จ
            data.docNo,                             // เลขที่ใบเสร็จ
            data.invoiceNo || "-",                  // เลขที่ใบวางบิล
            data.clientName,                        // ชื่อลูกค้า
            data.clientTaxId || "-",                // เลขผู้เสียภาษีลูกค้า
            data.clientAddress || "-",              // ที่อยู่ลูกค้า
            data.clientBranch || "00000",           // รหัสสาขา
            item.desc || data.detail || "-",        // รายละเอียดงานย่อย
            item.subtotal,                          // ยอดก่อน VAT
            item.vat,                               // VAT 7%
            item.gross || (item.subtotal + item.vat), // ยอดรวม VAT
            item.whtRate !== undefined ? item.whtRate : (data.whtRate || 0), // อัตรา WHT %
            item.wht,                               // ยอด WHT
            item.net,                               // ยอดเงินที่ได้รับจริง
            data.receivingBank || "KBank",          // บัญชีที่รับเงิน
            data.paymentStatus || "ชำระเงินแล้ว",   // สถานะการชำระเงิน
            data.actualPaymentDate || data.date,    // วันที่ได้รับเงินจริง
            item.profitShare || data.profitShare || "-", // สัดส่วนผู้รับผลประโยชน์
            data.driveLink || "-",                  // ลิงก์ Drive
            data.recordedBy || "-",                 // ผู้บันทึก
            data.remarks || "-"                     // หมายเหตุ
          ];
          sheet.appendRow(rowData);
        }
        
        return ContentService.createTextOutput(JSON.stringify({
          "status": "success",
          "message": "บันทึกข้อมูลรายรับแยกเป็น " + data.items.length + " รายการลงแท็บ 'รายรับ' สำเร็จแล้วจ้า!"
        })).setMimeType(ContentService.MimeType.JSON);
      } else {
        var rowData = [
          data.recordDate || data.date,
          data.date,
          data.docNo,
          data.invoiceNo || "-",
          data.clientName,
          data.clientTaxId || "-",
          data.clientAddress || "-",
          data.clientBranch || "00000",
          data.detail || "-",
          data.subtotal,
          data.vat,
          data.gross || (data.subtotal + data.vat),
          data.whtRate || 0,
          data.wht,
          data.net,
          data.receivingBank || "KBank",
          data.paymentStatus || "ชำระเงินแล้ว",
          data.actualPaymentDate || data.date,
          data.profitShare || "-",
          data.driveLink || "-",
          data.recordedBy || "-",
          data.remarks || "-"
        ];
        sheet.appendRow(rowData);
        
        return ContentService.createTextOutput(JSON.stringify({
          "status": "success",
          "message": "บันทึกข้อมูลรายรับลงแท็บ 'รายรับ' (แถวเดียว) สำเร็จแล้วจ้า!"
        })).setMimeType(ContentService.MimeType.JSON);
      }
    }
    
    // ----------------------------------------------------
    // CASE 2: บันทึกข้อมูล รายจ่าย
    // ----------------------------------------------------
    else if (data.type === "expense") {
      var sheetName = "รายจ่าย";
      var sheet = activeSpreadsheet.getSheetByName(sheetName);
      
      if (!sheet) {
        sheet = activeSpreadsheet.insertSheet(sheetName);
        sheet.appendRow(EXPENSE_HEADERS);
        sheet.getRange(1, 1, 1, EXPENSE_HEADERS.length).setFontWeight("bold").setBackground("#fee2e2");
        sheet.setFrozenRows(1);
      } else {
        migrateSheetIfNeeded(sheet, EXPENSE_HEADERS);
      }
      
      var rowData = [
        data.recordDate || data.date,        // A: วันที่บันทึก
        data.date,                            // B: วันที่ตามใบเสร็จ
        data.docNo,                           // C: เลขที่บิล/ใบเสร็จ
        data.payeeName,                       // D: ชื่อผู้ให้บริการ
        data.payeeTaxId || "-",               // E: เลขประจำตัวผู้เสียภาษี
        data.payeeAddress || "-",             // F: ที่อยู่
        data.payeeBranch || "00000",          // G: รหัสสาขา
        data.category || "-",                 // H: หมวดหมู่ค่าใช้จ่าย
        data.detail,                          // I: รายละเอียด
        data.gross,                           // J: ยอดก่อน VAT
        data.vat !== undefined ? data.vat : 0, // K: VAT 7%
        data.totalAmount !== undefined ? data.totalAmount : (data.gross + (data.vat || 0)), // L: ยอดรวม VAT
        data.whtRate || 0,                    // M: อัตรา WHT %
        data.tax || 0,                        // N: ยอดหัก WHT
        data.whtType || "none",               // O: ประเภทยื่น WHT
        data.net,                             // P: ยอดจ่ายเงินสุทธิ
        data.paymentMethod || "KBank",        // Q: ช่องทางจ่ายเงิน
        data.paymentStatus || "จ่ายเงินแล้ว", // R: สถานะจ่ายเงิน
        data.actualPaidDate || data.date,     // S: วันที่จ่ายเงินจริง
        data.whtCertificateNo || "-",         // T: เลขใบ 50 ทวิ
        data.driveLink || "-",                // U: ลิงก์ Drive
        data.taxFilingStatus || "ยังไม่ได้ยื่น", // V: สถานะยื่นภาษี
        data.projectLink || "",               // W: โครงการที่ผูก
        data.remarks || ""                    // X: หมายเหตุ
      ];
      
      sheet.appendRow(rowData);
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "message": "บันทึกข้อมูลรายจ่ายลงแท็บ 'รายจ่าย' แถวที่ " + sheet.getLastRow() + " สำเร็จแล้วจ้า!"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // ----------------------------------------------------
    // CASE 3: บันทึกข้อมูล เงินสดย่อย (Petty Cash)
    // ----------------------------------------------------
    else if (data.type === "petty_cash") {
      var sheetName = "เงินสดย่อย";
      var sheet = activeSpreadsheet.getSheetByName(sheetName);
      
      if (!sheet) {
        sheet = activeSpreadsheet.insertSheet(sheetName);
        sheet.appendRow(PETTY_CASH_HEADERS);
        sheet.getRange(1, 1, 1, PETTY_CASH_HEADERS.length).setFontWeight("bold").setBackground("#fef08a");
        sheet.setFrozenRows(1);
      }
      
      var rowData = [
        data.voucherNo,                      // A: เลขที่ใบสำคัญ
        data.date,                            // B: วันที่เบิกเงิน
        data.requester,                       // C: ชื่อผู้ขอเบิก
        data.category || "-",                 // D: หมวดหมู่ค่าใช้จ่าย
        data.detail,                          // E: รายละเอียด
        data.amountPaid,                      // F: ยอดจ่ายจริง
        data.balance,                         // G: ยอดคงเหลือ
        data.approver || "-",                 // H: ผู้อนุมัติ
        data.receiptUrl || "-",               // I: ลิงก์ใบเสร็จ
        data.remarks || ""                    // J: หมายเหตุ
      ];
      
      sheet.appendRow(rowData);
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "message": "บันทึกข้อมูลเงินสดย่อยลงแท็บ 'เงินสดย่อย' แถวที่ " + sheet.getLastRow() + " สำเร็จแล้วจ้า!"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // ----------------------------------------------------
    // CASE 4: บันทึกข้อมูล เงินเดือน (Payroll)
    // ----------------------------------------------------
    else if (data.type === "payroll") {
      var sheetName = "เงินเดือน";
      var sheet = activeSpreadsheet.getSheetByName(sheetName);
      
      if (!sheet) {
        sheet = activeSpreadsheet.insertSheet(sheetName);
        sheet.appendRow(PAYROLL_HEADERS);
        sheet.getRange(1, 1, 1, PAYROLL_HEADERS.length).setFontWeight("bold").setBackground("#e0f2fe");
        sheet.setFrozenRows(1);
      }
      
      var rowData = [
        data.payrollId,                      // A: รหัสรอบจ่าย
        data.employeeId,                      // B: รหัสพนักงาน
        data.employeeName,                    // C: ชื่อพนักงาน
        data.employeeTaxId || "-",            // D: เลขบัตรประชาชน
        data.baseSalary,                      // E: เงินเดือน
        data.allowances || 0,                 // F: ค่าตำแหน่ง/โบนัส
        data.totalEarnings,                   // G: ยอดรวมรายได้
        data.ssfDeduction,                    // H: หักประกันสังคม
        data.whtDeduction,                    // I: หักภาษี ณ ที่จ่าย (ภ.ง.ด.1)
        data.otherDeductions || 0,            // J: เงินหักอื่นๆ
        data.netPay,                          // K: ยอดโอนจริง
        data.bankAccount || "-",              // L: เลขบัญชี
        data.status || "รอดำเนินการ",          // M: สถานะ
        data.paySlipUrl || "-"                // N: ลิงก์สลิป
      ];
      
      sheet.appendRow(rowData);
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "message": "บันทึกข้อมูลเงินเดือนลงแท็บ 'เงินเดือน' แถวที่ " + sheet.getLastRow() + " สำเร็จแล้วจ้า!"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // ----------------------------------------------------
    // CASE 5: บันทึกข้อมูล กระทบยอดธนาคาร (Bank Rec)
    // ----------------------------------------------------
    else if (data.type === "bank_rec") {
      var sheetName = "กระทบยอดธนาคาร";
      var sheet = activeSpreadsheet.getSheetByName(sheetName);
      
      if (!sheet) {
        sheet = activeSpreadsheet.insertSheet(sheetName);
        sheet.appendRow(BANK_REC_HEADERS);
        sheet.getRange(1, 1, 1, BANK_REC_HEADERS.length).setFontWeight("bold").setBackground("#f3f4f6");
        sheet.setFrozenRows(1);
      }
      
      var rowData = [
        data.reconciliationId,                // A: รหัสรายงาน
        data.period,                          // B: รอบประจำเดือน
        data.bankAccount,                     // C: รหัสบัญชีธนาคาร
        data.statementBalance,                // D: ยอด Statement ธนาคาร
        data.bookBalance,                     // E: ยอดในระบบ
        data.depositInTransit || 0,           // F: เงินฝากระหว่างทาง
        data.outstandingCheques || 0,         // G: เช็คค้างจ่าย
        data.bankChargesNotRecorded || 0,     // H: ค่าธรรมเนียมค้างบันทึก
        data.adjustedStatementBalance,        // I: ยอดปรับปรุง Statement
        data.adjustedBookBalance,             // J: ยอดปรับปรุงระบบ
        data.difference,                      // K: ส่วนต่าง
        data.reconciledBy || "-"              // L: ผู้กระทบยอด
      ];
      
      sheet.appendRow(rowData);
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "message": "บันทึกข้อมูลกระทบยอดธนาคารลงแท็บ 'กระทบยอดธนาคาร' แถวที่ " + sheet.getLastRow() + " สำเร็จแล้วจ้า!"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // ----------------------------------------------------
    // CASE 6: เตรียมโครงสร้าง 5 แท็บหลักอัตโนมัติ (Initialize)
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
          sheet.getRange(1, 1, 1, headers.length).setFontWeight("bold").setBackground("#f3f4f6");
          sheet.setFrozenRows(1);
          createdSheets.push(sheetName);
        } else {
          migrateSheetIfNeeded(sheet, headers);
          checkedSheets.push(sheetName);
        }
      }
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "message": "เตรียมโครงสร้างชีตสำเร็จแล้วแก! (สร้างแท็บใหม่: " + createdSheets.join(", ") + " | ตรวจทานแท็บเดิม: " + checkedSheets.join(", ") + ")"
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
          newRow[12] = 0;        // WHT Rate (calculated below)
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
          newRow[18] = "คนดีล: " + oldRow[9] + " (" + oldRow[10] + "%)"; // Profit Share Distribution
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
          newRow[9] = oldRow[5]; // Pre-VAT (Gross in old layout)
          newRow[10] = 0;        // VAT
          newRow[11] = oldRow[5]; // Gross Amount
          newRow[12] = 0;        // WHT % (calculated below)
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
          newRow[23] = "Migrated from 9-column layout"; // Remarks
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
          newRow[9] = oldRow[5]; // Pre-VAT (Gross in 12-column layout)
          newRow[10] = oldRow[6]; // VAT
          newRow[11] = (parseFloat(oldRow[5]) || 0) + (parseFloat(oldRow[6]) || 0); // Gross Amount
          newRow[12] = 0;        // WHT % (calculated below)
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
          newRow[23] = "Migrated from 12-column layout"; // Remarks
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
    
    var headerColor = targetHeaders.length === 22 ? "#f3f4f6" : "#fee2e2";
    sheet.getRange(1, 1, 1, targetHeaders.length).setFontWeight("bold").setBackground(headerColor);
    sheet.setFrozenRows(1);
  }
}
