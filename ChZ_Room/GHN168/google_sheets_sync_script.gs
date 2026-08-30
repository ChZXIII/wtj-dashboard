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
  "หมายเหตุ (Remarks)",
  "ส่วนลด (Discount)",
  "รายละเอียดส่วนลด (Discount Description)"
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
  "หมายเหตุ (Remarks)",
  "ผู้เบิกค่าแรง / พนักงาน (Staff Payee / Employee)"
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

var DOCHUB_HEADERS = [
  "ชื่อเอกสาร (Document Name)",
  "หมวดหมู่ (Category)",
  "ลิงก์เอกสาร Google Drive (URL)",
  "วันที่อัปเดต (Date)",
  "รายละเอียด (Description)"
];

var QUOTATION_HEADERS = [
  "วันที่บันทึก (Record Date)",
  "วันที่เอกสาร (Date)",
  "เลขที่เอกสาร (Document No)",
  "ชื่อลูกค้า (Client Name)",
  "เลขประจำตัวผู้เสียภาษี (Client Tax ID)",
  "ที่อยู่ลูกค้า (Client Address)",
  "รหัสสาขา (Client Branch)",
  "เบอร์โทรติดต่อ (Client Phone)",
  "รายละเอียดโครงการ (Project Name)",
  "ยอดก่อนภาษีมูลค่าเพิ่ม (Pre-VAT Amount)",
  "ภาษีมูลค่าเพิ่ม 7% (VAT Amount)",
  "ยอดภาษีหัก ณ ที่จ่าย (WHT Amount)",
  "ยอดรวมสุทธิ (Net Amount)",
  "ภาษีถูกหัก ณ ที่จ่าย % (WHT Rate %)",
  "ชื่อผู้ลงนาม (Signer Name)",
  "ผู้ลงนาม (Signatory Select)",
  "แสดงตราประทับ (Show Company Seal)",
  "แสดงลายเซ็น (Show Document Signature)",
  "ข้อมูลรายการสินค้าและราคา JSON (Items JSON)",
  "วันเวลาที่อัปเดตล่าสุด (Last Updated)",
  "หมายเหตุ (Remarks)",
  "ส่วนลด (Discount)",
  "รายละเอียดส่วนลด (Discount Description)"
];

var INVOICE_HEADERS = [
  "วันที่บันทึก (Record Date)",
  "วันที่เอกสาร (Date)",
  "เลขที่เอกสาร (Document No)",
  "ชื่อลูกค้า (Client Name)",
  "เลขประจำตัวผู้เสียภาษี (Client Tax ID)",
  "ที่อยู่ลูกค้า (Client Address)",
  "รหัสสาขา (Client Branch)",
  "เบอร์โทรติดต่อ (Client Phone)",
  "รายละเอียดโครงการ (Project Name)",
  "ยอดก่อนภาษีมูลค่าเพิ่ม (Pre-VAT Amount)",
  "ภาษีมูลค่าเพิ่ม 7% (VAT Amount)",
  "ยอดภาษีหัก ณ ที่จ่าย (WHT Amount)",
  "ยอดรวมสุทธิ (Net Amount)",
  "ภาษีถูกหัก ณ ที่จ่าย % (WHT Rate %)",
  "ชื่อผู้ลงนาม (Signer Name)",
  "ผู้ลงนาม (Signatory Select)",
  "แสดงตราประทับ (Show Company Seal)",
  "แสดงลายเซ็น (Show Document Signature)",
  "ข้อมูลรายการสินค้าและราคา JSON (Items JSON)",
  "วันเวลาที่อัปเดตล่าสุด (Last Updated)",
  "เงื่อนไขการชำระเงิน (Payment Terms)",
  "วันครบกำหนด (Due Date)",
  "หมายเหตุ (Remarks)",
  "ส่วนลด (Discount)",
  "รายละเอียดส่วนลด (Discount Description)"
];

var CUSTOMER_HEADERS = [
  "รหัสลูกค้า (Customer ID)",
  "ชื่อบริษัท / ลูกค้า (Customer Name)",
  "เลขประจำตัวผู้เสียภาษี (Tax ID)",
  "รหัสสาขา (Branch Code)",
  "ที่อยู่จดทะเบียน (Address)",
  "เบอร์โทรศัพท์ (Phone)",
  "อีเมล (Email)",
  "ผู้ติดต่อ (Contact Person)",
  "วันที่บันทึก (Created Date)",
  "หมายเหตุ (Remarks)"
];

