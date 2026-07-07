/**
 * Feltz Studio Sync Script (v1.2)
 * วัตถุประสงค์: ซิงค์ข้อมูลบัญชีและปฏิทินสำหรับ Feltz Super App (โครงสร้าง 7 คอลัมน์)
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
    var spreadsheetId = data.spreadsheetId;
    
    if (!spreadsheetId) {
      return createJsonResponse({
        "status": "error",
        "message": "ไม่พบ Spreadsheet ID ในพารามิเตอร์ที่ส่งเข้ามานะแก!"
      });
    }
    
    var activeSpreadsheet = SpreadsheetApp.openById(spreadsheetId);
    
    // 1. type === 'fetch_summary'
    if (data.type === 'fetch_summary') {
      var grabSpreadsheetId = data.grabSpreadsheetId || spreadsheetId;
      var grabSpreadsheet = (grabSpreadsheetId === spreadsheetId) ? activeSpreadsheet : SpreadsheetApp.openById(grabSpreadsheetId);
      
      var summaryData = [];
      for (var i = 0; i < THAI_MONTHS.length; i++) {
        var mName = THAI_MONTHS[i];
        var feltzIncome = 0;
        var feltzExpense = 0;
        var feltzNetProfit = 0;
        var feltzSavings = 0;
        var grabTotal = 0;
        
        // 1.1 อ่านรายรับ Feltz และรายจ่ายจาก Spreadsheet หลัก
        var mainSheet = activeSpreadsheet.getSheetByName(mName);
        if (mainSheet) {
          var mainLastRow = mainSheet.getLastRow();
          
          if (mainLastRow > 1) {
            // ค้นหาแถวที่มีคำว่า "ยอดรวมทั้งเดือน", "รายได้สุทธิ", และ "ยอดรวมเงินเก็บสะสม 10%" จากข้อความคอลัมน์ B แยกแต่ละแถว
            var colBValues = mainSheet.getRange(1, 2, mainLastRow, 1).getValues();
            var totalRowIdx = -1;
            var netProfitRowIdx = -1;
            var savingsRowIdx = -1;
            
            for (var r = 0; r < colBValues.length; r++) {
              var cellVal = colBValues[r][0];
              if (cellVal) {
                var cleanText = cellVal.toString().trim();
                if (cleanText === 'ยอดรวมทั้งเดือน') {
                  totalRowIdx = r + 1;
                } else if (cleanText === 'รายได้สุทธิ') {
                  netProfitRowIdx = r + 1;
                } else if (cleanText === 'ยอดรวมเงินเก็บสะสม 10%') {
                  savingsRowIdx = r + 1;
                }
              }
            }
            
            if (totalRowIdx !== -1) {
              feltzIncome = parseFloat(mainSheet.getRange(totalRowIdx, 3).getValue()) || 0; // คอลัมน์ C (3)
              feltzExpense = parseFloat(mainSheet.getRange(totalRowIdx, 5).getValue()) || 0; // คอลัมน์ E (5)
            }
            
            if (netProfitRowIdx !== -1) {
              feltzNetProfit = parseFloat(mainSheet.getRange(netProfitRowIdx, 3).getValue()) || 0; // คอลัมน์ C (3)
            } else if (totalRowIdx !== -1) {
              feltzNetProfit = feltzIncome - feltzExpense;
            }
            
            if (savingsRowIdx !== -1) {
              feltzSavings = parseFloat(mainSheet.getRange(savingsRowIdx, 3).getValue()) || 0; // คอลัมน์ C (3)
            } else if (totalRowIdx !== -1) {
              feltzSavings = feltzIncome * 0.10;
            }
            
            // กรณีไม่มีทั้ง 3 แถวเลย ให้ตกไปที่ fallback คำนวณสดจากแถวที่ 2 ถึง 32
            if (totalRowIdx === -1 && netProfitRowIdx === -1 && savingsRowIdx === -1) {
              var limitRow = Math.min(mainLastRow, 32);
              if (limitRow >= 2) {
                var colCValues = mainSheet.getRange(2, 3, limitRow - 1, 1).getValues();
                colCValues.forEach(function(row) {
                  var val = parseFloat(row[0]);
                  if (!isNaN(val)) feltzIncome += val;
                });
                
                var colEValues = mainSheet.getRange(2, 5, limitRow - 1, 1).getValues();
                colEValues.forEach(function(row) {
                  var val = parseFloat(row[0]);
                  if (!isNaN(val)) feltzExpense += val;
                });
              }
              feltzNetProfit = feltzIncome - feltzExpense;
              feltzSavings = feltzIncome * 0.10;
            }
          }
        }
        
        // 1.2 อ่านรายรับ Grab จาก Grab Spreadsheet
        if (grabSpreadsheet) {
          var grabSheet = grabSpreadsheet.getSheetByName(mName);
          if (grabSheet) {
            var grabLastRow = grabSheet.getLastRow();
            if (grabLastRow > 1) {
              // ดึงข้อมูลคอลัมน์ C (3) และ D (4) เริ่มตั้งแต่แถวที่ 2
              var colCD = grabSheet.getRange(2, 3, grabLastRow - 1, 2).getValues();
              for (var r = 0; r < colCD.length; r++) {
                var valC = parseFloat(colCD[r][0]);
                var valD = parseFloat(colCD[r][1]);
                if (!isNaN(valC)) grabTotal += valC;
                if (!isNaN(valD)) grabTotal += valD;
              }
            }
          }
        }
        
        // บวกยอด Grab เข้ากับรายรับรวม, รายได้สุทธิ, และเงินเก็บสะสม 10% ของเดือนนั้น
        var income = feltzIncome + grabTotal;
        var expense = feltzExpense;
        var profit = feltzNetProfit + grabTotal;
        var savings = feltzSavings + (grabTotal * 0.10);
        
        summaryData.push({
          month: mName,
          monthName: mName,
          income: income,
          expense: expense,
          profit: profit,
          savings: savings
        });
      }
      
      return createJsonResponse({
        "status": "success",
        "data": summaryData
      });
    }
    
    // 2. type === 'general'
    else if (data.type === 'general') {
      var date = data.date; // format: DD/MM/YYYY
      var time = data.time || '12:00';
      var genDesc = data.genDesc || '';
      var hasTax = data.hasTaxWithholding || false;
      var amount = parseFloat(data.amount) || 0;
      var calendarEventId = data.calendarEventId || '';
      
      var sheetName = getMonthNameFromDateStr(date);
      var sheet = getOrCreateMonthSheet(activeSpreadsheet, sheetName);
      
      var parts = date.split('/');
      var day = parseInt(parts[0], 10);
      var targetRow = day + 1; // เขียนตรงตามวัน (แถว 2 = วันที่ 1)
      
      // บันทึก วันที่, รายละเอียดงาน, รายรับ, หักภาษี 3% (ถ้ามี), เงินเก็บสะสม 10% (เลี่ยงการเขียนทับคอลัมน์ 4 และ 5 เพื่อรักษารายจ่ายเดิม)
      sheet.getRange(targetRow, 1).setValue(date);
      sheet.getRange(targetRow, 2).setValue(genDesc);
      sheet.getRange(targetRow, 3).setValue(amount);
      sheet.getRange(targetRow, 6).setValue(hasTax ? amount * 0.03 : 0);
      sheet.getRange(targetRow, 7).setValue(amount * 0.10);
      
      // อัปเดตสี Google Calendar เป็นสีเขียว (10) เพื่อบอกว่าบันทึกแล้ว
      if (calendarEventId) {
        try {
          updateCalendarEventColor(calendarEventId, "10");
        } catch (e) {
          // ละเว้นหากเกิดข้อผิดพลาด
        }
      }
      
      return createJsonResponse({ "status": "success" });
    }
    
    // 3. type === 'expense'
    else if (data.type === 'expense') {
      var date = data.date; // DD/MM/YYYY
      var expDesc = data.expDesc || '';
      var amount = parseFloat(data.amount) || 0;
      
      var sheetName = getMonthNameFromDateStr(date);
      var sheet = getOrCreateMonthSheet(activeSpreadsheet, sheetName);
      
      var parts = date.split('/');
      var day = parseInt(parts[0], 10);
      var targetRow = day + 1; // เขียนตรงตามวัน (แถว 2 = วันที่ 1)
      
      // บันทึก วันที่, รายละเอียดรายจ่าย, รายจ่าย
      sheet.getRange(targetRow, 1).setValue(date);
      sheet.getRange(targetRow, 4).setValue(expDesc);
      sheet.getRange(targetRow, 5).setValue(amount);
      
      return createJsonResponse({ "status": "success" });
    }
    
    // 5. Fixed Costs Management
    else if (data.type === 'get_fixed_costs') {
      var sheet = getOrCreateFixedCostsSheet(activeSpreadsheet);
      var lastRow = sheet.getLastRow();
      var fixedCosts = [];
      if (lastRow > 1) {
        var values = sheet.getRange(2, 1, lastRow - 1, 2).getValues();
        values.forEach(function(row) {
          if (row[0]) {
            fixedCosts.push({
              desc: row[0],
              amount: parseFloat(row[1]) || 0
            });
          }
        });
      }
      return createJsonResponse({
        "status": "success",
        "data": fixedCosts
      });
    }
    
    else if (data.type === 'add_fixed_cost') {
      var desc = data.desc;
      var amount = parseFloat(data.amount) || 0;
      if (!desc) {
        return createJsonResponse({ "status": "error", "message": "ไม่พบรายละเอียด Fixed Cost" });
      }
      var sheet = getOrCreateFixedCostsSheet(activeSpreadsheet);
      sheet.appendRow([desc, amount]);
      beautifyFixedCostsSheet(sheet);
      return createJsonResponse({ "status": "success" });
    }
    
    else if (data.type === 'delete_fixed_cost') {
      var desc = data.desc;
      if (!desc) {
        return createJsonResponse({ "status": "error", "message": "ไม่ระบุรายละเอียด Fixed Cost ที่จะลบ" });
      }
      var sheet = getOrCreateFixedCostsSheet(activeSpreadsheet);
      var lastRow = sheet.getLastRow();
      var deleted = false;
      if (lastRow > 1) {
        var values = sheet.getRange(2, 1, lastRow - 1, 1).getValues();
        for (var r = values.length - 1; r >= 0; r--) {
          if (values[r][0] === desc) {
            sheet.deleteRow(r + 2);
            deleted = true;
          }
        }
      }
      if (deleted) {
        beautifyFixedCostsSheet(sheet);
        return createJsonResponse({ "status": "success" });
      } else {
        return createJsonResponse({ "status": "error", "message": "ไม่พบรายการที่จะลบ" });
      }
    }
    
    // 6. Todo tasks Management
    else if (data.type === 'read') {
      var sheetName = data.sheetName || 'Todo';
      var sheet = activeSpreadsheet.getSheetByName(sheetName);
      if (!sheet) {
        return createJsonResponse({
          "status": "error",
          "message": "ไม่พบแท็บชีต " + sheetName + " ของแกนะ!"
        });
      }
      var lastRow = sheet.getLastRow();
      var lastCol = sheet.getLastColumn();
      var values = [];
      if (lastRow > 1 && lastCol > 0) {
        values = sheet.getRange(2, 1, lastRow - 1, lastCol).getDisplayValues();
      }
      return createJsonResponse({
        "status": "success",
        "values": values
      });
    }
    
    else if (data.type === 'overwrite') {
      var sheetName = data.sheetName || 'Todo';
      var headers = data.headers;
      var rows = data.rows;
      var sheet = activeSpreadsheet.getSheetByName(sheetName);
      if (!sheet) {
        sheet = activeSpreadsheet.insertSheet(sheetName);
      }
      sheet.clear();
      if (headers && headers.length > 0) {
        sheet.appendRow(headers);
      }
      if (rows && rows.length > 0) {
        sheet.getRange(2, 1, rows.length, rows[0].length).setValues(rows);
      }
      beautifyTodoSheet(sheet);
      return createJsonResponse({ "status": "success" });
    }
    
    // 7. Google Calendar API Sync
    else if (data.type === 'fetch_calendar_events') {
      var startDate = data.startDate;
      var endDate = data.endDate;
      var eventsData = getCalendarEvents(startDate, endDate);
      return createJsonResponse({
        "status": "success",
        "data": eventsData
      });
    }
    
    else if (data.type === 'update_calendar_event_color') {
      var eventId = data.eventId;
      var colorId = data.colorId;
      updateCalendarEventColor(eventId, colorId);
      return createJsonResponse({ "status": "success" });
    }
    
    // Fallback: create_calendar_event
    else if (data.type === 'create_calendar_event') {
      var title = data.title;
      var description = data.description || '';
      var startTime = data.startTime;
      var endTime = data.endTime;
      
      var calendar = CalendarApp.getDefaultCalendar();
      var event = calendar.createEvent(title, new Date(startTime), new Date(endTime), {
        description: description
      });
      
      var eventData = {
        id: event.getId(),
        title: event.getTitle(),
        description: event.getDescription() || '',
        startTime: event.getStartTime().toISOString(),
        endTime: event.getEndTime().toISOString(),
        colorId: getEventColorIdFromEnum(event.getColor())
      };
      
      return createJsonResponse({
        "status": "success",
        "data": eventData
      });
    }
    

    
    // INVALID TYPE
    else {
      return createJsonResponse({
        "status": "error",
        "message": "ประเภทธุรกรรม '" + data.type + "' ไม่ถูกต้องนะแก!"
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
  if (mIdx >= 0 && mIdx < 12) {
    return THAI_MONTHS[mIdx];
  }
  return THAI_MONTHS[0];
}

// Helper: Get Block Last Row
function getBlockLastRow(sheet, startCol, numCols) {
  var lastRow = sheet.getLastRow();
  if (lastRow === 0) return 0;
  var range = sheet.getRange(1, startCol, lastRow, numCols);
  var values = range.getValues();
  for (var i = values.length - 1; i >= 0; i--) {
    var rowEmpty = true;
    for (var j = 0; j < numCols; j++) {
      if (values[i][j] !== "") {
        rowEmpty = false;
        break;
      }
    }
    if (!rowEmpty) {
      return i + 1;
    }
  }
  return 0;
}

// Helper: Get or Create Month Sheet (7 คอลัมน์)
function getOrCreateMonthSheet(activeSpreadsheet, sheetName) {
  var sheet = activeSpreadsheet.getSheetByName(sheetName);
  if (!sheet) {
    sheet = activeSpreadsheet.insertSheet(sheetName);
    var headers = [
      "วันที่", "รายละเอียดงาน", "รายรับ", "รายละเอียดรายจ่าย", "รายจ่าย", "หัก ณ ที่จ่าย 3%", "เก็บสะสม 10%"
    ];
    sheet.appendRow(headers);
    beautifyMonthSheet(sheet);
  }
  return sheet;
}

// Helper: Get or Create Fixed Costs Sheet
function getOrCreateFixedCostsSheet(activeSpreadsheet) {
  var sheetName = "ตั้งค่า Fix Cost";
  var sheet = activeSpreadsheet.getSheetByName(sheetName);
  if (!sheet) {
    sheet = activeSpreadsheet.insertSheet(sheetName);
    sheet.appendRow(["รายละเอียด", "จำนวนเงิน"]);
    beautifyFixedCostsSheet(sheet);
  }
  return sheet;
}

// Helper: Beautify Month Sheet (A-G เท่านั้น)
function beautifyMonthSheet(sheet) {
  // ยกเลิกการลบคอลัมน์หลัง Col 7 ตามคำขอ (ให้ปล่อยไว้เผื่อมีโน้ตหรือสูตรอื่น)


  // A-C (1-3) สีส้ม (รายรับ)
  sheet.getRange("A1:C1").setFontWeight("bold")
                         .setBackground("#ffedd5")
                         .setFontColor("#9a3412")
                         .setHorizontalAlignment("center")
                         .setVerticalAlignment("middle")
                         .setFontSize(10)
                         .setFontFamily("Google Sans Code");
  
  // D-E (4-5) สีแดง (รายจ่าย)
  sheet.getRange("D1:E1").setFontWeight("bold")
                         .setBackground("#fee2e2")
                         .setFontColor("#991b1b")
                         .setHorizontalAlignment("center")
                         .setVerticalAlignment("middle")
                         .setFontSize(10)
                         .setFontFamily("Google Sans Code");
                         
  // F-G (6-7) สีเขียว (ภาษีและเงินออม)
  sheet.getRange("F1:G1").setFontWeight("bold")
                         .setBackground("#dcfce7")
                         .setFontColor("#166534")
                         .setHorizontalAlignment("center")
                         .setVerticalAlignment("middle")
                         .setFontSize(10)
                         .setFontFamily("Google Sans Code");

  sheet.setRowHeight(1, 30);
  sheet.setFrozenRows(1);
  
  var lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    var dataRange = sheet.getRange(2, 1, lastRow - 1, 7);
    dataRange.setFontFamily("Google Sans Code")
             .setFontSize(10)
             .setVerticalAlignment("middle");
             
    sheet.setRowHeights(2, lastRow - 1, 24);
    
    // Batch update backgrounds to prevent rate limiting
    var backgrounds = [];
    for (var r = 2; r <= lastRow; r++) {
      var bg = (r % 2 === 0) ? "#fafafa" : "#ffffff";
      backgrounds.push([bg, bg, bg, bg, bg, bg, bg]);
    }
    dataRange.setBackgrounds(backgrounds);
    
    dataRange.setBorder(true, true, true, true, true, true, "#e5e7eb", SpreadsheetApp.BorderStyle.SOLID);
  }
  
  sheet.getRange("A1:C1").setBorder(null, null, true, null, null, null, "#9ca3af", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  sheet.getRange("D1:E1").setBorder(null, null, true, null, null, null, "#9ca3af", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  sheet.getRange("F1:G1").setBorder(null, null, true, null, null, null, "#9ca3af", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  
  sheet.autoResizeColumns(1, 7);
  
  for (var c = 1; c <= 7; c++) {
    var w = sheet.getColumnWidth(c);
    if (w < 90) sheet.setColumnWidth(c, 90);
  }
}

// Helper: Beautify Fixed Costs Sheet with Batch formatting
function beautifyFixedCostsSheet(sheet) {
  var lastCol = sheet.getLastColumn();
  if (lastCol === 0) return;
  var headers = sheet.getRange(1, 1, 1, lastCol);
  headers.setFontWeight("bold")
         .setBackground("#f3f4f6")
         .setFontColor("#1f2937")
         .setHorizontalAlignment("center")
         .setVerticalAlignment("middle")
         .setFontSize(10)
         .setFontFamily("Google Sans Code");
  
  sheet.setRowHeight(1, 30);
  sheet.setFrozenRows(1);
  
  var lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    var dataRange = sheet.getRange(2, 1, lastRow - 1, lastCol);
    dataRange.setFontFamily("Google Sans Code")
             .setFontSize(10)
             .setVerticalAlignment("middle");
    sheet.setRowHeights(2, lastRow - 1, 24);
    
    // Batch update backgrounds
    var backgrounds = [];
    for (var r = 2; r <= lastRow; r++) {
      var bg = (r % 2 === 0) ? "#fafafa" : "#ffffff";
      var rowBg = [];
      for (var c = 1; c <= lastCol; c++) {
        rowBg.push(bg);
      }
      backgrounds.push(rowBg);
    }
    dataRange.setBackgrounds(backgrounds);
    
    dataRange.setBorder(true, true, true, true, true, true, "#e5e7eb", SpreadsheetApp.BorderStyle.SOLID);
  }
  headers.setBorder(null, null, true, null, null, null, "#9ca3af", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  sheet.autoResizeColumns(1, lastCol);
  for (var c = 1; c <= lastCol; c++) {
    var w = sheet.getColumnWidth(c);
    if (w < 100) sheet.setColumnWidth(c, 100);
  }
}

// Helper: Beautify Todo Sheet with Batch formatting
function beautifyTodoSheet(sheet) {
  var lastCol = sheet.getLastColumn();
  if (lastCol === 0) return;
  var headers = sheet.getRange(1, 1, 1, lastCol);
  headers.setFontWeight("bold")
         .setBackground("#f3e8ff")
         .setFontColor("#581c87")
         .setHorizontalAlignment("center")
         .setVerticalAlignment("middle")
         .setFontSize(10)
         .setFontFamily("Google Sans Code");
         
  sheet.setRowHeight(1, 30);
  sheet.setFrozenRows(1);
  
  var lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    var dataRange = sheet.getRange(2, 1, lastRow - 1, lastCol);
    dataRange.setFontFamily("Google Sans Code")
             .setFontSize(10)
             .setVerticalAlignment("middle");
    sheet.setRowHeights(2, lastRow - 1, 24);
    
    // Batch update backgrounds
    var backgrounds = [];
    for (var r = 2; r <= lastRow; r++) {
      var bg = (r % 2 === 0) ? "#fafafa" : "#ffffff";
      var rowBg = [];
      for (var c = 1; c <= lastCol; c++) {
        rowBg.push(bg);
      }
      backgrounds.push(rowBg);
    }
    dataRange.setBackgrounds(backgrounds);
    
    dataRange.setBorder(true, true, true, true, true, true, "#e5e7eb", SpreadsheetApp.BorderStyle.SOLID);
  }
  headers.setBorder(null, null, true, null, null, null, "#9ca3af", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  sheet.autoResizeColumns(1, lastCol);
}



// Google Calendar API Helper wrapper
function getCalendarEvents(startDate, endDate) {
  try {
    if (typeof Calendar !== 'undefined') {
      return getCalendarEventsAdvanced(startDate, endDate);
    }
  } catch (e) {}
  return getCalendarEventsStandard(startDate, endDate);
}

function updateCalendarEventColor(eventId, colorId) {
  try {
    if (typeof Calendar !== 'undefined') {
      updateCalendarEventColorAdvanced(eventId, colorId);
      return;
    }
  } catch (e) {}
  updateCalendarEventColorStandard(eventId, colorId);
}

function getCalendarEventsAdvanced(startDate, endDate) {
  var calendarId = "primary";
  var events = Calendar.Events.list(calendarId, {
    timeMin: startDate,
    timeMax: endDate,
    singleEvents: true,
    orderBy: "startTime"
  });
  if (events.items) {
    return events.items.map(function(item) {
      return {
        id: item.id,
        title: item.summary || "(No Title)",
        description: item.description || "",
        startTime: item.start.dateTime || item.start.date,
        endTime: item.end.dateTime || item.end.date,
        colorId: item.colorId || ""
      };
    });
  }
  return [];
}

function updateCalendarEventColorAdvanced(eventId, colorId) {
  var calendarId = "primary";
  Calendar.Events.patch({ colorId: colorId }, calendarId, eventId);
}

function getCalendarEventsStandard(startDate, endDate) {
  var calendar = CalendarApp.getDefaultCalendar();
  var events = calendar.getEvents(new Date(startDate), new Date(endDate));
  return events.map(function(ev) {
    return {
      id: ev.getId(),
      title: ev.getTitle() || "(No Title)",
      description: ev.getDescription() || "",
      startTime: ev.getStartTime().toISOString(),
      endTime: ev.getEndTime().toISOString(),
      colorId: getEventColorIdFromEnum(ev.getColor())
    };
  });
}

function updateCalendarEventColorStandard(eventId, colorId) {
  var calendar = CalendarApp.getDefaultCalendar();
  var event = calendar.getEventById(eventId);
  if (event) {
    event.setColor(getEventColorEnum(colorId));
  }
}

// Convert Color ID to CalendarApp.EventColor Enum
function getEventColorEnum(colorId) {
  if (!colorId) return CalendarApp.EventColor.BLUE;
  switch (String(colorId)) {
    case "1": return CalendarApp.EventColor.PALE_BLUE;
    case "2": return CalendarApp.EventColor.PALE_GREEN;
    case "3": return CalendarApp.EventColor.MAUVE;
    case "4": return CalendarApp.EventColor.PALE_RED;
    case "5": return CalendarApp.EventColor.YELLOW;
    case "6": return CalendarApp.EventColor.ORANGE;
    case "7": return CalendarApp.EventColor.CYAN;
    case "8": return CalendarApp.EventColor.GRAY;
    case "9": return CalendarApp.EventColor.BLUE;
    case "10": return CalendarApp.EventColor.GREEN;
    case "11": return CalendarApp.EventColor.RED;
    default: return CalendarApp.EventColor.BLUE;
  }
}

// Convert CalendarApp.EventColor Enum to Color ID
function getEventColorIdFromEnum(colorEnum) {
  if (!colorEnum) return "";
  var str = String(colorEnum).toUpperCase();
  
  if (str.indexOf("PALE_GREEN") !== -1) return "2";
  
  // Green variations mapping (Sage, Basil, Mint, Sprout, Teal, Forest, Olive etc.)
  if (str.indexOf("GREEN") !== -1 || str.indexOf("MINT") !== -1 || str.indexOf("SPROUT") !== -1 || 
      str.indexOf("TEAL") !== -1 || str.indexOf("FOREST") !== -1 || str.indexOf("OLIVE") !== -1 || 
      str.indexOf("SAGE") !== -1 || str.indexOf("BASIL") !== -1) {
    return "10";
  }
  
  // Red variations mapping (Flamingo, Tomato, Cherry, Crimson etc.)
  if (str.indexOf("RED") !== -1 || str.indexOf("CHERRY") !== -1 || str.indexOf("CRIMSON") !== -1 || 
      str.indexOf("FLAMINGO") !== -1 || str.indexOf("TOMATO") !== -1) {
    return "11";
  }
  
  // Yellow/Orange variations mapping
  if (str.indexOf("YELLOW") !== -1 || str.indexOf("LEMON") !== -1 || str.indexOf("MUSTARD") !== -1 || 
      str.indexOf("ORANGE") !== -1 || str.indexOf("PEACH") !== -1 || str.indexOf("PUMPKIN") !== -1 || 
      str.indexOf("MELON") !== -1) {
    return "5";
  }
  
  if (str.indexOf("PALE_BLUE") !== -1) return "1";
  if (str.indexOf("MAUVE") !== -1) return "3";
  if (str.indexOf("CYAN") !== -1) return "7";
  if (str.indexOf("GRAY") !== -1) return "8";
  if (str.indexOf("BLUE") !== -1) return "9";
  return "";
}
