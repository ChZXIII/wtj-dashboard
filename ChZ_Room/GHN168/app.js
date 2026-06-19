// --- GHN168 Dashboard & Document Sync App Logic ---

// Catch and display global errors on screen for easy debugging
window.onerror = function(message, source, lineno, colno, error) {
  // Ignore generic cross-origin script errors (often caused by browser extensions or file:// protocol security restrictions)
  if (message === 'Script error.' || lineno === 0 || colno === 0) {
    console.warn(`Ignored generic cross-origin/extension script error: ${message} at line ${lineno}:${colno}`);
    return false;
  }
  alert(`JS ERROR:\n${message}\nat line ${lineno}:${colno}`);
  return false;
};

// Safe safeStorage wrapper to prevent crashes when third-party storage is blocked
const safeStorage = {
  getItem(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (e) {
      console.warn(`safeStorage.getItem failed for key "${key}":`, e);
      return null;
    }
  },
  setItem(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (e) {
      console.warn(`safeStorage.setItem failed for key "${key}":`, e);
    }
  }
};

// --- State Management ---
let currentView = 'dashboard';
let currentDocType = 'quotation'; // quotation, invoice, receipt, wht
let docItems = [{ desc: '', qty: 1, unit: 'งาน', price: 0, worker: 'เก่ง' }];
let dbDocs = []; // Local history of documents
let docHubLinks = []; // Google Drive documents
let syncHistory = []; // Logs of synced items
let editingDocIndex = null;
let pettyCashDb = [];
let payrollDb = [];
let bankRecDb = [];

// Default configs
const defaultSellerConfig = {
  sellerName: 'บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด',
  sellerNameEn: 'GHN 168 MEDIA & CREATION COMPANY LIMITED',
  sellerTaxId: '0105566123456',
  sellerAddress: '65/1 ถนนต้นขาม 2 ตำบลท่าศาลา อำเภอเมือง จังหวัดเชียงใหม่ 50000',
  sellerPhone: '089-554-4355',
  sellerEmail: 'ghn168media@gmail.com',
  bankDetails: 'ธนาคารกสิกรไทย เลขที่ 123-4-56789-0 บจก. จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น',
  signerName: 'มงคล วงศ์สกุลยานนท์'
};

const PREDEFINED_PAYEES = {
  'เก่ง': {
    name: 'นาย มงคล วงศ์สกุลยานนท์',
    taxId: '3509900218949',
    branch: '00000',
    address: '65/1 ถ.ต้นขาม2 ต.ท่าศาลา อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50000',
    category: '101 - ค่าจ้างทีมงานภายนอก/ฟรีแลนซ์ (Freelance Crew Fee)',
    description: 'ค่าจ้างทำงาน',
    rate: '3'
  },
  'พี่นิค': {
    name: 'นาย อนุชิต  อภิชัย',
    taxId: '3630200045082',
    branch: '00000',
    address: '61/2 ถ.เทพารักษ์ ต.ช้างเผือก อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50300',
    category: '101 - ค่าจ้างทีมงานภายนอก/ฟรีแลนซ์ (Freelance Crew Fee)',
    description: 'ค่าจ้างทำงาน',
    rate: '3'
  },
  'หอม': {
    name: 'นาย ณัฐวัฒน์  ปวงจันทร์หอม',
    taxId: '1509900596688',
    branch: '00000',
    address: '437/2 ถ.ลำพูน ต.วัดเกต อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50000',
    category: '101 - ค่าจ้างทีมงานภายนอก/ฟรีแลนซ์ (Freelance Crew Fee)',
    description: 'ค่าจ้างทำงาน',
    rate: '3'
  },
  'มด': {
    name: 'นาง ณัฐนรี วงศ์สกุลยานนท์',
    taxId: '1509900148537',
    branch: '00000',
    address: '65/1 ถ.ต้นขาม2 ต.ท่าศาลา อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50000',
    category: '101 - ค่าจ้างทีมงานภายนอก/ฟรีแลนซ์ (Freelance Crew Fee)',
    description: 'ค่าจ้างทำงาน',
    rate: '3'
  }
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  try {
    initTheme();
    loadConfiguration();
    loadData();
    setupEventListeners();
    setupPreviewAutoScaling();
    renderDashboard();
    switchView('dashboard');
    setDocType('quotation');
    fetchDocHubFromSheets(false);
    fetchDocumentsFromSheets(false);
  } catch (err) {
    alert(`LOCAL ERROR IN INITIALIZATION:\nName: ${err.name}\nMessage: ${err.message}\nStack: ${err.stack}`);
  }
});

// --- Theme Settings ---
function initTheme() {
  const theme = safeStorage.getItem('ghn168_theme') || 'dark';
  setTheme(theme);
}

// Fixed WebKit rendering issue by binding styles on body class directly
function setTheme(theme) {
  if (theme === 'light') {
    document.body.classList.remove('dark-mode');
    document.body.classList.add('light-mode');
    document.getElementById('themeToggleBtn').innerHTML = `
      <svg class="theme-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
      </svg>
      โหมดมืด (Dark)
    `;
  } else {
    document.body.classList.remove('light-mode');
    document.body.classList.add('dark-mode');
    document.getElementById('themeToggleBtn').innerHTML = `
      <svg class="theme-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m12.728 12.728l.707.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
      </svg>
      โหมดสว่าง (Light)
    `;
  }
  safeStorage.setItem('ghn168_theme', theme);
}

function toggleTheme() {
  const isDark = document.body.classList.contains('dark-mode');
  setTheme(isDark ? 'light' : 'dark');
}

// --- Data Loading & Saving ---
function loadConfiguration() {
  // Load Seller settings
  const sellerData = safeStorage.getItem('ghn168_seller_config');
  if (sellerData) {
    try {
      const parsed = JSON.parse(sellerData);
      
      // Auto-migrate spelling/spacing changes for existing users
      if (parsed.sellerName === 'บริษัท จีเอชเอ็น168 มีเดีย ครีเอชั่น จำกัด (GHN168 Media Creation Co., Ltd.)' || 
          parsed.sellerName === 'บริษัท จีเอชเอ็น168 มีเดีย ครีเอชั่น จำกัด') {
        parsed.sellerName = 'บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด';
        safeStorage.setItem('ghn168_seller_config', JSON.stringify(parsed));
      }
      if (!parsed.sellerNameEn) {
        parsed.sellerNameEn = 'GHN 168 MEDIA & CREATION COMPANY LIMITED';
        safeStorage.setItem('ghn168_seller_config', JSON.stringify(parsed));
      }
      if (parsed.bankDetails && parsed.bankDetails.includes('จีเอชเอ็น168 มีเดีย ครีเอชั่น')) {
        parsed.bankDetails = parsed.bankDetails.replace('จีเอชเอ็น168 มีเดีย ครีเอชั่น', 'จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น');
        safeStorage.setItem('ghn168_seller_config', JSON.stringify(parsed));
      }

      if (parsed.showSeal === undefined) {
        parsed.showSeal = true;
      }
      Object.keys(parsed).forEach(key => {
        // FIXED TYPO: Check element using correct 'doc_sellerName' pattern
        const input = document.getElementById('doc_sellerName') ? document.getElementById(`doc_${key}`) : null;
        if (input) {
          if (input.type === 'checkbox') {
            input.checked = parsed[key];
          } else {
            input.value = parsed[key];
          }
        }
      });
    } catch (e) {
      console.error('Error parsing seller config', e);
    }
  } else {
    // Fill defaults
    document.getElementById('doc_sellerName').value = defaultSellerConfig.sellerName;
    document.getElementById('doc_sellerNameEn').value = defaultSellerConfig.sellerNameEn;
    document.getElementById('doc_sellerTaxId').value = defaultSellerConfig.sellerTaxId;
    document.getElementById('doc_sellerAddress').value = defaultSellerConfig.sellerAddress;
    document.getElementById('doc_sellerPhone').value = defaultSellerConfig.sellerPhone;
    document.getElementById('doc_sellerEmail').value = defaultSellerConfig.sellerEmail;
    document.getElementById('doc_bankDetails').value = defaultSellerConfig.bankDetails;
    document.getElementById('doc_signerName').value = defaultSellerConfig.signerName;
    document.getElementById('doc_showSeal').checked = true;
    saveSellerConfig();
  }

  // Load Script Settings
  const scriptUrl = safeStorage.getItem('ghn168_script_url') || '';
  const sheetId = safeStorage.getItem('ghn168_sheet_id') || '';
  const companyDriveUrl = safeStorage.getItem('ghn168_company_drive_url') || 'https://drive.google.com';
  document.getElementById('settingScriptUrl').value = scriptUrl;
  document.getElementById('settingSheetId').value = sheetId;
  const driveUrlInput = document.getElementById('settingCompanyDriveUrl');
  if (driveUrlInput) {
    driveUrlInput.value = companyDriveUrl;
  }
}

function saveSellerConfig() {
  const config = {
    sellerName: document.getElementById('doc_sellerName').value,
    sellerNameEn: document.getElementById('doc_sellerNameEn').value,
    sellerTaxId: document.getElementById('doc_sellerTaxId').value,
    sellerAddress: document.getElementById('doc_sellerAddress').value,
    sellerPhone: document.getElementById('doc_sellerPhone').value,
    sellerEmail: document.getElementById('doc_sellerEmail').value,
    bankDetails: document.getElementById('doc_bankDetails').value,
    signerName: document.getElementById('doc_signerName').value,
    showSeal: document.getElementById('doc_showSeal').checked
  };
  safeStorage.setItem('ghn168_seller_config', JSON.stringify(config));
  syncDocPreview();
}

function saveScriptSettings() {
  const url = document.getElementById('settingScriptUrl').value.trim();
  let id = document.getElementById('settingSheetId').value.trim();
  const driveUrlInput = document.getElementById('settingCompanyDriveUrl');
  const driveUrl = driveUrlInput ? driveUrlInput.value.trim() : 'https://drive.google.com';
  
  // Auto-extract ID if full Google Sheets URL is pasted
  const sheetUrlRegex = /\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/;
  const match = id.match(sheetUrlRegex);
  if (match) {
    id = match[1];
    document.getElementById('settingSheetId').value = id;
  }
  
  safeStorage.setItem('ghn168_script_url', url);
  safeStorage.setItem('ghn168_sheet_id', id);
  safeStorage.setItem('ghn168_company_drive_url', driveUrl);
  
  // Sync changes to dashboard shortcuts immediately
  renderDashboardDocHubShortcuts();
  
  alert('บันทึกการเชื่อมต่อเรียบร้อยแล้ว');
}

function initializeGoogleSheet() {
  const scriptUrl = safeStorage.getItem('ghn168_script_url');
  const sheetId = safeStorage.getItem('ghn168_sheet_id');
  
  if (!scriptUrl || !sheetId) {
    alert('กรุณากรอก URL และ Spreadsheet ID จากนั้นกด "บันทึกการเชื่อมต่อบัญชี" ก่อนเริ่มใช้งาน');
    return;
  }
  
  // Set loading state on button
  const btn = document.getElementById('btnInitSheets');
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.style.opacity = '0.7';
  btn.innerHTML = `
    <svg class="btn-icon animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M9 11l3-3 3 3m-3-3v12" />
    </svg>
    กำลังจัดเตรียมโครงสร้างชีต...
  `;
  
  const payload = {
    spreadsheetId: sheetId,
    type: 'initialize'
  };
  
  fetch(scriptUrl, {
    method: 'POST',
    mode: 'cors',
    headers: { 'Content-Type': 'text/plain' },
    body: JSON.stringify(payload)
  })
  .then(res => {
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    return res.json();
  })
  .then(res => {
    if (res.status === 'success') {
      alert(`${res.message}`);
    } else {
      alert(`เกิดข้อผิดพลาดจาก Apps Script: ${res.message}`);
    }
  })
  .catch(err => {
    console.error(err);
    alert(`เกิดข้อผิดพลาดในการเชื่อมต่อสคริปต์: ${err.toString()}\n\n*ข้อแนะนำ: ตรวจสอบว่าได้คัดลอกสคริปต์เวอร์ชันล่าสุดไปวางและทำการติดตั้ง (Deploy) เป็น Web App แบบ 'ทุกคน (Anyone)' เรียบร้อยแล้วหรือยัง`);
  })
  .finally(() => {
    btn.disabled = false;
    btn.style.opacity = '1';
    btn.innerHTML = originalHtml;
  });
}

function loadData() {
  const disableMock = safeStorage.getItem('ghn168_disable_mock') === 'true';

  // FIXED STABILITY: Wrapped parsing in try-catch and defensive filters to prevent app crash on data corruption
  try {
    dbDocs = JSON.parse(safeStorage.getItem('ghn168_db_docs')) || [];
    if (!Array.isArray(dbDocs)) dbDocs = [];
    dbDocs = dbDocs.filter(d => d && typeof d === 'object');
  } catch (e) {
    console.error('Error parsing dbDocs, resetting to empty array', e);
    dbDocs = [];
  }

  // Pre-populate dbDocs with sample corporate accounting/project transactions if empty
  if (dbDocs.length === 0 && !disableMock) {
    dbDocs = [
      {
        number: "RE-20260615-001",
        type: "receipt",
        date: "15/06/2026",
        name: "บริษัท ลูกค้าจำกัด",
        detail: "งานถ่ายทำ MV เพลงใจเกเร",
        amount: 50000.00,
        vat: 3500.00,
        wht: 1500.00,
        net: 52000.00,
        status: "synced",
        timestamp: new Date().toLocaleString()
      },
      {
        number: "PV-20260616-102",
        type: "expense",
        date: "16/06/2026",
        name: "สมเกียรติ ใจเกเร",
        category: "ค่าบริการจ้างทำของ",
        desc: "นักแสดงร่วม MV เพลงใจเกเร",
        baseAmount: 15000.00,
        vatAmount: 0.00,
        whtAmount: 450.00,
        amount: 14550.00,
        whtType: "pnd3",
        projectLink: "งานถ่ายทำ MV เพลงใจเกเร",
        status: "synced",
        timestamp: new Date().toLocaleString()
      },
      {
        number: "PV-20260618-999",
        type: "expense",
        date: "18/06/2026",
        name: "หจก. ร้านกล้องโปรดักชั่น",
        category: "ค่าอุปกรณ์สำนักงาน",
        desc: "เช่ากล้องสเตดิแคมรุ่นท็อป",
        baseAmount: 12000.00,
        vatAmount: 840.00,
        whtAmount: 360.00,
        amount: 12480.00,
        whtType: "pnd53",
        projectLink: "งานถ่ายทำ MV เพลงใจเกเร",
        status: "pending_approval",
        timestamp: new Date().toLocaleString()
      }
    ];
    safeStorage.setItem('ghn168_db_docs', JSON.stringify(dbDocs));
  }

  try {
    docHubLinks = JSON.parse(safeStorage.getItem('ghn168_doc_hub')) || [];
    if (!Array.isArray(docHubLinks)) docHubLinks = [];
    docHubLinks = docHubLinks.filter(d => d && typeof d === 'object');
  } catch (e) {
    console.error('Error parsing docHubLinks, resetting to empty array', e);
    docHubLinks = [];
  }

  try {
    syncHistory = JSON.parse(safeStorage.getItem('ghn168_sync_history')) || [];
    if (!Array.isArray(syncHistory)) syncHistory = [];
    syncHistory = syncHistory.filter(d => d && typeof d === 'object');
  } catch (e) {
    console.error('Error parsing syncHistory, resetting to empty array', e);
    syncHistory = [];
  }
  
  // Fill sample hub data if empty
  if (docHubLinks.length === 0 && !disableMock) {
    docHubLinks = [
      { name: 'หนังสือรับรองบริษัท GHN168', category: 'เอกสารจัดตั้ง', url: 'https://drive.google.com/open?id=SampleCompanyCertificate', date: '17/06/2026', desc: 'หนังสือรับรองอัปเดตล่าสุด' },
      { name: 'ภ.พ.20 บริษัท', category: 'เอกสารภาษี', url: 'https://drive.google.com/open?id=SamplePP20', date: '17/06/2026', desc: 'ใบทะเบียนภาษีมูลค่าเพิ่มสำหรับแนบวางบิล' }
    ];
    safeStorage.setItem('ghn168_doc_hub', JSON.stringify(docHubLinks));
  }

  // Load Petty Cash
  try {
    pettyCashDb = JSON.parse(safeStorage.getItem('ghn168_petty_cash')) || [];
    if (!Array.isArray(pettyCashDb)) pettyCashDb = [];
    pettyCashDb = pettyCashDb.filter(d => d && typeof d === 'object');
  } catch (e) {
    console.error('Error parsing pettyCashDb, resetting to empty array', e);
    pettyCashDb = [];
  }

  if (pettyCashDb.length === 0 && !disableMock) {
    pettyCashDb = [
      {
        voucherNo: "PCV-260618-001",
        date: "18/06/2026",
        requester: "เจน",
        category: "ค่าใช้จ่ายเบ็ดเตล็ด",
        detail: "ซื้อกาแฟต้อนรับทีมงาน",
        amountPaid: 320.00,
        balance: 9680.00,
        approver: "เก่ง",
        receiptUrl: "https://drive.google.com/open?id=SampleReceiptCoffee",
        remarks: "ต้อนรับลูกค้าประชุมด่วน",
        status: "synced"
      }
    ];
    safeStorage.setItem('ghn168_petty_cash', JSON.stringify(pettyCashDb));
  }

  // Load Payroll
  try {
    payrollDb = JSON.parse(safeStorage.getItem('ghn168_payroll')) || [];
    if (!Array.isArray(payrollDb)) payrollDb = [];
    payrollDb = payrollDb.filter(d => d && typeof d === 'object');
  } catch (e) {
    console.error('Error parsing payrollDb, resetting to empty array', e);
    payrollDb = [];
  }

  if (payrollDb.length === 0 && !disableMock) {
    payrollDb = [
      {
        payrollId: "PAY-2026-06",
        employeeId: "EMP01",
        employeeName: "เจน บัญชี",
        employeeTaxId: "1100200876543",
        baseSalary: 25000.00,
        allowances: 2000.00,
        totalEarnings: 27000.00,
        ssfDeduction: 750.00,
        whtDeduction: 500.00,
        otherDeductions: 0.00,
        netPay: 25750.00,
        bankAccount: "KBANK 123-4-56789-0",
        status: "โอนเงินแล้ว",
        paySlipUrl: "https://drive.google.com/open?id=SamplePaySlipSomchai",
        syncStatus: "synced"
      }
    ];
    safeStorage.setItem('ghn168_payroll', JSON.stringify(payrollDb));
  }

  // Load Bank Reconciliation
  try {
    bankRecDb = JSON.parse(safeStorage.getItem('ghn168_bank_rec')) || [];
    if (!Array.isArray(bankRecDb)) bankRecDb = [];
    bankRecDb = bankRecDb.filter(d => d && typeof d === 'object');
  } catch (e) {
    console.error('Error parsing bankRecDb, resetting to empty array', e);
    bankRecDb = [];
  }

  if (bankRecDb.length === 0 && !disableMock) {
    bankRecDb = [
      {
        reconciliationId: "REC-2026-06",
        period: "2026-06",
        bankAccount: "KBANK-Main",
        statementBalance: 125000.00,
        bookBalance: 129250.00,
        depositInTransit: 5000.00,
        outstandingCheques: 1000.00,
        bankChargesNotRecorded: 250.00,
        adjustedStatementBalance: 129000.00,
        adjustedBookBalance: 129000.00,
        difference: 0.00,
        reconciledBy: "พิม",
        syncStatus: "synced"
      }
    ];
    safeStorage.setItem('ghn168_bank_rec', JSON.stringify(bankRecDb));
  }
}

function saveData() {
  safeStorage.setItem('ghn168_db_docs', JSON.stringify(dbDocs));
  safeStorage.setItem('ghn168_doc_hub', JSON.stringify(docHubLinks));
  safeStorage.setItem('ghn168_sync_history', JSON.stringify(syncHistory));
  safeStorage.setItem('ghn168_petty_cash', JSON.stringify(pettyCashDb));
  safeStorage.setItem('ghn168_payroll', JSON.stringify(payrollDb));
  safeStorage.setItem('ghn168_bank_rec', JSON.stringify(bankRecDb));
}

// --- Navigation & Routing ---
function updatePageTitle() {
  if (currentView !== 'docgen') {
    document.title = 'GHN168 | Accounting & Document Hub';
    return;
  }
  
  let customTitle = 'เอกสาร';
  if (currentDocType === 'wht') {
    const whtNo = document.getElementById('whtDocNumber') ? document.getElementById('whtDocNumber').value.trim() : '';
    customTitle = 'ใบหัก_ณ_ที่จ่าย_50_ทวิ';
    if (whtNo) customTitle += `_${cleanDocNo(whtNo)}`;
  } else {
    const docNo = document.getElementById('docNumber') ? document.getElementById('docNumber').value.trim() : '';
    if (currentDocType === 'quotation') {
      customTitle = 'ใบเสนอราคา_สัญญาจ้าง';
    } else if (currentDocType === 'invoice') {
      customTitle = 'ใบวางบิล';
    } else if (currentDocType === 'receipt') {
      customTitle = 'ใบเสร็จรับเงิน';
    }
    if (docNo) customTitle += `_${cleanDocNo(docNo)}`;
  }
  
  document.title = customTitle.replace(/[\/\\?%*:|"<>\s]+/g, '_');
}

function switchView(viewId) {
  currentView = viewId;
  document.querySelectorAll('.view-section').forEach(section => {
    section.classList.remove('active');
  });
  
  const targetSection = document.getElementById(`${viewId}-view`);
  if (targetSection) targetSection.classList.add('active');

  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.remove('active');
    if (item.dataset.view === viewId) {
      item.classList.add('active');
    }
  });

  // Re-renders or setup logic
  if (viewId === 'dashboard') {
    renderDashboard();
  } else if (viewId === 'dochub') {
    renderDocHubList();
    fetchDocHubFromSheets(false);
  } else if (viewId === 'expense') {
    renderExpenseList();
  } else if (viewId === 'pettycash') {
    renderPettyCash();
  } else if (viewId === 'payroll') {
    renderPayroll();
  } else if (viewId === 'bankrec') {
    renderBankRec();
  } else if (viewId === 'taxexport') {
    previewTaxFiling();
  }
  
  updatePageTitle();
}