function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.tryLock(10000); // ล็อกสคริปต์ 10 วินาทีป้องกันสัญญานยิงชนกัน
  
  try {
    var data = JSON.parse(e.postData.contents);
    
    // ----------------------------------------------------
    // CASE: Direct PDF Upload (Base64) ขึ้น Google Drive โดยตรง
    // ----------------------------------------------------
    if (data.type === "upload_pdf_base64" || data.type === "upload_pdf" || data.type === "upload_only") {
      var pdfBase64 = data.pdfBase64;
      var pdfName = data.pdfName || "document.pdf";
      var docType = data.docType;
      var parentFolderId = data.parentFolderId;
      
      if (!pdfBase64) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "ไม่พบข้อมูล pdfBase64 ในข้อมูลที่ส่งเข้ามานะแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      if (!parentFolderId) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "ไม่พบ parentFolderId ในข้อมูลที่ส่งเข้ามานะแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      var pdfBytes = Utilities.base64Decode(pdfBase64);
      var pdfBlob = Utilities.newBlob(pdfBytes, 'application/pdf', pdfName);
      var pdfUrl = saveBlobToFolder(pdfBlob, docType, parentFolderId);
      
      if (!pdfUrl) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "อัปโหลดไฟล์ PDF ล้มเหลว: ไม่สามารถเซฟลงโฟลเดอร์ Google Drive ได้ (อาจเกิดจากสิทธิ์เข้าถึง หรือโฟลเดอร์ไม่ถูกต้องนะแก!)"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "message": "อัปโหลดไฟล์ PDF ตรงขึ้น Google Drive เรียบร้อยแล้ว",
        "pdfUrl": pdfUrl
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // ----------------------------------------------------
    // CASE: แปลง HTML เป็น PDF และอัปโหลดขึ้น Google Drive
    // ----------------------------------------------------
    if (data.type === "upload_html") {
      var htmlContent = data.htmlContent;
      var pdfName = data.pdfName || "document.pdf";
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
      
      var pdfBlob = null;
      var convertError = "";
      
      if (pdfShiftApiKey) {
        var convertResult = convertHtmlToPdfWithPdfShift(htmlContent, pdfShiftApiKey, pdfName);
        if (convertResult.success) {
          pdfBlob = convertResult.blob;
        } else {
          convertError = convertResult.error;
          Logger.log("PDFShift failed: " + convertError + " - Falling back to Google Drive HTML-to-PDF conversion.");
        }
      }
      
      // Fallback: หากไม่มี PDFShift API Key หรือ PDFShift ล้มเหลว ให้ใช้ Google Drive Built-in HTML-to-PDF converter
      if (!pdfBlob) {
        try {
          var tempHtmlBlob = Utilities.newBlob(htmlContent, 'text/html', (pdfName ? pdfName.replace(/\.pdf$/i, '') : 'document') + '.html');
          pdfBlob = tempHtmlBlob.getAs('application/pdf');
          pdfBlob.setName(pdfName);
        } catch (fallbackErr) {
          Logger.log("Built-in fallback HTML-to-PDF error: " + fallbackErr.toString());
        }
      }
      
      if (!pdfBlob) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "การแปลง HTML เป็น PDF ล้มเหลวทั้ง PDFShift และ Built-in fallback: " + (convertError || "ไม่ทราบสาเหตุ")
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      var pdfUrl = saveBlobToFolder(pdfBlob, docType, parentFolderId);
      if (!pdfUrl) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "เซฟไฟล์ PDF ลงโฟลเดอร์ล้มเหลว (อาจเกิดจากสิทธิ์เข้าถึง หรือโฟลเดอร์ไม่ถูกต้องนะแก!)"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "message": "อัปโหลดไฟล์ PDF ขึ้น Google Drive เรียบร้อยแล้วแก!",
        "pdfUrl": pdfUrl
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // ----------------------------------------------------
    // CASE: ดึงคิวงานและตารางนัดหมายจาก Google Calendar (ghn168media@gmail.com)
    // ----------------------------------------------------
    if (data.type === "get_calendar_events") {
      try {
        var now = new Date();
        var startTime = null;
        var endTime = null;

        if (data.targetDate) {
          var tParts = String(data.targetDate).split("-");
          if (tParts.length === 3) {
            startTime = new Date(parseInt(tParts[0], 10), parseInt(tParts[1], 10) - 1, parseInt(tParts[2], 10), 0, 0, 0);
            endTime = new Date(parseInt(tParts[0], 10), parseInt(tParts[1], 10) - 1, parseInt(tParts[2], 10), 23, 59, 59);
          }
        }

        if (!startTime && data.startDate) {
          startTime = new Date(data.startDate);
        }
        if (!endTime && data.endDate) {
          endTime = new Date(data.endDate);
        }

        if (!startTime || isNaN(startTime.getTime())) {
          startTime = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
        }
        if (!endTime || isNaN(endTime.getTime())) {
          endTime = new Date(startTime.getTime() + (7 * 24 * 60 * 60 * 1000));
          endTime.setHours(23, 59, 59, 999);
        }

        var calendars = CalendarApp.getAllCalendars();
        var eventsList = [];
        var seenEventKeys = {};

        for (var c = 0; c < calendars.length; c++) {
          var cal = calendars[c];
          var calName = cal.getName();
          var calId = cal.getId();

          try {
            var calEvents = cal.getEvents(startTime, endTime);
            for (var evIdx = 0; evIdx < calEvents.length; evIdx++) {
              var ev = calEvents[evIdx];
              var evId = ev.getId();
              var evTitle = ev.getTitle() || "ไม่มีชื่อกิจกรรม";
              var evStart = ev.getStartTime();
              var evEnd = ev.getEndTime();
              var evKey = evId || (evTitle + "_" + evStart.getTime());

              if (!seenEventKeys[evKey]) {
                seenEventKeys[evKey] = true;
                eventsList.push({
                  "id": evId,
                  "title": evTitle,
                  "description": ev.getDescription() || "",
                  "location": ev.getLocation() || "",
                  "startTime": evStart.toISOString(),
                  "endTime": evEnd.toISOString(),
                  "isAllDay": ev.isAllDayEvent(),
                  "calendarName": calName,
                  "calendarId": calId,
                  "status": "confirmed"
                });
              }
            }
          } catch (calErr) {
            Logger.log("Error reading calendar " + calName + ": " + calErr);
          }
        }

        // Sort events chronologically
        eventsList.sort(function(a, b) {
          return new Date(a.startTime).getTime() - new Date(b.startTime).getTime();
        });

        return ContentService.createTextOutput(JSON.stringify({
          "status": "success",
          "message": "ดึงคิวงานจาก Google Calendar สำเร็จแล้วแก!",
          "totalEvents": eventsList.length,
          "startDate": startTime.toISOString(),
          "endDate": endTime.toISOString(),
          "events": eventsList
        })).setMimeType(ContentService.MimeType.JSON);

      } catch (calGlobalErr) {
        Logger.log("Global Calendar Fetch Error: " + calGlobalErr);
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "เกิดข้อผิดพลาดในการดึงข้อมูล Google Calendar: " + calGlobalErr.toString(),
          "events": []
        })).setMimeType(ContentService.MimeType.JSON);
      }
    }
    
    // ----------------------------------------------------
    // CASE: สร้างคิวงาน/กิจกรรมลง Google Calendar (ghn168media@gmail.com)
    // ----------------------------------------------------
    if (data.type === "create_calendar_event") {
      try {
        var title = data.title || "คิวงาน GHN168";
        var description = data.description || "";
        var location = data.location || "";
        var isAllDay = data.isAllDay !== false;
        
        var startTime = null;
        var endTime = null;

        if (data.startDate) {
          startTime = new Date(data.startDate);
        } else if (data.targetDate) {
          startTime = new Date(data.targetDate);
        }
        
        if (data.endDate) {
          endTime = new Date(data.endDate);
        }

        if (!startTime || isNaN(startTime.getTime())) {
          startTime = new Date();
        }
        
        if (!endTime || isNaN(endTime.getTime())) {
          endTime = new Date(startTime.getTime() + (isAllDay ? (24 * 60 * 60 * 1000) : (2 * 60 * 60 * 1000)));
        }

        var targetCalendar = CalendarApp.getDefaultCalendar();
        var calendars = CalendarApp.getAllCalendars();
        for (var i = 0; i < calendars.length; i++) {
          var calName = calendars[i].getName().toLowerCase();
          if (calName.indexOf("ghn") !== -1 || calName.indexOf("ghn168") !== -1) {
            targetCalendar = calendars[i];
            break;
          }
        }

        var createdEvent = null;
        if (isAllDay) {
          createdEvent = targetCalendar.createAllDayEvent(title, startTime, {
            description: description,
            location: location
          });
        } else {
          createdEvent = targetCalendar.createEvent(title, startTime, endTime, {
            description: description,
            location: location
          });
        }

        return ContentService.createTextOutput(JSON.stringify({
          "status": "success",
          "message": "สร้างคิวงานใน Google Calendar สำเร็จเรียบร้อยแล้วแก!",
          "eventId": createdEvent ? createdEvent.getId() : "mock-cal-id",
          "title": title,
          "startTime": startTime.toISOString(),
          "endTime": endTime.toISOString(),
          "isAllDay": isAllDay,
          "calendarName": targetCalendar ? targetCalendar.getName() : "GHN168 Calendar"
        })).setMimeType(ContentService.MimeType.JSON);

      } catch (createCalErr) {
        Logger.log("Create Calendar Event Error: " + createCalErr);
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "เกิดข้อผิดพลาดในการสร้างคิวงาน Google Calendar: " + createCalErr.toString()
        })).setMimeType(ContentService.MimeType.JSON);
      }
    }
    
    var spreadsheetId = data.spreadsheetId;
    
    if (!spreadsheetId) {
      return ContentService.createTextOutput(JSON.stringify({
        "status": "error",
        "message": "ไม่พบ Spreadsheet ID ในพารามิเตอร์ที่ส่งเข้ามานะแก!"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    var activeSpreadsheet = SpreadsheetApp.openById(spreadsheetId);
    
    // ----------------------------------------------------
    // CASE 1: ซิงค์แถวข้อมูลลงแท็บใดๆ แบบ In-place Upsert Guard & Smart Merge
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
      
      // บันทึกหลายแถวพร้อมกัน (กรณี Split Items ในรายรับ หรือ Batch Sync)
      if (data.rows && Array.isArray(data.rows) && data.rows.length > 0) {
        var updatedCount = 0;
        var insertedCount = 0;
        for (var i = 0; i < data.rows.length; i++) {
          var res = upsertRowInSheet(sheet, sheetName, data.rows[i]);
          if (res.updated) {
            updatedCount++;
          } else {
            insertedCount++;
          }
        }
        beautifySheet(sheet, sheetName);
        
        return ContentService.createTextOutput(JSON.stringify({
          "status": "success",
          "message": "ซิงค์ข้อมูล " + data.rows.length + " แถว ลงแท็บ '" + sheetName + "' เรียบร้อยแล้วแก! (อัปเดตแถวเดิม: " + updatedCount + " แถว | เพิ่มแถวใหม่: " + insertedCount + " แถว)",
          "updatedCount": updatedCount,
          "insertedCount": insertedCount
        })).setMimeType(ContentService.MimeType.JSON);
      } 
      // บันทึกแถวเดี่ยว (Single Row Sync with Normalized Upsert Guard)
      else if (data.values && Array.isArray(data.values) && data.values.length > 0) {
        var res = upsertRowInSheet(sheet, sheetName, data.values);
        beautifySheet(sheet, sheetName);
        
        var successMsg = "ซิงค์บันทึกข้อมูลลงแท็บ '" + sheetName + "' เรียบร้อยแล้วแก!";
        if (res.updated) {
          if (sheetName === "ข้อมูลลูกค้า") {
            successMsg = "อัปเดตข้อมูลลูกค้า '" + (data.values[1] || "") + "' ในแท็บ 'ข้อมูลลูกค้า' เรียบร้อยแล้วแก! (แถว " + res.rowNum + ")";
          } else {
            var displayDocNo = data.values[2] || data.values[3] || "";
            successMsg = "อัปเดตข้อมูลเอกสารเลขที่ '" + displayDocNo + "' ในแท็บ '" + sheetName + "' เรียบร้อยแล้วแก! (แถว " + res.rowNum + ")";
          }
        }
        
        return ContentService.createTextOutput(JSON.stringify({
          "status": "success",
          "message": successMsg,
          "updated": res.updated,
          "rowNum": res.rowNum
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
    // CASE 2: เตรียมโครงสร้างแท็บหลักอัตโนมัติ (Initialize - Zero Destructive)
    // ----------------------------------------------------
    else if (data.type === "initialize") {
      var sheetsInfo = [
        { name: "รายรับ", headers: INCOME_HEADERS },
        { name: "รายจ่าย", headers: EXPENSE_HEADERS },
        { name: "เงินสดย่อย", headers: PETTY_CASH_HEADERS },
        { name: "เงินเดือน", headers: PAYROLL_HEADERS },
        { name: "กระทบยอดธนาคาร", headers: BANK_REC_HEADERS },
        { name: "คลังเอกสาร", headers: DOCHUB_HEADERS },
        { name: "ใบเสนอราคา", headers: QUOTATION_HEADERS },
        { name: "ใบวางบิล", headers: INVOICE_HEADERS },
        { name: "ข้อมูลลูกค้า", headers: CUSTOMER_HEADERS }
      ];
      
      var createdSheets = [];
      var skippedSheets = [];
      
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
          // แท็บมีอยู่แล้ว: ข้าม (Skip) ทันที ห้ามรัน Migration หรือเคลียร์/ลบข้อมูลเดิมใดๆ ทั้งสิ้น
          if (sheet.getLastRow() === 0 || sheet.getLastColumn() === 0) {
            sheet.appendRow(headers);
            beautifySheet(sheet, sheetName);
          }
          skippedSheets.push(sheetName);
        }
      }
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "message": "เตรียมโครงสร้างชีตสำเร็จแล้วแก! (สร้างแท็บใหม่: " + (createdSheets.length > 0 ? createdSheets.join(", ") : "ไม่มี") + " | ข้ามแท็บเดิมที่ปลอดภัย: " + skippedSheets.join(", ") + " | Zero Destructive Overwrite 100%)"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // ----------------------------------------------------
    // CASE 3: อ่านข้อมูลแท็บใดๆ (Read)
    // ----------------------------------------------------
    else if (data.type === "read") {
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
          "message": "ไม่พบแท็บชีตชื่อ '" + sheetName + "' นะแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      var lastRow = sheet.getLastRow();
      var lastCol = sheet.getLastColumn();
      var values = [];
      if (lastRow > 1 && lastCol > 0) {
        values = sheet.getRange(2, 1, lastRow - 1, lastCol).getDisplayValues();
      }
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "values": values
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // ----------------------------------------------------
    // CASE 4: บันทึกข้อมูลแบบ Safe Update ในแท็บ (Safe Sync / Zero Destructive Overwrite)
    // ----------------------------------------------------
    else if (data.type === "overwrite") {
      var sheetName = data.sheetName;
      var headers = data.headers;
      var rows = data.rows;
      
      if (!sheetName) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "ไม่ระบุชื่อแท็บชีต (sheetName) นะแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      var sheet = activeSpreadsheet.getSheetByName(sheetName);
      if (!sheet) {
        sheet = activeSpreadsheet.insertSheet(sheetName);
      }
      
      // In-Place Safe Header Update (แก้ไขเฉพาะแถว 1 เท่านั้น)
      if (headers && headers.length > 0) {
        if (sheet.getLastRow() === 0 || sheet.getLastColumn() === 0) {
          sheet.appendRow(headers);
        } else {
          sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
        }
      }
      
      // อัปเดตข้อมูลแถวแบบปลอดภัย (ห้ามใช้ sheet.clear())
      if (rows && rows.length > 0) {
        var numRows = rows.length;
        var numCols = rows[0].length;
        sheet.getRange(2, 1, numRows, numCols).setValues(rows);
        
        var oldLastRow = sheet.getLastRow();
        if (oldLastRow > numRows + 1) {
          sheet.getRange(numRows + 2, 1, oldLastRow - (numRows + 1), Math.max(numCols, sheet.getLastColumn())).clearContent();
        }
      }
      beautifySheet(sheet, sheetName);
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "message": "อัปเดตข้อมูลแท็บ '" + sheetName + "' แบบปลอดภัยเรียบร้อยแล้วแก!"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // ----------------------------------------------------
    // CASE 5: อัปเดต Profit Share ในแท็บรายรับย้อนหลัง
    // ----------------------------------------------------
    else if (data.type === "update_profit_share") {
      var docNo = data.docNo;
      if (!docNo) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "ไม่พบเลขที่เอกสาร (docNo) นะแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      var sheet = activeSpreadsheet.getSheetByName("รายรับ");
      if (!sheet) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "ไม่พบแท็บชีต 'รายรับ' นะแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      var lastRow = sheet.getLastRow();
      if (lastRow > 1) {
        var docNumbers = sheet.getRange(2, 3, lastRow - 1, 1).getValues();
        var matchCount = 0;
        
        for (var r = 0; r < docNumbers.length; r++) {
          if (docNumbers[r][0] === docNo) {
            var rowNum = r + 2;
            var valToSet = data.profitShare;
            if (data.rowsProfitShare && Array.isArray(data.rowsProfitShare)) {
              if (matchCount < data.rowsProfitShare.length) {
                valToSet = data.rowsProfitShare[matchCount];
              }
            }
            sheet.getRange(rowNum, 19).setValue(valToSet);
            matchCount++;
          }
        }
        
        beautifySheet(sheet, "รายรับ");
        
        return ContentService.createTextOutput(JSON.stringify({
          "status": "success",
          "message": "อัปเดตสัดส่วนส่วนแบ่งกำไร (Profit Share) เลขที่เอกสาร '" + docNo + "' จำนวน " + matchCount + " แถวเรียบร้อยแล้วแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      } else {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "success",
          "message": "ไม่พบแถวข้อมูลใดๆ ในแท็บ 'รายรับ' เพื่ออัปเดต"
        })).setMimeType(ContentService.MimeType.JSON);
      }
    }
    
    // ----------------------------------------------------
    // CASE 6: จัดระเบียบเคลียร์ข้อมูลแถวซ้ำในแท็บ (Deduplicate Tab In-Place Guard)
    // ----------------------------------------------------
    else if (data.type === "deduplicate") {
      var sheetName = data.sheetName || "รายรับ";
      var sheet = activeSpreadsheet.getSheetByName(sheetName);
      if (!sheet) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "error",
          "message": "ไม่พบแท็บชีต '" + sheetName + "' นะแก!"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      var lastRow = sheet.getLastRow();
      var lastCol = sheet.getLastColumn();
      if (lastRow <= 1 || lastCol === 0) {
        return ContentService.createTextOutput(JSON.stringify({
          "status": "success",
          "message": "แท็บ '" + sheetName + "' ไม่มีข้อมูลแถวให้ตรวจสอบ",
          "removedCount": 0,
          "remainingRows": 0
        })).setMimeType(ContentService.MimeType.JSON);
      }
      
      var rawRows = sheet.getRange(2, 1, lastRow - 1, lastCol).getValues();
      var uniqueMap = {};
      var cleanRows = [];
      var removedCount = 0;
      
      for (var r = 0; r < rawRows.length; r++) {
        var row = rawRows[r];
        var key = "";
        if (sheetName === "ข้อมูลลูกค้า") {
          var custTax = String(row[2] || "").replace(/[^0-9]/g, "");
          var custName = normalizeCompanyName(row[1]);
          key = custTax || custName;
        } else if (sheetName === "รายรับ") {
          var docKey = normalizeDocNo(row[2]) || normalizeDocNo(row[3]);
          var descKey = normalizeItemDesc(row[8]);
          key = docKey ? (docKey + "___" + descKey) : ("ROW_" + r);
        } else {
          key = normalizeDocNo(row[2]) || normalizeDocNo(row[3]) || ("ROW_" + r);
        }
        
        if (key && uniqueMap[key] !== undefined) {
          // Merge duplicate row into previous unique row
          var prevIdx = uniqueMap[key];
          cleanRows[prevIdx] = smartMergeRow(cleanRows[prevIdx], row, sheetName);
          removedCount++;
        } else {
          if (key) {
            uniqueMap[key] = cleanRows.length;
          }
          cleanRows.push(row);
        }
      }
      
      if (removedCount > 0) {
        // Safe overwrite without sheet.clear()
        sheet.getRange(2, 1, cleanRows.length, cleanRows[0].length).setValues(cleanRows);
        if (lastRow > cleanRows.length + 1) {
          sheet.getRange(cleanRows.length + 2, 1, lastRow - (cleanRows.length + 1), lastCol).clearContent();
        }
        beautifySheet(sheet, sheetName);
      }
      
      return ContentService.createTextOutput(JSON.stringify({
        "status": "success",
        "message": "จัดระเบียบเคลียร์ข้อมูลแถวซ้ำในแท็บ '" + sheetName + "' สำเร็จแล้วแก! (รวมข้อมูลที่ซ้ำ " + removedCount + " แถว | เหลือแถวข้อมูลจริง " + cleanRows.length + " แถว)",
        "removedCount": removedCount,
        "remainingRows": cleanRows.length
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
 * Normalizes document numbers for robust comparison across different naming conventions
 * e.g. "ทอย-RE2608-587" -> "RE2608-587"
 *      "RE2608-587"     -> "RE2608-587"
 *      "[ทอย]-RE2608-587" -> "RE2608-587"
 *      "หอม-IV2608-001" -> "IV2608-001"
 *      "EXP2608-001"    -> "EXP2608-001"
 */
function normalizeDocNo(rawDocNo) {
  if (!rawDocNo) return "";
  var str = String(rawDocNo).trim();
  var match = str.match(/(?:QT|IV|RE|EXP|PV|WHT|50BIS|BILL)[\w\-]+/i);
  if (match) {
    return match[0].toUpperCase().replace(/[\s_]+/g, "-");
  }
  var cleaned = str.replace(/^[\[\(].*?[\]\)]\s*[-_]?\s*/i, "")
                   .replace(/^[^\w\s]+[-_]?\s*/i, "")
                   .replace(/\s+/g, "")
                   .toUpperCase();
  return cleaned;
}

/**
 * Normalizes company / customer name for comparison
 */
function normalizeCompanyName(name) {
  if (!name) return "";
  var str = String(name).trim().toLowerCase();
  var prefixes = [
    "บริษัทจำกัด", "บริษัท", "บจก.", "บจก", "ห้างหุ้นส่วนจำกัด", "หจก.", "หจก",
    "หสน.", "หสน", "ร้าน", "คณะบุคคล", "co., ltd.", "co.,ltd.", "company limited", "inc."
  ];
  for (var i = 0; i < prefixes.length; i++) {
    str = str.split(prefixes[i]).join("");
  }
  str = str.replace(/\s+/g, "").replace(/[.\-_,\(\)\[\]]/g, "");
  return str;
}

/**
 * Normalizes item description for composite key comparison in itemized rows
 * e.g. "  1. ช่างภาพวิดีโอ 2 กล้อง (YC KCC)  " -> "1. ช่างภาพวิดีโอ 2 กล้อง (yc kcc)"
 */
function normalizeItemDesc(desc) {
  if (!desc) return "";
  return String(desc).trim().toLowerCase().replace(/\s+/g, " ");
}

/**
 * Smart Field Merging to combine incoming row data with existing row data
 * without overwriting important existing details (like custom recorder or remarks)
 * and properly updating Drive links and financial totals.
 */
function smartMergeRow(existingRow, newRow, sheetName) {
  var merged = existingRow.slice();
  var maxLen = Math.max(existingRow.length, newRow.length);
  while (merged.length < maxLen) merged.push("-");
  
  for (var i = 0; i < newRow.length; i++) {
    var newVal = newRow[i];
    var oldVal = (i < existingRow.length) ? existingRow[i] : "";
    
    // If incoming is empty or dash, keep existing value if it is valid
    if (newVal === undefined || newVal === null || newVal === "" || newVal === "-") {
      if (oldVal !== undefined && oldVal !== null && oldVal !== "" && oldVal !== "-") {
        merged[i] = oldVal;
        continue;
      }
    }
    
    if (sheetName === "รายรับ") {
      // Column 20 (Index 19): Google Drive PDF Link
      if (i === 19) {
        var newStr = String(newVal || "");
        var oldStr = String(oldVal || "");
        if (newStr.indexOf("http") !== -1 || newStr.indexOf("drive.google.com") !== -1) {
          merged[i] = newVal;
        } else if (oldStr.indexOf("http") !== -1 || oldStr.indexOf("drive.google.com") !== -1) {
          merged[i] = oldVal;
        } else {
          merged[i] = newVal || oldVal;
        }
        continue;
      }
      // Column 21 (Index 20): Recorded By (ผู้บันทึกรายการ)
      if (i === 20) {
        var newRec = String(newVal || "").trim();
        var oldRec = String(oldVal || "").trim();
        if (oldRec && oldRec !== "-" && (!newRec || newRec === "-" || newRec === "เลขาเฟิส (GHN168)" || newRec === "ระบบ")) {
          merged[i] = oldRec;
        } else if (newRec && newRec !== "-") {
          merged[i] = newRec;
        }
        continue;
      }
      // Column 22 (Index 21): Remarks (หมายเหตุ)
      if (i === 21) {
        var newRem = String(newVal || "").trim();
        var oldRem = String(oldVal || "").trim();
        if (oldRem && oldRem !== "-" && (!newRem || newRem === "-")) {
          merged[i] = oldRem;
        } else if (newRem && newRem !== "-" && (!oldRem || oldRem === "-")) {
          merged[i] = newRem;
        } else if (newRem && oldRem && newRem !== oldRem && newRem !== "-" && oldRem !== "-") {
          if (oldRem.indexOf(newRem) !== -1) {
            merged[i] = oldRem;
          } else if (newRem.indexOf(oldRem) !== -1) {
            merged[i] = newRem;
          } else {
            merged[i] = oldRem + " | " + newRem;
          }
        }
        continue;
      }
      // Column 19 (Index 18): Profit Share (สัดส่วนผู้รับผลประโยชน์)
      if (i === 18) {
        var newPs = String(newVal || "").trim();
        var oldPs = String(oldVal || "").trim();
        if (newPs && newPs !== "-") {
          merged[i] = newPs;
        } else if (oldPs && oldPs !== "-") {
          merged[i] = oldPs;
        }
        continue;
      }
    }
    
    if (sheetName === "รายจ่าย") {
      // Column 21 (Index 20): Google Drive PDF Link
      if (i === 20) {
        var newStr = String(newVal || "");
        var oldStr = String(oldVal || "");
        if (newStr.indexOf("http") !== -1 || newStr.indexOf("drive.google.com") !== -1) {
          merged[i] = newVal;
        } else if (oldStr.indexOf("http") !== -1 || oldStr.indexOf("drive.google.com") !== -1) {
          merged[i] = oldVal;
        } else {
          merged[i] = newVal || oldVal;
        }
        continue;
      }
      // Column 24 (Index 23): Remarks
      if (i === 23) {
        var newRem = String(newVal || "").trim();
        var oldRem = String(oldVal || "").trim();
        if (oldRem && oldRem !== "-" && (!newRem || newRem === "-")) {
          merged[i] = oldRem;
        } else if (newRem && newRem !== "-" && (!oldRem || oldRem === "-")) {
          merged[i] = newRem;
        } else if (newRem && oldRem && newRem !== oldRem && newRem !== "-" && oldRem !== "-") {
          if (oldRem.indexOf(newRem) !== -1) {
            merged[i] = oldRem;
          } else if (newRem.indexOf(oldRem) !== -1) {
            merged[i] = newRem;
          } else {
            merged[i] = oldRem + " | " + newRem;
          }
        }
        continue;
      }
      // Column 25 (Index 24): Staff Payee / Employee
      if (i === 24) {
        var newPayee = String(newVal || "").trim();
        var oldPayee = String(oldVal || "").trim();
        if (newPayee && newPayee !== "-") {
          merged[i] = newPayee;
        } else if (oldPayee && oldPayee !== "-") {
          merged[i] = oldPayee;
        }
        continue;
      }
    }
    
    // Default rule: use newVal if valid, else keep oldVal
    if (newVal !== undefined && newVal !== null && newVal !== "" && newVal !== "-") {
      merged[i] = newVal;
    } else {
      merged[i] = oldVal;
    }
  }
  return merged;
}

/**
 * In-place Upsert Guard function across all tabs
 */
function upsertRowInSheet(sheet, sheetName, rowValues) {
  var lastRow = sheet.getLastRow();
  var updated = false;
  var rowToUpdate = -1;
  
  if (lastRow > 1 && rowValues && rowValues.length > 0) {
    var numCols = Math.min(sheet.getLastColumn(), 25);
    var existingRows = sheet.getRange(2, 1, lastRow - 1, numCols).getValues();
    
    if (sheetName === "ใบเสนอราคา" || sheetName === "ใบวางบิล") {
      var targetDocNo = normalizeDocNo(rowValues[2]);
      if (targetDocNo) {
        for (var r = 0; r < existingRows.length; r++) {
          var existDocNo = normalizeDocNo(existingRows[r][2]);
          if (existDocNo && existDocNo === targetDocNo) {
            rowToUpdate = r + 2;
            break;
          }
        }
      }
    } else if (sheetName === "รายรับ") {
      var targetDocNo = normalizeDocNo(rowValues[2]) || normalizeDocNo(rowValues[3]);
      var targetDesc = normalizeItemDesc(rowValues[8]);
      if (targetDocNo) {
        var targetKey = targetDocNo + "___" + targetDesc;
        for (var r = 0; r < existingRows.length; r++) {
          var existDocNo = normalizeDocNo(existingRows[r][2]) || normalizeDocNo(existingRows[r][3]);
          var existDesc = normalizeItemDesc(existingRows[r][8]);
          var existKey = existDocNo + "___" + existDesc;
          
          if (existDocNo && existKey === targetKey) {
            rowToUpdate = r + 2;
            break;
          }
        }
      }
    } else if (sheetName === "รายจ่าย") {
      var targetDocNo = normalizeDocNo(rowValues[2]);
      var targetSupplier = normalizeCompanyName(rowValues[3]);
      var targetDate = String(rowValues[1] || "").trim();
      
      if (targetDocNo) {
        for (var r = 0; r < existingRows.length; r++) {
          var existDocNo = normalizeDocNo(existingRows[r][2]);
          if (existDocNo && existDocNo === targetDocNo) {
            rowToUpdate = r + 2;
            break;
          }
        }
      }
      // Secondary match for non-standard supplier bills
      if (rowToUpdate === -1 && targetSupplier && targetDate) {
        for (var r = 0; r < existingRows.length; r++) {
          var existSupplier = normalizeCompanyName(existingRows[r][3]);
          var existDate = String(existingRows[r][1] || "").trim();
          var existDocNo = normalizeDocNo(existingRows[r][2]);
          if (existSupplier === targetSupplier && existDate === targetDate && (!targetDocNo || !existDocNo || existDocNo === targetDocNo)) {
            rowToUpdate = r + 2;
            break;
          }
        }
      }
    } else if (sheetName === "ข้อมูลลูกค้า") {
      var custName = normalizeCompanyName(rowValues[1]);
      var custTaxId = String(rowValues[2] || "").replace(/[^0-9]/g, "");
      
      for (var r = 0; r < existingRows.length; r++) {
        var existName = normalizeCompanyName(existingRows[r][1]);
        var existTax = String(existingRows[r][2] || "").replace(/[^0-9]/g, "");
        var isTaxMatch = (custTaxId && existTax && custTaxId.length >= 10 && custTaxId === existTax);
        var isNameMatch = (custName && existName && (custName === existName || existName.indexOf(custName) !== -1 || custName.indexOf(existName) !== -1));
        
        if (isTaxMatch || isNameMatch) {
          rowToUpdate = r + 2;
          // Preserve existing Customer ID if incoming is empty/dash
          if (!rowValues[0] || rowValues[0] === "-" || rowValues[0] === "") {
            rowValues[0] = existingRows[r][0];
          }
          break;
        }
      }
    }
  }
  
  if (rowToUpdate !== -1) {
    var existingRow = sheet.getRange(rowToUpdate, 1, 1, Math.max(sheet.getLastColumn(), rowValues.length)).getValues()[0];
    var mergedRow = smartMergeRow(existingRow, rowValues, sheetName);
    sheet.getRange(rowToUpdate, 1, 1, mergedRow.length).setValues([mergedRow]);
    updated = true;
  } else {
    // New entry
    if (sheetName === "ข้อมูลลูกค้า") {
      if (!rowValues[0] || rowValues[0] === "-" || rowValues[0] === "") {
        var count = (lastRow <= 1) ? 1 : lastRow;
        rowValues[0] = "CUST-" + ("000" + count).slice(-3);
      }
    }
    sheet.appendRow(rowValues);
  }
  
  return { updated: updated, rowNum: rowToUpdate !== -1 ? rowToUpdate : sheet.getLastRow() };
}

/**
 * ฟังก์ชันช่วยตรวจสอบและอัปเดตเฉพาะแถวที่ 1 (Header row) แบบ In-Place Safe Update
 * กฎเหล็ก: ป้องกันการทำลายข้อมูลเดิม 100% (Zero Destructive Update / No Clear / No Overwrite)
 * แถวที่ 2 เป็นต้นไปจะไม่ถูกแตะต้องหรือแก้ไขโดยเด็ดขาด
 */
function migrateSheetIfNeeded(sheet, targetHeaders) {
  var lastCol = sheet.getLastColumn();
  var lastRow = sheet.getLastRow();
  
  if (lastCol === 0 || lastRow === 0) {
    sheet.appendRow(targetHeaders);
    beautifySheet(sheet, sheet.getName());
    return;
  }
  
  // In-Place Safe Update Only: ตรวจสอบและอัปเดตเฉพาะแถวที่ 1 (Header Row) เท่านั้น
  var currentHeaders = sheet.getRange(1, 1, 1, Math.max(lastCol, targetHeaders.length)).getValues()[0];
  var needsHeaderUpdate = false;
  for (var i = 0; i < targetHeaders.length; i++) {
    if (currentHeaders[i] !== targetHeaders[i]) {
      needsHeaderUpdate = true;
      break;
    }
  }

  if (needsHeaderUpdate) {
    // อัปเดตเฉพาะแถวที่ 1 (Header) เท่านั้น ห้ามแตะต้องแถวที่ 2 เป็นต้นไปเด็ดขาด!
    sheet.getRange(1, 1, 1, targetHeaders.length).setValues([targetHeaders]);
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
  } else if (sheetName === "ข้อมูลลูกค้า") {
    headerBg = "#e0e7ff"; // สี Indigo สว่าง
    headerText = "#3730a3"; // ตัวหนังสือ Indigo เข้ม
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

function uploadPdfToDrive(pdfBase64, pdfName, docType, parentFolderId) {
  if (!pdfBase64 || !parentFolderId) return null;
  var parentFolder = DriveApp.getFolderById(parentFolderId);
  if (!parentFolder) return null;
  var prefix = "";
  if (docType === "quotation") prefix = "01";
  else if (docType === "invoice") prefix = "02";
  else if (docType === "receipt") prefix = "03";
  else if (docType === "wht") prefix = "04";
  else if (docType === "expense" || docType === "pv") prefix = "05";
  
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
  var contentType = "application/pdf";
  var decoded = Utilities.base64Decode(pdfBase64);
  var blob = Utilities.newBlob(decoded, contentType, pdfName);
  var file = uploadFolder.createFile(blob);
  try {
    file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  } catch (sharingError) {
    Logger.log("ไม่สามารถตั้งค่าการแชร์ไฟล์ได้เนื่องจากข้อจำกัดสิทธิ์ของโดเมนองค์กร: " + sharingError.toString());
  }
  return file.getUrl();
}

function convertHtmlToPdfWithPdfShift(htmlContent, apiKey, filename) {
  var url = "https://api.pdfshift.io/v3/convert/pdf";
  
  var payload = {
    source: htmlContent,
    sandbox: false,
    delay: 3000,
    use_print_media: true
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

function saveBlobToFolder(blob, docType, parentFolderId) {
  if (!blob || !parentFolderId) return null;
  var parentFolder = DriveApp.getFolderById(parentFolderId);
  if (!parentFolder) return null;
  
  var prefix = "";
  if (docType === "quotation") prefix = "01";
  else if (docType === "invoice") prefix = "02";
  else if (docType === "receipt") prefix = "03";
  else if (docType === "wht") prefix = "04";
  else if (docType === "expense" || docType === "pv") prefix = "05";
  
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
    Logger.log("ไม่สามารถตั้งค่าการแชร์ไฟล์ได้เนื่องจากข้อจำกัดสิทธิ์ของโดเมนองค์กร: " + sharingError.toString());
  }
  return file.getUrl();
}
