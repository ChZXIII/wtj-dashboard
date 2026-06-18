// --- GHN168 Dashboard & Document Sync App Logic ---

// Catch and display global errors on screen for easy debugging
window.onerror = function(message, source, lineno, colno, error) {
  // Ignore generic cross-origin script errors (often caused by browser extensions or file:// protocol security restrictions)
  if (message === 'Script error.' || lineno === 0 || colno === 0) {
    console.warn(`Ignored generic cross-origin/extension script error: ${message} at line ${lineno}:${colno}`);
    return false;
  }
  alert(`🔴 JS ERROR:\n${message}\nat line ${lineno}:${colno}`);
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
  } catch (err) {
    alert(`🔴 LOCAL ERROR IN INITIALIZATION:\nName: ${err.name}\nMessage: ${err.message}\nStack: ${err.stack}`);
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
  
  alert('บันทึกการเชื่อมต่อเรียบร้อยแล้วแก!');
}

function initializeGoogleSheet() {
  const scriptUrl = safeStorage.getItem('ghn168_script_url');
  const sheetId = safeStorage.getItem('ghn168_sheet_id');
  
  if (!scriptUrl || !sheetId) {
    alert('⚠️ กรุณากรอก URL และ Spreadsheet ID จากนั้นกด "บันทึกการเชื่อมต่อบัญชี" ก่อนนะแก!');
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
      alert(`🎉 ${res.message}`);
    } else {
      alert(`❌ เกิดข้อผิดพลาดจาก Apps Script: ${res.message}`);
    }
  })
  .catch(err => {
    console.error(err);
    alert(`❌ เกิดข้อผิดพลาดเชื่อมต่อสคริปต์: ${err.toString()}\n\n*ข้อแนะนำ: ตรวจสอบว่าแกได้ก๊อปปี้สคริปต์ตัวปรับปรุงล่าสุดไปวางและกด Deploy เป็น Web App แบบ 'ทุกคน (Anyone)' แล้วหรือยังนะแก!`);
  })
  .finally(() => {
    btn.disabled = false;
    btn.style.opacity = '1';
    btn.innerHTML = originalHtml;
  });
}