// --- Event Listeners Setup ---
function setupEventListeners() {
  // Auto-blur date inputs on change to close calendar picker on select
  document.querySelectorAll('input[type="date"]').forEach(el => {
    el.addEventListener('change', () => {
      el.blur();
    });
  });

  // Sidebar navigation
  document.querySelectorAll('.nav-item').forEach(item => {
    const btn = item.querySelector('button');
    if (btn) {
      btn.addEventListener('click', () => {
        switchView(item.dataset.view);
        // Mobile menu auto-close on navigate
        if (window.innerWidth <= 768) {
          closeMobileMenu();
        }
      });
    }
  });

  // Mobile Hamburger Toggle
  const mobileMenuBtn = document.getElementById('mobileMenuBtn');
  const sidebar = document.querySelector('.sidebar');
  const sidebarOverlay = document.getElementById('sidebarOverlay');
  const hamburgerIcon = document.querySelector('.hamburger-icon');
  const closeIcon = document.querySelector('.close-icon');

  function toggleMobileMenu() {
    if (!sidebar) return;
    const isActive = sidebar.classList.toggle('active');
    if (sidebarOverlay) sidebarOverlay.classList.toggle('active', isActive);
    
    if (isActive) {
      if (hamburgerIcon) hamburgerIcon.style.display = 'none';
      if (closeIcon) closeIcon.style.display = 'block';
    } else {
      if (hamburgerIcon) hamburgerIcon.style.display = 'block';
      if (closeIcon) closeIcon.style.display = 'none';
    }
  }

  function closeMobileMenu() {
    if (sidebar) sidebar.classList.remove('active');
    if (sidebarOverlay) sidebarOverlay.classList.remove('active');
    if (hamburgerIcon) hamburgerIcon.style.display = 'block';
    if (closeIcon) closeIcon.style.display = 'none';
  }

  if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener('click', toggleMobileMenu);
  }
  if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', closeMobileMenu);
  }

  // Document type tabs
  document.getElementById('btnDocTypeQuotation').addEventListener('click', () => setDocType('quotation'));
  document.getElementById('btnDocTypeInvoice').addEventListener('click', () => setDocType('invoice'));
  document.getElementById('btnDocTypeReceipt').addEventListener('click', () => setDocType('receipt'));
  document.getElementById('btnDocTypeWht').addEventListener('click', () => setDocType('wht'));

  // Quick-select client listeners
  const btnQuickClientMCool = document.getElementById('btnQuickClientMCool');
  if (btnQuickClientMCool) {
    btnQuickClientMCool.addEventListener('click', () => {
      document.getElementById('docClientName').value = 'บริษัท เอ็ม-คูล เฮ้าส์ ออแกไนซ์ จำกัด';
      document.getElementById('docClientTaxId').value = '0505568016475';
      document.getElementById('docClientBranch').value = 'สำนักงานใหญ่';
      const phoneInput = document.getElementById('docClientPhone');
      if (phoneInput) phoneInput.value = '092-419-3953';
      document.getElementById('docClientAddress').value = '21/6 หมู่ 2 ต.ริมใต้ อ.แม่ริม จ.เชียงใหม่ 50180\nE-mail : m-cool-house@hotmail.com, m.cool.house@gmail.com';
      syncDocPreview();
    });
  }

  const btnQuickClientIdex = document.getElementById('btnQuickClientIdex');
  if (btnQuickClientIdex) {
    btnQuickClientIdex.addEventListener('click', () => {
      document.getElementById('docClientName').value = 'บริษัท ไอเด็กซ์ ไมซ์ จำกัด';
      document.getElementById('docClientTaxId').value = '0505555007201';
      document.getElementById('docClientBranch').value = '00000';
      const phoneInput = document.getElementById('docClientPhone');
      if (phoneInput) phoneInput.value = '';
      document.getElementById('docClientAddress').value = '500/60 หมู่ที่ 2 ตำบลแม่เหียะ อำเภอเมืองเชียงใหม่ จังหวัดเชียงใหม่';
      syncDocPreview();
    });
  }

  const inputsToSync = [
    'docClientName', 'docClientTaxId', 'docClientAddress', 'docClientPhone', 'docClientBranch',
    'docNumber', 'docPaymentTerm', 'docProjectName', 'doc_sellerName', 
    'doc_sellerTaxId', 'doc_sellerAddress', 'doc_sellerPhone', 'doc_sellerEmail',
    'doc_bankDetails', 'doc_signerName', 'docRemarks'
  ];
  inputsToSync.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', () => {
        if (id.startsWith('doc_')) {
          saveSellerConfig();
        } else {
          if (id === 'docNumber') {
            updateCreatorSelectFromDocNo(el.value);
          }
          syncDocPreview();
        }
      });
    }
  });

  const creatorSelect = document.getElementById('docCreatorSelect');
  if (creatorSelect) {
    creatorSelect.addEventListener('change', (e) => {
      const selected = e.target.value;
      const docNumInput = document.getElementById('docNumber');
      if (docNumInput) {
        let currentVal = docNumInput.value.trim();
        currentVal = cleanDocNo(currentVal);
        
        if (selected === 'keng') docNumInput.value = `เก่ง-${currentVal}`;
        else if (selected === 'mod') docNumInput.value = `มด-${currentVal}`;
        else if (selected === 'hom') docNumInput.value = `หอม-${currentVal}`;
        else if (selected === 'nick') docNumInput.value = `พี่นิค-${currentVal}`;
        else docNumInput.value = currentVal;
        
        syncDocPreview();
      }
    });
  }

  document.getElementById('docDate').addEventListener('change', () => {
    updateDueDateFromPaymentTerm();
    syncDocPreview();
  });
  
  const paymentTermEl = document.getElementById('docPaymentTerm');
  if (paymentTermEl) {
    paymentTermEl.addEventListener('change', () => {
      updateDueDateFromPaymentTerm();
      syncDocPreview();
    });
  }

  document.getElementById('docDueDate').addEventListener('change', syncDocPreview);

  // Auto-fill documents select listener
  const autofillSelect = document.getElementById('autofillDocSelect');
  if (autofillSelect) {
    autofillSelect.addEventListener('change', (e) => {
      const docNo = e.target.value;
      if (!docNo) return;
      
      const sourceDoc = dbDocs.find(d => d.number === docNo);
      if (!sourceDoc) return;
      
      // ดึงข้อมูลกรอกลงฟอร์ม
      document.getElementById('docClientName').value = sourceDoc.name || '';
      document.getElementById('docClientTaxId').value = sourceDoc.clientTaxId || sourceDoc.taxId || '';
      document.getElementById('docClientAddress').value = sourceDoc.clientAddress || sourceDoc.address || '';
      const phoneInput = document.getElementById('docClientPhone');
      if (phoneInput) {
        phoneInput.value = sourceDoc.clientPhone || sourceDoc.phone || '';
      }
      document.getElementById('docProjectName').value = sourceDoc.detail || sourceDoc.projectName || '';
      
      // ตรวจสอบว่าเป็นเอกสารประเภทเดียวกัน (โหมดแก้ไข) หรือต่างประเภท (โหมดดึงข้อมูลอ้างอิง)
      const isSameType = sourceDoc.type === currentDocType;
      
      if (isSameType) {
        // ถ้าเป็นประเภทเดียวกัน ให้ดึงเลขที่เอกสารมาด้วยเพื่อเซฟทับตัวเดิม
        document.getElementById('docNumber').value = sourceDoc.number;
        updateCreatorSelectFromDocNo(sourceDoc.number);
        if (currentDocType === 'receipt') {
          const invNoEl = document.getElementById('docInvoiceNo');
          if (invNoEl) invNoEl.value = sourceDoc.invoiceNo || '';
        }
      } else {
        // ถ้าต่างประเภทกัน (เช่น ดึง QT มาออก IV) ไม่ต้องเปลี่ยนเลขที่เอกสารของใบใหม่
        updateCreatorSelectFromDocNo(document.getElementById('docNumber').value);
        if (currentDocType === 'receipt') {
          const invNoEl = document.getElementById('docInvoiceNo');
          if (invNoEl) invNoEl.value = sourceDoc.number || '';
        }
      }
      
      // ดึงรายการสินค้า
      if (sourceDoc.items && Array.isArray(sourceDoc.items)) {
        docItems = sourceDoc.items.map(item => ({
          desc: item.desc || '',
          qty: item.qty || 1,
          unit: item.unit || 'งาน',
          price: item.price || 0,
          worker: item.worker || 'เก่ง'
        }));
      } else {
        docItems = [{ desc: sourceDoc.detail || '', qty: 1, unit: 'งาน', price: sourceDoc.amount || 0, worker: 'เก่ง' }];
      }
      
      // อัปเดตตารางและคำนวณยอดเงินใหม่
      renderDocItemsTable();
      calculateDocTotals();
      syncDocPreview();
      
      // ตั้งค่ากลับเป็นเริ่มต้น
      autofillSelect.value = '';
      
      if (isSameType) {
        alert(`โหลดข้อมูลเอกสาร ${sourceDoc.number} เพื่อแก้ไขเรียบร้อยแล้ว (เมื่อกดบันทึกจะบันทึกเขียนทับใบเดิมในระบบ)`);
      } else {
        alert(`ดึงข้อมูลอ้างอิงจากเอกสาร ${sourceDoc.number} เรียบร้อยแล้ว`);
      }
    });
  }

  // Add Item row button
  document.getElementById('btnAddDocItem').addEventListener('click', addDocItem);

  // Checkboxes & Selects
  document.getElementById('doc_showSeal').addEventListener('change', saveSellerConfig);
  document.getElementById('docVatCheckbox').addEventListener('change', calculateDocTotals);
  document.getElementById('docWhtSelect').addEventListener('change', calculateDocTotals);
  document.getElementById('docOwner').addEventListener('change', calculateDocTotals);
  document.getElementById('docRetentionRate').addEventListener('input', calculateDocTotals);
  if (document.getElementById('docRetentionType')) {
    document.getElementById('docRetentionType').addEventListener('change', calculateDocTotals);
  }

  // Signatures
  if (document.getElementById('doc_showSignature')) {
    document.getElementById('doc_showSignature').addEventListener('change', syncDocPreview);
  }
  if (document.getElementById('doc_signatureSelect')) {
    document.getElementById('doc_signatureSelect').addEventListener('change', (e) => {
      const selected = e.target.value;
      const signerInput = document.getElementById('doc_signerName');
      if (signerInput) {
        if (selected === 'keng') signerInput.value = 'มงคล วงศ์สกุลยานนท์';
        else if (selected === 'mod') signerInput.value = 'ณัฐนรี วงศ์สกุลยานนท์';
        else if (selected === 'hom') signerInput.value = 'ณัฐวัฒน์ ปวงจันทร์หอม';
        else if (selected === 'nick') signerInput.value = 'อนุชิต อภิชัย';
        saveSellerConfig();
      }
      syncDocPreview();
    });
  }

  // Export PDF Button
  document.getElementById('btnExportDocPdf').addEventListener('click', () => {
    const isMobileOrTablet = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
                            (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    if (isMobileOrTablet) {
      exportPdfClientSide();
    } else {
      window.print();
    }
  });

  // Create New Doc Button
  const btnCreateNewDoc = document.getElementById('btnCreateNewDoc');
  if (btnCreateNewDoc) {
    btnCreateNewDoc.addEventListener('click', createNewDocument);
  }

  // (Removed event-based document title switching to favor real-time document title synchronization)

  // Save Config Button
  document.getElementById('btnSaveConfig').addEventListener('click', saveScriptSettings);

  // WHT Editor details
  const whtInputs = [
    'whtPayeeName', 'whtPayeeTaxId', 'whtPayeeAddress', 'whtDescription',
    'whtGrossAmount', 'whtRateSelect'
  ];
  whtInputs.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', () => {
        // Reset payee dropdown to manual if user modifies details manually
        if (['whtPayeeName', 'whtPayeeTaxId', 'whtPayeeAddress'].includes(id)) {
          const select = document.getElementById('whtPayeeSelect');
          if (select) select.value = '';
        }
        calculateWhtTotals();
        syncWhtPreview();
      });
    }
  });

  // WHT Predefined Payee Selection Event Listener
  const whtPayeeSelect = document.getElementById('whtPayeeSelect');
  if (whtPayeeSelect) {
    whtPayeeSelect.addEventListener('change', (e) => {
      const selected = e.target.value;
      if (selected && PREDEFINED_PAYEES[selected]) {
        const payee = PREDEFINED_PAYEES[selected];
        document.getElementById('whtPayeeName').value = payee.name;
        document.getElementById('whtPayeeTaxId').value = payee.taxId;
        document.getElementById('whtPayeeBranch').value = payee.branch;
        document.getElementById('whtPayeeAddress').value = payee.address;
        
        const catEl = document.getElementById('whtCategory');
        if (catEl) {
          catEl.value = payee.category;
        }
        
        document.getElementById('whtDescription').value = payee.description;
        
        const rateEl = document.getElementById('whtRateSelect');
        if (rateEl) {
          rateEl.value = payee.rate;
        }
        
        // Hide warning if the taxId is correct length (13 digits)
        const warningEl = document.getElementById('payeeTaxIdWarning');
        if (warningEl) {
          warningEl.style.display = payee.taxId.length === 13 ? 'none' : 'block';
        }
        
        // Recalculate and update preview
        calculateWhtTotals();
        syncWhtPreview();
      }
    });
  }

  document.getElementById('whtDate').addEventListener('change', () => {
    syncWhtPreview();
  });

  document.getElementById('whtDocNumber').addEventListener('input', () => {
    syncWhtPreview();
  });

  // Tax ID validations (ADVISORY)
  document.getElementById('docClientTaxId').addEventListener('input', (e) => {
    validateTaxId(e.target.value, 'clientTaxIdWarning');
  });
  document.getElementById('whtPayeeTaxId').addEventListener('input', (e) => {
    validateTaxId(e.target.value, 'payeeTaxIdWarning');
  });
  document.getElementById('doc_sellerTaxId').addEventListener('input', (e) => {
    validateTaxId(e.target.value, 'sellerTaxIdWarning');
  });

  // Backup & Restore Actions (ADVISORY)
  document.getElementById('btnExportBackup').addEventListener('click', exportBackup);
  document.getElementById('btnImportBackup').addEventListener('click', () => {
    document.getElementById('importBackupFile').click();
  });
  document.getElementById('importBackupFile').addEventListener('change', importBackup);

  const btnClearDb = document.getElementById('btnClearDatabase');
  if (btnClearDb) {
    btnClearDb.addEventListener('click', clearLocalDatabase);
  }

  // Agent Nong Pim Modal Toggle
  const agentProfileWidget = document.querySelector('.agent-profile');
  const agentPimModal = document.getElementById('agentPimModal');
  const btnCloseAgentPimModal = document.getElementById('btnCloseAgentPimModal');
  const confirmPimResetInput = document.getElementById('confirmPimResetInput');

  if (agentProfileWidget && agentPimModal) {
    agentProfileWidget.addEventListener('click', () => {
      // Clear confirmation text on open
      if (confirmPimResetInput) {
        confirmPimResetInput.value = '';
      }
      if (btnClearDb) {
        btnClearDb.disabled = true;
        btnClearDb.style.cursor = 'not-allowed';
        btnClearDb.style.opacity = '0.6';
      }
      agentPimModal.classList.add('active');
    });
  }

  if (btnCloseAgentPimModal && agentPimModal) {
    btnCloseAgentPimModal.addEventListener('click', () => {
      agentPimModal.classList.remove('active');
    });
  }

  // Close Nong Pim modal when clicking backdrop
  if (agentPimModal) {
    agentPimModal.addEventListener('click', (e) => {
      if (e.target === agentPimModal) {
        agentPimModal.classList.remove('active');
      }
    });
  }

  // Text validation to enable reset button
  if (confirmPimResetInput) {
    confirmPimResetInput.addEventListener('input', (e) => {
      const value = e.target.value.trim();
      if (btnClearDb) {
        if (value === 'RESET') {
          btnClearDb.disabled = false;
          btnClearDb.style.cursor = 'pointer';
          btnClearDb.style.opacity = '1';
        } else {
          btnClearDb.disabled = true;
          btnClearDb.style.cursor = 'not-allowed';
          btnClearDb.style.opacity = '0.6';
        }
      }
    });
  }

  const addDocModal = document.getElementById('addDocModal');
  const formAddDoc = document.getElementById('formAddDoc');
  const modalDocCategory = document.getElementById('modalDocCategory');
  const groupCustomCategory = document.getElementById('groupCustomCategory');

  // Open Add Doc Modal
  document.getElementById('btnOpenAddDocModal').addEventListener('click', () => {
    document.querySelector('#addDocModal .modal-title').textContent = 'เพิ่มลิงก์เอกสารใหม่';
    document.getElementById('btnSubmitDocModal').innerHTML = `
      <svg class="btn-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
      </svg>
      บันทึกเอกสาร
    `;
    formAddDoc.reset();
    groupCustomCategory.style.display = 'none';
    addDocModal.classList.add('active');
  });

  // Close Modal Actions
  document.getElementById('btnCloseDocModal').addEventListener('click', () => {
    addDocModal.classList.remove('active');
  });
  document.getElementById('btnCancelDocModal').addEventListener('click', () => {
    addDocModal.classList.remove('active');
  });

  // Toggle Custom Category Input
  modalDocCategory.addEventListener('change', (e) => {
    if (e.target.value === 'อื่นๆ') {
      groupCustomCategory.style.display = 'block';
      document.getElementById('modalDocCustomCategory').required = true;
    } else {
      groupCustomCategory.style.display = 'none';
      document.getElementById('modalDocCustomCategory').required = false;
    }
  });

  // Form Submit Action
  formAddDoc.addEventListener('submit', (e) => {
    e.preventDefault();
    let name = document.getElementById('modalDocName').value.trim();
    let category = modalDocCategory.value;
    if (category === 'อื่นๆ') {
      category = document.getElementById('modalDocCustomCategory').value.trim() || 'เอกสารสำคัญ';
    }
    let url = document.getElementById('modalDocUrl').value.trim();
    let desc = document.getElementById('modalDocDesc').value.trim();

    // AUTO-CORRECTION: If user mistakenly pasted URL in the Name field
    const isUrlPattern = (str) => str.includes('http://') || str.includes('https://') || str.includes('drive.google.com') || str.includes('docs.google.com');
    if (isUrlPattern(name)) {
      const temp = name;
      name = isUrlPattern(url) ? 'เอกสารใหม่' : url;
      url = temp;
      alert('น้องพิมตรวจพบว่าพี่วางลิงก์สลับช่องกับชื่อเอกสาร เลยทำการสลับกลับคืนให้เรียบร้อยแล้วค่ะ!');
    }

    // Auto-prepend protocol if missing
    if (url && !url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://' + url;
    }

    const now = new Date();
    const dateStr = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()}`;

    if (editingDocIndex === null) {
      docHubLinks.push({ name, category, url, date: dateStr, desc: desc || '-' });
    } else {
      docHubLinks[editingDocIndex] = { name, category, url, date: dateStr, desc: desc || '-' };
      editingDocIndex = null;
    }

    saveData();
    renderDocHubList();
    syncDocHubToSheets(false);
    addDocModal.classList.remove('active');
  });

  // Sync Data Button
  document.getElementById('btnSaveAndSyncDoc').addEventListener('click', processDocumentSync);

  // Sync Document Hub Button
  const btnSyncDocHub = document.getElementById('btnSyncDocHub');
  if (btnSyncDocHub) {
    btnSyncDocHub.addEventListener('click', () => {
      fetchDocHubFromSheets(true);
    });
  }

  // --- Expense Tracker Event Listeners ---
  const addExpenseModal = document.getElementById('addExpenseModal');
  const formAddExpense = document.getElementById('formAddExpense');
  const expenseCategory = document.getElementById('expenseCategory');
  const groupCustomExpenseCategory = document.getElementById('groupCustomExpenseCategory');

  if (document.getElementById('btnOpenAddExpenseModal')) {
    // Open Add Expense Modal
    document.getElementById('btnOpenAddExpenseModal').addEventListener('click', () => {
      editingDocIndex = null;
      populateProjectList(); // Populate project list dynamically
      document.querySelector('#addExpenseModal .modal-title').textContent = 'บันทึกรายจ่ายใหม่';
      document.getElementById('btnSubmitExpenseModal').innerHTML = `
        <svg class="btn-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
        </svg>
        บันทึกรายจ่าย
      `;
      formAddExpense.reset();
      setExpenseMode('simple');
      document.getElementById('expenseDate').value = new Date().toISOString().slice(0, 10);
      groupCustomExpenseCategory.style.display = 'none';
      calculateExpenseForm();
      addExpenseModal.classList.add('active');
    });

    // Close Expense Modal
    document.getElementById('btnCloseExpenseModal').addEventListener('click', () => {
      addExpenseModal.classList.remove('active');
    });
    document.getElementById('btnCancelExpenseModal').addEventListener('click', () => {
      addExpenseModal.classList.remove('active');
    });

    // Toggle Custom Expense Category
    expenseCategory.addEventListener('change', (e) => {
      if (e.target.value === 'อื่นๆ') {
        groupCustomExpenseCategory.style.display = 'block';
        document.getElementById('expenseCustomCategory').required = true;
      } else {
        groupCustomExpenseCategory.style.display = 'none';
        document.getElementById('expenseCustomCategory').required = false;
      }
    });

    // Switch mode events
    document.getElementById('btnExpenseModeSimple').addEventListener('click', () => setExpenseMode('simple'));
    document.getElementById('btnExpenseModeDetailed').addEventListener('click', () => setExpenseMode('detailed'));

    // Sync simple VAT dropdown to detailed elements
    const simpleVatSelect = document.getElementById('expenseVatSystemSimple');
    if (simpleVatSelect) {
      simpleVatSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        const priceTypeEl = document.getElementById('expensePriceType');
        const vatSelectEl = document.getElementById('expenseVatSelect');
        if (val === '0') {
          if (priceTypeEl) priceTypeEl.value = 'exclude';
          if (vatSelectEl) vatSelectEl.value = '0';
        } else if (val === '7_exclude') {
          if (priceTypeEl) priceTypeEl.value = 'exclude';
          if (vatSelectEl) vatSelectEl.value = '7';
        } else if (val === '7_include') {
          if (priceTypeEl) priceTypeEl.value = 'include';
          if (vatSelectEl) vatSelectEl.value = '7';
        }
        calculateExpenseForm();
      });
    }

    // Live calculator events
    document.getElementById('expensePriceType').addEventListener('change', calculateExpenseForm);
    document.getElementById('expenseBaseAmount').addEventListener('input', calculateExpenseForm);
    document.getElementById('expenseVatSelect').addEventListener('change', calculateExpenseForm);
    document.getElementById('expenseWhtSelect').addEventListener('change', calculateExpenseForm);

    // Payee Tax ID validation and auto WHT form type selection
    document.getElementById('expensePayeeTaxId').addEventListener('input', (e) => {
      validateTaxId(e.target.value, 'expensePayeeTaxIdWarning');
      const taxIdVal = e.target.value.trim();
      const selectEl = document.getElementById('expenseWhtType');
      const whtSelect = document.getElementById('expenseWhtSelect').value;
      if (selectEl && taxIdVal && whtSelect !== '0') {
        const cleanId = taxIdVal.replace(/\D/g, '');
        if (cleanId.length > 0) {
          if (cleanId.startsWith('0')) {
            selectEl.value = 'pnd53';
          } else {
            selectEl.value = 'pnd3';
          }
        }
      }
    });

    // Form Submit Expense
    formAddExpense.addEventListener('submit', (e) => {
      e.preventDefault();
      saveExpense();
    });
  }

  // Tax filter change listener
  if (document.getElementById('taxFilterMonth')) {
    document.getElementById('taxFilterMonth').addEventListener('change', renderTaxAndProjectSummary);
  }

  // Petty Cash Event Listeners
  if (document.getElementById('btnOpenAddPettyCashModal')) {
    document.getElementById('btnOpenAddPettyCashModal').addEventListener('click', () => {
      editingDocIndex = null;
      document.querySelector('#addPettyCashModal .modal-title').textContent = 'จ่ายเงินสดย่อยใหม่';
      document.getElementById('btnSubmitPettyCashModal').innerHTML = `
        <svg class="btn-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
        </svg>
        บันทึกเงินสดย่อย
      `;
      document.getElementById('formAddPettyCash').reset();
      document.getElementById('pettyCashDate').value = new Date().toISOString().slice(0, 10);
      document.getElementById('pettyCashVoucherNo').value = autoGeneratePettyCashVoucherNo();
      document.getElementById('addPettyCashModal').classList.add('active');
    });

    document.getElementById('btnClosePettyCashModal').addEventListener('click', () => {
      document.getElementById('addPettyCashModal').classList.remove('active');
    });
    document.getElementById('btnCancelPettyCashModal').addEventListener('click', () => {
      document.getElementById('addPettyCashModal').classList.remove('active');
    });
    document.getElementById('formAddPettyCash').addEventListener('submit', (e) => {
      e.preventDefault();
      savePettyCash();
    });
  }

  // Payroll Event Listeners
  if (document.getElementById('btnOpenAddPayrollModal')) {
    document.getElementById('btnOpenAddPayrollModal').addEventListener('click', () => {
      editingDocIndex = null;
      document.querySelector('#addPayrollModal .modal-title').textContent = 'บันทึกรอบจ่ายเงินเดือน';
      document.getElementById('btnSubmitPayrollModal').innerHTML = `
        <svg class="btn-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
        </svg>
        บันทึกเงินเดือน
      `;
      document.getElementById('formAddPayroll').reset();
      document.getElementById('payrollIdInput').value = autoGeneratePayrollId();
      onPayrollEmployeeChange();
      document.getElementById('addPayrollModal').classList.add('active');
    });

    document.getElementById('btnClosePayrollModal').addEventListener('click', () => {
      document.getElementById('addPayrollModal').classList.remove('active');
    });
    document.getElementById('btnCancelPayrollModal').addEventListener('click', () => {
      document.getElementById('addPayrollModal').classList.remove('active');
    });
    document.getElementById('formAddPayroll').addEventListener('submit', (e) => {
      e.preventDefault();
      savePayroll();
    });
  }

  // Bank Reconciliation Event Listeners
  if (document.getElementById('btnOpenAddBankRecModal')) {
    document.getElementById('btnOpenAddBankRecModal').addEventListener('click', () => {
      editingDocIndex = null;
      document.querySelector('#addBankRecModal .modal-title').textContent = 'บันทึกงบกระทบยอดใหม่';
      document.getElementById('btnSubmitBankRecModal').innerHTML = `
        <svg class="btn-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
        </svg>
        บันทึกงบกระทบยอด
      `;
      document.getElementById('formAddBankRec').reset();

      const now = new Date();
      const yyyy = now.getFullYear();
      const mm = String(now.getMonth() + 1).padStart(2, '0');
      const monthVal = `${yyyy}-${mm}`;
      document.getElementById('bankRecPeriod').value = monthVal;
      document.getElementById('bankRecReconciliationId').value = autoGenerateBankRecId(monthVal);
      onBankRecPeriodChange();

      document.getElementById('addBankRecModal').classList.add('active');
    });

    document.getElementById('bankRecPeriod').addEventListener('change', (e) => {
      document.getElementById('bankRecReconciliationId').value = autoGenerateBankRecId(e.target.value);
    });

    document.getElementById('btnCloseBankRecModal').addEventListener('click', () => {
      document.getElementById('addBankRecModal').classList.remove('active');
    });
    document.getElementById('btnCancelBankRecModal').addEventListener('click', () => {
      document.getElementById('addBankRecModal').classList.remove('active');
    });
    document.getElementById('formAddBankRec').addEventListener('submit', (e) => {
      e.preventDefault();
      saveBankRec();
    });
  }
}

// --- Document Editor Actions ---
function setDocType(type, keepCurrentNumber = false) {
  currentDocType = type;
  
  // Toggle buttons active class
  ['Quotation', 'Invoice', 'Receipt', 'Wht'].forEach(t => {
    const btn = document.getElementById(`btnDocType${t}`);
    if (btn) {
      if (t.toLowerCase() === type.toLowerCase()) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    }
  });

  // Display fields according to doc type
  const formDocs = document.getElementById('formGroupDocItems');
  const formWht = document.getElementById('formGroupWhtDetails');
  const previewStandard = document.getElementById('previewStandardDoc');
  const previewWht = document.getElementById('previewWhtDoc');
  const formInternalDetails = document.getElementById('formGroupInternalDetails');

  // Toggle class for standard layout overrides (hiding Qty/Unit/Price columns)
  const formStandardDetails = document.getElementById('formGroupStandardDetails');
  const previewStandardDoc = document.getElementById('previewStandardDoc');
  const editorPriceHeader = document.querySelector('.editor-items-table th.col-price');
  if (type === 'quotation' || type === 'invoice' || type === 'receipt') {
    if (formStandardDetails) formStandardDetails.classList.add('doc-type-quotation');
    if (previewStandardDoc) previewStandardDoc.classList.add('doc-type-quotation');
    if (formDocs) formDocs.classList.add('doc-type-quotation');
    if (editorPriceHeader) {
      editorPriceHeader.innerHTML = 'จำนวนเงิน (บาท)<br>Amount (THB)';
    }
  } else {
    if (formStandardDetails) formStandardDetails.classList.remove('doc-type-quotation');
    if (previewStandardDoc) previewStandardDoc.classList.remove('doc-type-quotation');
    if (formDocs) formDocs.classList.remove('doc-type-quotation');
    if (editorPriceHeader) {
      editorPriceHeader.textContent = 'ราคาต่อหน่วย';
    }
  }

  // Field group toggles
  const groupDueDate = document.getElementById('groupDocDueDate');
  const groupPaymentTerm = document.getElementById('groupDocPaymentTerm');
  const groupInvoiceNo = document.getElementById('groupDocInvoiceNo');
  if (groupInvoiceNo) {
    groupInvoiceNo.style.display = type === 'receipt' ? 'block' : 'none';
  }
  
  const syncBtn = document.getElementById('btnSaveAndSyncDoc');

  if (type === 'wht') {
    formDocs.style.display = 'none';
    formWht.style.display = 'block';
    previewStandard.style.display = 'none';
    previewWht.style.display = 'block';
    if (formInternalDetails) formInternalDetails.style.display = 'none';
    
    // Expenses Sync Button text
    syncBtn.innerHTML = `
      <svg class="btn-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      พิมพ์ 50 ทวิ & บันทึกรายจ่ายลงชีต
    `;
    syncBtn.style.display = 'block';
    
    // Set auto doc number
    if (!keepCurrentNumber) {
      document.getElementById('whtDocNumber').value = autoGenerateDocNumber('wht');
    }
    
    // Reset predefined payee select
    const whtPayeeSelect = document.getElementById('whtPayeeSelect');
    if (whtPayeeSelect) {
      whtPayeeSelect.value = '';
    }
    
    calculateWhtTotals();
    syncWhtPreview();
  } else {
    formDocs.style.display = 'block';
    formWht.style.display = 'none';
    previewStandard.style.display = 'block';
    previewWht.style.display = 'none';
    if (formInternalDetails) formInternalDetails.style.display = (type === 'quotation') ? 'none' : 'block';

    // Show/hide due date terms (hide for receipt and quotation)
    if (type === 'receipt' || type === 'quotation') {
      groupDueDate.style.display = 'none';
      groupPaymentTerm.style.display = 'none';
      syncBtn.style.display = 'block';
      if (type === 'receipt') {
        syncBtn.innerHTML = `
          <svg class="btn-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          พิมพ์ใบเสร็จ & บันทึกรายรับลงชีต
        `;
      } else {
        syncBtn.innerHTML = `
          <svg class="btn-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
          </svg>
          บันทึกประวัติใบเสนอราคาลงเครื่อง
        `;
      }
    } else {
      groupDueDate.style.display = 'block';
      groupPaymentTerm.style.display = 'block';
      syncBtn.style.display = 'block'; // แสดงปุ่มเซฟเสมอสำหรับ QT และ IV
      if (type === 'invoice') {
        syncBtn.innerHTML = `
          <svg class="btn-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
          </svg>
          บันทึกประวัติใบวางบิลลงเครื่อง
        `;
      }
      updateDueDateFromPaymentTerm();
    }

    // โหลดตัวเลือก Dropdown Auto-fill
    const autofillGroup = document.getElementById('groupAutofillDoc');
    const autofillSelect = document.getElementById('autofillDocSelect');
    const autofillLabel = document.getElementById('lblAutofill');

    if (autofillGroup && autofillSelect) {
      autofillSelect.innerHTML = '<option value="">-- เลือกเอกสารอ้างอิง --</option>';
      
      if (type === 'receipt') {
        autofillLabel.textContent = 'ดึงข้อมูลอ้างอิง:';
        
        // Group 1: แก้ไขใบเสร็จเดิม
        const receipts = dbDocs.filter(d => d.type === 'receipt');
        if (receipts.length > 0) {
          const g1 = document.createElement('optgroup');
          g1.label = 'แก้ไขใบเสร็จเดิม';
          receipts.forEach(r => {
            const opt = document.createElement('option');
            opt.value = r.number;
            opt.textContent = `${r.number} - ${r.name}`;
            g1.appendChild(opt);
          });
          autofillSelect.appendChild(g1);
        }
        
        // Group 2: ดึงข้อมูลจากใบวางบิล
        const invoices = dbDocs.filter(d => d.type === 'invoice');
        if (invoices.length > 0) {
          const g2 = document.createElement('optgroup');
          g2.label = 'ดึงข้อมูลจากใบวางบิล';
          invoices.forEach(inv => {
            const opt = document.createElement('option');
            opt.value = inv.number;
            const statusSuffix = inv.paymentStatus ? ` [${inv.paymentStatus}]` : '';
            opt.textContent = `${inv.number} - ${inv.name}${statusSuffix}`;
            g2.appendChild(opt);
          });
          autofillSelect.appendChild(g2);
        }
        
        autofillGroup.style.display = (receipts.length > 0 || invoices.length > 0) ? 'flex' : 'none';
        
      } else if (type === 'invoice') {
        autofillLabel.textContent = 'ดึงข้อมูลอ้างอิง:';
        
        // Group 1: แก้ไขใบวางบิลเดิม
        const invoices = dbDocs.filter(d => d.type === 'invoice');
        if (invoices.length > 0) {
          const g1 = document.createElement('optgroup');
          g1.label = 'แก้ไขใบวางบิลเดิม';
          invoices.forEach(inv => {
            const opt = document.createElement('option');
            opt.value = inv.number;
            opt.textContent = `${inv.number} - ${inv.name}`;
            g1.appendChild(opt);
          });
          autofillSelect.appendChild(g1);
        }
        
        // Group 2: ดึงข้อมูลจากใบเสนอราคา
        const quotations = dbDocs.filter(d => d.type === 'quotation');
        if (quotations.length > 0) {
          const g2 = document.createElement('optgroup');
          g2.label = 'ดึงข้อมูลจากใบเสนอราคา';
          quotations.forEach(qt => {
            const opt = document.createElement('option');
            opt.value = qt.number;
            opt.textContent = `${qt.number} - ${qt.name}`;
            g2.appendChild(opt);
          });
          autofillSelect.appendChild(g2);
        }
        
        autofillGroup.style.display = (invoices.length > 0 || quotations.length > 0) ? 'flex' : 'none';
        
      } else if (type === 'quotation') {
        autofillLabel.textContent = 'แก้ไขใบเสนอราคาเดิม:';
        
        // Group 1: แก้ไขใบเสนอราคาเดิม
        const quotations = dbDocs.filter(d => d.type === 'quotation');
        if (quotations.length > 0) {
          quotations.forEach(qt => {
            const opt = document.createElement('option');
            opt.value = qt.number;
            opt.textContent = `${qt.number} - ${qt.name}`;
            autofillSelect.appendChild(opt);
          });
          autofillGroup.style.display = 'flex';
        } else {
          autofillGroup.style.display = 'none';
        }
      } else {
        autofillGroup.style.display = 'none';
      }
    }

    // Set auto doc number
    if (!keepCurrentNumber) {
      document.getElementById('docNumber').value = autoGenerateDocNumber(type);
    }
    updateCreatorSelectFromDocNo(document.getElementById('docNumber').value);

    renderDocItemsTable();
    calculateDocTotals();
    syncDocPreview();
  }

  hideHitlWarning();
}

function autoGenerateDocNumber(type) {
  const now = new Date();
  const yy = now.getFullYear().toString().substring(2);
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const prefix = type === 'quotation' ? 'QT' : (type === 'invoice' ? 'IV' : (type === 'receipt' ? 'RE' : 'WHT'));
  
  const matchPattern = `${prefix}${yy}${mm}`;
  const monthItems = dbDocs.filter(d => d.number && d.number.startsWith(matchPattern));
  
  let maxNum = 0;
  monthItems.forEach(d => {
    const parts = d.number.split('-');
    if (parts.length > 1) {
      const suffix = parseInt(parts[1], 10);
      if (!isNaN(suffix) && suffix > maxNum) {
        maxNum = suffix;
      }
    }
  });

  const nextNum = String(maxNum + 1).padStart(3, '0');
  return `${matchPattern}-${nextNum}`;
}

function createNewDocument() {
  if (!confirm('ยืนยันการสร้างเอกสารใหม่? ข้อมูลปัจจุบันที่กำลังพิมพ์อยู่จะถูกล้างออก (ข้อมูลที่บันทึกไปก่อนหน้านี้จะไม่สูญหาย)')) {
    return;
  }
  
  // Clear inputs
  document.getElementById('docClientName').value = '';
  document.getElementById('docClientTaxId').value = '';
  document.getElementById('docClientBranch').value = '00000';
  document.getElementById('docClientAddress').value = '';
  const phoneEl = document.getElementById('docClientPhone');
  if (phoneEl) phoneEl.value = '';
  document.getElementById('docProjectName').value = '';
  document.getElementById('docRemarks').value = '';
  
  // Reset items
  const defaultWorker = document.getElementById('docOwner') ? document.getElementById('docOwner').value : 'เก่ง';
  docItems = [{ desc: '', qty: 1, unit: 'งาน', price: 0, worker: defaultWorker }];
  
  // Set auto doc number
  document.getElementById('docNumber').value = autoGenerateDocNumber(currentDocType);
  
  // Reset creator dropdown
  const creatorSelect = document.getElementById('docCreatorSelect');
  if (creatorSelect) creatorSelect.value = '';

  // Render & sync
  renderDocItemsTable();
  calculateDocTotals();
  syncDocPreview();
}

function renderPrevItemsTable() {
  const prevBody = document.getElementById('prevItemsBody');
  if (prevBody) {
    if (docItems.length === 0) {
      const isStandardHidden = currentDocType === 'quotation' || currentDocType === 'invoice' || currentDocType === 'receipt';
      const colspan = isStandardHidden ? 3 : 6;
      prevBody.innerHTML = `<tr><td colspan="${colspan}" style="text-align:center; padding: 15px; font-style:italic;">ไม่มีรายการ</td></tr>`;
    } else {
      prevBody.innerHTML = docItems.map((item, idx) => {
        const total = (item.qty || 0) * (item.price || 0);
        return `
          <tr>
            <td style="text-align:center;">${idx + 1}</td>
            <td style="text-align:left; white-space: pre-wrap;">${escapeHtml(item.desc || '-')}</td>
            <td style="text-align:center;" class="col-qty">${item.qty}</td>
            <td style="text-align:center;" class="col-unit">${escapeHtml(item.unit || 'งาน')}</td>
            <td style="text-align:right;" class="col-price">${item.price.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
            <td style="text-align:right;">${total.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
          </tr>
        `;
      }).join('');
    }
  }
}

function renderDocItemsTable() {
  const body = document.getElementById('editorItemsBody');
  if (!body) return;

  body.innerHTML = docItems.map((item, idx) => `
    <tr>
      <td>
        <textarea oninput="updateDocItem(${idx}, 'desc', this.value)" class="form-control" style="border:none; padding:4px; height: 38px; min-height: 38px; resize: vertical; display: block; font-family: inherit; font-size: inherit; width: 100%;" placeholder="เช่น ถ่ายวีดีโอโฆษณา" required>${escapeHtml(item.desc)}</textarea>
      </td>
      <td style="width: 80px;" class="col-qty">
        <input type="number" value="${item.qty}" min="1" step="any" oninput="updateDocItem(${idx}, 'qty', this.value)" class="form-control" style="border:none; padding:4px; text-align:center;" required>
      </td>
      <td style="width: 80px;" class="col-unit">
        <input type="text" value="${escapeHtml(item.unit)}" oninput="updateDocItem(${idx}, 'unit', this.value)" class="form-control" style="border:none; padding:4px; text-align:center;" placeholder="เช่น งาน" required>
      </td>
      <td style="width: 140px;">
        <input type="number" value="${item.price}" min="0" step="0.01" oninput="updateDocItem(${idx}, 'price', this.value)" class="form-control" style="border:none; padding:4px; text-align:right;" required>
      </td>
      <td style="width: 120px;">
        <select onchange="updateDocItem(${idx}, 'worker', this.value)" class="form-control" style="border:none; padding:4px;">
          <option value="เก่ง" ${item.worker === 'เก่ง' ? 'selected' : ''}>เก่ง</option>
          <option value="พี่นิค" ${item.worker === 'พี่นิค' ? 'selected' : ''}>พี่นิค</option>
          <option value="หอม" ${item.worker === 'หอม' ? 'selected' : ''}>หอม</option>
          <option value="บริษัท" ${item.worker === 'บริษัท' ? 'selected' : ''}>บริษัท (กองกลาง)</option>
        </select>
      </td>
      <td style="text-align:center; width: 60px;">
        <button type="button" class="btn-secondary" onclick="deleteDocItem(${idx})" style="padding:4px 8px; margin:0; background:#fee2e2; color:#b91c1c; border-color:#fee2e2; box-shadow:none;">ลบ</button>
      </td>
    </tr>
  `).join('');

  // Update preview table items
  renderPrevItemsTable();
}

function addDocItem() {
  const defaultWorker = document.getElementById('docOwner') ? document.getElementById('docOwner').value : 'เก่ง';
  docItems.push({ desc: '', qty: 1, unit: 'งาน', price: 0, worker: defaultWorker });
  renderDocItemsTable();
  calculateDocTotals();
}

function deleteDocItem(index) {
  docItems.splice(index, 1);
  renderDocItemsTable();
  calculateDocTotals();
}

function updateDocItem(index, key, val) {
  if (key === 'qty') {
    docItems[index].qty = parseFloat(val) || 0;
  } else if (key === 'price') {
    docItems[index].price = parseFloat(val) || 0;
  } else {
    docItems[index][key] = val;
  }
  calculateDocTotals();
  syncDocPreview();
}

// --- Total Calculations ---
function calculateDocTotals() {
  let subtotal = 0;
  docItems.forEach(item => {
    subtotal += (item.qty || 0) * (item.price || 0);
  });

  const vatChecked = document.getElementById('docVatCheckbox').checked;
  const whtRate = parseInt(document.getElementById('docWhtSelect').value) || 0;

  const vat = vatChecked ? subtotal * 0.07 : 0;
  const wht = subtotal * (whtRate / 100);
  const grandTotal = subtotal + vat - wht;

  // Render previews
  document.getElementById('prevSubtotalVal').textContent = `฿${subtotal.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  
  const prevVatRow = document.getElementById('prevVatRow');
  if (prevVatRow) {
    if (vatChecked) {
      prevVatRow.style.display = '';
      document.getElementById('prevVatVal').textContent = `฿${vat.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    } else {
      prevVatRow.style.display = 'none';
    }
  }

  const prevWhtRow = document.getElementById('prevWhtRow');
  if (prevWhtRow) {
    if (whtRate > 0) {
      prevWhtRow.style.display = '';
      document.getElementById('prevWhtRateVal').textContent = whtRate;
      document.getElementById('prevWhtVal').textContent = `-฿${wht.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    } else {
      prevWhtRow.style.display = 'none';
    }
  }

  document.getElementById('prevGrandTotalVal').textContent = `฿${grandTotal.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById('prevBahtTextVal').textContent = thaiBahtText(grandTotal);

  // Update internal company details calculation
  const retentionType = document.getElementById('docRetentionType') ? document.getElementById('docRetentionType').value : 'percent';
  const retentionVal = parseFloat(document.getElementById('docRetentionRate').value) || 0;
  
  // Update label
  const lblRetentionRate = document.getElementById('lblRetentionRate');
  if (lblRetentionRate) {
    lblRetentionRate.textContent = retentionType === 'percent' ? 'หักเก็บเข้าบริษัท (%)' : 'หักเก็บเข้าบริษัท (บาท)';
  }

  let retainedAmount = 0;
  if (retentionType === 'percent') {
    retainedAmount = subtotal * (retentionVal / 100);
  } else {
    retainedAmount = retentionVal;
  }
  const payoutAmount = subtotal - retainedAmount;
  
  document.getElementById('internalRetainedAmount').textContent = `฿${retainedAmount.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById('internalPayoutAmount').textContent = `฿${payoutAmount.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  // Check HITL Limits
  if (currentDocType === 'receipt' && grandTotal > 10000) {
    showHitlWarning(grandTotal);
  } else {
    hideHitlWarning();
  }
}

// --- WHT (50 Tawi) Calculations ---
function calculateWhtTotals() {
  const gross = parseFloat(document.getElementById('whtGrossAmount').value) || 0;
  const rate = parseInt(document.getElementById('whtRateSelect').value) || 0;

  const whtAmount = gross * (rate / 100);
  const netPay = gross - whtAmount;

  document.getElementById('whtAmountResult').value = whtAmount.toFixed(2);
  document.getElementById('whtNetPayResult').value = netPay.toFixed(2);

  // Check HITL Limits
  if (gross > 10000) {
    showHitlWarning(gross);
  } else {
    hideHitlWarning();
  }
}

// --- HITL Warning UI ---
function showHitlWarning(amount) {
  const warningPanel = document.getElementById('hitlWarningPanel');
  if (!warningPanel) return;

  warningPanel.innerHTML = `
    <div class="hitl-warning-card">
      <div class="hitl-warning-title">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        แจ้งเตือนยอดเงินสูง (HITL AUDIT BY PIM)
      </div>
      <p style="font-size: 13px;">
        ยอดเงินของเอกสารนี้คือ <strong>฿${amount.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong> ซึ่งเกินข้อกำหนดความปลอดภัย 10,000 บาท
      </p>
      <label class="checkbox-label" style="margin-top: 6px;">
        <input type="checkbox" id="hitlApprovedCheckbox">
        ฉันได้ตรวจสอบและอนุมัติบันทึกบัญชีรายการนี้แล้ว (คุณเก่ง / พี่เฟิส)
      </label>
    </div>
  `;
  warningPanel.style.display = 'block';
}

function hideHitlWarning() {
  const warningPanel = document.getElementById('hitlWarningPanel');
  if (warningPanel) warningPanel.style.display = 'none';
}

function updateDueDateFromPaymentTerm() {
  const docDateEl = document.getElementById('docDate');
  const termEl = document.getElementById('docPaymentTerm');
  const dueDateEl = document.getElementById('docDueDate');

  if (!docDateEl || !termEl || !dueDateEl) return;

  const docDateVal = docDateEl.value; // Format: YYYY-MM-DD
  if (!docDateVal) return;

  const dateObj = new Date(docDateVal);
  if (isNaN(dateObj.getTime())) return;

  const termVal = termEl.value; // e.g., "30 วัน", "ชำระทันที", "7 วัน"
  let daysToAdd = 0;

  if (termVal.includes('30 วัน')) {
    daysToAdd = 30;
  } else if (termVal.includes('15 วัน')) {
    daysToAdd = 15;
  } else if (termVal.includes('7 วัน')) {
    daysToAdd = 7;
  } else if (termVal.includes('3 วัน')) {
    daysToAdd = 3;
  } else if (termVal.includes('ชำระทันที')) {
    daysToAdd = 0;
  } else {
    const numMatch = termVal.match(/\d+/);
    if (numMatch) {
      daysToAdd = parseInt(numMatch[0]);
    }
  }

  dateObj.setDate(dateObj.getDate() + daysToAdd);

  const yyyy = dateObj.getFullYear();
  const mm = String(dateObj.getMonth() + 1).padStart(2, '0');
  const dd = String(dateObj.getDate()).padStart(2, '0');
  dueDateEl.value = `${yyyy}-${mm}-${dd}`;
}

// --- Sync Previews ---
function syncDocPreview() {
  const docTitle = currentDocType === 'quotation' ? 'ใบเสนอราคา / สัญญาจ้าง' : (currentDocType === 'invoice' ? 'ใบวางบิล / ใบแจ้งหนี้' : 'ใบเสร็จรับเงิน / ใบกำกับภาษี');
  const docTitleEn = currentDocType === 'quotation' ? 'QUOTATION / CONTRACT' : (currentDocType === 'invoice' ? 'INVOICE' : 'RECEIPT / TAX INVOICE');

  document.getElementById('prevDocTitleText').textContent = docTitle;
  document.getElementById('prevDocTitleEnText').textContent = docTitleEn;

  // Hide Due Date row on Receipt and Quotation (Only show on Invoice)
  const dueDateRow = document.getElementById('prevDocDueDateRow');
  if (dueDateRow) {
    dueDateRow.style.display = currentDocType === 'invoice' ? '' : 'none';
  }

  // Hide Payment Terms block on Receipt and Quotation (Only show on Invoice)
  const prevPaymentTermTitle = document.getElementById('prevPaymentTermTitle');
  const prevPaymentTermVal = document.getElementById('prevPaymentTermVal');
  if (prevPaymentTermTitle && prevPaymentTermVal) {
    const showPaymentTerm = currentDocType === 'invoice';
    prevPaymentTermTitle.style.display = showPaymentTerm ? '' : 'none';
    prevPaymentTermVal.style.display = showPaymentTerm ? '' : 'none';
  }

  // Simple mappings
  const fields = [
    { from: 'doc_sellerName', to: 'prevSellerName' },
    { from: 'doc_sellerNameEn', to: 'prevSellerNameEn' },
    { from: 'doc_sellerTaxId', to: 'prevSellerTaxId' },
    { from: 'doc_sellerPhone', to: 'prevSellerPhone' },
    { from: 'doc_sellerEmail', to: 'prevSellerEmail' },
    { from: 'doc_bankDetails', to: 'prevBankDetailsVal' },

    { from: 'docClientName', to: 'prevClientName' },
    { from: 'docClientTaxId', to: 'prevClientTaxId' },
    { from: 'docClientPhone', to: 'prevClientPhone' },
    { from: 'docNumber', to: 'prevDocNoVal' },
    { from: 'docProjectName', to: 'prevProjectNameVal' },
    { from: 'docPaymentTerm', to: 'prevPaymentTermVal' }
  ];

  fields.forEach(f => {
    const input = document.getElementById(f.from);
    const prev = document.getElementById(f.to);
    if (input && prev) {
      let val = input.value || '-';
      if (f.from === 'docNumber') {
        val = cleanDocNo(val);
      }
      prev.textContent = val;
    }
  });

  // Seller & Client address format
  document.getElementById('prevSellerAddress').innerHTML = document.getElementById('doc_sellerAddress').value.replace(/\n/g, '<br>');
  document.getElementById('prevClientAddress').innerHTML = document.getElementById('docClientAddress').value.replace(/\n/g, '<br>');

  // Date format
  document.getElementById('prevDocDateVal').textContent = formatDate(document.getElementById('docDate').value);
  document.getElementById('prevDocDueDateVal').textContent = formatDate(document.getElementById('docDueDate').value);

  // Client Tax ID visibility
  const prevClientTaxIdRow = document.getElementById('prevClientTaxIdRow');
  const taxIdVal = document.getElementById('docClientTaxId').value;
  if (prevClientTaxIdRow) {
    if (taxIdVal) {
      prevClientTaxIdRow.style.display = 'block';
      const branchInput = document.getElementById('docClientBranch');
      const branchVal = (branchInput ? branchInput.value.trim() : '') || '00000';
      const branchText = (branchVal === '00000' || branchVal === 'สำนักงานใหญ่') ? ' (สำนักงานใหญ่)' : ` (สาขาที่ ${branchVal})`;
      document.getElementById('prevClientTaxId').textContent = taxIdVal + branchText;
    } else {
      prevClientTaxIdRow.style.display = 'none';
    }
  }

  // Signer name and label custom formatting
  const signerNameInput = document.getElementById('doc_signerName');
  const prevSignerNameVal = document.getElementById('prevSignerNameVal');
  const prevSignerLabel = document.getElementById('prevSignerLabel');
  if (prevSignerNameVal && prevSignerLabel) {
    const signerName = signerNameInput ? signerNameInput.value.trim() : '';
    // Signer name is wrapped in parentheses for all standard docs (quotation, invoice, receipt)
    prevSignerNameVal.textContent = signerName ? `( ${signerName} )` : '(           ชื่อ สกุล            )';
    
    if (currentDocType === 'receipt') {
      prevSignerLabel.innerHTML = 'ผู้รับเงิน/บัญชี<br>ในนาม บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด';
    } else {
      prevSignerLabel.innerHTML = 'ในนาม บริษัท จีเอชเอ็น 168 มีเดีย แอนด์ ครีเอชั่น จำกัด';
    }
  }

  // Toggle left signature box (use visibility to preserve right signature alignment)
  const prevLeftSignBox = document.getElementById('prevLeftSignBox');
  if (prevLeftSignBox) {
    prevLeftSignBox.style.visibility = 'visible';
    prevLeftSignBox.style.display = '';
  }

  // Toggle bank details and cheque rule
  const prevBankDetailsRow = document.getElementById('prevBankDetailsRow');
  const prevChequeRule = document.getElementById('prevChequeRule');
  if (prevBankDetailsRow) {
    // Only Invoice has bank details row. Quotation and Receipt hide it.
    prevBankDetailsRow.style.display = currentDocType === 'invoice' ? '' : 'none';
  }
  if (prevChequeRule) {
    if (currentDocType === 'receipt') {
      prevChequeRule.style.display = '';
      prevChequeRule.textContent = 'หมายเหตุ : ใบเสร็จรับเงินจะสมบูรณ์ก็ต่อเมื่อ ผู้รับเงินลงลายมือชื่อและเรียกเก็บเงินตามจำนวนเรียบร้อยแล้ว';
    } else {
      prevChequeRule.style.display = 'none';
    }
  }

  // Dynamic colspan/colspans for table footer elements to prevent column alignment bugs
  const isStandardHidden = currentDocType === 'quotation' || currentDocType === 'invoice' || currentDocType === 'receipt';
  const labelColspan = isStandardHidden ? 2 : 5;
  const totalColspan = isStandardHidden ? 3 : 6;

  ['prevSubtotalLabelCell', 'prevVatLabelCell', 'prevWhtLabelCell', 'prevNetTotalLabelCell'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.colSpan = labelColspan;
  });

  const bahtTextCell = document.getElementById('prevBahtTextCell');
  if (bahtTextCell) {
    bahtTextCell.colSpan = totalColspan;
  }

  // Sync docRemarks to prevRemarksVal and toggle visibility
  const remarksVal = document.getElementById('docRemarks') ? document.getElementById('docRemarks').value.trim() : '';
  const prevRemarksContainer = document.getElementById('prevRemarksContainer');
  const prevRemarksVal = document.getElementById('prevRemarksVal');
  if (prevRemarksContainer && prevRemarksVal) {
    if (remarksVal) {
      prevRemarksContainer.style.display = 'block';
      prevRemarksVal.textContent = remarksVal;
    } else {
      prevRemarksContainer.style.display = 'none';
      prevRemarksVal.textContent = '-';
    }
  }

  // Toggle fixed quotation payment terms container
  const prevPaymentTermsQuotationContainer = document.getElementById('prevPaymentTermsQuotationContainer');
  if (prevPaymentTermsQuotationContainer) {
    prevPaymentTermsQuotationContainer.style.display = currentDocType === 'quotation' ? 'block' : 'none';
  }

  // Render item tables
  renderPrevItemsTable();

  // Toggle company seal visibility
  const showSeal = document.getElementById('doc_showSeal').checked;
  document.querySelectorAll('.company-seal-img').forEach(img => {
    img.style.display = showSeal ? 'block' : 'none';
  });

  // Toggle signature visibility
  const showSignature = document.getElementById('doc_showSignature') ? document.getElementById('doc_showSignature').checked : false;
  const signatureSelectVal = document.getElementById('doc_signatureSelect') ? document.getElementById('doc_signatureSelect').value : 'keng';
  const prevSignatureImg = document.getElementById('prevSignatureImg');
  if (prevSignatureImg) {
    if (showSignature) {
      prevSignatureImg.style.display = 'block';
      prevSignatureImg.src = `signatures/sig_${signatureSelectVal}.png`;
    } else {
      prevSignatureImg.style.display = 'none';
    }
  }

  updatePageTitle();
}

function syncWhtPreview() {
  let docNo = document.getElementById('whtDocNumber').value || '-';
  docNo = cleanDocNo(docNo);
  const dateStr = formatDate(document.getElementById('whtDate').value);

  document.getElementById('prevWhtDocNo').textContent = docNo;
  document.getElementById('prevWhtDate').textContent = dateStr;

  // Seller config mappings
  document.getElementById('prevWhtSellerName').textContent = document.getElementById('doc_sellerName').value;
  document.getElementById('prevWhtSellerTaxId').textContent = document.getElementById('doc_sellerTaxId').value;
  document.getElementById('prevWhtSellerAddress').textContent = document.getElementById('doc_sellerAddress').value;

  // Payee config mappings
  document.getElementById('prevWhtPayeeName').textContent = document.getElementById('whtPayeeName').value || '-';
  document.getElementById('prevWhtPayeeTaxId').textContent = document.getElementById('whtPayeeTaxId').value || '-';
  document.getElementById('prevWhtPayeeAddress').textContent = document.getElementById('whtPayeeAddress').value || '-';

  // Money table
  const gross = parseFloat(document.getElementById('whtGrossAmount').value) || 0;
  const rate = parseInt(document.getElementById('whtRateSelect').value) || 0;
  const tax = gross * (rate / 100);

  document.getElementById('prevWhtDescription').textContent = document.getElementById('whtDescription').value || '-';
  document.getElementById('prevWhtRate').textContent = rate > 0 ? `${rate}%` : '-';
  document.getElementById('prevWhtGross').textContent = gross > 0 ? `฿${gross.toLocaleString('th-TH', { minimumFractionDigits: 2 })}` : '-';
  document.getElementById('prevWhtTax').textContent = tax > 0 ? `฿${tax.toLocaleString('th-TH', { minimumFractionDigits: 2 })}` : '-';

  document.getElementById('prevWhtTotalGross').textContent = gross > 0 ? `฿${gross.toLocaleString('th-TH', { minimumFractionDigits: 2 })}` : '-';
  document.getElementById('prevWhtTotalTax').textContent = tax > 0 ? `฿${tax.toLocaleString('th-TH', { minimumFractionDigits: 2 })}` : '-';
  document.getElementById('prevWhtNetText').textContent = thaiBahtText(gross - tax);

  document.getElementById('prevWhtSigner').textContent = document.getElementById('doc_signerName').value;

  // Toggle company seal visibility
  const showSeal = document.getElementById('doc_showSeal').checked;
  document.querySelectorAll('.company-seal-img').forEach(img => {
    img.style.display = showSeal ? 'block' : 'none';
  });

  updatePageTitle();
}

function formatDate(dateStr) {
  if (!dateStr) return '-';
  const parts = dateStr.split('-');
  if (parts.length === 3) {
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }
  return dateStr;
}

function cleanDocNo(val) {
  if (!val || val === '-') return val;
  const parts = val.split('-');
  if (parts.length > 1) {
    for (let i = 1; i < parts.length; i++) {
      const part = parts[i].toUpperCase();
      if (part.startsWith('QT') || part.startsWith('IV') || part.startsWith('RE') || part.startsWith('WHT') || part.startsWith('PV')) {
        return parts.slice(i).join('-');
      }
    }
  }
  return val;
}

function updateCreatorSelectFromDocNo(docNo) {
  const creatorSelect = document.getElementById('docCreatorSelect');
  if (!creatorSelect) return;
  
  if (!docNo || docNo === '-') {
    creatorSelect.value = '';
    return;
  }
  
  const parts = docNo.split('-');
  if (parts.length > 1) {
    const prefix = parts[0];
    const secondPart = parts[1].toUpperCase();
    if (secondPart.startsWith('QT') || secondPart.startsWith('IV') || secondPart.startsWith('RE') || secondPart.startsWith('WHT') || secondPart.startsWith('PV')) {
      if (prefix === 'เก่ง') creatorSelect.value = 'keng';
      else if (prefix === 'มด') creatorSelect.value = 'mod';
      else if (prefix === 'หอม') creatorSelect.value = 'hom';
      else if (prefix === 'พี่นิค') creatorSelect.value = 'nick';
      else creatorSelect.value = '';
      return;
    }
  }
  creatorSelect.value = '';
}

// --- Tax ID Validation Helper (ADVISORY) ---
function validateTaxId(id, warningElId) {
  const warning = document.getElementById(warningElId);
  if (!warning) return;
  
  if (id && !/^\d{13}$/.test(id)) {
    warning.style.display = 'block';
  } else {
    warning.style.display = 'none';
  }
}

// --- Sync to Sheets & Database Save Process ---
function processDocumentSync() {
  const scriptUrl = safeStorage.getItem('ghn168_script_url');
  const sheetId = safeStorage.getItem('ghn168_sheet_id');

  if (!scriptUrl || !sheetId) {
    alert('กรุณาตั้งค่า URL ของ Google Apps Script และ Spreadsheet ID ที่แท็บการตั้งค่าก่อนเริ่มใช้งาน');
    switchView('settings');
    return;
  }

  // Check HITL status if amount is high
  const hasHitl = document.getElementById('hitlWarningPanel').style.display === 'block';
  if (hasHitl) {
    const chk = document.getElementById('hitlApprovedCheckbox');
    if (!chk || !chk.checked) {
      alert('รายการนี้มียอดเงินเกิน 10,000 บาท น้องพิมขอแนะนำให้พี่กดยืนยันอนุมัติบัญชีในช่องสี่เหลี่ยมสีแดงก่อนกดยืนยันเซฟลงชีตค่ะ!');
      return;
    }
  }

  // Gather doc meta and construct HTTP payload
  let payload = {
    spreadsheetId: sheetId,
    type: 'sync'
  };

  const recordDate = formatDate(new Date().toISOString().split('T')[0]);
  let docRecord = null;

  if (currentDocType === 'quotation' || currentDocType === 'invoice') {
    const docNo = document.getElementById('docNumber').value;
    const dateVal = document.getElementById('docDate').value;
    const clientName = document.getElementById('docClientName').value;
    const clientTaxId = document.getElementById('docClientTaxId').value;
    const clientBranch = document.getElementById('docClientBranch').value || '00000';
    const clientAddress = document.getElementById('docClientAddress').value || '-';
    const phoneInput = document.getElementById('docClientPhone');
    const clientPhone = phoneInput ? phoneInput.value : '-';
    const detail = document.getElementById('docProjectName').value;
    
    let subtotal = 0;
    docItems.forEach(item => {
      subtotal += (item.qty || 0) * (item.price || 0);
    });
    
    const vatChecked = document.getElementById('docVatCheckbox').checked;
    const whtRate = parseInt(document.getElementById('docWhtSelect').value) || 0;
    const vat = Math.round((vatChecked ? subtotal * 0.07 : 0) * 100) / 100;
    const wht = Math.round((subtotal * (whtRate / 100)) * 100) / 100;
    const net = Math.round((subtotal + vat - wht) * 100) / 100;
    const paymentTerm = document.getElementById('docPaymentTerm').value;
    const dueDate = document.getElementById('docDueDate').value;

    const signatureSelectVal = document.getElementById('doc_signatureSelect') ? document.getElementById('doc_signatureSelect').value : 'keng';
    const signerName = document.getElementById('doc_signerName') ? document.getElementById('doc_signerName').value : '';
    const showSeal = document.getElementById('doc_showSeal') ? document.getElementById('doc_showSeal').checked : false;
    const showSignature = document.getElementById('doc_showSignature') ? document.getElementById('doc_showSignature').checked : false;

    const isDetailRequired = currentDocType !== 'quotation';
    if (!docNo || !dateVal || !clientName || (isDetailRequired && !detail) || subtotal <= 0) {
      alert('กรุณากรอกข้อมูลเอกสารและระบุรายการสินค้าให้ครบถ้วนก่อนบันทึก');
      return;
    }

    const dateStr = formatDate(dateVal);
    const dueDateStr = formatDate(dueDate);

    // ป้องกันเลขซ้ำ
    dbDocs = dbDocs.filter(d => d.number !== docNo);

    docRecord = {
      number: docNo,
      type: currentDocType,
      date: dateStr,
      name: clientName,
      detail: detail,
      amount: subtotal,
      status: 'pending', // จะเปลี่ยนเป็น synced เมื่อซิงค์สำเร็จ
      timestamp: new Date().toLocaleString(),
      clientBranch: clientBranch,
      clientAddress: clientAddress,
      clientTaxId: clientTaxId,
      clientPhone: clientPhone,
      vat: vat,
      wht: wht,
      net: net,
      whtRate: whtRate,
      paymentTerm: paymentTerm,
      dueDate: dueDateStr,
      signatureSelect: signatureSelectVal,
      signerName: signerName,
      showSeal: showSeal,
      showSignature: showSignature,
      items: docItems.map(item => ({
        desc: item.desc || "-",
        qty: item.qty || 1,
        unit: item.unit || "งาน",
        price: item.price || 0,
        worker: item.worker || "เก่ง"
      }))
    };

    if (currentDocType === 'quotation') {
      payload.sheetName = 'ใบเสนอราคา';
      payload.values = [
        recordDate,
        dateStr,
        docNo,
        clientName,
        clientTaxId || "-",
        clientAddress || "-",
        clientBranch || "00000",
        clientPhone || "-",
        detail,
        subtotal,
        vat,
        wht,
        net,
        whtRate,
        signerName,
        signatureSelectVal,
        showSeal,
        showSignature,
        JSON.stringify(docRecord.items),
        new Date().toLocaleString(),
        document.getElementById('docRemarks').value || "-"
      ];
    } else {
      payload.sheetName = 'ใบวางบิล';
      payload.values = [
        recordDate,
        dateStr,
        docNo,
        clientName,
        clientTaxId || "-",
        clientAddress || "-",
        clientBranch || "00000",
        clientPhone || "-",
        detail,
        subtotal,
        vat,
        wht,
        net,
        whtRate,
        signerName,
        signatureSelectVal,
        showSeal,
        showSignature,
        JSON.stringify(docRecord.items),
        new Date().toLocaleString(),
        paymentTerm || "-",
        dueDateStr || "-",
        document.getElementById('docRemarks').value || "-"
      ];
    }
  } else if (currentDocType === 'wht') {
    const docNo = document.getElementById('whtDocNumber').value;
    const dateVal = document.getElementById('whtDate').value;
    const payeeName = document.getElementById('whtPayeeName').value;
    const payeeTaxId = document.getElementById('whtPayeeTaxId').value;
    const payeeBranch = document.getElementById('whtPayeeBranch').value || '00000';
    const payeeAddress = document.getElementById('whtPayeeAddress').value || '-';
    const category = document.getElementById('whtCategory').value;
    const projectLink = document.getElementById('whtProjectLink').value;
    const detail = document.getElementById('whtDescription').value;
    const gross = parseFloat(document.getElementById('whtGrossAmount').value) || 0;
    const rate = parseInt(document.getElementById('whtRateSelect').value) || 0;
    const tax = Math.round((gross * (rate / 100)) * 100) / 100;
    const net = Math.round((gross - tax) * 100) / 100;
    
    const paymentMethod = document.getElementById('whtPaymentMethod').value;
    const paymentStatus = document.getElementById('whtPaymentStatus').value;
    const actualPaidDate = document.getElementById('whtActualPaidDate').value || dateVal;
    const taxFilingStatus = document.getElementById('whtTaxFilingStatus').value;
    const remarks = document.getElementById('whtRemarks').value;

    if (!docNo || !dateVal || !payeeName || !detail || gross <= 0) {
      alert('กรุณากรอกข้อมูลรายจ่ายหัก ณ ที่จ่ายให้ครบถ้วนก่อนทำการบันทึก');
      return;
    }

    const dateStr = formatDate(dateVal);
    const actualPaidDateStr = formatDate(actualPaidDate);

    // Detect form type based on payee tax id
    let formType = 'none';
    if (rate > 0) {
      const cleanId = payeeTaxId.replace(/\D/g, '');
      if (cleanId.startsWith('0')) {
        formType = 'pnd53';
      } else {
        formType = 'pnd3';
      }
    }

    payload.sheetName = 'รายจ่าย';
    payload.values = [
      recordDate,
      dateStr,
      docNo,
      payeeName,
      payeeTaxId || "-",
      payeeAddress || "-",
      payeeBranch || "00000",
      category || "-",
      detail,
      Math.round(gross * 100) / 100,
      0, // VAT for WHT
      Math.round(gross * 100) / 100,
      rate,
      Math.round(tax * 100) / 100,
      formType,
      Math.round(net * 100) / 100,
      paymentMethod || "KBank",
      paymentStatus || "จ่ายเงินแล้ว",
      actualPaidDateStr || dateStr,
      docNo,
      '-',
      taxFilingStatus || "ยังไม่ได้ยื่น",
      projectLink || "",
      remarks || ""
    ];

    docRecord = {
      number: docNo,
      type: 'wht',
      date: dateStr,
      name: payeeName,
      detail: detail,
      amount: gross,
      status: 'pending', // Will update to synced on success
      timestamp: new Date().toLocaleString(),
      payeeTaxId: payeeTaxId,
      payeeBranch: payeeBranch,
      payeeAddress: payeeAddress,
      category: category,
      vat: 0,
      wht: tax,
      net: net,
      whtRate: rate,
      receivingBank: '-',
      paymentStatus: paymentStatus,
      actualPaymentDate: '-',
      profitShare: '-',
      recordedBy: '-',
      remarks: remarks,
      paymentMethod: paymentMethod,
      actualPaidDate: actualPaidDateStr,
      whtCertificateNo: docNo,
      taxFilingStatus: taxFilingStatus,
      projectLink: projectLink,
      items: null
    };

  } else {
    // Receipt (Income)
    const docNo = document.getElementById('docNumber').value;
    const invoiceNo = document.getElementById('docInvoiceNo').value || '-';
    const dateVal = document.getElementById('docDate').value;
    const clientName = document.getElementById('docClientName').value;
    const clientTaxId = document.getElementById('docClientTaxId').value;
    const clientBranch = document.getElementById('docClientBranch').value || '00000';
    const clientAddress = document.getElementById('docClientAddress').value || '-';
    const detail = document.getElementById('docProjectName').value;

    let subtotal = 0;
    docItems.forEach(item => {
      subtotal += (item.qty || 0) * (item.price || 0);
    });

    const vatChecked = document.getElementById('docVatCheckbox').checked;
    const whtRate = parseInt(document.getElementById('docWhtSelect').value) || 0;
    const vat = Math.round((vatChecked ? subtotal * 0.07 : 0) * 100) / 100;
    const wht = Math.round((subtotal * (whtRate / 100)) * 100) / 100;
    const net = Math.round((subtotal + vat - wht) * 100) / 100;
    const owner = document.getElementById('docOwner').value;
    const retentionType = document.getElementById('docRetentionType') ? document.getElementById('docRetentionType').value : 'percent';
    const retentionVal = parseFloat(document.getElementById('docRetentionRate').value) || 0;
    
    let retentionAmount = 0;
    let profitShare = '';
    let itemProfitShareFunc;
    
    if (retentionType === 'percent') {
      retentionAmount = Math.round((subtotal * (retentionVal / 100)) * 100) / 100;
      profitShare = `คนดีล: ${owner} (${100 - retentionVal}%)`;
      itemProfitShareFunc = (itemWorker) => `คนทำงาน: ${itemWorker} (${100 - retentionVal}%)`;
    } else {
      retentionAmount = Math.round(retentionVal * 100) / 100;
      profitShare = `คนดีล: ${owner} (หัก บ. ฿${retentionVal.toLocaleString('th-TH')})`;
      itemProfitShareFunc = (itemWorker) => `คนทำงาน: ${itemWorker} (หัก บ. รวม ฿${retentionVal.toLocaleString('th-TH')})`;
    }
    const payoutAmount = Math.round((subtotal - retentionAmount) * 100) / 100;

    const receivingBank = document.getElementById('docReceivingBank').value;
    const paymentStatus = document.getElementById('docPaymentStatus').value;
    const actualPaymentDate = document.getElementById('docActualPaymentDate').value || dateVal;
    const recordedBy = document.getElementById('docRecordedBy').value;
    const remarks = document.getElementById('docRemarks').value;

    if (!docNo || !dateVal || !clientName || !detail || subtotal <= 0) {
      alert('กรุณากรอกข้อมูลรายรับให้ครบถ้วนก่อนทำการบันทึก');
      return;
    }

    const dateStr = formatDate(dateVal);
    const actualPaymentDateStr = formatDate(actualPaymentDate);

    payload.sheetName = 'รายรับ';

    const localItems = docItems.map(item => {
      const itemSubtotal = Math.round(((item.qty || 0) * (item.price || 0)) * 100) / 100;
      const itemVat = Math.round((vatChecked ? itemSubtotal * 0.07 : 0) * 100) / 100;
      const itemWht = Math.round((itemSubtotal * (whtRate / 100)) * 100) / 100;
      const itemNet = Math.round((itemSubtotal + itemVat - itemWht) * 100) / 100;

      return {
        desc: item.desc || "-",
        subtotal: itemSubtotal,
        vat: itemVat,
        gross: Math.round((itemSubtotal + itemVat) * 100) / 100,
        whtRate: whtRate,
        wht: itemWht,
        net: itemNet,
        worker: item.worker || owner,
        profitShare: itemProfitShareFunc(item.worker || owner)
      };
    });

    if (localItems.length > 0) {
      payload.rows = localItems.map(item => {
        return [
          recordDate,
          dateStr,
          docNo,
          invoiceNo || "-",
          clientName,
          clientTaxId || "-",
          clientAddress || "-",
          clientBranch || "00000",
          item.desc || detail || "-",
          item.subtotal,
          item.vat,
          item.gross,
          whtRate,
          item.wht,
          item.net,
          receivingBank || "KBank",
          paymentStatus || "ชำระเงินแล้ว",
          actualPaymentDateStr || dateStr,
          item.profitShare,
          '-',
          recordedBy || "-",
          remarks || "-"
        ];
      });
    } else {
      payload.values = [
        recordDate,
        dateStr,
        docNo,
        invoiceNo || "-",
        clientName,
        clientTaxId || "-",
        clientAddress || "-",
        clientBranch || "00000",
        detail || "-",
        Math.round(subtotal * 100) / 100,
        Math.round(vat * 100) / 100,
        Math.round((subtotal + vat) * 100) / 100,
        whtRate,
        Math.round(wht * 100) / 100,
        Math.round(net * 100) / 100,
        receivingBank || "KBank",
        paymentStatus || "ชำระเงินแล้ว",
        actualPaymentDateStr || dateStr,
        profitShare,
        '-',
        recordedBy || "-",
        remarks || "-"
      ];
    }

    docRecord = {
      number: docNo,
      type: 'receipt',
      date: dateStr,
      name: clientName,
      detail: detail,
      amount: subtotal,
      status: 'pending', // Will update to synced on success
      timestamp: new Date().toLocaleString(),
      invoiceNo: invoiceNo,
      clientBranch: clientBranch,
      clientAddress: clientAddress,
      vat: vat,
      wht: wht,
      net: net,
      whtRate: whtRate,
      receivingBank: receivingBank,
      paymentStatus: paymentStatus,
      actualPaymentDate: actualPaymentDateStr,
      profitShare: profitShare,
      recordedBy: recordedBy,
      remarks: remarks,
      items: localItems.length > 0 ? localItems : null
    };
  }

  // Send to Sheets via POST
  const syncBtn = document.getElementById('btnSaveAndSyncDoc');
  const origHtml = syncBtn.innerHTML;
  syncBtn.textContent = 'กำลังซิงค์ข้อมูลลงชีต...';
  syncBtn.disabled = true;

  fetch(scriptUrl, {
    method: 'POST',
    mode: 'cors',
    headers: {
      'Content-Type': 'text/plain'
    },
    body: JSON.stringify(payload)
  })
  .then(res => {
    if (!res.ok) {
      throw new Error(`HTTP Error Status: ${res.status}`);
    }
    return res.json();
  })
  .then(res => {
    if (res.status === 'success') {
      alert(`บันทึกและซิงค์ข้อมูลลง Google Sheets เรียบร้อยแล้ว\nข้อความระบบ: ${res.message}`);
      
      docRecord.status = 'synced';
      dbDocs.unshift(docRecord);
      syncHistory.unshift({ docNo: docRecord.number, status: 'Success', time: new Date().toLocaleString() });

      // Update referenced invoice status
      if (currentDocType === 'receipt' && docRecord.invoiceNo && docRecord.invoiceNo !== '-') {
        const matchingInv = dbDocs.find(d => d.number === docRecord.invoiceNo && d.type === 'invoice');
        if (matchingInv) {
          matchingInv.paymentStatus = 'ชำระเงินแล้ว';
        }
      }

      saveData();
      setDocType(currentDocType, true);
    } else {
      alert(`ซิงค์ข้อมูลล้มเหลว: ${res.message}`);
    }
  })
  .catch(err => {
    console.error(err);
    alert(`เกิดข้อผิดพลาดในการเชื่อมต่อระบบ Apps Script: ${err.toString()}\n\nแต่ระบบได้บันทึกข้อมูลแบบออฟไลน์ (Pending) ไว้ในเครื่องเรียบร้อยแล้ว`);
    
    // Save as pending locally
    docRecord.status = 'pending';
    dbDocs.unshift(docRecord);

    // Update referenced invoice status
    if (currentDocType === 'receipt' && docRecord.invoiceNo && docRecord.invoiceNo !== '-') {
      const matchingInv = dbDocs.find(d => d.number === docRecord.invoiceNo && d.type === 'invoice');
      if (matchingInv) {
        matchingInv.paymentStatus = 'ชำระเงินแล้ว';
      }
    }

    saveData();
    setDocType(currentDocType, true);
  })
  .finally(() => {
    syncBtn.innerHTML = origHtml;
    syncBtn.disabled = false;
  });
}

// --- Sync Pending Queue (ADVISORY) ---
function syncPendingDocs() {
  const pendingDocs = dbDocs.filter(d => d.status === 'pending');
  if (pendingDocs.length === 0) {
    alert('ไม่มีรายการค้างซิงค์สะสมในระบบ');
    return;
  }

  const scriptUrl = safeStorage.getItem('ghn168_script_url');
  const sheetId = safeStorage.getItem('ghn168_sheet_id');

  if (!scriptUrl || !sheetId) {
    alert('ไม่พบการตั้งค่า Google Sheets API สำหรับการซิงค์ข้อมูล');
    return;
  }

  if (!confirm(`ต้องการซิงค์รายการค้างส่งจำนวน ${pendingDocs.length} รายการขึ้น Sheet หรือไม่?`)) {
    return;
  }

  const syncBtn = document.getElementById('btnSyncPendingDocs');
  let origHtml = '';
  if (syncBtn) {
    origHtml = syncBtn.innerHTML;
    syncBtn.disabled = true;
    syncBtn.textContent = 'กำลังซิงค์คิว...';
  }

  let successCount = 0;
  let failCount = 0;

  function syncNext(index) {
    if (index >= pendingDocs.length) {
      alert(`ซิงค์ประวัติค้างส่งเสร็จสิ้น!\nสำเร็จ: ${successCount} รายการ\nล้มเหลว: ${failCount} รายการ`);
      saveData();
      renderDashboard();
      if (syncBtn) {
        syncBtn.disabled = false;
        syncBtn.innerHTML = origHtml;
      }
      return;
    }

    const doc = pendingDocs[index];
    let payload = {
      spreadsheetId: sheetId,
      type: 'sync'
    };

    if (doc.type === 'wht' || doc.type === 'expense') {
      payload.sheetName = 'รายจ่าย';
      
      const recordDate = doc.recordDate || formatDate(new Date().toISOString().split('T')[0]);
      const taxInvoiceDate = doc.date;
      const docNo = doc.number;
      const payeeName = doc.name;
      const payeeTaxId = doc.payeeTaxId || '-';
      const payeeBranch = doc.payeeBranch || '00000';
      const payeeAddress = doc.payeeAddress || '-';
      const category = doc.category || '-';
      const detail = doc.desc ? `${doc.category}: ${doc.desc}` : doc.category;
      
      const gross = Math.round((doc.baseAmount || doc.amount) * 100) / 100;
      const vat = Math.round((doc.vatAmount || 0) * 100) / 100;
      const totalAmount = Math.round((gross + vat) * 100) / 100;
      const whtRate = doc.whtRate !== undefined ? doc.whtRate : (doc.whtAmount > 0 ? Math.round((doc.whtAmount / gross) * 100) : 0);
      const tax = Math.round((doc.whtAmount || 0) * 100) / 100;
      const whtType = doc.whtType || 'none';
      const net = Math.round(doc.amount * 100) / 100;
      const paymentMethod = doc.paymentMethod || 'KBank';
      const paymentStatus = doc.paymentStatus || 'จ่ายเงินแล้ว';
      const actualPaidDate = doc.actualPaidDate || doc.date;
      const whtCertificateNo = doc.whtCertificateNo || ((whtRate > 0) ? doc.number : '-');
      const driveLink = doc.driveLink || '-';
      const taxFilingStatus = doc.taxFilingStatus || 'ยังไม่ได้ยื่น';
      const projectLink = doc.projectLink || '';
      const remarks = doc.remarks || '';

      payload.values = [
        recordDate, taxInvoiceDate, docNo, payeeName, payeeTaxId, payeeAddress, payeeBranch,
        category, detail, gross, vat, totalAmount, whtRate, tax, whtType, net,
        paymentMethod, paymentStatus, actualPaidDate, whtCertificateNo, driveLink,
        taxFilingStatus, projectLink, remarks
      ];
    } else if (doc.type === 'receipt') {
      payload.sheetName = 'รายรับ';
      
      const recordDate = doc.recordDate || formatDate(new Date().toISOString().split('T')[0]);
      const taxInvoiceDate = doc.date;
      const docNo = doc.number;
      const invoiceNo = doc.invoiceNo || '-';
      const clientName = doc.name;
      const clientTaxId = doc.clientTaxId || '-';
      const clientBranch = doc.clientBranch || '00000';
      const clientAddress = doc.clientAddress || '-';
      const detail = doc.detail || '-';
      const whtRate = doc.whtRate || 0;
      
      const receivingBank = doc.receivingBank || 'KBank';
      const paymentStatus = doc.paymentStatus || 'ชำระเงินแล้ว';
      const actualPaymentDate = doc.actualPaymentDate || doc.date;
      const recordedBy = doc.recordedBy || '-';
      const remarks = doc.remarks || '-';
      
      if (doc.items && doc.items.length > 0) {
        payload.rows = doc.items.map(item => {
          const itemSubtotal = Math.round(item.subtotal * 100) / 100;
          const itemVat = Math.round(item.vat * 100) / 100;
          const itemGross = Math.round(item.gross * 100) / 100;
          const itemWht = Math.round(item.wht * 100) / 100;
          const itemNet = Math.round(item.net * 100) / 100;
          
          return [
            recordDate, taxInvoiceDate, docNo, invoiceNo, clientName, clientTaxId, clientAddress, clientBranch,
            item.desc || detail || '-', itemSubtotal, itemVat, itemGross, whtRate, itemWht, itemNet,
            receivingBank, paymentStatus, actualPaymentDate, item.profitShare || doc.profitShare || '-',
            doc.driveLink || '-', recordedBy, remarks
          ];
        });
      } else {
        const subtotal = Math.round(doc.amount * 100) / 100;
        const vat = Math.round(subtotal * 0.07 * 100) / 100;
        const gross = Math.round((subtotal + vat) * 100) / 100;
        const wht = Math.round((subtotal * (whtRate / 100)) * 100) / 100;
        const net = Math.round((subtotal + vat - wht) * 100) / 100;
        const profitShare = doc.profitShare || `คนดีล: ${doc.owner || '-'} (${100 - (doc.retentionRate || 0)}%)`;
        
        payload.values = [
          recordDate, taxInvoiceDate, docNo, invoiceNo, clientName, clientTaxId, clientAddress, clientBranch,
          detail, subtotal, vat, gross, whtRate, wht, net,
          receivingBank, paymentStatus, actualPaymentDate, profitShare,
          doc.driveLink || '-', recordedBy, remarks
        ];
      }
    } else if (doc.type === 'quotation') {
      payload.sheetName = 'ใบเสนอราคา';
      const recordDate = doc.recordDate || formatDate(new Date().toISOString().split('T')[0]);
      payload.values = [
        recordDate,
        doc.date,
        doc.number,
        doc.name,
        doc.clientTaxId || "-",
        doc.clientAddress || "-",
        doc.clientBranch || "00000",
        doc.clientPhone || "-",
        doc.detail || "-",
        Math.round(doc.amount * 100) / 100,
        Math.round((doc.vat || 0) * 100) / 100,
        Math.round((doc.wht || 0) * 100) / 100,
        Math.round((doc.net || 0) * 100) / 100,
        doc.whtRate || 0,
        doc.signerName || "",
        doc.signatureSelect || "keng",
        doc.showSeal || false,
        doc.showSignature || false,
        JSON.stringify(doc.items || []),
        doc.timestamp || new Date().toLocaleString(),
        doc.remarks || "-"
      ];
    } else if (doc.type === 'invoice') {
      payload.sheetName = 'ใบวางบิล';
      const recordDate = doc.recordDate || formatDate(new Date().toISOString().split('T')[0]);
      payload.values = [
        recordDate,
        doc.date,
        doc.number,
        doc.name,
        doc.clientTaxId || "-",
        doc.clientAddress || "-",
        doc.clientBranch || "00000",
        doc.clientPhone || "-",
        doc.detail || "-",
        Math.round(doc.amount * 100) / 100,
        Math.round((doc.vat || 0) * 100) / 100,
        Math.round((doc.wht || 0) * 100) / 100,
        Math.round((doc.net || 0) * 100) / 100,
        doc.whtRate || 0,
        doc.signerName || "",
        doc.signatureSelect || "keng",
        doc.showSeal || false,
        doc.showSignature || false,
        JSON.stringify(doc.items || []),
        doc.timestamp || new Date().toLocaleString(),
        doc.paymentTerm || "-",
        doc.dueDate || "-",
        doc.remarks || "-"
      ];
    }

    fetch(scriptUrl, {
      method: 'POST',
      mode: 'cors',
      headers: { 'Content-Type': 'text/plain' },
      body: JSON.stringify(payload)
    })
    .then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    })
    .then(res => {
      if (res.status === 'success') {
        doc.status = 'synced';
        successCount++;
      } else {
        failCount++;
      }
      syncNext(index + 1);
    })
    .catch(err => {
      console.error('Error syncing pending item:', err);
      failCount++;
      syncNext(index + 1);
    });
  }

  syncNext(0);
}

// --- Backup & Restore (ADVISORY) ---
function exportBackup() {
  const backup = {
    sellerConfig: JSON.parse(safeStorage.getItem('ghn168_seller_config') || '{}'),
    dbDocs: dbDocs,
    docHubLinks: docHubLinks,
    syncHistory: syncHistory,
    scriptUrl: safeStorage.getItem('ghn168_script_url') || '',
    sheetId: safeStorage.getItem('ghn168_sheet_id') || '',
    companyDriveUrl: safeStorage.getItem('ghn168_company_drive_url') || ''
  };

  const blob = new Blob([JSON.stringify(backup, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ghn168_backup_${new Date().toISOString().slice(0,10)}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function importBackup(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(evt) {
    try {
      const data = JSON.parse(evt.target.result);
      
      if (data.dbDocs) {
        dbDocs = data.dbDocs;
        safeStorage.setItem('ghn168_db_docs', JSON.stringify(dbDocs));
      }
      if (data.docHubLinks) {
        docHubLinks = data.docHubLinks;
        safeStorage.setItem('ghn168_doc_hub', JSON.stringify(docHubLinks));
      }
      if (data.syncHistory) {
        syncHistory = data.syncHistory;
        safeStorage.setItem('ghn168_sync_history', JSON.stringify(syncHistory));
      }
      if (data.sellerConfig) {
        safeStorage.setItem('ghn168_seller_config', JSON.stringify(data.sellerConfig));
      }
      if (data.scriptUrl) {
        safeStorage.setItem('ghn168_script_url', data.scriptUrl);
      }
      if (data.sheetId) {
        safeStorage.setItem('ghn168_sheet_id', data.sheetId);
      }
      if (data.companyDriveUrl) {
        safeStorage.setItem('ghn168_company_drive_url', data.companyDriveUrl);
      }

      alert('นำเข้าข้อมูลสำรองสำเร็จแล้ว');
      loadConfiguration();
      loadData();
      renderDashboard();
    } catch (err) {
      alert('ไฟล์สำรองข้อมูลไม่ถูกต้องหรือชำรุด: ' + err.toString());
    }
  };
  reader.readAsText(file);
}

function clearLocalDatabase() {
  if (confirm("ยืนยันการล้างข้อมูลทดสอบทั้งหมดในเครื่องนี้?\n\n(ข้อมูลใบเสนอราคา, รายจ่าย, เงินสดย่อย, เงินเดือน และการกระทบยอดธนาคารจะถูกลบทั้งหมดเพื่อเริ่มต้นระบบใหม่ โดยที่ข้อมูลบริษัทและการตั้งค่าชีตจะยังคงอยู่)")) {
    safeStorage.setItem('ghn168_disable_mock', 'true');
    
    dbDocs = [];
    docHubLinks = [];
    syncHistory = [];
    pettyCashDb = [];
    payrollDb = [];
    bankRecDb = [];

    saveData();
    
    alert("ล้างข้อมูลทดสอบเรียบร้อยแล้ว ระบบพร้อมสำหรับการเก็บบันทึกข้อมูลจริง");
    
    // โหลดข้อมูลและเรนเดอร์ใหม่ทั้งหมด
    loadData();
    renderDashboard();
    
    // สั่ง rerender หน้าจออื่นๆ เพื่อความปลอดภัย
    if (typeof renderDocTable === 'function') renderDocTable();
    if (typeof renderDocHubList === 'function') renderDocHubList();
    if (typeof renderExpenseList === 'function') renderExpenseList();
    if (typeof renderPettyCash === 'function') renderPettyCash();
    if (typeof renderPayroll === 'function') renderPayroll();
    if (typeof renderBankRec === 'function') renderBankRec();
    
    // รีเฟรชหน้าเพื่อล้าง State ทุกอย่างใน DOM ให้คลีนที่สุด
    window.location.reload();
  }
}

// --- Dashboard Rendering ---
function renderDashboard() {
  // Sum cards
  let totalIncome = 0;
  let totalExpense = 0;
  let syncedCount = 0;
  let pendingCount = 0;

  // Initialize breakdown stats
  const salesStats = {
    'เก่ง': { revenue: 0, retained: 0 },
    'พี่นิค': { revenue: 0, retained: 0 },
    'หอม': { revenue: 0, retained: 0 }
  };

  dbDocs.forEach(d => {
    if (d.type === 'receipt') {
      totalIncome += d.amount;
      
      // Sum stats for individual salesperson if present and synced
      if (d.status === 'synced') {
        if (d.items && Array.isArray(d.items) && d.items.length > 0) {
          // Loop over individual items to sum up split stats
          d.items.forEach(item => {
            const worker = item.worker || d.owner;
            if (salesStats[worker]) {
              salesStats[worker].revenue += item.subtotal || 0;
              salesStats[worker].retained += item.retentionAmount || 0;
            }
          });
        } else if (d.owner && salesStats[d.owner]) {
          // Fallback for older data without itemized arrays
          salesStats[d.owner].revenue += d.amount || 0;
          salesStats[d.owner].retained += d.retentionAmount || 0;
        }
      }
    } else if (d.type === 'wht' || d.type === 'expense') {
      totalExpense += d.amount;
    }

    if (d.status === 'synced') syncedCount++;
    else if (d.status === 'pending') pendingCount++;
  });

  document.getElementById('dashTotalIncome').textContent = `฿${totalIncome.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  document.getElementById('dashTotalExpense').textContent = `฿${totalExpense.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  document.getElementById('dashNetBalance').textContent = `฿${(totalIncome - totalExpense).toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  document.getElementById('dashSyncedCount').textContent = syncedCount;
  document.getElementById('dashPendingCount').textContent = pendingCount;

  // Calculate percentages and update Dashboard Sales Summary cards
  let totalRevenueForShare = 0;
  Object.keys(salesStats).forEach(k => {
    totalRevenueForShare += salesStats[k].revenue;
  });

  Object.keys(salesStats).forEach(k => {
    const revenue = salesStats[k].revenue;
    const retained = salesStats[k].retained;
    const share = totalRevenueForShare > 0 ? (revenue / totalRevenueForShare) * 100 : 0.0;
    
    const revEl = document.getElementById(`salesRevenue_${k}`);
    const shareEl = document.getElementById(`salesShare_${k}`);
    const retEl = document.getElementById(`salesRetained_${k}`);

    if (revEl) revEl.textContent = `฿${revenue.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    if (shareEl) shareEl.textContent = `${share.toFixed(1)}%`;
    if (retEl) retEl.textContent = `฿${retained.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  });

  // Render Dynamic SVG 3D Donut Chart
  const donutChart = document.getElementById('salesDonutChart');
  const donutTotal = document.getElementById('donutTotalRevenue');
  if (donutTotal) {
    donutTotal.textContent = `฿${totalRevenueForShare.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  if (donutChart) {
    if (totalRevenueForShare === 0) {
      donutChart.style.background = '#e5e7eb';
      donutChart.style.border = '2px solid var(--border-color)';
      donutChart.innerHTML = '';
    } else {
      donutChart.style.background = 'none';
      donutChart.style.border = 'none';
      
      const pKeng = (salesStats['เก่ง'].revenue / totalRevenueForShare) * 100;
      const pNick = (salesStats['พี่นิค'].revenue / totalRevenueForShare) * 100;
      const pHom = (salesStats['หอม'].revenue / totalRevenueForShare) * 100;
      
      const slices = [
        { name: 'เก่ง', percent: pKeng, color: '#e52521' },
        { name: 'พี่นิค', percent: pNick, color: '#2563eb' },
        { name: 'หอม', percent: pHom, color: '#16a34a' }
      ].filter(s => s.percent > 0);

      // Adjust 100% case to avoid SVG arc calculation bugs (360 degrees looks like 0 degrees)
      slices.forEach(s => {
        if (s.percent >= 100) s.percent = 99.99;
      });

      let currentAngle = 0;
      let svgContent = '';

      slices.forEach(slice => {
        const sliceAngle = slice.percent * 3.6; // Convert % to degrees
        const startAngle = currentAngle;
        const endAngle = currentAngle + sliceAngle;
        currentAngle = endAngle;

        // Path coordinates (Center = 75, 75. Outer radius = 75. Inner radius = 48)
        const pathStr = getDonutSlicePath(75, 75, 48, 75, startAngle, endAngle);

        // Hover translation vector (Translate by 6px)
        const d2r = Math.PI / 180;
        const midAngleRad = ((startAngle + endAngle) / 2 - 90) * d2r;
        const tx = (6 * Math.cos(midAngleRad)).toFixed(2);
        const ty = (6 * Math.sin(midAngleRad)).toFixed(2);

        // Text coordinate (Radius = 61.5)
        const textX = (75 + 61.5 * Math.cos(midAngleRad)).toFixed(2);
        const textY = (75 + 61.5 * Math.sin(midAngleRad)).toFixed(2);

        svgContent += `
          <g class="donut-group" style="--tx: ${tx}px; --ty: ${ty}px;">
            <!-- 3D Solid Shadow Path -->
            <path d="${pathStr}" fill="var(--border-color)" transform="translate(4, 4)" class="donut-slice-shadow" />
            <!-- Main Path -->
            <path d="${pathStr}" fill="${slice.color}" class="donut-slice-main" />
            <!-- Percentage Text -->
            <text x="${textX}" y="${textY}" fill="#ffffff" font-size="10px" font-weight="bold" text-anchor="middle" dominant-baseline="central">
              ${Math.round(slice.percent)}%
            </text>
          </g>
        `;
      });

      donutChart.innerHTML = `
        <svg width="100%" height="100%" viewBox="0 0 150 150" style="overflow: visible;" xmlns="http://www.w3.org/2000/svg">
          ${svgContent}
        </svg>
      `;
    }
  }

  // Toggle sync pending button state based on pending count
  const syncBtn = document.getElementById('btnSyncPendingDocs');
  if (syncBtn) {
    if (pendingCount > 0) {
      syncBtn.style.display = 'block';
    } else {
      syncBtn.style.display = 'none';
    }
  }

  // Render recent table
  const tbody = document.getElementById('dashRecentTransactionsBody');
  if (tbody) {
    if (dbDocs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-secondary);">ยังไม่มีประวัติการบันทึกเอกสาร</td></tr>`;
    } else {
      tbody.innerHTML = dbDocs.slice(0, 8).map(d => `
        <tr>
          <td>${d.date}</td>
          <td class="mono" style="font-weight: 700;">${d.number}</td>
          <td><span class="badge" style="background-color: ${d.type === 'wht' ? '#fee2e2' : (d.type === 'expense' ? '#ffedd5' : '#dcfce7')}; color: ${d.type === 'wht' ? '#991b1b' : (d.type === 'expense' ? '#c2410c' : '#166534')}; border: 1px solid var(--border-color);">${d.type.toUpperCase()}</span></td>
          <td>
            <div>${escapeHtml(d.name)}</div>
            ${d.paymentStatus ? `<div style="font-size: 10px; color: var(--text-secondary); margin-top: 2px;">สถานะ: ${d.paymentStatus}</div>` : ''}
          </td>
          <td style="text-align:right; font-weight:700;">฿${d.amount.toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
          <td style="text-align:center;">
            <span class="badge ${d.status}">${d.status === 'synced' ? 'ซิงค์แล้ว' : (d.status === 'pending_approval' ? 'รออนุมัติ' : 'ค้างส่ง')}</span>
          </td>
        </tr>
      `).join('');
    }
  }

  // Render Expense Category Breakdown
  const expenseContainer = document.getElementById('dashExpenseCategoryContainer');
  if (expenseContainer) {
    const categories = {};
    let totalExpenseForBreakdown = 0;
    
    dbDocs.forEach(d => {
      if (d.type === 'expense' || d.type === 'wht') {
        const cat = d.category || 'อื่นๆ';
        categories[cat] = (categories[cat] || 0) + (d.amount || 0);
        totalExpenseForBreakdown += (d.amount || 0);
      }
    });

    const sortedCats = Object.entries(categories).sort((a, b) => b[1] - a[1]);

    if (sortedCats.length === 0) {
      expenseContainer.innerHTML = `<div style="text-align: center; color: var(--text-secondary); padding: 16px; font-style: italic; border: 2px dashed var(--border-color); border-radius: 8px; background: var(--input-bg);">ยังไม่มีข้อมูลรายจ่ายสะสม</div>`;
    } else {
      const palette = ['#ff4500', '#2563eb', '#16a34a', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#6366f1', '#14b8a6', '#f43f5e'];
      expenseContainer.innerHTML = sortedCats.map(([cat, amount], idx) => {
        const pct = totalExpenseForBreakdown > 0 ? (amount / totalExpenseForBreakdown) * 100 : 0;
        const color = palette[idx % palette.length];
        return `
          <div style="margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 700; margin-bottom: 4px; flex-wrap: wrap; gap: 8px;">
              <span style="color: var(--text-primary);">${escapeHtml(cat)}</span>
              <span class="mono" style="color: var(--text-primary);">฿${amount.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} (${pct.toFixed(1)}%)</span>
            </div>
            <div style="height: 12px; background: var(--input-bg); border: 2px solid var(--border-color); border-radius: 6px; overflow: hidden; position: relative;">
              <div style="height: 100%; width: ${pct}%; background: ${color}; border-radius: 4px; transition: width 0.3s ease;"></div>
            </div>
          </div>
        `;
      }).join('');
    }
  }

  // Render shortcuts
  renderDashboardDocHubShortcuts();

  // Populate tax month filter and render summaries
  populateTaxFilterMonths();
  renderTaxAndProjectSummary();
}

// --- Document Hub Synchronization ---
function fetchDocHubFromSheets(showToast = false) {
  const scriptUrl = safeStorage.getItem('ghn168_script_url');
  const sheetId = safeStorage.getItem('ghn168_sheet_id');
  if (!scriptUrl || !sheetId) {
    if (showToast) alert('กรุณาตั้งค่าการเชื่อมต่อ Google Sheets ก่อนเริ่มใช้งาน');
    return Promise.resolve();
  }

  const btn = document.getElementById('btnSyncDocHub');
  let originalHtml = '';
  if (btn && showToast) {
    originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `
      <svg class="btn-icon animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 16px; height: 16px; stroke-width: 2.5; display: inline-block; vertical-align: middle; margin-right: 6px;">
        <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M9 11l3-3 3 3m-3-3v12" />
      </svg>
      กำลังซิงค์...
    `;
  }

  const payload = {
    spreadsheetId: sheetId,
    type: 'read',
    sheetName: 'คลังเอกสาร'
  };

  return fetch(scriptUrl, {
    method: 'POST',
    mode: 'cors',
    headers: { 'Content-Type': 'text/plain' },
    body: JSON.stringify(payload)
  })
  .then(res => {
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return res.json();
  })
  .then(res => {
    if (res.status === 'success') {
      if (res.values && Array.isArray(res.values)) {
        docHubLinks = res.values.map(row => {
          let dateVal = row[3] || '';
          if (dateVal && typeof dateVal === 'string' && dateVal.includes('T') && dateVal.includes('Z')) {
            try {
              const d = new Date(dateVal);
              const day = String(d.getDate()).padStart(2, '0');
              const month = String(d.getMonth() + 1).padStart(2, '0');
              const year = d.getFullYear();
              dateVal = `${day}/${month}/${year}`;
            } catch (e) {
              console.error('Error parsing ISO date:', e);
            }
          }
          return {
            name: row[0] || '',
            category: row[1] || '',
            url: row[2] || '',
            date: dateVal,
            desc: row[4] || ''
          };
        });
        safeStorage.setItem('ghn168_doc_hub', JSON.stringify(docHubLinks));
        renderDocHubList();
        renderDashboardDocHubShortcuts();
        if (showToast) alert('ซิงค์ดึงข้อมูลคลังเอกสารจาก Google Sheets สำเร็จแล้ว');
      }
    } else {
      if (showToast) alert(`เกิดข้อผิดพลาด: ${res.message}`);
    }
  })
  .catch(err => {
    console.error('DocHub fetch error:', err);
    if (showToast) alert(`ไม่สามารถดึงข้อมูลคลังเอกสารได้: ${err.toString()}`);
  })
  .finally(() => {
    if (btn && showToast) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  });
}

function fetchDocumentsFromSheets(showToast = false) {
  const scriptUrl = safeStorage.getItem('ghn168_script_url');
  const sheetId = safeStorage.getItem('ghn168_sheet_id');
  if (!scriptUrl || !sheetId) {
    if (showToast) alert('กรุณาตั้งค่าการเชื่อมต่อ Google Sheets ก่อนเริ่มใช้งาน');
    return Promise.resolve();
  }

  const fetchTab = (sheetName) => {
    const payload = {
      spreadsheetId: sheetId,
      type: 'read',
      sheetName: sheetName
    };
    return fetch(scriptUrl, {
      method: 'POST',
      mode: 'cors',
      headers: { 'Content-Type': 'text/plain' },
      body: JSON.stringify(payload)
    })
    .then(res => {
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      return res.json();
    });
  };

  return Promise.all([
    fetchTab('ใบเสนอราคา').catch(err => { console.error('Quotation load error:', err); return null; }),
    fetchTab('ใบวางบิล').catch(err => { console.error('Invoice load error:', err); return null; })
  ])
  .then(([qtRes, ivRes]) => {
    let mergedAny = false;

    if (qtRes && qtRes.status === 'success' && Array.isArray(qtRes.values)) {
      qtRes.values.forEach(row => {
        if (row.length < 3) return;
        const docNo = row[2];
        if (!docNo) return;
        
        let items = [];
        try {
          items = JSON.parse(row[18] || '[]');
        } catch(e) {
          console.error('Error parsing items JSON for', docNo, e);
        }

        const docRecord = {
          number: docNo,
          type: 'quotation',
          date: row[1] || '',
          name: row[3] || '',
          detail: row[8] || '',
          amount: parseFloat(row[9]) || 0,
          status: 'synced',
          timestamp: row[19] || '',
          clientBranch: row[6] || '00000',
          clientAddress: row[5] || '-',
          clientTaxId: row[4] || '-',
          clientPhone: row[7] || '-',
          vat: parseFloat(row[10]) || 0,
          wht: parseFloat(row[11]) || 0,
          net: parseFloat(row[12]) || 0,
          whtRate: parseInt(row[13]) || 0,
          signerName: row[14] || '',
          signatureSelect: row[15] || 'keng',
          showSeal: String(row[16]) === 'true',
          showSignature: String(row[17]) === 'true',
          remarks: row[20] || '-',
          items: items
        };

        dbDocs = dbDocs.filter(d => d.number !== docNo);
        dbDocs.push(docRecord);
        mergedAny = true;
      });
    }

    if (ivRes && ivRes.status === 'success' && Array.isArray(ivRes.values)) {
      ivRes.values.forEach(row => {
        if (row.length < 3) return;
        const docNo = row[2];
        if (!docNo) return;
        
        let items = [];
        try {
          items = JSON.parse(row[18] || '[]');
        } catch(e) {
          console.error('Error parsing items JSON for', docNo, e);
        }

        const docRecord = {
          number: docNo,
          type: 'invoice',
          date: row[1] || '',
          name: row[3] || '',
          detail: row[8] || '',
          amount: parseFloat(row[9]) || 0,
          status: 'synced',
          timestamp: row[19] || '',
          clientBranch: row[6] || '00000',
          clientAddress: row[5] || '-',
          clientTaxId: row[4] || '-',
          clientPhone: row[7] || '-',
          vat: parseFloat(row[10]) || 0,
          wht: parseFloat(row[11]) || 0,
          net: parseFloat(row[12]) || 0,
          whtRate: parseInt(row[13]) || 0,
          signerName: row[14] || '',
          signatureSelect: row[15] || 'keng',
          showSeal: String(row[16]) === 'true',
          showSignature: String(row[17]) === 'true',
          items: items,
          paymentTerm: row[20] || '-',
          dueDate: row[21] || '',
          remarks: row[22] || '-'
        };

        dbDocs = dbDocs.filter(d => d.number !== docNo);
        dbDocs.push(docRecord);
        mergedAny = true;
      });
    }

    if (mergedAny) {
      saveData();
      renderDashboard();
      // Update autofill select immediately if doc type is loaded
      if (currentView === 'docgen') {
        const clientName = document.getElementById('docClientName') ? document.getElementById('docClientName').value.trim() : '';
        const detail = document.getElementById('docProjectName') ? document.getElementById('docProjectName').value.trim() : '';
        const subtotal = docItems.reduce((acc, item) => acc + ((item.qty || 0) * (item.price || 0)), 0);
        const isClean = (!clientName && !detail && subtotal === 0);
        setDocType(currentDocType, !isClean); // If clean, update document number (keepCurrentNumber = false)
      }
      if (showToast) alert('ซิงค์ข้อมูลใบเสนอราคาและใบวางบิลจาก Google Sheets สำเร็จแล้ว');
    }
  })
  .catch(err => {
    console.error('fetchDocumentsFromSheets error:', err);
    if (showToast) alert(`ไม่สามารถซิงค์เอกสารได้: ${err.toString()}`);
  });
}

function syncDocHubToSheets(showToast = false) {
  const scriptUrl = safeStorage.getItem('ghn168_script_url');
  const sheetId = safeStorage.getItem('ghn168_sheet_id');
  if (!scriptUrl || !sheetId) {
    if (showToast) alert('กรุณาตั้งค่าการเชื่อมต่อ Google Sheets ก่อนเริ่มใช้งาน');
    return Promise.resolve();
  }

  const payload = {
    spreadsheetId: sheetId,
    type: 'overwrite',
    sheetName: 'คลังเอกสาร',
    headers: ['ชื่อเอกสาร (Document Name)', 'หมวดหมู่ (Category)', 'ลิงก์เอกสาร Google Drive (URL)', 'วันที่อัปเดต (Date)', 'รายละเอียด (Description)'],
    rows: docHubLinks.map(doc => [
      doc.name || '',
      doc.category || '',
      doc.url || '',
      doc.date || '',
      doc.desc || ''
    ])
  };

  return fetch(scriptUrl, {
    method: 'POST',
    mode: 'cors',
    headers: { 'Content-Type': 'text/plain' },
    body: JSON.stringify(payload)
  })
  .then(res => {
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return res.json();
  })
  .then(res => {
    if (res.status === 'success') {
      if (showToast) alert('ซิงค์ส่งข้อมูลคลังเอกสารไป Google Sheets สำเร็จแล้ว');
    } else {
      if (showToast) alert(`ซิงค์อัปโหลดล้มเหลว: ${res.message}`);
    }
  })
  .catch(err => {
    console.error('DocHub push error:', err);
    if (showToast) alert(`เกิดข้อผิดพลาดขณะส่งข้อมูลไป Google Sheets: ${err.toString()}`);
  });
}

// --- Document Hub Rendering ---
function renderDocHubList() {
  const container = document.getElementById('docHubListContainer');
  if (!container) return;

  if (docHubLinks.length === 0) {
    container.innerHTML = `<p style="text-align:center; color: var(--text-secondary); font-style:italic;">ยังไม่มีเอกสารที่อัปโหลดไว้</p>`;
    renderDashboardDocHubShortcuts();
    return;
  }

  container.innerHTML = docHubLinks.map((doc, idx) => `
    <div class="doc-hub-item">
      <div class="doc-hub-meta">
        <span class="doc-hub-name">${escapeHtml(doc.name)}</span>
        <div class="doc-hub-info">
          <span class="doc-hub-tag">${escapeHtml(doc.category)}</span>
          <span>
            <svg class="btn-icon" style="width:14px; height:14px; display:inline-block; vertical-align:middle; margin-right:4px; stroke-width:2;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            วันที่อัปเดต: ${doc.date}
          </span>
          <span>
            <svg class="btn-icon" style="width:14px; height:14px; display:inline-block; vertical-align:middle; margin-right:4px; stroke-width:2;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            ${escapeHtml(doc.desc)}
          </span>
        </div>
      </div>
      <div style="display:flex; gap: 8px; align-items: center;">
        <a href="${doc.url}" target="_blank" class="btn-primary" style="padding: 6px 12px; font-size:12px; box-shadow: 2px 2px 0 var(--border-color); display: inline-flex; align-items: center; gap: 4px;">
          <svg class="btn-icon" style="width:14px; height:14px; stroke-width:2.5;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
          </svg>
          เปิด Drive
        </a>
        <button class="btn-secondary" onclick="editDocHubItem(${idx})" style="padding: 6px 12px; font-size:12px; box-shadow: 2px 2px 0 var(--border-color); color: var(--text-primary); font-weight:700;">แก้ไข</button>
        <button class="btn-danger" onclick="deleteDocHubItem(${idx})" style="padding: 6px 12px; font-size:12px; box-shadow: 2px 2px 0 var(--border-color)">ลบ</button>
      </div>
    </div>
  `).join('');

  renderDashboardDocHubShortcuts();
}

window.deleteDocHubItem = function(index) {
  if (confirm('ยืนยันที่จะลบลิงก์เอกสารสำคัญรายการนี้หรือไม่?')) {
    docHubLinks.splice(index, 1);
    saveData();
    renderDocHubList();
    syncDocHubToSheets(false);
  }
};

window.editDocHubItem = function(index) {
  const doc = docHubLinks[index];
  if (!doc) return;

  editingDocIndex = index;
  
  // Set modal title and submit text
  document.querySelector('#addDocModal .modal-title').textContent = 'แก้ไขลิงก์เอกสาร';
  document.getElementById('btnSubmitDocModal').innerHTML = `
    <svg class="btn-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
    </svg>
    บันทึกการแก้ไข
  `;

  document.getElementById('modalDocName').value = doc.name;
  
  // Select category
  const select = document.getElementById('modalDocCategory');
  const customGroup = document.getElementById('groupCustomCategory');
  const categories = ['เอกสารสำคัญ', 'เอกสารจัดตั้ง', 'เอกสารภาษี', 'ใบเสนอราคา'];
  
  if (categories.includes(doc.category)) {
    select.value = doc.category;
    customGroup.style.display = 'none';
    document.getElementById('modalDocCustomCategory').required = false;
  } else {
    select.value = 'อื่นๆ';
    customGroup.style.display = 'block';
    document.getElementById('modalDocCustomCategory').value = doc.category;
    document.getElementById('modalDocCustomCategory').required = true;
  }

  document.getElementById('modalDocUrl').value = doc.url;
  document.getElementById('modalDocDesc').value = doc.desc === '-' ? '' : doc.desc;

  document.getElementById('addDocModal').classList.add('active');
};

function renderDashboardDocHubShortcuts() {
  const container = document.getElementById('dashDocHubShortcutContainer');
  if (!container) return;

  const companyDriveUrl = safeStorage.getItem('ghn168_company_drive_url') || 'https://drive.google.com';

  let html = '';
  // Show first 3 links from the hub
  const shortcuts = docHubLinks.slice(0, 3);
  shortcuts.forEach(doc => {
    html += `
      <a href="${doc.url}" target="_blank" class="btn-secondary" style="justify-content:flex-start; text-decoration:none; font-weight:700; gap: 8px; display: inline-flex; align-items: center;">
        <svg class="btn-icon" style="width:16px; height:16px; stroke-width:2.5; flex-shrink: 0;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
        </svg>
        <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(doc.name)}</span>
        <span style="font-weight: normal; font-size: 11px; opacity: 0.7; margin-left: auto; flex-shrink: 0;">${escapeHtml(doc.category)}</span>
      </a>
    `;
  });

  // Default google drive link at the end
  html += `
    <a href="${escapeHtml(companyDriveUrl)}" target="_blank" class="btn-secondary" style="justify-content:flex-start; text-decoration:none; font-weight:700; border-style: dashed; gap: 8px; display: inline-flex; align-items: center;">
      <svg class="btn-icon" style="width:16px; height:16px; stroke-width:2.5; flex-shrink: 0;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
      </svg>
      เข้าสู่ Google Drive หลักของบริษัท
    </a>
  `;
  container.innerHTML = html;
}

// --- Helper Utilities ---
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str).replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#039;');
}

// --- Thai Baht Text Conversion ---
function thaiBahtText(amount) {
  if (isNaN(amount) || amount === null) return 'ศูนย์บาทถ้วน';
  amount = Math.round(amount * 100) / 100;
  if (amount === 0) return 'ศูนย์บาทถ้วน';
  
  const textNumbers = ['ศูนย์', 'หนึ่ง', 'สอง', 'สาม', 'สี่', 'ห้า', 'หก', 'เจ็ด', 'แปด', 'เก้า'];
  const textPositions = ['', 'สิบ', 'ร้อย', 'พัน', 'หมื่น', 'แสน', 'ล้าน'];
  
  const parts = amount.toString().split('.');
  const integerPart = parts[0];
  const decimalPart = parts[1] || '';
  
  let bahtStr = '';
  
  const len = integerPart.length;
  for (let i = 0; i < len; i++) {
    const digit = parseInt(integerPart.charAt(i));
    const pos = len - i - 1;
    if (digit !== 0) {
      if (pos % 6 === 1 && digit === 1) {
        bahtStr += '';
      } else if (pos % 6 === 1 && digit === 2) {
        bahtStr += 'ยี่';
      } else if (pos % 6 === 0 && digit === 1 && i > 0) {
        bahtStr += 'เอ็ด';
      } else {
        bahtStr += textNumbers[digit];
      }
      bahtStr += textPositions[pos % 6];
    }
    if (pos > 0 && pos % 6 === 0) {
      bahtStr += 'ล้าน';
    }
  }
  
  if (bahtStr !== '') bahtStr += 'บาท';
  
  let satangStr = '';
  if (decimalPart !== '') {
    const paddedDecimal = decimalPart.padEnd(2, '0').substring(0, 2);
    const decVal = parseInt(paddedDecimal);
    
    if (decVal > 0) {
      const d1 = parseInt(paddedDecimal.charAt(0));
      const d2 = parseInt(paddedDecimal.charAt(1));
      
      if (d1 !== 0) {
        if (d1 === 1) satangStr += 'สิบ';
        else if (d1 === 2) satangStr += 'ยี่สิบ';
        else satangStr += textNumbers[d1] + 'สิบ';
      }
      if (d2 !== 0) {
        if (d2 === 1 && d1 !== 0) satangStr += 'เอ็ด';
        else satangStr += textNumbers[d2];
      }
      satangStr += 'สตางค์';
    } else {
      bahtStr += 'ถ้วน';
    }
  } else {
    bahtStr += 'ถ้วน';
  }
  
  return bahtStr + satangStr;
}

// Expose handlers to global window scope
window.setDocType = setDocType;
window.addDocItem = addDocItem;
window.deleteDocItem = deleteDocItem;
window.updateDocItem = updateDocItem;
window.syncPendingDocs = syncPendingDocs;
window.exportBackup = exportBackup;
window.toggleTheme = toggleTheme;
window.switchView = switchView;

// --- Expense Tracker Logic ---
function renderExpenseList() {
  const container = document.getElementById('expenseListBody');
  if (!container) return;

  const expenses = dbDocs.filter(d => d.type === 'expense');

  if (expenses.length === 0) {
    container.innerHTML = `<tr><td colspan="9" style="text-align:center; color: var(--text-secondary);">ยังไม่มีประวัติการบันทึกรายจ่าย</td></tr>`;
    return;
  }

  container.innerHTML = expenses.map(doc => {
    // We need to find the actual index in the main dbDocs array for delete/edit actions
    const globalIdx = dbDocs.indexOf(doc);
    return `
      <tr>
        <td>${doc.date}</td>
        <td class="mono" style="font-weight: 700;">${escapeHtml(doc.number)}</td>
        <td><strong>${escapeHtml(doc.name)}</strong></td>
        <td><span class="badge" style="background:#e0f2fe; color:#0369a1; border: 1px solid var(--border-color); font-weight:700;">${escapeHtml(doc.category || 'รายจ่าย')}</span></td>
        <td>${escapeHtml(doc.desc || '-')}</td>
        <td style="text-align:right;" class="mono">฿${(doc.baseAmount || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
        <td style="text-align:right; font-weight:700;" class="mono">฿${(doc.amount || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
        <td style="text-align:center;">
          <span class="badge ${doc.status}">${doc.status === 'synced' ? 'ซิงค์แล้ว' : (doc.status === 'pending_approval' ? 'รออนุมัติ' : 'ค้างส่ง')}</span>
        </td>
        <td style="text-align:center;">
          <div style="display:flex; gap:6px; justify-content:center;">
            ${doc.status === 'pending_approval' ? `
              <button class="btn-primary" onclick="approveExpense(${globalIdx})" style="padding: 4px 8px; font-size:11px; box-shadow: 2px 2px 0 var(--border-color); font-weight:700; background:#f97316; border-color:#f97316; color:#fff;">อนุมัติจ่าย</button>
            ` : ''}
            <button class="btn-secondary" onclick="printPaymentVoucher(${globalIdx})" style="padding: 4px 8px; font-size:11px; box-shadow: 2px 2px 0 var(--border-color); font-weight:700;">
              <svg class="btn-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 12px; height: 12px; stroke-width: 2.5; display: inline-block; vertical-align: middle; margin-right: 4px;">
                <path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
              </svg>
              พิมพ์ PV
            </button>
            <button class="btn-secondary" onclick="editExpense(${globalIdx})" style="padding: 4px 8px; font-size:11px; box-shadow: 2px 2px 0 var(--border-color); font-weight:700; color:var(--text-primary);">แก้ไข</button>
            <button class="btn-danger" onclick="deleteExpense(${globalIdx})" style="padding: 4px 8px; font-size:11px; box-shadow: 2px 2px 0 var(--border-color);">ลบ</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function setExpenseMode(mode) {
  const form = document.getElementById('formAddExpense');
  if (!form) return;
  form.dataset.mode = mode;

  const btnSimple = document.getElementById('btnExpenseModeSimple');
  const btnDetailed = document.getElementById('btnExpenseModeDetailed');

  if (mode === 'simple') {
    if (btnSimple) {
      btnSimple.classList.add('active');
      btnSimple.style.background = 'var(--accent-color)';
      btnSimple.style.color = 'white';
    }
    if (btnDetailed) {
      btnDetailed.classList.remove('active');
      btnDetailed.style.background = 'var(--card-bg)';
      btnDetailed.style.color = 'var(--text-color)';
    }

    document.querySelectorAll('.expense-detailed-field').forEach(el => {
      el.style.display = 'none';
    });
    document.querySelectorAll('.expense-simple-field').forEach(el => {
      el.style.display = el.tagName === 'DIV' || el.classList.contains('form-group') ? 'block' : 'inline-block';
    });

    const payeeEl = document.getElementById('expensePayee');
    const descEl = document.getElementById('expenseDesc');
    if (payeeEl) payeeEl.required = false;
    if (descEl) descEl.required = false;
  } else {
    if (btnSimple) {
      btnSimple.classList.remove('active');
      btnSimple.style.background = 'var(--card-bg)';
      btnSimple.style.color = 'var(--text-color)';
    }
    if (btnDetailed) {
      btnDetailed.classList.add('active');
      btnDetailed.style.background = 'var(--accent-color)';
      btnDetailed.style.color = 'white';
    }

    document.querySelectorAll('.expense-detailed-field').forEach(el => {
      if (el.classList.contains('form-row')) {
        el.style.display = 'flex';
      } else if (el.classList.contains('form-group')) {
        el.style.display = 'block';
      } else {
        el.style.display = 'block';
      }
    });
    document.querySelectorAll('.expense-simple-field').forEach(el => {
      el.style.display = 'none';
    });

    const payeeEl = document.getElementById('expensePayee');
    const descEl = document.getElementById('expenseDesc');
    if (payeeEl) payeeEl.required = true;
    if (descEl) descEl.required = true;
  }

  calculateExpenseForm();
}

function calculateExpenseForm() {
  const baseEl = document.getElementById('expenseBaseAmount');
  if (!baseEl) return;
  const inputVal = parseFloat(baseEl.value) || 0;
  const priceType = document.getElementById('expensePriceType').value;
  const vatRate = parseFloat(document.getElementById('expenseVatSelect').value) || 0;
  const whtRate = parseFloat(document.getElementById('expenseWhtSelect').value) || 0;

  // Check current mode
  const form = document.getElementById('formAddExpense');
  const mode = form ? (form.dataset.mode || 'simple') : 'simple';

  // Change Label according to mode and priceType
  const labelAmount = document.getElementById('labelExpenseAmount');
  if (labelAmount) {
    if (mode === 'simple') {
      labelAmount.textContent = 'จำนวนเงิน / ยอดจ่าย';
    } else {
      if (priceType === 'include') {
        labelAmount.textContent = 'จำนวนเงินรวม VAT (Net/Gross)';
      } else {
        labelAmount.textContent = 'จำนวนเงินก่อน VAT (Gross)';
      }
    }
  }

  let base = 0;
  let vat = 0;

  if (priceType === 'include') {
    if (vatRate > 0) {
      base = inputVal / (1 + vatRate / 100);
      vat = inputVal - base;
    } else {
      base = inputVal;
      vat = 0;
    }
  } else {
    base = inputVal;
    vat = base * (vatRate / 100);
  }

  base = Math.round(base * 100) / 100;
  vat = Math.round(vat * 100) / 100;
  const wht = Math.round((base * (whtRate / 100)) * 100) / 100;
  const net = Math.round((base + vat - wht) * 100) / 100;

  document.getElementById('calcExpenseVat').textContent = `฿${vat.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById('calcExpenseWht').textContent = `฿${wht.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById('calcExpenseNet').textContent = `฿${net.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function saveExpense() {
  try {
    const dateVal = document.getElementById('expenseDate').value;
    if (!dateVal) {
      alert('กรุณาระบุวันที่จ่ายเงินก่อนทำการบันทึก');
      return;
    }
    // Parse date from YYYY-MM-DD to DD/MM/YYYY
    const dateParts = dateVal.split('-');
    const dateStr = dateParts.length === 3 ? `${dateParts[2]}/${dateParts[1]}/${dateParts[0]}` : '';

    const form = document.getElementById('formAddExpense');
    const expenseMode = form ? (form.dataset.mode || 'simple') : 'simple';

    let billNo = document.getElementById('expenseBillNo').value.trim();
    let payee = document.getElementById('expensePayee').value.trim();
    let payeeTaxId = document.getElementById('expensePayeeTaxId').value.trim();
    let payeeBranch = document.getElementById('expensePayeeBranch').value.trim();
    let payeeAddress = document.getElementById('expensePayeeAddress').value.trim();
    let category = document.getElementById('expenseCategory').value;
    if (category === 'อื่นๆ') {
      category = document.getElementById('expenseCustomCategory').value.trim() || 'อื่นๆ';
    }
    let desc = document.getElementById('expenseDesc').value.trim();
    const inputVal = parseFloat(document.getElementById('expenseBaseAmount').value) || 0;
    const priceType = document.getElementById('expensePriceType').value;
    const vatRate = parseFloat(document.getElementById('expenseVatSelect').value) || 0;
    const whtRate = parseFloat(document.getElementById('expenseWhtSelect').value) || 0;
    let whtType = document.getElementById('expenseWhtType').value;
    let taxFilingStatus = document.getElementById('expenseTaxFilingStatus').value;
    const paymentMethod = document.getElementById('expensePaymentMethod').value;
    let paymentStatus = document.getElementById('expensePaymentStatus').value;
    const actualPaidDateVal = document.getElementById('expenseActualPaidDate').value;
    let actualPaidDate = actualPaidDateVal ? formatDate(actualPaidDateVal) : dateStr;
    let billUrl = document.getElementById('expenseBillUrl').value.trim();
    let remarks = document.getElementById('expenseRemarks').value.trim();
    let projectLink = document.getElementById('expenseProjectLink').value;

    if (expenseMode === 'simple') {
      payee = "ทั่วไป";
      payeeTaxId = "";
      payeeBranch = "00000";
      payeeAddress = "-";
      taxFilingStatus = "ยังไม่ได้ยื่น";
      paymentStatus = "จ่ายเงินแล้ว";
      actualPaidDate = dateStr;
      billUrl = "";
      remarks = "";
      projectLink = "";
      whtType = (whtRate > 0) ? "pnd3" : "none";
      if (!desc) {
        desc = category;
      }
    } else {
      payeeBranch = payeeBranch || '00000';
      payeeAddress = payeeAddress || '-';
    }

    // Calculations based on Price Type (VAT Inclusive vs Exclusive)
    let baseAmount = 0;
    let vatAmount = 0;

    if (priceType === 'include') {
      if (vatRate > 0) {
        baseAmount = inputVal / (1 + vatRate / 100);
        vatAmount = inputVal - baseAmount;
      } else {
        baseAmount = inputVal;
        vatAmount = 0;
      }
    } else {
      baseAmount = inputVal;
      vatAmount = baseAmount * (vatRate / 100);
    }

    baseAmount = Math.round(baseAmount * 100) / 100;
    vatAmount = Math.round(vatAmount * 100) / 100;
    const whtAmount = Math.round((baseAmount * (whtRate / 100)) * 100) / 100;
    const netAmount = Math.round((baseAmount + vatAmount - whtAmount) * 100) / 100;

    // Generate PV number if empty
    if (!billNo) {
      const cleanDate = dateVal.replace(/-/g, '');
      const rand = Math.floor(100 + Math.random() * 900);
      billNo = `PV-${cleanDate}-${rand}`;
    }

    const isNew = editingDocIndex === null;

    const docRecord = {
      number: billNo,
      type: 'expense',
      date: dateStr,
      name: payee,
      category: category,
      desc: desc,
      baseAmount: baseAmount,
      vatAmount: vatAmount,
      whtAmount: whtAmount,
      amount: netAmount,
      driveLink: billUrl,
      whtType: whtType,
      projectLink: projectLink,
      priceType: priceType,
      status: 'pending',
      timestamp: new Date().toLocaleString(),
      payeeTaxId: payeeTaxId,
      payeeBranch: payeeBranch,
      payeeAddress: payeeAddress,
      taxFilingStatus: taxFilingStatus,
      paymentMethod: paymentMethod,
      paymentStatus: paymentStatus,
      actualPaidDate: actualPaidDate,
      whtCertificateNo: (whtRate > 0) ? billNo : '-',
      remarks: remarks,
      vatRate: vatRate,
      whtRate: whtRate,
      expenseMode: expenseMode
    };

    // Check if HITL approval is required (Amount > 10,000 THB)
    if (netAmount > 10000 && paymentStatus === 'รออนุมัติจ่าย') {
      alert(`รายการรายจ่ายนี้มียอดโอนจริง ฿${netAmount.toLocaleString('th-TH', { minimumFractionDigits: 2 })} เกิน 10,000 บาท\n\nระบบได้บันทึกข้อมูลไว้ในเครื่องเพื่อรอการอนุมัติ (Pending Approval) เรียบร้อยแล้ว กรุณารอผู้มีอำนาจทำการอนุมัติก่อนซิงค์ลงชีตจริง`);
      
      docRecord.status = 'pending_approval';
      docRecord.paymentStatus = 'รออนุมัติจ่าย';

      if (isNew) {
        dbDocs.unshift(docRecord);
      } else {
        dbDocs[editingDocIndex] = docRecord;
        editingDocIndex = null;
      }

      saveData();
      renderExpenseList();
      renderDashboard();
      document.getElementById('addExpenseModal').classList.remove('active');
      return;
    }

    // Construct payload
    const scriptUrl = safeStorage.getItem('ghn168_script_url');
    const sheetId = safeStorage.getItem('ghn168_sheet_id');

    const payload = {
      spreadsheetId: sheetId,
      type: 'sync',
      sheetName: 'รายจ่าย',
      values: [
        formatDate(new Date().toISOString().split('T')[0]), // A: วันที่บันทึก
        dateStr,                            // B: วันที่ตามใบเสร็จ
        billNo,                             // C: เลขที่บิล/ใบเสร็จ
        payee,                              // D: ชื่อผู้ให้บริการ
        payeeTaxId || '-',                  // E: เลขประจำตัวผู้เสียภาษี
        payeeAddress || '-',                // F: ที่อยู่
        payeeBranch || '00000',             // G: รหัสสาขา
        category,                           // H: หมวดหมู่ค่าใช้จ่าย
        desc,                               // I: รายละเอียด
        Math.round(baseAmount * 100) / 100, // J: ยอดก่อน VAT
        Math.round(vatAmount * 100) / 100,  // K: VAT 7%
        Math.round((baseAmount + vatAmount) * 100) / 100, // L: ยอดรวม VAT
        whtRate,                            // M: อัตรา WHT %
        Math.round(whtAmount * 100) / 100,  // N: ยอดหัก WHT
        whtType || 'none',                  // O: ประเภทยื่น WHT
        Math.round(netAmount * 100) / 100,  // P: ยอดจ่ายเงินสุทธิ
        paymentMethod || 'KBank',           // Q: ช่องทางจ่ายเงิน
        paymentStatus || 'จ่ายเงินแล้ว',    // R: สถานะจ่ายเงิน
        actualPaidDate,                     // S: วันที่จ่ายเงินจริง
        (whtRate > 0) ? billNo : '-',       // T: เลขใบ 50 ทวิ
        billUrl || '-',                     // U: ลิงก์ Drive
        taxFilingStatus,                    // V: สถานะยื่นภาษี
        projectLink || '',                  // W: โครงการที่ผูก
        remarks || ''                       // X: หมายเหตุ
      ]
    };

    // Send request
    if (scriptUrl && sheetId) {
      const submitBtn = document.getElementById('btnSubmitExpenseModal');
      const origHtml = submitBtn.innerHTML;
      submitBtn.textContent = 'กำลังซิงค์...';
      submitBtn.disabled = true;

      fetch(scriptUrl, {
        method: 'POST',
        mode: 'cors',
        headers: { 'Content-Type': 'text/plain' },
        body: JSON.stringify(payload)
      })
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(res => {
        if (res.status === 'success') {
          alert(`บันทึกและซิงค์รายจ่ายลง Google Sheets สำเร็จแล้ว\nข้อความ: ${res.message}`);
          
          docRecord.status = 'synced';

          if (isNew) {
            dbDocs.unshift(docRecord);
          } else {
            dbDocs[editingDocIndex] = docRecord;
            editingDocIndex = null;
          }

          saveData();
          renderExpenseList();
          document.getElementById('addExpenseModal').classList.remove('active');
        } else {
          alert(`ซิงค์ล้มเหลว: ${res.message}`);
          submitBtn.innerHTML = origHtml;
          submitBtn.disabled = false;
        }
      })
      .catch(err => {
        console.error(err);
        alert(`เกิดข้อผิดพลาดในการเชื่อมต่อสคริปต์: ${err.toString()}\n\nแต่ระบบได้บันทึกข้อมูลแบบออฟไลน์ (Pending) ไว้ในเครื่องเรียบร้อยแล้ว`);
        
        docRecord.status = 'pending';

        if (isNew) {
          dbDocs.unshift(docRecord);
        } else {
          dbDocs[editingDocIndex] = docRecord;
          editingDocIndex = null;
        }

        saveData();
        renderExpenseList();
        document.getElementById('addExpenseModal').classList.remove('active');
      });
    } else {
      // Offline Save directly
      alert('ไม่พบการเชื่อมต่อชีต ระบบได้ทำการบันทึกข้อมูลแบบออฟไลน์ไว้ในเครื่องชั่วคราว');
      docRecord.status = 'pending';

      if (isNew) {
        dbDocs.unshift(docRecord);
      } else {
        dbDocs[editingDocIndex] = docRecord;
        editingDocIndex = null;
      }

      saveData();
      renderExpenseList();
      document.getElementById('addExpenseModal').classList.remove('active');
    }
  } catch (err) {
    console.error(err);
    alert('บันทึกรายจ่ายล้มเหลวเนื่องจากข้อผิดพลาด: ' + err.toString());
  }
}

function deleteExpense(index) {
  if (confirm('ต้องการลบประวัติรายจ่ายรายการนี้ใช่หรือไม่? (ลบเฉพาะในตัวแอปเท่านั้น)')) {
    dbDocs.splice(index, 1);
    saveData();
    renderExpenseList();
  }
}

function editExpense(index) {
  const doc = dbDocs[index];
  editingDocIndex = index;

  populateProjectList(); // Populate project list dynamically

  document.querySelector('#addExpenseModal .modal-title').textContent = 'แก้ไขข้อมูลรายจ่าย';
  document.getElementById('btnSubmitExpenseModal').innerHTML = `
    <svg class="btn-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
    </svg>
    บันทึกการแก้ไข
  `;

  // Convert Date from DD/MM/YYYY to YYYY-MM-DD
  const dateParts = doc.date.split('/');
  if (dateParts.length === 3) {
    document.getElementById('expenseDate').value = `${dateParts[2]}-${dateParts[1]}-${dateParts[0]}`;
  }

  // Load mode & set layout
  let mode = doc.expenseMode;
  if (!mode) {
    mode = (doc.name === 'ทั่วไป' || !doc.name) ? 'simple' : 'detailed';
  }
  setExpenseMode(mode);

  document.getElementById('expenseBillNo').value = doc.number.startsWith('PV-') && doc.number.split('-').length === 3 ? '' : doc.number;
  document.getElementById('expensePayee').value = doc.name;
  document.getElementById('expensePayeeTaxId').value = doc.payeeTaxId || '';
  document.getElementById('expensePayeeBranch').value = doc.payeeBranch || '00000';
  document.getElementById('expensePayeeAddress').value = doc.payeeAddress || '';
  
  const select = document.getElementById('expenseCategory');
  const customGroup = document.getElementById('groupCustomExpenseCategory');

  // Check if option exists in select, else use Custom
  let optionExists = false;
  for (let i = 0; i < select.options.length; i++) {
    if (select.options[i].value === doc.category) {
      optionExists = true;
      break;
    }
  }

  if (optionExists) {
    select.value = doc.category;
    customGroup.style.display = 'none';
  } else {
    select.value = 'อื่นๆ';
    customGroup.style.display = 'block';
    document.getElementById('expenseCustomCategory').value = doc.category;
  }

  document.getElementById('expenseDesc').value = doc.desc || '';
  
  // Set price type dropdown and calculate correct value to populate
  const priceType = doc.priceType || 'exclude';
  document.getElementById('expensePriceType').value = priceType;
  document.getElementById('expenseBaseAmount').value = priceType === 'include' ? (doc.baseAmount + (doc.vatAmount || 0)) : (doc.baseAmount || doc.amount);
  
  // Deduce VAT and WHT rates
  const vatRate = doc.vatAmount > 0 ? 7 : 0;
  const whtRate = doc.whtAmount > 0 ? Math.round((doc.whtAmount / doc.baseAmount) * 100) : 0;

  // Sync simple VAT dropdown
  let vatSystemSimpleVal = '0';
  if (vatRate === 7) {
    if (priceType === 'exclude') {
      vatSystemSimpleVal = '7_exclude';
    } else if (priceType === 'include') {
      vatSystemSimpleVal = '7_include';
    }
  }
  const vatSimpleEl = document.getElementById('expenseVatSystemSimple');
  if (vatSimpleEl) {
    vatSimpleEl.value = vatSystemSimpleVal;
  }

  document.getElementById('expenseVatSelect').value = vatRate.toString();
  document.getElementById('expenseWhtSelect').value = whtRate.toString();
  document.getElementById('expenseWhtType').value = doc.whtType || 'none';
  document.getElementById('expenseTaxFilingStatus').value = doc.taxFilingStatus || 'ยังไม่ได้ยื่น';
  document.getElementById('expensePaymentMethod').value = doc.paymentMethod || 'KBank';
  document.getElementById('expensePaymentStatus').value = doc.paymentStatus || 'จ่ายเงินแล้ว';
  
  if (doc.actualPaidDate && doc.actualPaidDate !== '-') {
    const paidParts = doc.actualPaidDate.split('/');
    if (paidParts.length === 3) {
      document.getElementById('expenseActualPaidDate').value = `${paidParts[2]}-${paidParts[1]}-${paidParts[0]}`;
    } else {
      document.getElementById('expenseActualPaidDate').value = '';
    }
  } else {
    document.getElementById('expenseActualPaidDate').value = '';
  }

  document.getElementById('expenseProjectLink').value = doc.projectLink || '';
  document.getElementById('expenseBillUrl').value = doc.driveLink || '';
  document.getElementById('expenseRemarks').value = doc.remarks || '';

  calculateExpenseForm();
  document.getElementById('addExpenseModal').classList.add('active');
}

function printPaymentVoucher(index) {
  const doc = dbDocs[index];
  
  document.getElementById('pvPrintNo').textContent = cleanDocNo(doc.number);
  document.getElementById('pvPrintDate').textContent = doc.date;
  document.getElementById('pvPrintPayee').textContent = doc.name;
  document.getElementById('pvPrintPayeeTaxId').textContent = doc.payeeTaxId || '-';
  
  document.getElementById('pvPrintDesc').textContent = `${doc.category || 'รายจ่าย'}: ${doc.desc || ''}`;
  document.getElementById('pvPrintNote').textContent = `บันทึกรายการจ่าย: ${doc.timestamp || ''}`;
  
  const base = doc.baseAmount || doc.amount;
  const vat = doc.vatAmount || 0;
  const wht = doc.whtAmount || 0;
  const net = doc.amount;

  document.getElementById('pvPrintBaseAmount').textContent = `฿${base.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  document.getElementById('pvPrintVat').textContent = `฿${vat.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  document.getElementById('pvPrintWht').textContent = `฿${wht.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  document.getElementById('pvPrintNet').textContent = `฿${net.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  document.getElementById('pvPrintNetText').textContent = thaiBahtText(net);

  // Set printing class
  document.body.classList.add('printing-pv');
  window.print();
  
  // Remove class after printing starts/completes
  setTimeout(() => {
    document.body.classList.remove('printing-pv');
  }, 1000);
}

function exportPdfClientSide() {
  const isWht = currentView === 'docgen' && currentDocType === 'wht';
  const element = isWht ? document.getElementById('previewWhtDoc') : document.getElementById('previewStandardDoc');
  
  if (!element) return;
  
  const originalZoom = element.style.zoom;
  const originalBoxShadow = element.style.boxShadow;
  const originalHeight = element.style.height;
  const originalMinHeight = element.style.minHeight;
  const originalMaxHeight = element.style.maxHeight;
  const originalOverflow = element.style.overflow;
  
  element.style.zoom = '1';
  element.style.boxShadow = 'none';
  element.style.minHeight = 'auto';
  element.style.maxHeight = 'none';
  element.style.height = 'auto';
  element.style.overflow = 'visible';
  
  const scrollHeight = element.scrollHeight;
  const N = Math.max(1, Math.ceil(scrollHeight / 1122.5));
  const clampedHeight = `${N * 295}mm`;
  
  element.style.minHeight = clampedHeight;
  element.style.maxHeight = clampedHeight;
  element.style.height = clampedHeight;
  element.style.overflow = 'hidden';
  
  const opt = {
    margin: 0,
    filename: document.title + '.pdf',
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { 
      scale: 3, 
      useCORS: true, 
      logging: false,
      letterRendering: true
    },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
  };
  
  const btn = document.getElementById('btnExportDocPdf');
  const originalBtnText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = 'กำลังสร้างไฟล์ PDF...';
  
  html2pdf().set(opt).from(element).save().then(() => {
    btn.disabled = false;
    btn.innerHTML = originalBtnText;
    element.style.zoom = originalZoom;
    element.style.boxShadow = originalBoxShadow;
    element.style.height = originalHeight;
    element.style.minHeight = originalMinHeight;
    element.style.maxHeight = originalMaxHeight;
    element.style.overflow = originalOverflow;
  }).catch(err => {
    console.error('PDF export failed:', err);
    alert('เกิดข้อผิดพลาดในการสร้างไฟล์ PDF');
    btn.disabled = false;
    btn.innerHTML = originalBtnText;
    element.style.zoom = originalZoom;
    element.style.boxShadow = originalBoxShadow;
    element.style.height = originalHeight;
    element.style.minHeight = originalMinHeight;
    element.style.maxHeight = originalMaxHeight;
    element.style.overflow = originalOverflow;
  });
}

// Expose handlers to global window scope
window.setDocType = setDocType;
window.addDocItem = addDocItem;
window.deleteDocItem = deleteDocItem;
window.updateDocItem = updateDocItem;
window.syncPendingDocs = syncPendingDocs;
window.exportBackup = exportBackup;
window.toggleTheme = toggleTheme;
window.switchView = switchView;
window.printPaymentVoucher = printPaymentVoucher;
window.exportPdfClientSide = exportPdfClientSide;
window.editExpense = editExpense;
window.deleteExpense = deleteExpense;
window.setExpenseMode = setExpenseMode;

function getDonutSlicePath(x, y, r, R, startAngle, endAngle) {
  const d2r = Math.PI / 180;
  const a1 = (startAngle - 90) * d2r;
  const a2 = (endAngle - 90) * d2r;
  
  const x1_out = x + R * Math.cos(a1);
  const y1_out = y + R * Math.sin(a1);
  const x2_out = x + R * Math.cos(a2);
  const y2_out = y + R * Math.sin(a2);
  
  const x1_in = x + r * Math.cos(a1);
  const y1_in = y + r * Math.sin(a1);
  const x2_in = x + r * Math.cos(a2);
  const y2_in = y + r * Math.sin(a2);
  
  const largeArc = (endAngle - startAngle) > 180 ? 1 : 0;
  
  return `M ${x1_out.toFixed(2)} ${y1_out.toFixed(2)} A ${R} ${R} 0 ${largeArc} 1 ${x2_out.toFixed(2)} ${y2_out.toFixed(2)} L ${x2_in.toFixed(2)} ${y2_in.toFixed(2)} A ${r} ${r} 0 ${largeArc} 0 ${x1_in.toFixed(2)} ${y1_in.toFixed(2)} Z`;
}

// --- Corporate Accounting Upgrades ---
const THAI_MONTHS = [
  'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน',
  'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'
];

function populateProjectList() {
  const select = document.getElementById('expenseProjectLink');
  if (!select) return;
  select.innerHTML = '<option value="">-- ไม่ผูกโครงการ (ทั่วไป) --</option>';
  const projects = new Set();
  dbDocs.forEach(d => {
    if ((d.type === 'receipt' || d.type === 'invoice' || d.type === 'quotation') && d.detail) {
      projects.add(d.detail.trim());
    }
  });
  Array.from(projects).sort().forEach(proj => {
    const opt = document.createElement('option');
    opt.value = proj;
    opt.textContent = proj;
    select.appendChild(opt);
  });
}

function populateTaxFilterMonths() {
  const select = document.getElementById('taxFilterMonth');
  if (!select) return;
  
  const selected = select.value;
  select.innerHTML = '';
  
  const months = new Set();
  dbDocs.forEach(d => {
    if (d.date) {
      const parts = d.date.split('/');
      if (parts.length === 3) {
        months.add(`${parts[1]}/${parts[2]}`);
      }
    }
  });
  
  const sortedMonths = Array.from(months).sort((a, b) => {
    const [ma, ya] = a.split('/').map(Number);
    const [mb, yb] = b.split('/').map(Number);
    if (ya !== yb) return yb - ya;
    return mb - ma;
  });
  
  if (sortedMonths.length === 0) {
    const now = new Date();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    const y = now.getFullYear();
    sortedMonths.push(`${m}/${y}`);
  }
  
  sortedMonths.forEach(mStr => {
    const [m, y] = mStr.split('/');
    const thaiMonth = THAI_MONTHS[parseInt(m) - 1];
    const thaiYear = parseInt(y) + 543;
    
    const opt = document.createElement('option');
    opt.value = mStr;
    opt.textContent = `${thaiMonth} ${thaiYear}`;
    select.appendChild(opt);
  });
  
  if (selected && sortedMonths.includes(selected)) {
    select.value = selected;
  } else {
    select.value = sortedMonths[0];
  }
}

function renderTaxAndProjectSummary() {
  const filterSelect = document.getElementById('taxFilterMonth');
  if (!filterSelect) return;
  const filterVal = filterSelect.value;
  if (!filterVal) return;
  const [targetMonth, targetYear] = filterVal.split('/');

  let outputVat = 0;
  let inputVat = 0;
  let pnd3 = 0;
  let pnd53 = 0;
  let withheldTax = 0;
  
  let monthIncome = 0;
  let monthExpense = 0;

  const projectStats = {};

  dbDocs.forEach(d => {
    if (!d.date) return;
    const parts = d.date.split('/');
    if (parts.length !== 3) return;
    const m = parts[1];
    const y = parts[2];

    if (m === targetMonth && y === targetYear) {
      if (d.type === 'receipt') {
        monthIncome += d.amount || 0;
        if (d.vat) outputVat += parseFloat(d.vat) || 0;
        if (d.wht) withheldTax += parseFloat(d.wht) || 0;

        if (d.detail) {
          const proj = d.detail.trim();
          if (!projectStats[proj]) {
            projectStats[proj] = { revenue: 0, cost: 0 };
          }
          projectStats[proj].revenue += d.amount || 0;
        }
      } else if (d.type === 'expense' && d.status !== 'pending_approval') {
        monthExpense += d.baseAmount || d.amount || 0;
        if (d.vatAmount) inputVat += parseFloat(d.vatAmount) || 0;
        
        if (d.whtType === 'pnd3') {
          pnd3 += parseFloat(d.whtAmount) || 0;
        } else if (d.whtType === 'pnd53') {
          pnd53 += parseFloat(d.whtAmount) || 0;
        }

        if (d.projectLink) {
          const proj = d.projectLink.trim();
          if (!projectStats[proj]) {
            projectStats[proj] = { revenue: 0, cost: 0 };
          }
          projectStats[proj].cost += d.baseAmount || d.amount || 0;
        }
      } else if (d.type === 'wht') {
        monthExpense += d.amount || 0;
        if (d.wht) pnd3 += parseFloat(d.wht) || 0;
      }
    }
  });

  const netVat = outputVat - inputVat;
  const monthBalance = monthIncome - monthExpense;

  document.getElementById('summaryOutputVat').textContent = `฿${outputVat.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  document.getElementById('summaryInputVat').textContent = `฿${inputVat.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  
  const netVatEl = document.getElementById('summaryNetVat');
  if (netVat > 0) {
    netVatEl.textContent = `฿${netVat.toLocaleString('th-TH', { minimumFractionDigits: 2 })} (ต้องชำระ)`;
    netVatEl.style.color = 'var(--accent-color)';
  } else if (netVat < 0) {
    netVatEl.textContent = `฿${Math.abs(netVat).toLocaleString('th-TH', { minimumFractionDigits: 2 })} (เครดิตคืน)`;
    netVatEl.style.color = '#16a34a';
  } else {
    netVatEl.textContent = `฿0.00`;
    netVatEl.style.color = 'var(--text-primary)';
  }

  document.getElementById('summaryPnd3').textContent = `฿${pnd3.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  document.getElementById('summaryPnd53').textContent = `฿${pnd53.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  document.getElementById('summaryWithheldTax').textContent = `฿${withheldTax.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;

  document.getElementById('summaryMonthIncome').textContent = `฿${monthIncome.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  document.getElementById('summaryMonthExpense').textContent = `฿${monthExpense.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  
  const balanceEl = document.getElementById('summaryMonthBalance');
  balanceEl.textContent = `฿${monthBalance.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  balanceEl.style.color = monthBalance >= 0 ? '#16a34a' : 'var(--accent-color)';

  const tbody = document.getElementById('summaryProjectProfitabilityBody');
  if (tbody) {
    const projArray = Object.keys(projectStats);
    if (projArray.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: var(--text-secondary);">ไม่มีโครงการที่มีธุรกรรมในเดือนนี้</td></tr>`;
    } else {
      tbody.innerHTML = projArray.map(proj => {
        const stats = projectStats[proj];
        const margin = stats.revenue - stats.cost;
        const marginPercent = stats.revenue > 0 ? (margin / stats.revenue) * 100 : 0;
        
        return `
          <tr>
            <td><strong>${escapeHtml(proj)}</strong></td>
            <td style="text-align:right;" class="mono">฿${stats.revenue.toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
            <td style="text-align:right;" class="mono">฿${stats.cost.toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
            <td style="text-align:right; font-weight:700; color: ${margin >= 0 ? '#16a34a' : 'var(--accent-color)'};" class="mono">
              ฿${margin.toLocaleString('th-TH', { minimumFractionDigits: 2 })}
            </td>
            <td style="text-align:center; font-weight:700; color: ${marginPercent >= 50 ? '#16a34a' : (marginPercent >= 20 ? 'var(--text-primary)' : 'var(--accent-color)')};" class="mono">
              ${marginPercent.toFixed(2)}%
            </td>
          </tr>
        `;
      }).join('');
    }
  }
}

function approveExpense(index) {
  const doc = dbDocs[index];
  if (!doc || doc.status !== 'pending_approval') return;

  if (!confirm(`ต้องการอนุมัติรายการจ่ายเงินจำนวน ฿${doc.amount.toLocaleString('th-TH', { minimumFractionDigits: 2 })} สำหรับ "${doc.name}" ใช่หรือไม่?`)) {
    return;
  }

  const scriptUrl = safeStorage.getItem('ghn168_script_url');
  const sheetId = safeStorage.getItem('ghn168_sheet_id');

  if (scriptUrl && sheetId) {
    doc.status = 'pending';
    renderExpenseList();

    const whtRate = doc.whtRate !== undefined ? doc.whtRate : (doc.whtAmount > 0 ? Math.round((doc.whtAmount / doc.baseAmount) * 100) : 0);
    const vatRate = doc.vatRate !== undefined ? doc.vatRate : (doc.vatAmount > 0 ? 7 : 0);

    const payload = {
      spreadsheetId: sheetId,
      type: 'sync',
      sheetName: 'รายจ่าย',
      values: [
        doc.recordDate || formatDate(new Date().toISOString().split('T')[0]), // A: วันที่บันทึก
        doc.date, // B: วันที่ตามใบเสร็จ
        doc.number, // C: เลขที่บิล/ใบเสร็จ
        doc.name, // D: ชื่อผู้ให้บริการ
        doc.payeeTaxId || '-', // E: เลขประจำตัวผู้เสียภาษี
        doc.payeeAddress || '-', // F: ที่อยู่
        doc.payeeBranch || '00000', // G: รหัสสาขา
        doc.category || '-', // H: หมวดหมู่ค่าใช้จ่าย
        doc.desc ? `${doc.category}: ${doc.desc}` : doc.category, // I: รายละเอียด
        Math.round((doc.baseAmount || doc.amount) * 100) / 100, // J: ยอดก่อน VAT
        Math.round((doc.vatAmount || 0) * 100) / 100, // K: VAT 7%
        Math.round(((doc.baseAmount || doc.amount) + (doc.vatAmount || 0)) * 100) / 100, // L: ยอดรวม VAT
        whtRate, // M: อัตรา WHT %
        Math.round((doc.whtAmount || 0) * 100) / 100, // N: ยอดหัก WHT
        doc.whtType || 'none', // O: ประเภทยื่น WHT
        Math.round(doc.amount * 100) / 100, // P: ยอดจ่ายเงินสุทธิ
        doc.paymentMethod || 'KBank', // Q: ช่องทางจ่ายเงิน
        'จ่ายเงินแล้ว', // R: สถานะจ่ายเงิน
        doc.actualPaidDate || doc.date, // S: วันที่จ่ายเงินจริง
        doc.whtCertificateNo || ((whtRate > 0) ? doc.number : '-'), // T: เลขใบ 50 ทวิ
        doc.driveLink || '-', // U: ลิงก์ Drive
        doc.taxFilingStatus || 'ยังไม่ได้ยื่น', // V: สถานะยื่นภาษี
        doc.projectLink || '', // W: โครงการที่ผูก
        doc.remarks || '' // X: หมายเหตุ
      ]
    };

    fetch(scriptUrl, {
      method: 'POST',
      mode: 'cors',
      headers: { 'Content-Type': 'text/plain' },
      body: JSON.stringify(payload)
    })
    .then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    })
    .then(res => {
      if (res.status === 'success') {
        alert('อนุมัติจ่ายและซิงค์ข้อมูลลง Google Sheets เรียบร้อยแล้ว');
        doc.status = 'synced';
      } else {
        alert(`ซิงค์ข้อมูลล้มเหลว: ${res.message}\nรายการบันทึกสถานะเป็นค้างส่ง (Pending)`);
        doc.status = 'pending';
      }
      saveData();
      renderExpenseList();
      renderDashboard();
    })
    .catch(err => {
      console.error(err);
      alert(`อนุมัติแล้วแต่เชื่อมต่อสคริปต์ล้มเหลว: ${err.toString()}\nเปลี่ยนสถานะเป็นค้างส่ง (Pending) ไว้ในเครื่องเพื่อซิงค์ภายหลัง`);
      doc.status = 'pending';
      saveData();
      renderExpenseList();
      renderDashboard();
    });
  } else {
    alert('ไม่พบค่าสคริปต์เชื่อมต่อ เปลี่ยนสถานะเป็นค้างส่ง (Pending) ไว้ในเครื่องแล้ว');
    doc.status = 'pending';
    saveData();
    renderExpenseList();
    renderDashboard();
  }
}

// Expose handlers to global window scope
window.approveExpense = approveExpense;
window.renderTaxAndProjectSummary = renderTaxAndProjectSummary;
window.populateProjectList = populateProjectList;
window.toggleTheme = toggleTheme;
window.syncPendingDocs = syncPendingDocs;
window.switchView = switchView;
window.printPaymentVoucher = printPaymentVoucher;
window.editExpense = editExpense;
window.deleteExpense = deleteExpense;

// --- Petty Cash Logic ---
function autoGeneratePettyCashVoucherNo() {
  const now = new Date();
  const yy = now.getFullYear().toString().substring(2);
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  const matchPattern = `PCV-${yy}${mm}${dd}`;
  const dayItems = pettyCashDb.filter(d => d.voucherNo.startsWith(matchPattern));
  const num = String(dayItems.length + 1).padStart(3, '0');
  return `${matchPattern}-${num}`;
}

function renderPettyCash() {
  const body = document.getElementById('pettyCashListBody');
  if (!body) return;

  let currentBalance = 10000.00;
  for (let i = pettyCashDb.length - 1; i >= 0; i--) {
    currentBalance -= pettyCashDb[i].amountPaid;
    pettyCashDb[i].balance = currentBalance;
  }

  document.getElementById('pettyCashSafeBalance').textContent = `฿${currentBalance.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  document.getElementById('pettyCashTotalPaid').textContent = `฿${(10000.00 - currentBalance).toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;

  if (pettyCashDb.length === 0) {
    body.innerHTML = `<tr><td colspan="9" style="text-align:center; color: var(--text-secondary); padding:20px;">ไม่มีข้อมูลเงินสดย่อย</td></tr>`;
    return;
  }

  body.innerHTML = pettyCashDb.map((doc, idx) => `
    <tr>
      <td class="mono">${escapeHtml(doc.voucherNo)}</td>
      <td style="text-align:center;">${escapeHtml(doc.date)}</td>
      <td>${escapeHtml(doc.requester)}</td>
      <td><span class="badge" style="background:#fef08a; color:#854d0e; border: 1px solid var(--border-color); font-weight:700;">${escapeHtml(doc.category)}</span></td>
      <td>${escapeHtml(doc.detail)}</td>
      <td style="text-align:right;" class="mono">฿${(doc.amountPaid || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
      <td style="text-align:right;" class="mono">฿${(doc.balance || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
      <td style="text-align:center;">${escapeHtml(doc.approver)}</td>
      <td style="text-align:center;">
        <div style="display:flex; gap:6px; justify-content:center;">
          ${doc.status === 'pending' ? `
            <button class="btn-primary" onclick="syncPettyCash(${idx})" style="padding: 4px 8px; font-size:11px; box-shadow: 2px 2px 0 var(--border-color); background:#f59e0b; border-color:#f59e0b; color:#fff;">ซิงค์</button>
          ` : '<span class="badge synced" style="padding: 4px 8px; font-size:11px;">ซิงค์แล้ว</span>'}
          <button class="btn-secondary" onclick="editPettyCash(${idx})" style="padding: 4px 8px; font-size:11px; box-shadow: 2px 2px 0 var(--border-color); font-weight:700;">แก้ไข</button>
          <button class="btn-danger" onclick="deletePettyCash(${idx})" style="padding: 4px 8px; font-size:11px; box-shadow: 2px 2px 0 var(--border-color);">ลบ</button>
        </div>
      </td>
    </tr>
  `).join('');
}

function savePettyCash() {
  try {
    const voucherNo = document.getElementById('pettyCashVoucherNo').value;
    const dateVal = document.getElementById('pettyCashDate').value;
    if (!dateVal) {
      alert('กรุณาระบุวันที่ก่อนทำการบันทึก');
      return;
    }
    const dateParts = dateVal.split('-');
    const dateStr = `${dateParts[2]}/${dateParts[1]}/${dateParts[0]}`;
    const requester = document.getElementById('pettyCashRequester').value.trim();
    const category = document.getElementById('pettyCashCategory').value;
    const detail = document.getElementById('pettyCashDetail').value.trim();
    const amountPaid = parseFloat(document.getElementById('pettyCashAmountPaid').value) || 0;
    const approver = document.getElementById('pettyCashApprover').value.trim();
    const receiptUrl = document.getElementById('pettyCashReceiptUrl').value.trim();
    const remarks = document.getElementById('pettyCashRemarks').value.trim();

    if (amountPaid <= 0) {
      alert('ยอดจ่ายต้องมากกว่า 0 บาท');
      return;
    }

    const isNew = editingDocIndex === null;
    const docRecord = {
      voucherNo, date: dateStr, requester, category, detail, amountPaid, balance: 0, approver,
      receiptUrl: receiptUrl || '-', remarks: remarks || '-',
      status: isNew ? 'pending' : (pettyCashDb[editingDocIndex].status || 'pending')
    };

    if (isNew) {
      pettyCashDb.unshift(docRecord);
    } else {
      pettyCashDb[editingDocIndex] = docRecord;
      editingDocIndex = null;
    }

    saveData();
    renderPettyCash();
    document.getElementById('addPettyCashModal').classList.remove('active');

    const scriptUrl = safeStorage.getItem('ghn168_script_url');
    const sheetId = safeStorage.getItem('ghn168_sheet_id');
    if (scriptUrl && sheetId && isNew) {
      syncPettyCash(0);
    }
  } catch (err) {
    console.error(err);
    alert('บันทึกเงินสดย่อยล้มเหลว: ' + err.toString());
  }
}

function syncPettyCash(index) {
  const doc = pettyCashDb[index];
  if (!doc) return;
  const scriptUrl = safeStorage.getItem('ghn168_script_url');
  const sheetId = safeStorage.getItem('ghn168_sheet_id');
  if (!scriptUrl || !sheetId) {
    alert('กรุณาตั้งค่าการเชื่อมต่อ Google Sheets ก่อนเริ่มใช้งาน');
    return;
  }
  const payload = {
    spreadsheetId: sheetId,
    type: 'sync',
    sheetName: 'เงินสดย่อย',
    values: [
      doc.voucherNo,
      doc.date,
      doc.requester,
      doc.category || "-",
      doc.detail,
      Math.round(parseFloat(doc.amountPaid || 0) * 100) / 100,
      Math.round(parseFloat(doc.balance || 0) * 100) / 100,
      doc.approver || "-",
      doc.receiptUrl || "-",
      doc.remarks || ""
    ]
  };
  fetch(scriptUrl, {
    method: 'POST', mode: 'cors', headers: { 'Content-Type': 'text/plain' }, body: JSON.stringify(payload)
  })
  .then(res => res.json())
  .then(res => {
    if (res.status === 'success') {
      alert('ซิงค์ข้อมูลเงินสดย่อยสำเร็จแล้ว');
      doc.status = 'synced';
      saveData();
      renderPettyCash();
    } else {
      alert(`ซิงค์ล้มเหลว: ${res.message}`);
    }
  })
  .catch(err => {
    console.error(err);
    alert(`เกิดข้อผิดพลาดเชื่อมต่อสคริปต์: ${err.toString()}`);
  });
}

function editPettyCash(index) {
  const doc = pettyCashDb[index];
  editingDocIndex = index;
  document.querySelector('#addPettyCashModal .modal-title').textContent = 'แก้ไขข้อมูลเงินสดย่อย';
  document.getElementById('btnSubmitPettyCashModal').innerHTML = 'บันทึกการแก้ไข';
  document.getElementById('pettyCashVoucherNo').value = doc.voucherNo;
  const dateParts = doc.date.split('/');
  document.getElementById('pettyCashDate').value = `${dateParts[2]}-${dateParts[1]}-${dateParts[0]}`;
  document.getElementById('pettyCashRequester').value = doc.requester;
  document.getElementById('pettyCashCategory').value = doc.category;
  document.getElementById('pettyCashDetail').value = doc.detail;
  document.getElementById('pettyCashAmountPaid').value = doc.amountPaid;
  document.getElementById('pettyCashApprover').value = doc.approver;
  document.getElementById('pettyCashReceiptUrl').value = doc.receiptUrl === '-' ? '' : doc.receiptUrl;
  document.getElementById('pettyCashRemarks').value = doc.remarks === '-' ? '' : doc.remarks;
  document.getElementById('addPettyCashModal').classList.add('active');
}

function deletePettyCash(index) {
  if (confirm('ต้องการลบรายการเงินสดย่อยนี้ใช่หรือไม่?')) {
    pettyCashDb.splice(index, 1);
    saveData();
    renderPettyCash();
  }
}

// --- Payroll Logic ---
function autoGeneratePayrollId() {
  const now = new Date();
  return `PAY-${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function onPayrollEmployeeChange() {
  const select = document.getElementById('payrollEmployeeSelect');
  if (!select) return;
  const opt = select.options[select.selectedIndex];
  if (!opt || !opt.value) {
    document.getElementById('payrollEmployeeName').value = '';
    document.getElementById('payrollEmployeeTaxId').value = '';
    document.getElementById('payrollBaseSalary').value = '';
    document.getElementById('payrollBankAccount').value = '';
    calculatePayrollTotals();
    return;
  }
  document.getElementById('payrollEmployeeName').value = opt.getAttribute('data-name') || '';
  document.getElementById('payrollEmployeeTaxId').value = opt.getAttribute('data-taxid') || '';
  document.getElementById('payrollBaseSalary').value = opt.getAttribute('data-salary') || '';
  document.getElementById('payrollBankAccount').value = opt.getAttribute('data-bank') || '';
  calculatePayrollTotals();
}

function calculatePayrollTotals() {
  const baseSalary = parseFloat(document.getElementById('payrollBaseSalary').value) || 0;
  const allowances = parseFloat(document.getElementById('payrollAllowances').value) || 0;
  const wht = parseFloat(document.getElementById('payrollWhtDeduction').value) || 0;
  const other = parseFloat(document.getElementById('payrollOtherDeductions').value) || 0;
  const totalEarnings = Math.round((baseSalary + allowances) * 100) / 100;
  const ssf = Math.round((Math.min(totalEarnings * 0.05, 750)) * 100) / 100;
  const netPay = Math.round((totalEarnings - ssf - wht - other) * 100) / 100;

  document.getElementById('payrollSsfDeduction').value = ssf.toFixed(2);
  document.getElementById('calcPayrollTotalEarnings').textContent = `฿${totalEarnings.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  document.getElementById('calcPayrollNetPay').textContent = `฿${netPay.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
}

function renderPayroll() {
  const body = document.getElementById('payrollListBody');
  if (!body) return;
  if (payrollDb.length === 0) {
    body.innerHTML = `<tr><td colspan="10" style="text-align:center; color: var(--text-secondary); padding:20px;">ไม่มีข้อมูลเงินเดือน</td></tr>`;
    return;
  }
  body.innerHTML = payrollDb.map((doc, idx) => `
    <tr>
      <td class="mono">${escapeHtml(doc.payrollId)}</td>
      <td><strong>${escapeHtml(doc.employeeName)}</strong> <span class="mono" style="font-size:11px; color:var(--text-secondary);">(${escapeHtml(doc.employeeId)})</span></td>
      <td style="text-align:right;" class="mono">฿${(doc.baseSalary || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
      <td style="text-align:right;" class="mono">฿${(doc.allowances || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
      <td style="text-align:right;" class="mono">฿${(doc.totalEarnings || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
      <td style="text-align:right;" class="mono">฿${(doc.ssfDeduction || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
      <td style="text-align:right;" class="mono">฿${(doc.whtDeduction || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
      <td style="text-align:right; font-weight:700; color:var(--accent-color);" class="mono">฿${(doc.netPay || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
      <td style="text-align:center;"><span class="badge ${doc.status === 'โอนเงินแล้ว' ? 'synced' : 'pending'}">${escapeHtml(doc.status)}</span></td>
      <td style="text-align:center;">
        <div style="display:flex; gap:6px; justify-content:center;">
          ${doc.syncStatus !== 'synced' ? `
            <button class="btn-primary" onclick="syncPayroll(${idx})" style="padding: 4px 8px; font-size:11px; box-shadow: 2px 2px 0 var(--border-color); background:#f59e0b; border-color:#f59e0b; color:#fff;">ซิงค์</button>
          ` : '<span class="badge synced" style="padding: 4px 8px; font-size:11px;">ซิงค์แล้ว</span>'}
          <button class="btn-secondary" onclick="editPayroll(${idx})" style="padding: 4px 8px; font-size:11px; box-shadow: 2px 2px 0 var(--border-color); font-weight:700;">แก้ไข</button>
          <button class="btn-danger" onclick="deletePayroll(${idx})" style="padding: 4px 8px; font-size:11px; box-shadow: 2px 2px 0 var(--border-color);">ลบ</button>
        </div>
      </td>
    </tr>
  `).join('');
}

function savePayroll() {
  try {
    const payrollId = document.getElementById('payrollIdInput').value;
    const employeeId = document.getElementById('payrollEmployeeSelect').value;
    const employeeName = document.getElementById('payrollEmployeeName').value;
    const employeeTaxId = document.getElementById('payrollEmployeeTaxId').value;
    const baseSalary = parseFloat(document.getElementById('payrollBaseSalary').value) || 0;
    const allowances = parseFloat(document.getElementById('payrollAllowances').value) || 0;
    const ssfDeduction = parseFloat(document.getElementById('payrollSsfDeduction').value) || 0;
    const whtDeduction = parseFloat(document.getElementById('payrollWhtDeduction').value) || 0;
    const otherDeductions = parseFloat(document.getElementById('payrollOtherDeductions').value) || 0;
    const bankAccount = document.getElementById('payrollBankAccount').value;
    const status = document.getElementById('payrollStatus').value;
    const paySlipUrl = document.getElementById('payrollPaySlipUrl').value.trim();

    if (!employeeId) {
      alert('กรุณาเลือกพนักงานก่อนทำการบันทึก');
      return;
    }
    const totalEarnings = Math.round((baseSalary + allowances) * 100) / 100;
    const netPay = Math.round((totalEarnings - ssfDeduction - whtDeduction - otherDeductions) * 100) / 100;

    const isNew = editingDocIndex === null;
    const docRecord = {
      payrollId, employeeId, employeeName, employeeTaxId, baseSalary, allowances, totalEarnings,
      ssfDeduction, whtDeduction, otherDeductions, netPay, bankAccount, status, paySlipUrl: paySlipUrl || '-',
      syncStatus: isNew ? 'pending' : (payrollDb[editingDocIndex].syncStatus || 'pending')
    };

    if (isNew) {
      payrollDb.unshift(docRecord);
    } else {
      payrollDb[editingDocIndex] = docRecord;
      editingDocIndex = null;
    }
    saveData();
    renderPayroll();
    document.getElementById('addPayrollModal').classList.remove('active');

    const scriptUrl = safeStorage.getItem('ghn168_script_url');
    const sheetId = safeStorage.getItem('ghn168_sheet_id');
    if (scriptUrl && sheetId && isNew) {
      syncPayroll(0);
    }
  } catch (err) {
    console.error(err);
    alert('บันทึกเงินเดือนล้มเหลว: ' + err.toString());
  }
}

function syncPayroll(index) {
  const doc = payrollDb[index];
  if (!doc) return;
  const scriptUrl = safeStorage.getItem('ghn168_script_url');
  const sheetId = safeStorage.getItem('ghn168_sheet_id');
  if (!scriptUrl || !sheetId) {
    alert('กรุณาตั้งค่าการเชื่อมต่อ Google Sheets ก่อนเริ่มใช้งาน');
    return;
  }
  const payload = {
    spreadsheetId: sheetId,
    type: 'sync',
    sheetName: 'เงินเดือน',
    values: [
      doc.payrollId,
      doc.employeeId,
      doc.employeeName,
      doc.employeeTaxId || "-",
      Math.round(parseFloat(doc.baseSalary || 0) * 100) / 100,
      Math.round(parseFloat(doc.allowances || 0) * 100) / 100,
      Math.round(parseFloat(doc.totalEarnings || 0) * 100) / 100,
      Math.round(parseFloat(doc.ssfDeduction || 0) * 100) / 100,
      Math.round(parseFloat(doc.whtDeduction || 0) * 100) / 100,
      Math.round(parseFloat(doc.otherDeductions || 0) * 100) / 100,
      Math.round(parseFloat(doc.netPay || 0) * 100) / 100,
      doc.bankAccount || "-",
      doc.status || "รอดำเนินการ",
      doc.paySlipUrl || "-"
    ]
  };
  fetch(scriptUrl, {
    method: 'POST', mode: 'cors', headers: { 'Content-Type': 'text/plain' }, body: JSON.stringify(payload)
  })
  .then(res => res.json())
  .then(res => {
    if (res.status === 'success') {
      alert('ซิงค์ข้อมูลเงินเดือนสำเร็จแล้ว');
      doc.syncStatus = 'synced';
      saveData();
      renderPayroll();
    } else {
      alert(`ซิงค์ล้มเหลว: ${res.message}`);
    }
  })
  .catch(err => {
    console.error(err);
    alert(`เกิดข้อผิดพลาดเชื่อมต่อสคริปต์: ${err.toString()}`);
  });
}

function editPayroll(index) {
  const doc = payrollDb[index];
  editingDocIndex = index;
  document.querySelector('#addPayrollModal .modal-title').textContent = 'แก้ไขข้อมูลเงินเดือน';
  document.getElementById('btnSubmitPayrollModal').innerHTML = 'บันทึกการแก้ไข';
  document.getElementById('payrollIdInput').value = doc.payrollId;
  document.getElementById('payrollEmployeeSelect').value = doc.employeeId;
  document.getElementById('payrollEmployeeName').value = doc.employeeName;
  document.getElementById('payrollEmployeeTaxId').value = doc.employeeTaxId;
  document.getElementById('payrollBaseSalary').value = doc.baseSalary;
  document.getElementById('payrollAllowances').value = doc.allowances;
  document.getElementById('payrollSsfDeduction').value = doc.ssfDeduction;
  document.getElementById('payrollWhtDeduction').value = doc.whtDeduction;
  document.getElementById('payrollOtherDeductions').value = doc.otherDeductions;
  document.getElementById('payrollBankAccount').value = doc.bankAccount;
  document.getElementById('payrollStatus').value = doc.status;
  document.getElementById('payrollPaySlipUrl').value = doc.paySlipUrl === '-' ? '' : doc.paySlipUrl;
  calculatePayrollTotals();
  document.getElementById('addPayrollModal').classList.add('active');
}

function deletePayroll(index) {
  if (confirm('ต้องการลบประวัติรอบจ่ายเงินเดือนนี้ใช่หรือไม่?')) {
    payrollDb.splice(index, 1);
    saveData();
    renderPayroll();
  }
}

// --- Bank Reconciliation Logic ---
function autoGenerateBankRecId(period) {
  return period ? `REC-${period}` : 'REC-YYYY-MM';
}

function onBankRecPeriodChange() {
  const periodVal = document.getElementById('bankRecPeriod').value;
  const bankAcc = document.getElementById('bankRecBankAccount').value;
  if (!periodVal || !bankAcc) {
    document.getElementById('bankRecBookBalance').value = '0.00';
    calculateBankRecTotals();
    return;
  }
  const [targetYear, targetMonth] = periodVal.split('-').map(Number);
  let bookBalance = 100000.00; // Starting base treasury balance

  const isBeforeOrEqual = (dateStr) => {
    if (!dateStr) return false;
    const parts = dateStr.split('/');
    if (parts.length !== 3) return false;
    const m = parseInt(parts[1]);
    const y = parseInt(parts[2]);
    return y < targetYear || (y === targetYear && m <= targetMonth);
  };

  const matchBank = (docVal, targetVal) => {
    if (!docVal) return false;
    const docLower = docVal.toLowerCase();
    const targetLower = targetVal.toLowerCase();
    if (docLower === targetLower) return true;
    if (targetLower.includes('kbank') && (docLower.includes('kbank') || docLower.includes('k-bank') || docLower.includes('kasikorn') || docLower.includes('โอน') || docLower.includes('เช็ค') || docLower.includes('เชค'))) return true;
    if (targetLower.includes('scb') && (docLower.includes('scb') || docLower.includes('siam commercial'))) return true;
    return false;
  };

  dbDocs.forEach(d => {
    if (!isBeforeOrEqual(d.date)) return;
    if (d.type === 'receipt') {
      if (matchBank(d.receivingBank || 'KBank', bankAcc)) {
        bookBalance += (d.net || d.amount || 0);
      }
    } else if (d.type === 'expense' && d.status !== 'pending_approval') {
      if (matchBank(d.paymentMethod || d.fundingSource || 'KBank', bankAcc)) {
        bookBalance -= (d.net || d.amount || 0);
      }
    }
  });

  payrollDb.forEach(p => {
    if (!p.payrollId) return;
    const parts = p.payrollId.split('-');
    if (parts.length >= 3) {
      const py = parseInt(parts[1]);
      const pm = parseInt(parts[2]);
      const isPayBefore = py < targetYear || (py === targetYear && pm <= targetMonth);
      if (isPayBefore && p.status === 'โอนเงินแล้ว' && bankAcc === 'KBANK-Main') {
        bookBalance -= (p.netPay || 0);
      }
    }
  });

  document.getElementById('bankRecBookBalance').value = bookBalance.toFixed(2);
  calculateBankRecTotals();
}

function calculateBankRecTotals() {
  const statementBal = parseFloat(document.getElementById('bankRecStatementBalance').value) || 0;
  const bookBal = parseFloat(document.getElementById('bankRecBookBalance').value) || 0;
  const depositInTransit = parseFloat(document.getElementById('bankRecDepositInTransit').value) || 0;
  const outstandingCheques = parseFloat(document.getElementById('bankRecOutstandingCheques').value) || 0;
  const chargesNotRecorded = parseFloat(document.getElementById('bankRecChargesNotRecorded').value) || 0;

  const adjustedStatement = Math.round((statementBal + depositInTransit - outstandingCheques) * 100) / 100;
  const adjustedBook = Math.round((bookBal - chargesNotRecorded) * 100) / 100;
  const diff = Math.round((adjustedStatement - adjustedBook) * 100) / 100;

  document.getElementById('calcBankRecAdjustedStatement').textContent = `฿${adjustedStatement.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  document.getElementById('calcBankRecAdjustedBook').textContent = `฿${adjustedBook.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  
  const diffEl = document.getElementById('calcBankRecDifference');
  diffEl.textContent = `฿${diff.toLocaleString('th-TH', { minimumFractionDigits: 2 })}`;
  diffEl.style.color = Math.abs(diff) < 0.01 ? '#16a34a' : 'var(--accent-color)';
}

function renderBankRec() {
  const body = document.getElementById('bankRecListBody');
  if (!body) return;
  if (bankRecDb.length === 0) {
    body.innerHTML = `<tr><td colspan="9" style="text-align:center; color: var(--text-secondary); padding:20px;">ไม่มีข้อมูลการกระทบยอดธนาคาร</td></tr>`;
    return;
  }
  body.innerHTML = bankRecDb.map((doc, idx) => `
    <tr>
      <td class="mono">${escapeHtml(doc.reconciliationId)}</td>
      <td style="text-align:center;">${escapeHtml(doc.period)}</td>
      <td><strong>${escapeHtml(doc.bankAccount)}</strong></td>
      <td style="text-align:right;" class="mono">฿${(doc.statementBalance || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
      <td style="text-align:right;" class="mono">฿${(doc.bookBalance || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
      <td style="text-align:right;" class="mono">฿${(doc.adjustedStatementBalance || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
      <td style="text-align:right; font-weight:700; color:${Math.abs(doc.difference) < 0.01 ? '#16a34a' : 'var(--accent-color)'};" class="mono">฿${(doc.difference || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
      <td>${escapeHtml(doc.reconciledBy)}</td>
      <td style="text-align:center;">
        <div style="display:flex; gap:6px; justify-content:center;">
          ${doc.syncStatus !== 'synced' ? `
            <button class="btn-primary" onclick="syncBankRec(${idx})" style="padding: 4px 8px; font-size:11px; box-shadow: 2px 2px 0 var(--border-color); background:#f59e0b; border-color:#f59e0b; color:#fff;">ซิงค์</button>
          ` : '<span class="badge synced" style="padding: 4px 8px; font-size:11px;">ซิงค์แล้ว</span>'}
          <button class="btn-secondary" onclick="editBankRec(${idx})" style="padding: 4px 8px; font-size:11px; box-shadow: 2px 2px 0 var(--border-color); font-weight:700;">แก้ไข</button>
          <button class="btn-danger" onclick="deleteBankRec(${idx})" style="padding: 4px 8px; font-size:11px; box-shadow: 2px 2px 0 var(--border-color);">ลบ</button>
        </div>
      </td>
    </tr>
  `).join('');
}

function saveBankRec() {
  try {
    const reconciliationId = document.getElementById('bankRecReconciliationId').value;
    const period = document.getElementById('bankRecPeriod').value;
    const bankAccount = document.getElementById('bankRecBankAccount').value;
    const statementBalance = parseFloat(document.getElementById('bankRecStatementBalance').value) || 0;
    const bookBalance = parseFloat(document.getElementById('bankRecBookBalance').value) || 0;
    const depositInTransit = parseFloat(document.getElementById('bankRecDepositInTransit').value) || 0;
    const outstandingCheques = parseFloat(document.getElementById('bankRecOutstandingCheques').value) || 0;
    const bankChargesNotRecorded = parseFloat(document.getElementById('bankRecChargesNotRecorded').value) || 0;
    const reconciledBy = document.getElementById('bankRecReconciledBy').value.trim();

    if (!period) {
      alert('กรุณาระบุงวดประจำเดือนก่อนทำการบันทึก');
      return;
    }
    const adjustedStatementBalance = Math.round((statementBalance + depositInTransit - outstandingCheques) * 100) / 100;
    const adjustedBookBalance = Math.round((bookBalance - bankChargesNotRecorded) * 100) / 100;
    const difference = Math.round((adjustedStatementBalance - adjustedBookBalance) * 100) / 100;

    const isNew = editingDocIndex === null;
    const docRecord = {
      reconciliationId, period, bankAccount, statementBalance, bookBalance, depositInTransit,
      outstandingCheques, bankChargesNotRecorded, adjustedStatementBalance, adjustedBookBalance, difference, reconciledBy,
      syncStatus: isNew ? 'pending' : (bankRecDb[editingDocIndex].syncStatus || 'pending')
    };

    if (isNew) {
      bankRecDb.unshift(docRecord);
    } else {
      bankRecDb[editingDocIndex] = docRecord;
      editingDocIndex = null;
    }
    saveData();
    renderBankRec();
    document.getElementById('addBankRecModal').classList.remove('active');

    const scriptUrl = safeStorage.getItem('ghn168_script_url');
    const sheetId = safeStorage.getItem('ghn168_sheet_id');
    if (scriptUrl && sheetId && isNew) {
      syncBankRec(0);
    }
  } catch (err) {
    console.error(err);
    alert('บันทึกงบกระทบยอดล้มเหลว: ' + err.toString());
  }
}

function syncBankRec(index) {
  const doc = bankRecDb[index];
  if (!doc) return;
  const scriptUrl = safeStorage.getItem('ghn168_script_url');
  const sheetId = safeStorage.getItem('ghn168_sheet_id');
  if (!scriptUrl || !sheetId) {
    alert('กรุณาตั้งค่าการเชื่อมต่อ Google Sheets ก่อนเริ่มใช้งาน');
    return;
  }
  const payload = {
    spreadsheetId: sheetId,
    type: 'sync',
    sheetName: 'กระทบยอดธนาคาร',
    values: [
      doc.reconciliationId,
      doc.period,
      doc.bankAccount,
      Math.round(parseFloat(doc.statementBalance || 0) * 100) / 100,
      Math.round(parseFloat(doc.bookBalance || 0) * 100) / 100,
      Math.round(parseFloat(doc.depositInTransit || 0) * 100) / 100,
      Math.round(parseFloat(doc.outstandingCheques || 0) * 100) / 100,
      Math.round(parseFloat(doc.bankChargesNotRecorded || 0) * 100) / 100,
      Math.round(parseFloat(doc.adjustedStatementBalance || 0) * 100) / 100,
      Math.round(parseFloat(doc.adjustedBookBalance || 0) * 100) / 100,
      Math.round(parseFloat(doc.difference || 0) * 100) / 100,
      doc.reconciledBy || "-"
    ]
  };
  fetch(scriptUrl, {
    method: 'POST', mode: 'cors', headers: { 'Content-Type': 'text/plain' }, body: JSON.stringify(payload)
  })
  .then(res => res.json())
  .then(res => {
    if (res.status === 'success') {
      alert('ซิงค์ข้อมูลกระทบยอดธนาคารสำเร็จแล้ว');
      doc.syncStatus = 'synced';
      saveData();
      renderBankRec();
    } else {
      alert(`ซิงค์ล้มเหลว: ${res.message}`);
    }
  })
  .catch(err => {
    console.error(err);
    alert(`เกิดข้อผิดพลาดเชื่อมต่อสคริปต์: ${err.toString()}`);
  });
}

function editBankRec(index) {
  const doc = bankRecDb[index];
  editingDocIndex = index;
  document.querySelector('#addBankRecModal .modal-title').textContent = 'แก้ไขข้อมูลกระทบยอดธนาคาร';
  document.getElementById('btnSubmitBankRecModal').innerHTML = 'บันทึกการแก้ไข';
  document.getElementById('bankRecReconciliationId').value = doc.reconciliationId;
  document.getElementById('bankRecPeriod').value = doc.period;
  document.getElementById('bankRecBankAccount').value = doc.bankAccount;
  document.getElementById('bankRecStatementBalance').value = doc.statementBalance;
  document.getElementById('bankRecBookBalance').value = doc.bookBalance;
  document.getElementById('bankRecDepositInTransit').value = doc.depositInTransit;
  document.getElementById('bankRecOutstandingCheques').value = doc.outstandingCheques;
  document.getElementById('bankRecChargesNotRecorded').value = doc.bankChargesNotRecorded;
  document.getElementById('bankRecReconciledBy').value = doc.reconciledBy;
  calculateBankRecTotals();
  document.getElementById('addBankRecModal').classList.add('active');
}

function deleteBankRec(index) {
  if (confirm('ต้องการลบประวัติงบกระทบยอดรายการนี้ใช่หรือไม่?')) {
    bankRecDb.splice(index, 1);
    saveData();
    renderBankRec();
  }
}

// --- Tax Export Logic & Helpers ---
function parseThaiName(fullName) {
  fullName = fullName.trim();
  let prefix = 'นาย';
  let firstName = fullName;
  let lastName = '';
  const prefixes = ['นาย', 'นางสาว', 'นาง', 'บริษัท จำกัด', 'บริษัท', 'บจก.', 'หจก.', 'ห้างหุ้นส่วนจำกัด'];
  for (let p of prefixes) {
    if (fullName.startsWith(p)) {
      prefix = p;
      firstName = fullName.substring(p.length).trim();
      if (prefix === 'บจก.' || prefix === 'บริษัท จำกัด') prefix = 'บริษัท';
      if (prefix === 'หจก.') prefix = 'ห้างหุ้นส่วนจำกัด';
      break;
    }
  }
  if (prefix === 'นาย' || prefix === 'นาง' || prefix === 'นางสาว') {
    const parts = firstName.split(/\s+/);
    if (parts.length > 1) {
      firstName = parts[0];
      lastName = parts.slice(1).join(' ');
    }
  }
  return { prefix, firstName, lastName };
}

function toThaiBuddhistDate(dateStr) {
  if (!dateStr) return '';
  const parts = dateStr.split('/');
  if (parts.length !== 3) return dateStr;
  return `${parts[0]}/${parts[1]}/${parseInt(parts[2]) + 543}`;
}

function previewTaxFiling() {
  const periodVal = document.getElementById('taxExportPeriod').value;
  const formType = document.getElementById('taxExportFormType').value;
  const tbody = document.getElementById('taxExportListBody');
  if (!tbody) return;

  if (!periodVal) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-secondary); padding: 20px;">กรุณาเลือกงวดประจำเดือนก่อน</td></tr>`;
    return;
  }
  const [targetYear, targetMonth] = periodVal.split('-').map(Number);
  const filtered = dbDocs.filter(d => {
    if (d.type !== 'expense' || d.status === 'pending_approval') return false;
    if (d.whtType !== formType) return false;
    if (!d.date) return false;
    const parts = d.date.split('/');
    if (parts.length !== 3) return false;
    return parseInt(parts[1]) === targetMonth && parseInt(parts[2]) === targetYear;
  });

  const formTitle = formType === 'pnd3' ? 'ภ.ง.ด.3 (บุคคลธรรมดา)' : 'ภ.ง.ด.53 (นิติบุคคล)';
  const [y, m] = periodVal.split('-');
  document.getElementById('taxExportTableTitle').textContent = `รายการภาษีหัก ณ ที่จ่ายประจำรอบ ${THAI_MONTHS[parseInt(m) - 1]} ${parseInt(y) + 543} [แบบ ${formTitle}]`;

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-secondary); padding: 20px;">ไม่มีข้อมูลภาษีหัก ณ ที่จ่าย (WHT (50.ทวิ)) สำหรับช่วงเวลาและแบบยื่นที่ระบุ</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(d => {
    const whtRate = d.whtAmount > 0 ? Math.round((d.whtAmount / d.baseAmount) * 100) : 0;
    return `
      <tr>
        <td class="mono">${escapeHtml(d.payeeTaxId || '-')}</td>
        <td style="text-align:center;" class="mono">${escapeHtml(d.payeeBranch || '00000')}</td>
        <td><strong>${escapeHtml(d.name)}</strong></td>
        <td>${escapeHtml(d.payeeAddress || '-')}</td>
        <td style="text-align:center;">${escapeHtml(toThaiBuddhistDate(d.date))}</td>
        <td>${escapeHtml(d.desc ? `${d.category}: ${d.desc}` : d.category)}</td>
        <td style="text-align:center;" class="mono">${whtRate}%</td>
        <td style="text-align:right;" class="mono">฿${(d.baseAmount || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
        <td style="text-align:right; font-weight:700; color:var(--accent-color);" class="mono">฿${(d.whtAmount || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
      </tr>
    `;
  }).join('');
}

function downloadRDPrepText() {
  const periodVal = document.getElementById('taxExportPeriod').value;
  const formType = document.getElementById('taxExportFormType').value;
  if (!periodVal) {
    alert('กรุณาเลือกงวดประจำเดือนก่อน');
    return;
  }
  const [targetYear, targetMonth] = periodVal.split('-').map(Number);
  const filtered = dbDocs.filter(d => {
    if (d.type !== 'expense' || d.status === 'pending_approval') return false;
    if (d.whtType !== formType) return false;
    if (!d.date) return false;
    const parts = d.date.split('/');
    if (parts.length !== 3) return false;
    return parseInt(parts[1]) === targetMonth && parseInt(parts[2]) === targetYear;
  });

  if (filtered.length === 0) {
    alert('ไม่มีรายการภาษีสำหรับดาวน์โหลดในช่วงเวลาและแบบยื่นที่เลือก');
    return;
  }

  const lines = filtered.map(d => {
    const taxId = (d.payeeTaxId || '').replace(/\D/g, '');
    const branch = (d.payeeBranch || '00000').replace(/\D/g, '');
    const { prefix, firstName, lastName } = parseThaiName(d.name);
    const address = (d.payeeAddress || '-').trim();
    const dateBE = toThaiBuddhistDate(d.date);
    const incomeType = d.desc ? `${d.category}: ${d.desc}` : d.category;
    const whtRate = d.whtAmount > 0 ? Math.round((d.whtAmount / d.baseAmount) * 100) : 0;
    const baseAmtStr = (d.baseAmount || 0).toFixed(2);
    const whtAmtStr = (d.whtAmount || 0).toFixed(2);
    return `${taxId}|${branch}|${prefix}|${firstName}|${lastName}|${address}|${dateBE}|${incomeType}|${whtRate}|${baseAmtStr}|${whtAmtStr}|1`;
  });

  const blob = new Blob([lines.join('\r\n')], { type: 'text/plain;charset=utf-8' });
  const filename = `WHT_Export_${formType}_${periodVal.replace('-', '')}.txt`;
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  alert(`ดาวน์โหลดไฟล์นำส่งสำเร็จแล้ว\nชื่อไฟล์: ${filename}`);
}

// --- Auto-scale A4 previews to fit their container width ---
function setupPreviewAutoScaling() {
  try {
    const previewPanel = document.querySelector('.doc-preview-panel');
    if (!previewPanel) return;

    const resizeObserver = new ResizeObserver(entries => {
      try {
        for (let entry of entries) {
          const panelWidth = entry.contentRect.width;
          // Spacing inside the panel: A4 width is 794px. We add 40px breathing room.
          const targetWidth = 794 + 40;
          
          const isMobileOrTablet = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
                                  (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
          
          let scale = 1;
          if (!isMobileOrTablet && panelWidth < targetWidth) {
            scale = panelWidth / targetWidth;
            // Cap the minimum scale to 0.4 on extremely small screens to keep it readable
            if (scale < 0.4) scale = 0.4;
          }
          
          previewPanel.style.setProperty('--preview-scale-factor', scale);
        }
      } catch (err) {
        alert(`ERROR IN RESIZE OBSERVER:\n${err.message}\n${err.stack}`);
      }
    });

    resizeObserver.observe(previewPanel);
  } catch (err) {
    alert(`ERROR IN setupPreviewAutoScaling:\n${err.message}\n${err.stack}`);
  }
}

async function forceClearCacheAndReload() {
  if (!confirm('ต้องการล้างแคชแอปพลิเคชันเพื่ออัปเดตระบบใช่หรือไม่? (ข้อมูลที่บันทึกไว้ในเครื่องจะไม่สูญหาย)')) {
    return;
  }
  try {
    if ('serviceWorker' in navigator) {
      const registrations = await navigator.serviceWorker.getRegistrations();
      for (let registration of registrations) {
        await registration.unregister();
      }
    }
    if ('caches' in window) {
      const cacheNames = await caches.keys();
      for (let cacheName of cacheNames) {
        await caches.delete(cacheName);
      }
    }
    alert('ล้างแคชสำเร็จ ระบบจะทำการรีโหลดหน้าจอเพื่ออัปเดตเวอร์ชันใหม่');
    window.location.reload(true);
  } catch (err) {
    console.error(err);
    alert('เกิดข้อผิดพลาดในการล้างแคช: ' + err.message);
  }
}
window.forceClearCacheAndReload = forceClearCacheAndReload;

// Expose corporate handlers to global window scope
window.autoGeneratePettyCashVoucherNo = autoGeneratePettyCashVoucherNo;
window.renderPettyCash = renderPettyCash;
window.savePettyCash = savePettyCash;
window.syncPettyCash = syncPettyCash;
window.editPettyCash = editPettyCash;
window.deletePettyCash = deletePettyCash;
window.autoGeneratePayrollId = autoGeneratePayrollId;
window.onPayrollEmployeeChange = onPayrollEmployeeChange;
window.calculatePayrollTotals = calculatePayrollTotals;
window.renderPayroll = renderPayroll;
window.savePayroll = savePayroll;
window.syncPayroll = syncPayroll;
window.editPayroll = editPayroll;
window.deletePayroll = deletePayroll;
window.autoGenerateBankRecId = autoGenerateBankRecId;
window.onBankRecPeriodChange = onBankRecPeriodChange;
window.calculateBankRecTotals = calculateBankRecTotals;
window.renderBankRec = renderBankRec;
window.saveBankRec = saveBankRec;
window.syncBankRec = syncBankRec;
window.editBankRec = editBankRec;
window.deleteBankRec = deleteBankRec;
window.previewTaxFiling = previewTaxFiling;
window.downloadRDPrepText = downloadRDPrepText;