function loadData() {
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
  if (dbDocs.length === 0) {
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
  if (docHubLinks.length === 0) {
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

  if (pettyCashDb.length === 0) {
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

  if (payrollDb.length === 0) {
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

  if (bankRecDb.length === 0) {
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
}

// --- Event Listeners Setup ---
function setupEventListeners() {
  // Sidebar navigation
  document.querySelectorAll('.nav-item').forEach(item => {
    const btn = item.querySelector('button');
    if (btn) {
      btn.addEventListener('click', () => {
        switchView(item.dataset.view);
      });
    }
  });

  // Document type tabs
  document.getElementById('btnDocTypeQuotation').addEventListener('click', () => setDocType('quotation'));
  document.getElementById('btnDocTypeInvoice').addEventListener('click', () => setDocType('invoice'));
  document.getElementById('btnDocTypeReceipt').addEventListener('click', () => setDocType('receipt'));
  document.getElementById('btnDocTypeWht').addEventListener('click', () => setDocType('wht'));

  // Editor detail inputs
  const inputsToSync = [
    'docClientName', 'docClientTaxId', 'docClientAddress', 'docClientPhone',
    'docNumber', 'docPaymentTerm', 'docProjectName', 'doc_sellerName', 
    'doc_sellerTaxId', 'doc_sellerAddress', 'doc_sellerPhone', 'doc_sellerEmail',
    'doc_bankDetails', 'doc_signerName'
  ];
  inputsToSync.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', () => {
        if (id.startsWith('doc_')) {
          saveSellerConfig();
        } else {
          syncDocPreview();
        }
      });
    }
  });

  document.getElementById('docDate').addEventListener('change', syncDocPreview);
  document.getElementById('docDueDate').addEventListener('change', syncDocPreview);

  // Add Item row button
  document.getElementById('btnAddDocItem').addEventListener('click', addDocItem);

  // Checkboxes & Selects
  document.getElementById('doc_showSeal').addEventListener('change', saveSellerConfig);
  document.getElementById('docVatCheckbox').addEventListener('change', calculateDocTotals);
  document.getElementById('docWhtSelect').addEventListener('change', calculateDocTotals);
  document.getElementById('docOwner').addEventListener('change', calculateDocTotals);
  document.getElementById('docRetentionRate').addEventListener('input', calculateDocTotals);

  // Export PDF Button
  document.getElementById('btnExportDocPdf').addEventListener('click', () => {
    window.print();
  });

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
        calculateWhtTotals();
        syncWhtPreview();
      });
    }
  });

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
      alert('💡 น้องพิมตรวจพบว่าแกวางลิงก์สลับช่องกับชื่อเอกสาร เลยทำการสลับกลับคืนให้เรียบร้อยแล้วจ้า!');
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
    addDocModal.classList.remove('active');
  });

  // Sync Data Button
  document.getElementById('btnSaveAndSyncDoc').addEventListener('click', processDocumentSync);

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
function setDocType(type) {
  currentDocType = type;
  
  // Toggle buttons active class
  ['Quotation', 'Invoice', 'Receipt', 'Wht'].forEach(t => {
    const btn = document.getElementById(`btnDocType${t}`);
    if (t.toLowerCase() === type.toLowerCase()) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Display fields according to doc type
  const formDocs = document.getElementById('formGroupDocItems');
  const formWht = document.getElementById('formGroupWhtDetails');
  const previewStandard = document.getElementById('previewStandardDoc');
  const previewWht = document.getElementById('previewWhtDoc');
  const formInternalDetails = document.getElementById('formGroupInternalDetails');

  // Field group toggles
  const groupDueDate = document.getElementById('groupDocDueDate');
  const groupPaymentTerm = document.getElementById('groupDocPaymentTerm');
  
  const syncBtn = document.getElementById('btnSaveAndSyncDoc');

  if (type === 'wht') {
    formDocs.style.display = 'none';
    formWht.style.display = 'block';
    previewStandard.style.display = 'none';
    previewWht.style.display = 'block';
    if (formInternalDetails) formInternalDetails.style.display = 'none';
    
    // Expenses Sync Button text
    syncBtn.innerHTML = '📝 พิมพ์ 50 ทวิ & บันทึกรายจ่ายลงชีต';
    syncBtn.style.display = 'block';
    
    // Set auto doc number
    document.getElementById('whtDocNumber').value = autoGenerateDocNumber('wht');
    
    calculateWhtTotals();
    syncWhtPreview();
  } else {
    formDocs.style.display = 'block';
    formWht.style.display = 'none';
    previewStandard.style.display = 'block';
    previewWht.style.display = 'none';
    if (formInternalDetails) formInternalDetails.style.display = 'block';

    // Show/hide due date terms
    if (type === 'receipt') {
      groupDueDate.style.display = 'none';
      groupPaymentTerm.style.display = 'none';
      syncBtn.innerHTML = '💰 พิมพ์ใบเสร็จ & บันทึกรายรับลงชีต';
      syncBtn.style.display = 'block';
    } else {
      groupDueDate.style.display = 'block';
      groupPaymentTerm.style.display = 'block';
      syncBtn.style.display = 'none'; // No sheet sync for QT / IV
    }

    // Set auto doc number
    document.getElementById('docNumber').value = autoGenerateDocNumber(type);

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
  
  // Find current month items in local db to increment number
  const matchPattern = `${prefix}${yy}${mm}`;
  const monthItems = dbDocs.filter(d => d.number.startsWith(matchPattern));
  const num = String(monthItems.length + 1).padStart(3, '0');

  return `${matchPattern}-${num}`;
}

// --- Items List Rendering ---
function renderPrevItemsTable() {
  const prevBody = document.getElementById('prevItemsBody');
  if (prevBody) {
    if (docItems.length === 0) {
      prevBody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 15px; font-style:italic;">ไม่มีรายการ</td></tr>`;
    } else {
      prevBody.innerHTML = docItems.map((item, idx) => {
        const total = (item.qty || 0) * (item.price || 0);
        return `
          <tr>
            <td style="text-align:center;">${idx + 1}</td>
            <td style="text-align:left; white-space: pre-wrap;">${escapeHtml(item.desc || '-')}</td>
            <td style="text-align:center;">${item.qty}</td>
            <td style="text-align:center;">${escapeHtml(item.unit || 'งาน')}</td>
            <td style="text-align:right;">${item.price.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
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
        <input type="text" value="${escapeHtml(item.desc)}" oninput="updateDocItem(${idx}, 'desc', this.value)" class="form-control" style="border:none; padding:4px;" placeholder="เช่น ถ่ายวีดีโอโฆษณา" required>
      </td>
      <td style="width: 80px;">
        <input type="number" value="${item.qty}" min="1" step="any" oninput="updateDocItem(${idx}, 'qty', this.value)" class="form-control" style="border:none; padding:4px; text-align:center;" required>
      </td>
      <td style="width: 80px;">
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

  // Adjust rowspan of the Baht text cell dynamically based on visible rows
  let activeRows = 2; // Subtotal and Grand Total are always visible
  if (vatChecked) activeRows++;
  if (whtRate > 0) activeRows++;
  const bahtTextCell = document.getElementById('prevBahtTextCell');
  if (bahtTextCell) {
    bahtTextCell.setAttribute('rowspan', activeRows);
  }

  document.getElementById('prevGrandTotalVal').textContent = `฿${grandTotal.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById('prevBahtTextVal').textContent = thaiBahtText(grandTotal);

  // Update internal company details calculation
  const retentionRate = parseFloat(document.getElementById('docRetentionRate').value) || 0;
  const retainedAmount = subtotal * (retentionRate / 100);
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

// --- Sync Previews ---
function syncDocPreview() {
  const docTitle = currentDocType === 'quotation' ? 'ใบเสนอราคา' : (currentDocType === 'invoice' ? 'ใบวางบิล / ใบแจ้งหนี้' : 'ใบเสร็จรับเงิน / ใบกำกับภาษี');
  const docTitleEn = currentDocType === 'quotation' ? 'QUOTATION' : (currentDocType === 'invoice' ? 'INVOICE' : 'RECEIPT / TAX INVOICE');

  document.getElementById('prevDocTitleText').textContent = docTitle;
  document.getElementById('prevDocTitleEnText').textContent = docTitleEn;

  // Hide Due Date row on Receipt and Quotation (Only show on Invoice)
  const dueDateRow = document.getElementById('prevDocDueDateRow');
  if (dueDateRow) {
    dueDateRow.style.display = currentDocType === 'invoice' ? '' : 'none';
  }

  // Simple mappings
  const fields = [
    { from: 'doc_sellerName', to: 'prevSellerName' },
    { from: 'doc_sellerNameEn', to: 'prevSellerNameEn' },
    { from: 'doc_sellerTaxId', to: 'prevSellerTaxId' },
    { from: 'doc_sellerPhone', to: 'prevSellerPhone' },
    { from: 'doc_sellerEmail', to: 'prevSellerEmail' },
    { from: 'doc_bankDetails', to: 'prevBankDetailsVal' },
    { from: 'doc_signerName', to: 'prevSignerNameVal' },

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
      prev.textContent = input.value || '-';
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
      document.getElementById('prevClientTaxId').textContent = taxIdVal;
    } else {
      prevClientTaxIdRow.style.display = 'none';
    }
  }

  // Render item tables
  renderPrevItemsTable();

  // Toggle company seal visibility
  const showSeal = document.getElementById('doc_showSeal').checked;
  document.querySelectorAll('.company-seal-img').forEach(img => {
    img.style.display = showSeal ? 'block' : 'none';
  });
}

function syncWhtPreview() {
  const docNo = document.getElementById('whtDocNumber').value || '-';
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
}

function formatDate(dateStr) {
  if (!dateStr) return '-';
  const parts = dateStr.split('-');
  if (parts.length === 3) {
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }
  return dateStr;
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
    alert('⚠️ กรุณาไปตั้งค่า URL ของ Google Apps Script และ Spreadsheet ID ที่แท็บการตั้งค่าก่อนนะแก!');
    switchView('settings');
    return;
  }

  // Check HITL status if amount is high
  const hasHitl = document.getElementById('hitlWarningPanel').style.display === 'block';
  if (hasHitl) {
    const chk = document.getElementById('hitlApprovedCheckbox');
    if (!chk || !chk.checked) {
      alert('⚠️ รายการนี้มียอดเงินเกิน 10,000 บาท พิมขอแนะนำให้กดยืนยันอนุมัติบัญชีในช่องสี่เหลี่ยมสีแดงก่อนกดยืนยันเซฟลงชีตค่ะ!');
      return;
    }
  }

  // Gather doc meta
  let payload = {
    spreadsheetId: sheetId
  };

  if (currentDocType === 'wht') {
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
    const tax = gross * (rate / 100);
    const net = gross - tax;
    
    const paymentMethod = document.getElementById('whtPaymentMethod').value;
    const paymentStatus = document.getElementById('whtPaymentStatus').value;
    const actualPaidDate = document.getElementById('whtActualPaidDate').value || dateVal;
    const taxFilingStatus = document.getElementById('whtTaxFilingStatus').value;
    const remarks = document.getElementById('whtRemarks').value;

    if (!docNo || !dateVal || !payeeName || !detail || gross <= 0) {
      alert('⚠️ กรุณากรอกข้อมูลรายจ่ายหัก ณ ที่จ่ายให้ครบถ้วนก่อนบันทึกนะแก!');
      return;
    }

    payload.type = 'expense';
    payload.recordDate = formatDate(new Date().toISOString().split('T')[0]);
    payload.date = formatDate(dateVal);
    payload.docNo = docNo;
    payload.payeeName = payeeName;
    payload.payeeTaxId = payeeTaxId;
    payload.payeeAddress = payeeAddress;
    payload.payeeBranch = payeeBranch;
    payload.category = category;
    payload.detail = detail;
    payload.gross = gross;
    payload.vat = 0;
    payload.totalAmount = gross;
    payload.whtRate = rate;
    payload.tax = tax;
    payload.net = net;
    payload.paymentMethod = paymentMethod;
    payload.paymentStatus = paymentStatus;
    payload.actualPaidDate = formatDate(actualPaidDate);
    payload.whtCertificateNo = docNo;
    payload.taxFilingStatus = taxFilingStatus;
    payload.projectLink = projectLink;
    payload.remarks = remarks;

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
    payload.whtType = formType;
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
    const vat = vatChecked ? subtotal * 0.07 : 0;
    const wht = subtotal * (whtRate / 100);
    const net = subtotal + vat - wht;
    const owner = document.getElementById('docOwner').value;
    const retentionRate = parseFloat(document.getElementById('docRetentionRate').value) || 0;
    const retentionAmount = subtotal * (retentionRate / 100);
    const payoutAmount = subtotal - retentionAmount;

    const receivingBank = document.getElementById('docReceivingBank').value;
    const paymentStatus = document.getElementById('docPaymentStatus').value;
    const actualPaymentDate = document.getElementById('docActualPaymentDate').value || dateVal;
    const recordedBy = document.getElementById('docRecordedBy').value;
    const remarks = document.getElementById('docRemarks').value;

    payload.type = 'income';
    payload.recordDate = formatDate(new Date().toISOString().split('T')[0]);
    payload.date = formatDate(dateVal);
    payload.docNo = docNo;
    payload.invoiceNo = invoiceNo;
    payload.clientName = clientName;
    payload.clientTaxId = clientTaxId;
    payload.clientBranch = clientBranch;
    payload.clientAddress = clientAddress;
    payload.detail = detail;
    payload.subtotal = subtotal;
    payload.vat = vat;
    payload.gross = subtotal + vat;
    payload.whtRate = whtRate;
    payload.wht = wht;
    payload.net = net;
    payload.receivingBank = receivingBank;
    payload.paymentStatus = paymentStatus;
    payload.actualPaymentDate = formatDate(actualPaymentDate);
    payload.profitShare = `คนดีล: ${owner} (${100 - retentionRate}%)`;
    payload.recordedBy = recordedBy;
    payload.remarks = remarks;

    // Itemized breakdown for Google Sheets split rows
    payload.items = docItems.map(item => {
      const itemSubtotal = (item.qty || 0) * (item.price || 0);
      const itemVat = vatChecked ? itemSubtotal * 0.07 : 0;
      const itemWht = itemSubtotal * (whtRate / 100);
      const itemNet = itemSubtotal + itemVat - itemWht;
      const itemRetained = itemSubtotal * (retentionRate / 100);
      const itemPayout = itemSubtotal - itemRetained;

      return {
        desc: item.desc || "-",
        subtotal: itemSubtotal,
        vat: itemVat,
        gross: itemSubtotal + itemVat,
        whtRate: whtRate,
        wht: itemWht,
        net: itemNet,
        worker: item.worker || owner,
        profitShare: `คนทำงาน: ${item.worker || owner} (${100 - retentionRate}%)`
      };
    });
  }

  // Send to Sheets via POST
  const syncBtn = document.getElementById('btnSaveAndSyncDoc');
  const origHtml = syncBtn.innerHTML;
  syncBtn.textContent = '⏳ กำลังซิงค์ข้อมูลลงชีต...';
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
      alert(`🎉 บันทึกและซิงค์ข้อมูลลง Sheet เรียบร้อยแล้วแก!\nข้อความระบบ: ${res.message}`);
      
      // Save doc details to local history db
      const docRecord = {
        number: payload.docNo,
        type: currentDocType,
        date: payload.date,
        name: currentDocType === 'wht' ? payload.payeeName : payload.clientName,
        detail: payload.detail,
        amount: currentDocType === 'wht' ? payload.gross : payload.subtotal,
        status: 'synced',
        timestamp: new Date().toLocaleString(),
        invoiceNo: payload.invoiceNo || '-',
        clientBranch: payload.clientBranch || '-',
        clientAddress: payload.clientAddress || '-',
        payeeTaxId: payload.payeeTaxId || '-',
        payeeBranch: payload.payeeBranch || '-',
        payeeAddress: payload.payeeAddress || '-',
        category: payload.category || '-',
        vat: payload.vat || 0,
        wht: currentDocType === 'wht' ? payload.tax : payload.wht,
        net: payload.net,
        whtRate: payload.whtRate || 0,
        receivingBank: payload.receivingBank || '-',
        paymentStatus: payload.paymentStatus || '-',
        actualPaymentDate: payload.actualPaymentDate || '-',
        profitShare: payload.profitShare || '-',
        recordedBy: payload.recordedBy || '-',
        remarks: payload.remarks || '-',
        paymentMethod: payload.paymentMethod || '-',
        actualPaidDate: payload.actualPaidDate || '-',
        whtCertificateNo: payload.whtCertificateNo || '-',
        taxFilingStatus: payload.taxFilingStatus || '-',
        projectLink: payload.projectLink || '-',
        items: payload.items || null
      };

      dbDocs.unshift(docRecord);
      syncHistory.unshift({ docNo: payload.docNo, status: 'Success', time: new Date().toLocaleString() });

      saveData();
      setDocType(currentDocType);
    } else {
      alert(`❌ ซิงค์ข้อมูลล้มเหลว: ${res.message}`);
    }
  })
  .catch(err => {
    console.error(err);
    alert(`❌ เกิดข้อผิดพลาดเชื่อมต่อระบบ Apps Script: ${err.toString()}\n\nแต่บันทึกข้อมูลไว้ในเครื่องแบบ Offline (Pending) เรียบร้อยแล้วแก!`);
    
    // Save as pending locally
    const docRecord = {
      number: payload.docNo,
      type: currentDocType,
      date: payload.date,
      name: currentDocType === 'wht' ? payload.payeeName : payload.clientName,
      detail: payload.detail,
      amount: currentDocType === 'wht' ? payload.gross : payload.subtotal,
      status: 'pending',
      timestamp: new Date().toLocaleString(),
      invoiceNo: payload.invoiceNo || '-',
      clientBranch: payload.clientBranch || '-',
      clientAddress: payload.clientAddress || '-',
      payeeTaxId: payload.payeeTaxId || '-',
      payeeBranch: payload.payeeBranch || '-',
      payeeAddress: payload.payeeAddress || '-',
      category: payload.category || '-',
      vat: payload.vat || 0,
      wht: currentDocType === 'wht' ? payload.tax : payload.wht,
      net: payload.net,
      whtRate: payload.whtRate || 0,
      receivingBank: payload.receivingBank || '-',
      paymentStatus: payload.paymentStatus || '-',
      actualPaymentDate: payload.actualPaymentDate || '-',
      profitShare: payload.profitShare || '-',
      recordedBy: payload.recordedBy || '-',
      remarks: payload.remarks || '-',
      paymentMethod: payload.paymentMethod || '-',
      actualPaidDate: payload.actualPaidDate || '-',
      whtCertificateNo: payload.whtCertificateNo || '-',
      taxFilingStatus: payload.taxFilingStatus || '-',
      projectLink: payload.projectLink || '-',
      items: payload.items || null
    };

    dbDocs.unshift(docRecord);
    saveData();
    setDocType(currentDocType);
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
    alert('ไม่มีรายการค้างซิงค์สะสมจ้าแก!');
    return;
  }

  const scriptUrl = safeStorage.getItem('ghn168_script_url');
  const sheetId = safeStorage.getItem('ghn168_sheet_id');

  if (!scriptUrl || !sheetId) {
    alert('⚠️ ไม่พบการตั้งค่า Google Sheets API สำหรับการซิงค์แก!');
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
    syncBtn.textContent = '⏳ กำลังซิงค์คิว...';
  }

  let successCount = 0;
  let failCount = 0;

  function syncNext(index) {
    if (index >= pendingDocs.length) {
      alert(`🎉 ซิงค์ประวัติค้างส่งเสร็จสิ้น!\nสำเร็จ: ${successCount} รายการ\nล้มเหลว: ${failCount} รายการ`);
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
      docNo: doc.number,
      date: doc.date,
      detail: doc.detail,
    };

    if (doc.type === 'wht' || doc.type === 'expense') {
      payload.type = 'expense';
      payload.payeeName = doc.name;
      payload.gross = doc.baseAmount || doc.amount;
      payload.tax = doc.whtAmount || 0;
      payload.net = doc.amount;
      if (doc.payeeTaxId) payload.payeeTaxId = doc.payeeTaxId;
      if (doc.driveLink) payload.driveLink = doc.driveLink;
      if (doc.whtType) payload.whtType = doc.whtType;
      if (doc.projectLink) payload.projectLink = doc.projectLink;
    } else {
      payload.type = 'income';
      payload.clientName = doc.name;
      payload.subtotal = doc.amount;
      payload.vat = doc.amount * 0.07;
      payload.wht = 0;
      payload.net = doc.amount + payload.vat;
      if (doc.owner) {
        payload.owner = doc.owner;
        payload.retentionRate = doc.retentionRate;
        payload.retentionAmount = doc.retentionAmount;
        payload.payoutAmount = doc.payoutAmount;
      }
      if (doc.items) {
        payload.items = doc.items; // Restore items for sync
      }
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

      alert('🎉 นำเข้าข้อมูลสำรองสำเร็จแล้วแก!');
      loadConfiguration();
      loadData();
      renderDashboard();
    } catch (err) {
      alert('❌ ไฟล์สำรองข้อมูลไม่ถูกต้องหรือชำรุดจ้า: ' + err.toString());
    }
  };
  reader.readAsText(file);
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
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-secondary);">ยังไม่มีประวัติการบันทึกเอกสารแก</td></tr>`;
    } else {
      tbody.innerHTML = dbDocs.slice(0, 8).map(d => `
        <tr>
          <td>${d.date}</td>
          <td class="mono" style="font-weight: 700;">${d.number}</td>
          <td><span class="badge" style="background-color: ${d.type === 'wht' ? '#fee2e2' : (d.type === 'expense' ? '#ffedd5' : '#dcfce7')}; color: ${d.type === 'wht' ? '#991b1b' : (d.type === 'expense' ? '#c2410c' : '#166534')}; border: 1px solid var(--border-color);">${d.type.toUpperCase()}</span></td>
          <td>${escapeHtml(d.name)}</td>
          <td style="text-align:right; font-weight:700;">฿${d.amount.toLocaleString('th-TH', { minimumFractionDigits: 2 })}</td>
          <td style="text-align:center;">
            <span class="badge ${d.status}">${d.status === 'synced' ? 'ซิงค์แล้ว' : (d.status === 'pending_approval' ? 'รออนุมัติ' : 'ค้างส่ง')}</span>
          </td>
        </tr>
      `).join('');
    }
  }

  // Render shortcuts
  renderDashboardDocHubShortcuts();

  // Populate tax month filter and render summaries
  populateTaxFilterMonths();
  renderTaxAndProjectSummary();
}

// --- Document Hub Rendering ---
function renderDocHubList() {
  const container = document.getElementById('docHubListContainer');
  if (!container) return;

  if (docHubLinks.length === 0) {
    container.innerHTML = `<p style="text-align:center; color: var(--text-secondary); font-style:italic;">ยังไม่มีเอกสารที่อัปโหลดไว้จ้า</p>`;
    renderDashboardDocHubShortcuts();
    return;
  }

  container.innerHTML = docHubLinks.map((doc, idx) => `
    <div class="doc-hub-item">
      <div class="doc-hub-meta">
        <span class="doc-hub-name">${escapeHtml(doc.name)}</span>
        <div class="doc-hub-info">
          <span class="doc-hub-tag">${escapeHtml(doc.category)}</span>
          <span>📅 วันที่อัปเดต: ${doc.date}</span>
          <span>📝 ${escapeHtml(doc.desc)}</span>
        </div>
      </div>
      <div style="display:flex; gap: 8px;">
        <a href="${doc.url}" target="_blank" class="btn-primary" style="padding: 6px 12px; font-size:12px; box-shadow: 2px 2px 0 var(--border-color)">📂 เปิด Drive</a>
        <button class="btn-secondary" onclick="editDocHubItem(${idx})" style="padding: 6px 12px; font-size:12px; box-shadow: 2px 2px 0 var(--border-color); color: var(--text-primary); font-weight:700;">แก้ไข</button>
        <button class="btn-danger" onclick="deleteDocHubItem(${idx})" style="padding: 6px 12px; font-size:12px; box-shadow: 2px 2px 0 var(--border-color)">ลบ</button>
      </div>
    </div>
  `).join('');

  renderDashboardDocHubShortcuts();
}

window.deleteDocHubItem = function(index) {
  if (confirm('ยืนยันที่จะลบลิงก์เอกสารสำคัญรายการนี้ไหมแก?')) {
    docHubLinks.splice(index, 1);
    saveData();
    renderDocHubList();
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
      <a href="${doc.url}" target="_blank" class="btn-secondary" style="justify-content:flex-start; text-decoration:none; font-weight:700;">
        📂 ${escapeHtml(doc.name)} (${escapeHtml(doc.category)})
      </a>
    `;
  });

  // Default google drive link at the end
  html += `
    <a href="${escapeHtml(companyDriveUrl)}" target="_blank" class="btn-secondary" style="justify-content:flex-start; text-decoration:none; font-weight:700; border-style: dashed;">
      🌐 เข้าสู่ Google Drive หลักของบริษัท
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
        bahtStr += 'สิบ';
      } else if (pos % 6 === 1 && digit === 2) {
        bahtStr += 'ยี่สิบ';
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
    container.innerHTML = `<tr><td colspan="9" style="text-align:center; color: var(--text-secondary);">ยังไม่มีประวัติการบันทึกรายจ่ายแก</td></tr>`;
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

function calculateExpenseForm() {
  const baseEl = document.getElementById('expenseBaseAmount');
  if (!baseEl) return;
  const inputVal = parseFloat(baseEl.value) || 0;
  const priceType = document.getElementById('expensePriceType').value;
  const vatRate = parseFloat(document.getElementById('expenseVatSelect').value) || 0;
  const whtRate = parseFloat(document.getElementById('expenseWhtSelect').value) || 0;

  // Change Label according to priceType
  const labelAmount = document.getElementById('labelExpenseAmount');
  if (labelAmount) {
    if (priceType === 'include') {
      labelAmount.textContent = 'จำนวนเงินรวม VAT (Net/Gross)';
    } else {
      labelAmount.textContent = 'จำนวนเงินก่อน VAT (Gross)';
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

  const wht = base * (whtRate / 100);
  const net = base + vat - wht;

  document.getElementById('calcExpenseVat').textContent = `฿${vat.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById('calcExpenseWht').textContent = `฿${wht.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById('calcExpenseNet').textContent = `฿${net.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function saveExpense() {
  try {
    const dateVal = document.getElementById('expenseDate').value;
    if (!dateVal) {
      alert('⚠️ กรุณาระบุวันที่จ่ายเงินก่อนนะแก!');
      return;
    }
    // Parse date from YYYY-MM-DD to DD/MM/YYYY
    const dateParts = dateVal.split('-');
    const dateStr = dateParts.length === 3 ? `${dateParts[2]}/${dateParts[1]}/${dateParts[0]}` : '';

    let billNo = document.getElementById('expenseBillNo').value.trim();
    const payee = document.getElementById('expensePayee').value.trim();
    const payeeTaxId = document.getElementById('expensePayeeTaxId').value.trim();
    const payeeBranch = document.getElementById('expensePayeeBranch').value.trim() || '00000';
    const payeeAddress = document.getElementById('expensePayeeAddress').value.trim() || '-';
    let category = document.getElementById('expenseCategory').value;
    if (category === 'อื่นๆ') {
      category = document.getElementById('expenseCustomCategory').value.trim() || 'อื่นๆ';
    }
    const desc = document.getElementById('expenseDesc').value.trim();
    const inputVal = parseFloat(document.getElementById('expenseBaseAmount').value) || 0;
    const priceType = document.getElementById('expensePriceType').value;
    const vatRate = parseFloat(document.getElementById('expenseVatSelect').value) || 0;
    const whtRate = parseFloat(document.getElementById('expenseWhtSelect').value) || 0;
    const whtType = document.getElementById('expenseWhtType').value;
    const taxFilingStatus = document.getElementById('expenseTaxFilingStatus').value;
    const paymentMethod = document.getElementById('expensePaymentMethod').value;
    const paymentStatus = document.getElementById('expensePaymentStatus').value;
    const actualPaidDateVal = document.getElementById('expenseActualPaidDate').value;
    const actualPaidDate = actualPaidDateVal ? formatDate(actualPaidDateVal) : dateStr;
    const billUrl = document.getElementById('expenseBillUrl').value.trim();
    const remarks = document.getElementById('expenseRemarks').value.trim();
    const projectLink = document.getElementById('expenseProjectLink').value;

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

    const whtAmount = baseAmount * (whtRate / 100);
    const netAmount = baseAmount + vatAmount - whtAmount;

    // Generate PV number if empty
    if (!billNo) {
      const cleanDate = dateVal.replace(/-/g, '');
      const rand = Math.floor(100 + Math.random() * 900);
      billNo = `PV-${cleanDate}-${rand}`;
    }

    const isNew = editingDocIndex === null;

    // Check if HITL approval is required (Amount > 10,000 THB)
    if (netAmount > 10000 && paymentStatus === 'รออนุมัติจ่าย') {
      alert(`⚠️ รายการรายจ่ายนี้มียอดเงินโอนจ่ายจริง ฿${netAmount.toLocaleString('th-TH', { minimumFractionDigits: 2 })} เกิน 10,000 บาท\n\nระบบบันทึกสะสมรอการอนุมัติ (Pending Approval) ในเครื่องไว้เรียบร้อยแล้วแก รอให้ผู้มีอำนาจกดอนุมัติจ่าย (Approve) ก่อนจึงจะซิงค์ลงชีตจริงจ้า`);
      
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
        status: 'pending_approval',
        timestamp: new Date().toLocaleString(),
        payeeTaxId: payeeTaxId,
        payeeBranch: payeeBranch,
        payeeAddress: payeeAddress,
        taxFilingStatus: taxFilingStatus,
        paymentMethod: paymentMethod,
        paymentStatus: 'รออนุมัติจ่าย',
        actualPaidDate: actualPaidDate,
        whtCertificateNo: (whtRate > 0) ? billNo : '-',
        remarks: remarks
      };

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
      type: 'expense',
      recordDate: formatDate(new Date().toISOString().split('T')[0]),
      date: dateStr,
      docNo: billNo,
      payeeName: payee,
      payeeTaxId: payeeTaxId || '-',
      payeeBranch: payeeBranch || '00000',
      payeeAddress: payeeAddress || '-',
      category: category,
      detail: desc,
      gross: baseAmount,
      vat: vatAmount,
      totalAmount: baseAmount + vatAmount,
      whtRate: whtRate,
      tax: whtAmount,
      whtType: whtType,
      net: netAmount,
      paymentMethod: paymentMethod,
      paymentStatus: paymentStatus,
      actualPaidDate: actualPaidDate,
      whtCertificateNo: (whtRate > 0) ? billNo : '-',
      driveLink: billUrl || '-',
      taxFilingStatus: taxFilingStatus,
      projectLink: projectLink,
      remarks: remarks
    };

    // Send request
    if (scriptUrl && sheetId) {
      const submitBtn = document.getElementById('btnSubmitExpenseModal');
      const origHtml = submitBtn.innerHTML;
      submitBtn.textContent = '⏳ กำลังซิงค์...';
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
          alert(`🎉 บันทึกและซิงค์รายจ่ายลง Sheet สำเร็จแล้วแก!\nข้อความ: ${res.message}`);
          
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
            status: 'synced',
            timestamp: new Date().toLocaleString(),
            payeeTaxId: payeeTaxId,
            payeeBranch: payeeBranch,
            payeeAddress: payeeAddress,
            taxFilingStatus: taxFilingStatus,
            paymentMethod: paymentMethod,
            paymentStatus: paymentStatus,
            actualPaidDate: actualPaidDate,
            whtCertificateNo: (whtRate > 0) ? billNo : '-',
            remarks: remarks
          };

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
          alert(`❌ ซิงค์ล้มเหลว: ${res.message}`);
          submitBtn.innerHTML = origHtml;
          submitBtn.disabled = false;
        }
      })
      .catch(err => {
        console.error(err);
        alert(`❌ เกิดข้อผิดพลาดเชื่อมต่อสคริปต์: ${err.toString()}\n\nแต่บันทึกข้อมูลแบบออฟไลน์ (Pending) ไว้ในเครื่องเรียบร้อยแล้วแก!`);
        
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
          remarks: remarks
        };

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
      alert('💡 ไม่พบการเชื่อมต่อชีต บันทึกประวัติออฟไลน์ลงเครื่องไว้ก่อนนะแก');
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
        remarks: remarks
      };

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
    alert('❌ บันทึกรายจ่ายล้มเหลวเนื่องจากข้อผิดพลาด: ' + err.toString());
  }
}

function deleteExpense(index) {
  if (confirm('ต้องการลบประวัติรายจ่ายรายการนี้ใช่ไหมแก? (ลบเฉพาะในตัวแอปน้า)')) {
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
  
  document.getElementById('pvPrintNo').textContent = doc.number;
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
window.editExpense = editExpense;
window.deleteExpense = deleteExpense;

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
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: var(--text-secondary);">ไม่มีโครงการที่มีธุรกรรมในเดือนนี้แก</td></tr>`;
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

  if (!confirm(`ต้องการอนุมัติรายการจ่ายเงินจำนวน ฿${doc.amount.toLocaleString('th-TH', { minimumFractionDigits: 2 })} สำหรับ "${doc.name}" ใช่ไหมแก?`)) {
    return;
  }

  const scriptUrl = safeStorage.getItem('ghn168_script_url');
  const sheetId = safeStorage.getItem('ghn168_sheet_id');

  if (scriptUrl && sheetId) {
    doc.status = 'pending';
    renderExpenseList();

    const payload = {
      spreadsheetId: sheetId,
      type: 'expense',
      date: doc.date,
      docNo: doc.number,
      payeeName: doc.name,
      payeeTaxId: doc.payeeTaxId || '-',
      detail: doc.desc ? `${doc.category}: ${doc.desc}` : doc.category,
      gross: doc.baseAmount || doc.amount,
      vat: doc.vatAmount || 0,
      tax: doc.whtAmount || 0,
      net: doc.amount,
      driveLink: doc.driveLink || '-',
      whtType: doc.whtType || 'none',
      projectLink: doc.projectLink || ''
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
        alert('🎉 อนุมัติจ่ายและซิงค์ข้อมูลลง Google Sheets เรียบร้อยแล้วแก!');
        doc.status = 'synced';
      } else {
        alert(`❌ ซิงค์ข้อมูลล้มเหลว: ${res.message}\nรายการบันทึกสถานะเป็นค้างส่ง (Pending) จ้า`);
        doc.status = 'pending';
      }
      saveData();
      renderExpenseList();
      renderDashboard();
    })
    .catch(err => {
      console.error(err);
      alert(`❌ อนุมัติแล้วแต่เชื่อมต่อสคริปต์ล้มเหลว: ${err.toString()}\nเปลี่ยนสถานะเป็นค้างส่ง (Pending) ไว้ในเครื่องเพื่อซิงค์ภายหลังนะแก`);
      doc.status = 'pending';
      saveData();
      renderExpenseList();
      renderDashboard();
    });
  } else {
    alert('💡 ไม่พบค่าสคริปต์เชื่อมต่อ เปลี่ยนสถานะเป็นค้างส่ง (Pending) ไว้ในเครื่องแล้วแก');
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
    body.innerHTML = `<tr><td colspan="9" style="text-align:center; color: var(--text-secondary); padding:20px;">ไม่มีข้อมูลเงินสดย่อยจ้าแก</td></tr>`;
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
      alert('⚠️ กรุณาระบุวันที่ก่อนนะแก!');
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
      alert('⚠️ ยอดจ่ายต้องมากกว่า 0 บาทนะแก!');
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
    alert('❌ บันทึกเงินสดย่อยล้มเหลว: ' + err.toString());
  }
}

function syncPettyCash(index) {
  const doc = pettyCashDb[index];
  if (!doc) return;
  const scriptUrl = safeStorage.getItem('ghn168_script_url');
  const sheetId = safeStorage.getItem('ghn168_sheet_id');
  if (!scriptUrl || !sheetId) {
    alert('⚠️ กรุณาตั้งค่าเชื่อมต่อ Google Sheets ก่อนนะแก!');
    return;
  }
  const payload = {
    spreadsheetId: sheetId, type: 'petty_cash', voucherNo: doc.voucherNo, date: doc.date,
    requester: doc.requester, category: doc.category, detail: doc.detail, amountPaid: doc.amountPaid,
    balance: doc.balance, approver: doc.approver, receiptUrl: doc.receiptUrl, remarks: doc.remarks
  };
  fetch(scriptUrl, {
    method: 'POST', mode: 'cors', headers: { 'Content-Type': 'text/plain' }, body: JSON.stringify(payload)
  })
  .then(res => res.json())
  .then(res => {
    if (res.status === 'success') {
      alert('🎉 ซิงค์ข้อมูลเงินสดย่อยสำเร็จแล้วแก!');
      doc.status = 'synced';
      saveData();
      renderPettyCash();
    } else {
      alert(`❌ ซิงค์ล้มเหลว: ${res.message}`);
    }
  })
  .catch(err => {
    console.error(err);
    alert(`❌ เกิดข้อผิดพลาดเชื่อมต่อสคริปต์: ${err.toString()}`);
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
  if (confirm('ต้องการลบรายการเงินสดย่อยนี้ใช่ไหมแก?')) {
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
    body.innerHTML = `<tr><td colspan="10" style="text-align:center; color: var(--text-secondary); padding:20px;">ไม่มีข้อมูลเงินเดือนจ้าแก</td></tr>`;
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
      alert('⚠️ กรุณาเลือกพนักงานก่อนนะแก!');
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
    alert('❌ บันทึกเงินเดือนล้มเหลว: ' + err.toString());
  }
}

function syncPayroll(index) {
  const doc = payrollDb[index];
  if (!doc) return;
  const scriptUrl = safeStorage.getItem('ghn168_script_url');
  const sheetId = safeStorage.getItem('ghn168_sheet_id');
  if (!scriptUrl || !sheetId) {
    alert('⚠️ กรุณาตั้งค่าเชื่อมต่อ Google Sheets ก่อนนะแก!');
    return;
  }
  const payload = {
    spreadsheetId: sheetId, type: 'payroll', payrollId: doc.payrollId, employeeId: doc.employeeId,
    employeeName: doc.employeeName, employeeTaxId: doc.employeeTaxId, baseSalary: doc.baseSalary,
    allowances: doc.allowances, totalEarnings: doc.totalEarnings, ssfDeduction: doc.ssfDeduction,
    whtDeduction: doc.whtDeduction, otherDeductions: doc.otherDeductions, netPay: doc.netPay,
    bankAccount: doc.bankAccount, status: doc.status, paySlipUrl: doc.paySlipUrl
  };
  fetch(scriptUrl, {
    method: 'POST', mode: 'cors', headers: { 'Content-Type': 'text/plain' }, body: JSON.stringify(payload)
  })
  .then(res => res.json())
  .then(res => {
    if (res.status === 'success') {
      alert('🎉 ซิงค์ข้อมูลเงินเดือนสำเร็จแล้วแก!');
      doc.syncStatus = 'synced';
      saveData();
      renderPayroll();
    } else {
      alert(`❌ ซิงค์ล้มเหลว: ${res.message}`);
    }
  })
  .catch(err => {
    console.error(err);
    alert(`❌ เกิดข้อผิดพลาดเชื่อมต่อสคริปต์: ${err.toString()}`);
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
  if (confirm('ต้องการลบประวัติรอบจ่ายเงินเดือนนี้ใช่ไหมแก?')) {
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
    if (targetLower.includes('kbank') && (docLower.includes('kbank') || docLower.includes('k-bank') || docLower.includes('kasikorn'))) return true;
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
    body.innerHTML = `<tr><td colspan="9" style="text-align:center; color: var(--text-secondary); padding:20px;">ไม่มีข้อมูลการกระทบยอดธนาคารจ้าแก</td></tr>`;
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
      alert('⚠️ กรุณาระบุงวดประจำเดือนก่อนนะแก!');
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
    alert('❌ บันทึกงบกระทบยอดล้มเหลว: ' + err.toString());
  }
}

function syncBankRec(index) {
  const doc = bankRecDb[index];
  if (!doc) return;
  const scriptUrl = safeStorage.getItem('ghn168_script_url');
  const sheetId = safeStorage.getItem('ghn168_sheet_id');
  if (!scriptUrl || !sheetId) {
    alert('⚠️ กรุณาตั้งค่าเชื่อมต่อ Google Sheets ก่อนนะแก!');
    return;
  }
  const payload = {
    spreadsheetId: sheetId, type: 'bank_rec', reconciliationId: doc.reconciliationId, period: doc.period,
    bankAccount: doc.bankAccount, statementBalance: doc.statementBalance, bookBalance: doc.bookBalance,
    depositInTransit: doc.depositInTransit, outstandingCheques: doc.outstandingCheques,
    bankChargesNotRecorded: doc.bankChargesNotRecorded, adjustedStatementBalance: doc.adjustedStatementBalance,
    adjustedBookBalance: doc.adjustedBookBalance, difference: doc.difference, reconciledBy: doc.reconciledBy
  };
  fetch(scriptUrl, {
    method: 'POST', mode: 'cors', headers: { 'Content-Type': 'text/plain' }, body: JSON.stringify(payload)
  })
  .then(res => res.json())
  .then(res => {
    if (res.status === 'success') {
      alert('🎉 ซิงค์ข้อมูลกระทบยอดธนาคารสำเร็จแล้วแก!');
      doc.syncStatus = 'synced';
      saveData();
      renderBankRec();
    } else {
      alert(`❌ ซิงค์ล้มเหลว: ${res.message}`);
    }
  })
  .catch(err => {
    console.error(err);
    alert(`❌ เกิดข้อผิดพลาดเชื่อมต่อสคริปต์: ${err.toString()}`);
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
  if (confirm('ต้องการลบประวัติงบกระทบยอดรายการนี้ใช่ไหมแก?')) {
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
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-secondary); padding: 20px;">กรุณาเลือกงวดประจำเดือนก่อนนะแก!</td></tr>`;
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
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-secondary); padding: 20px;">ไม่มีข้อมูลภาษีหัก ณ ที่จ่าย (WHT) สำหรับช่วงเวลาและแบบยื่นที่ระบุจ้าแก</td></tr>`;
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
    alert('⚠️ กรุณาเลือกงวดประจำเดือนก่อนนะแก!');
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
    alert('💡 ไม่มีรายการภาษีสำหรับดาวน์โหลดในช่วงเวลาและแบบยื่นที่เลือกนะแก!');
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
  alert(`🎉 ดาวน์โหลดไฟล์นำส่งสำเร็จแล้วแก!\nชื่อไฟล์: ${filename}`);
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
          
          let scale = 1;
          if (panelWidth < targetWidth) {
            scale = panelWidth / targetWidth;
            // Cap the minimum scale to 0.4 on extremely small screens to keep it readable
            if (scale < 0.4) scale = 0.4;
          }
          
          previewPanel.style.setProperty('--preview-scale-factor', scale);
        }
      } catch (err) {
        alert(`🔴 ERROR IN RESIZE OBSERVER:\n${err.message}\n${err.stack}`);
      }
    });

    resizeObserver.observe(previewPanel);
  } catch (err) {
    alert(`🔴 ERROR IN setupPreviewAutoScaling:\n${err.message}\n${err.stack}`);
  }
}

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
