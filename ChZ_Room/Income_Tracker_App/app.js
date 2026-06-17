document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initNavigation();
  initFormDefaults();
  loadSettings();
  renderHistoryTable();
  initDocumentGenerator();
  
  // Bind events
  document.getElementById('jsFormGeneral').addEventListener('submit', (e) => handleFormSubmit(e, 'general'));
  document.getElementById('jsFormExpense').addEventListener('submit', (e) => handleFormSubmit(e, 'expense'));
  document.getElementById('jsFormGrab').addEventListener('submit', (e) => handleFormSubmit(e, 'grab'));
  document.getElementById('settingsForm').addEventListener('submit', saveSettings);
  
  // Bind dashboard events
  const btnRefreshDashboard = document.getElementById('btnRefreshDashboard');
  if (btnRefreshDashboard) {
    btnRefreshDashboard.addEventListener('click', () => refreshDashboardData(false));
  }
  
  // Bind fixed cost events
  const btnAddFixedCost = document.getElementById('btnAddFixedCost');
  if (btnAddFixedCost) {
    btnAddFixedCost.addEventListener('click', addFixedCost);
  }
  
  const fixedCostSelect = document.getElementById('fixedCostSelect');
  if (fixedCostSelect) {
    fixedCostSelect.addEventListener('change', handleFixedCostSelectChange);
  }
  
  const btnSubmitAllFixedCosts = document.getElementById('btnSubmitAllFixedCosts');
  if (btnSubmitAllFixedCosts) {
    btnSubmitAllFixedCosts.addEventListener('click', handleBatchFixedCostsSubmit);
  }
  
  // Mobile menu toggle
  const menuToggle = document.getElementById('menuToggle');
  const sidebar = document.getElementById('sidebar');
  if (menuToggle && sidebar) {
    menuToggle.addEventListener('click', () => {
      sidebar.classList.toggle('mobile-open');
    });
  }
  
  // Link in setup guide to open this readme file directly
  const readmeBtn = document.getElementById('readmeLinkBtn');
  if (readmeBtn) {
    readmeBtn.addEventListener('click', (e) => {
      e.preventDefault();
      alert('คู่มือการตั้งค่าสคริปต์ Google Sheets และโค้ดอยู่ในไฟล์ README.md ภายในโฟลเดอร์ของโปรเจกต์นี้เลยแก!');
    });
  }
});

// --- 1. Theme Management ---
function initTheme() {
  const themeToggle = document.getElementById('darkModeToggle');
  const mobileThemeToggle = document.getElementById('mobileThemeToggle');
  const savedTheme = localStorage.getItem('income_tracker_theme') || 'dark'; // Default to dark mode (Sunset Glow)
  
  if (savedTheme === 'dark') {
    document.documentElement.classList.add('dark-theme');
  } else {
    document.documentElement.classList.remove('dark-theme');
  }
  
  const toggleAction = () => {
    const isDark = document.documentElement.classList.toggle('dark-theme');
    localStorage.setItem('income_tracker_theme', isDark ? 'dark' : 'light');
  };
  
  if (themeToggle) themeToggle.addEventListener('click', toggleAction);
  if (mobileThemeToggle) mobileThemeToggle.addEventListener('click', toggleAction);
}

// --- 2. Navigation System ---
function initNavigation() {
  const menuItems = document.querySelectorAll('.menu-item');
  menuItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const targetView = item.getAttribute('data-view');
      switchToView(targetView);
      
      // Auto-close sidebar on mobile after clicking
      const sidebar = document.getElementById('sidebar');
      if (sidebar) {
        sidebar.classList.remove('mobile-open');
      }
    });
  });
}

function switchToView(viewId) {
  // Hide all panels
  document.querySelectorAll('.view-panel').forEach(panel => {
    panel.classList.remove('active');
  });
  
  // Show target panel
  const targetPanel = document.getElementById(viewId);
  if (targetPanel) {
    targetPanel.classList.add('active');
  }
  
  // Update menu active states
  document.querySelectorAll('.menu-item').forEach(item => {
    if (item.getAttribute('data-view') === viewId) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });
  
  // Update headers dynamically
  const viewTitle = document.getElementById('viewTitleHeader');
  const viewSubtitle = document.getElementById('viewSubtitleHeader');
  
  if (viewId === 'record-view') {
    viewTitle.textContent = 'บันทึกรายการ';
    viewSubtitle.textContent = 'เลือกประเภทรายการ กรอกรายละเอียด และกดบันทึกเพื่อคีย์ลงชีตได้เลยแก';
  } else if (viewId === 'dashboard-view') {
    viewTitle.textContent = 'แดชบอร์ดสรุปผลทางการเงิน';
    viewSubtitle.textContent = 'วิเคราะห์ข้อมูลรายรับ รายจ่าย กำไร และเงินเก็บ 10% สะสมประจำปี 2026';
    refreshDashboardData(false);
  } else if (viewId === 'history-view') {
    viewTitle.textContent = 'ประวัติการบันทึกข้อมูล';
    viewSubtitle.textContent = 'รายการทั้งหมดที่บันทึกผ่านแอปนี้ เก็บประวัติไว้บนเบราว์เซอร์ของแกจ้า';
  } else if (viewId === 'settings-view') {
    viewTitle.textContent = 'การตั้งค่าเชื่อมต่อระบบ';
    viewSubtitle.textContent = 'ผูกแอปเข้ากับสิทธิ์ Google Sheets ของแกเพื่อส่งข้อมูลธุรกรรมลงตารางโดยตรง';
  } else if (viewId === 'document-view') {
    viewTitle.textContent = 'ออกเอกสารการเงิน';
    viewSubtitle.textContent = 'สร้างและพิมพ์ใบเสนอราคา ใบวางบิล และใบเสร็จรับเงินเป็น PDF ในรูปแบบมาตรฐานแก';
  }

  // Manage document title dynamic changes for professional PDF export names
  if (viewId === 'document-view') {
    updateDynamicDocTitle();
  } else {
    document.title = 'ระบบบันทึกรายรับของเก่ง | Income Tracker';
  }
  
  // Close sidebar on mobile
  const sidebar = document.getElementById('sidebar');
  if (sidebar) {
    sidebar.classList.remove('mobile-open');
  }
}

// --- 3. Form Initialization & Type Switching ---
function initFormDefaults() {
  const today = new Date();
  
  // Format Date YYYY-MM-DD
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, '0');
  const dd = String(today.getDate()).padStart(2, '0');
  const dateStr = `${yyyy}-${mm}-${dd}`;
  
  // Format Time HH:MM
  const hh = String(today.getHours()).padStart(2, '0');
  const min = String(today.getMinutes()).padStart(2, '0');
  const timeStr = `${hh}:${min}`;
  
  // Apply to General Form
  document.getElementById('genDate').value = dateStr;
  document.getElementById('genTime').value = timeStr;
  
  // Apply to Expense Form
  const expDateEl = document.getElementById('expDate');
  const expTimeEl = document.getElementById('expTime');
  if (expDateEl) expDateEl.value = dateStr;
  if (expTimeEl) expTimeEl.value = timeStr;
  
  // Apply to Grab Form
  document.getElementById('grabDate').value = dateStr;
  document.getElementById('grabTime').value = timeStr;
}

function switchIncomeType(type) {
  const formGeneral = document.getElementById('formGeneral');
  const formGrab = document.getElementById('formGrab');
  const formExpense = document.getElementById('formExpense');
  const btnSelectGeneral = document.getElementById('btnSelectGeneral');
  const btnSelectGrab = document.getElementById('btnSelectGrab');
  const btnSelectExpense = document.getElementById('btnSelectExpense');
  
  if (type === 'general') {
    formGeneral.style.display = 'block';
    if (formExpense) formExpense.style.display = 'none';
    formGrab.style.display = 'none';
    btnSelectGeneral.classList.add('active');
    if (btnSelectExpense) btnSelectExpense.classList.remove('active');
    btnSelectGrab.classList.remove('active');
  } else if (type === 'expense') {
    formGeneral.style.display = 'none';
    if (formExpense) formExpense.style.display = 'block';
    formGrab.style.display = 'none';
    btnSelectGeneral.classList.remove('active');
    if (btnSelectExpense) btnSelectExpense.classList.add('active');
    btnSelectGrab.classList.remove('active');
  } else {
    formGeneral.style.display = 'none';
    if (formExpense) formExpense.style.display = 'none';
    formGrab.style.display = 'block';
    btnSelectGeneral.classList.remove('active');
    if (btnSelectExpense) btnSelectExpense.classList.remove('active');
    btnSelectGrab.classList.add('active');
  }
  
  // Recalculate defaults when switching just in case time moved
  initFormDefaults();
}

// --- 4. Settings Management ---
function loadSettings() {
  const scriptUrl = localStorage.getItem('income_tracker_gas_url');
  const grabSheetId = localStorage.getItem('income_tracker_grab_sheet_id') || '';
  const generalSheetId = localStorage.getItem('income_tracker_general_sheet_id') || '';
  
  if (scriptUrl) {
    document.getElementById('scriptUrlInput').value = scriptUrl;
    document.getElementById('connectionWarning').style.display = 'none';
  } else {
    document.getElementById('connectionWarning').style.display = 'block';
  }
  
  document.getElementById('grabSheetIdInput').value = grabSheetId;
  document.getElementById('generalSheetIdInput').value = generalSheetId;
  
  // Render fixed costs table and dropdown
  renderFixedCostsTable();
  populateFixedCostDropdown();
}

function saveSettings(e) {
  e.preventDefault();
  
  const scriptUrl = document.getElementById('scriptUrlInput').value.trim();
  const grabSheetId = document.getElementById('grabSheetIdInput').value.trim();
  const generalSheetId = document.getElementById('generalSheetIdInput').value.trim();
  
  localStorage.setItem('income_tracker_gas_url', scriptUrl);
  localStorage.setItem('income_tracker_grab_sheet_id', grabSheetId);
  localStorage.setItem('income_tracker_general_sheet_id', generalSheetId);
  
  // Hide warning banner since we have a URL now
  document.getElementById('connectionWarning').style.display = 'none';
  
  showPopup(true, 'บันทึกการตั้งค่าสำเร็จแล้ว!', 'ผูกแอปเข้ากับ Google Sheets เรียบร้อยแล้วแก ลองทดสอบคีย์ข้อมูลและกดบันทึกเพื่อตรวจสอบผลลัพธ์ได้เลย!');
}

// --- 5. Data Transmission to Google Sheets ---
async function handleFormSubmit(e, type) {
  e.preventDefault();
  
  const scriptUrl = localStorage.getItem('income_tracker_gas_url');
  const grabSheetId = localStorage.getItem('income_tracker_grab_sheet_id') || '';
  const generalSheetId = localStorage.getItem('income_tracker_general_sheet_id') || '';
  
  // Prepare payload
  let payload = {
    type: type,
    spreadsheetId: (type === 'general' || type === 'expense') ? generalSheetId : grabSheetId,
    timestamp: new Date().toISOString()
  };
  
  if (type === 'general') {
    const rawDate = document.getElementById('genDate').value; // YYYY-MM-DD
    const dateFormatted = formatDateToDMY(rawDate);
    
    payload.date = dateFormatted;
    payload.time = document.getElementById('genTime').value;
    payload.genDesc = document.getElementById('genDesc').value.trim();
    payload.hasTaxWithholding = document.getElementById('genTaxWithholding').checked;
    
    const amountInput = document.getElementById('genAmount').value.trim();
    if (amountInput.startsWith('=')) {
      payload.amount = amountInput;
    } else if (/[+\-*/]/.test(amountInput)) {
      payload.amount = '=' + amountInput;
    } else {
      payload.amount = parseFloat(amountInput) || 0;
    }
  } else if (type === 'expense') {
    const rawDate = document.getElementById('expDate').value; // YYYY-MM-DD
    const dateFormatted = formatDateToDMY(rawDate);
    
    payload.date = dateFormatted;
    payload.time = document.getElementById('expTime').value;
    payload.expDesc = document.getElementById('expDesc').value.trim();
    
    const amountInput = document.getElementById('expAmount').value.trim();
    if (amountInput.startsWith('=')) {
      payload.amount = amountInput;
    } else if (/[+\-*/]/.test(amountInput)) {
      payload.amount = '=' + amountInput;
    } else {
      payload.amount = parseFloat(amountInput) || 0;
    }
  } else {
    const rawDate = document.getElementById('grabDate').value; // YYYY-MM-DD
    const dateFormatted = formatDateToDMY(rawDate);
    
    payload.date = dateFormatted;
    payload.time = document.getElementById('grabTime').value;
    
    // Clean battery input (e.g. "100-50" or "50")
    let batteryInput = document.getElementById('grabBattery').value.trim();
    payload.battery = batteryInput;
    
    payload.distance = parseFloat(document.getElementById('grabDistance').value);
    payload.amount = parseFloat(document.getElementById('grabAmount').value);
    payload.tip = parseFloat(document.getElementById('grabTip').value || 0);
  }
  
  // Submit state
  let submitBtn;
  if (type === 'general') {
    submitBtn = document.getElementById('btnSubmitGeneral');
  } else if (type === 'expense') {
    submitBtn = document.getElementById('btnSubmitExpense');
  } else {
    submitBtn = document.getElementById('btnSubmitGrab');
  }
  
  const originalBtnHtml = submitBtn.innerHTML;
  submitBtn.disabled = true;
  submitBtn.innerHTML = `
    <svg class="btn-svg-icon spin-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" style="animation: rotate 1s linear infinite;">
      <circle cx="12" cy="12" r="10" stroke="rgba(255,255,255,0.2)"></circle>
      <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
    </svg>
    กำลังส่งข้อมูล...
  `;
  
  // Add rotation animation style on the fly if not in CSS
  if (!document.getElementById('spinnerStyle')) {
    const style = document.createElement('style');
    style.id = 'spinnerStyle';
    style.innerHTML = `@keyframes rotate { 100% { transform: rotate(360deg); } }`;
    document.head.appendChild(style);
  }

  // 1. If no URL settings, save locally only
  if (!scriptUrl) {
    saveToLocalHistory(payload, 'local_only');
    showPopup(false, 'บันทึกเข้าเครื่องชั่วคราว!', 'แกยังไม่ได้ตั้งค่า Web App URL ในหน้า Settings ข้อมูลจึงถูกบันทึกไว้บนบราวเซอร์ของเครื่องนี้เท่านั้น หากต้องการให้ข้อมูลเข้า Google Sheets อย่าลืมไปใส่ลิงก์เชื่อมต่อนะแก');
    
    // Reset form and btn
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalBtnHtml;
    resetFormInputs(type);
    return;
  }
  
  // 2. Perform API Post to Google Apps Script
  try {
    // We send as text/plain to prevent CORS preflight OPTIONS requests, which GAS web apps do not handle properly
    const response = await fetch(scriptUrl, {
      method: 'POST',
      mode: 'cors',
      headers: {
        'Content-Type': 'text/plain;charset=utf-8'
      },
      body: JSON.stringify(payload)
    });
    
    const result = await response.json();
    
    if (result.status === 'success') {
      saveToLocalHistory(payload, 'synced');
      showPopup(true, 'บันทึกข้อมูลสำเร็จ! ฿', result.message || 'ข้อมูลถูกบันทึกและซิงค์ลง Google Sheets เรียบร้อยแล้วแก!');
      resetFormInputs(type);
    } else {
      saveToLocalHistory(payload, 'failed');
      showPopup(false, 'เกิดข้อผิดพลาด ⚠', result.message || 'ไม่สามารถส่งข้อมูลลงตารางได้ เนื่องจากเกิดข้อผิดพลาดทางเทคนิคที่ Google Sheets หรือสคริปต์เชื่อมต่อ โปรดตรวจสอบสถานะการทำงานอีกครั้ง');
    }
  } catch (err) {
    console.error('Fetch Error:', err);
    saveToLocalHistory(payload, 'failed');
    showPopup(false, 'ส่งข้อมูลไม่สำเร็จ ❌', 'ไม่สามารถติดต่อเซิร์ฟเวอร์ Google Apps Script ได้ โปรดตรวจสอบความถูกต้องของลิงก์ URL หรือสถานะการเชื่อมต่ออินเทอร์เน็ตของแกด้วยนะ');
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalBtnHtml;
  }
}

// --- 6. Helper Utilities ---
function formatDateToDMY(dateStr) {
  if (!dateStr) return '';
  const parts = dateStr.split('-'); // YYYY-MM-DD
  if (parts.length !== 3) return dateStr;
  return `${parts[2]}/${parts[1]}/${parts[0]}`; // DD/MM/YYYY
}

function resetFormInputs(type) {
  if (type === 'general') {
    document.getElementById('genDesc').value = '';
    document.getElementById('genAmount').value = '';
  } else if (type === 'expense') {
    document.getElementById('expDesc').value = '';
    document.getElementById('expAmount').value = '';
    const fixedCostSelect = document.getElementById('fixedCostSelect');
    if (fixedCostSelect) fixedCostSelect.value = '';
  } else {
    document.getElementById('grabBattery').value = '';
    document.getElementById('grabDistance').value = '';
    document.getElementById('grabAmount').value = '';
    document.getElementById('grabTip').value = '0';
  }
  initFormDefaults();
}

// --- 7. History Log Operations (localStorage) ---
function saveToLocalHistory(data, syncStatus) {
  let history = JSON.parse(localStorage.getItem('income_tracker_history')) || [];
  
  // Format listing details
  let detail = '';
  let displayAmount = data.amount;
  let typeDisplay = '';
  
  if (data.type === 'general') {
    detail = `${data.genDesc || 'ไม่มีรายละเอียด'}`;
    typeDisplay = 'รายรับ Feltz Studio';
  } else if (data.type === 'expense') {
    detail = `${data.expDesc || 'ไม่มีรายละเอียด'}`;
    typeDisplay = 'รายจ่าย Feltz Studio';
  } else {
    detail = `Grab - วิ่ง ${data.distance} กม. (แบตใช้ ${data.battery}%) ${data.tip > 0 ? `+ ทิป ${data.tip} บาท` : ''}`;
    typeDisplay = 'รายได้วิ่ง Grab';
    displayAmount = data.amount + (data.tip || 0);
  }
  
  const newEntry = {
    dateTime: `${data.date} ${data.time}`,
    type: typeDisplay,
    detail: detail,
    amount: displayAmount,
    status: syncStatus,
    timestamp: new Date().getTime()
  };
  
  // Keep up to 100 entries
  history.unshift(newEntry);
  if (history.length > 100) {
    history.pop();
  }
  
  localStorage.setItem('income_tracker_history', JSON.stringify(history));
  renderHistoryTable();
}

function renderHistoryTable() {
  const tableBody = document.getElementById('historyTableBody');
  if (!tableBody) return;
  
  const history = JSON.parse(localStorage.getItem('income_tracker_history')) || [];
  
  if (history.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="5" class="empty-row-msg">ไม่มีประวัติการบันทึกข้อมูล</td>
      </tr>
    `;
    return;
  }
  
  tableBody.innerHTML = history.map(row => {
    let statusBadge = '';
    if (row.status === 'synced') {
      statusBadge = '<span class="badge success">ซิงค์เข้าระบบแล้ว</span>';
    } else if (row.status === 'local_only') {
      statusBadge = '<span class="badge warn">บันทึกในเครื่องชั่วคราว</span>';
    } else {
      statusBadge = '<span class="badge error">เกิดข้อผิดพลาด</span>';
    }
    
    const isExpense = row.type.indexOf('รายจ่าย') !== -1;
    let amountDisplay = '';
    const amountVal = row.amount;
    if (typeof amountVal === 'string' && amountVal.indexOf('=') === 0) {
      try {
        const sum = amountVal.substring(1).split('+').map(n => parseFloat(n) || 0).reduce((a, b) => a + b, 0);
        amountDisplay = `${isExpense ? '-' : ''}฿${sum.toFixed(2)}`;
      } catch (e) {
        amountDisplay = amountVal;
      }
    } else {
      amountDisplay = `${isExpense ? '-' : ''}฿${parseFloat(amountVal || 0).toFixed(2)}`;
    }
    
    const amountStyle = isExpense 
      ? 'color: var(--alert-error-text); font-weight: 700;' 
      : 'color: var(--alert-success-text); font-weight: 700;';
    
    return `
      <tr>
        <td class="mono-cell">${escapeHtml(row.dateTime)}</td>
        <td>${escapeHtml(row.type)}</td>
        <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(row.detail)}</td>
        <td class="mono-cell" style="${amountStyle}">${amountDisplay}</td>
        <td>${statusBadge}</td>
      </tr>
    `;
  }).join('');
}

function clearHistoryLog() {
  if (confirm('คุณแน่ใจใช่ไหมว่าต้องการล้างประวัติการคีย์ข้อมูลในเครื่องทั้งหมด? (ข้อมูลที่บันทึกลง Google Sheets แล้วจะไม่หาย)')) {
    localStorage.removeItem('income_tracker_history');
    renderHistoryTable();
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.toString()
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// --- 8. Status Popup Dialog Handling ---
function showPopup(isSuccess, title, message) {
  const popup = document.getElementById('statusPopup');
  const iconArea = document.getElementById('popupIconArea');
  const popupTitle = document.getElementById('popupTitle');
  const popupMessage = document.getElementById('popupMessage');
  
  if (!popup) return;
  
  popupTitle.textContent = title;
  popupMessage.textContent = message;
  
  if (isSuccess) {
    iconArea.className = 'popup-icon-area success';
    iconArea.innerHTML = `
      <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    `;
  } else {
    iconArea.className = 'popup-icon-area error';
    iconArea.innerHTML = `
      <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    `;
  }
  
  popup.style.display = 'flex';
}

function closePopup() {
  const popup = document.getElementById('statusPopup');
  if (popup) {
    popup.style.display = 'none';
  }
}

function openReadmeLink() {
  alert('ข้อมูลการตั้งค่าและสคริปต์สามารถคัดลอกได้จากไฟล์ README.md ภายในโฟลเดอร์ของโปรเจกต์นี้เลยจ้า!');
}

// --- Fixed Cost List Operations (localStorage: income_tracker_fixed_costs) ---

function getFixedCosts() {
  return JSON.parse(localStorage.getItem('income_tracker_fixed_costs')) || [];
}

function saveFixedCosts(fixedCosts) {
  localStorage.setItem('income_tracker_fixed_costs', JSON.stringify(fixedCosts));
}

function addFixedCost() {
  const descInput = document.getElementById('newFixedCostDesc');
  const amountInput = document.getElementById('newFixedCostAmount');
  
  if (!descInput || !amountInput) return;
  
  const desc = descInput.value.trim();
  const amount = parseFloat(amountInput.value);
  
  if (!desc) {
    alert('กรุณากรอกคำอธิบายรายการ Fix Cost ด้วยนะแก');
    return;
  }
  
  if (isNaN(amount) || amount <= 0) {
    alert('กรุณากรอกจำนวนเงินให้ถูกต้อง (ต้องมากกว่า 0 บาท) ด้วยนะแก');
    return;
  }
  
  const fixedCosts = getFixedCosts();
  fixedCosts.push({ desc, amount });
  saveFixedCosts(fixedCosts);
  
  // Clear inputs
  descInput.value = '';
  amountInput.value = '';
  
  // Re-render
  renderFixedCostsTable();
  populateFixedCostDropdown();
}

function deleteFixedCost(index) {
  if (confirm('แน่ใจนะแกที่จะลบรายการ Fix Cost นี้?')) {
    const fixedCosts = getFixedCosts();
    fixedCosts.splice(index, 1);
    saveFixedCosts(fixedCosts);
    
    // Re-render
    renderFixedCostsTable();
    populateFixedCostDropdown();
  }
}

function renderFixedCostsTable() {
  const tableBody = document.getElementById('fixedCostsTableBody');
  if (!tableBody) return;
  
  const fixedCosts = getFixedCosts();
  
  if (fixedCosts.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="3" class="empty-row-msg">ไม่มีรายการ Fix Cost มาตรฐาน</td>
      </tr>
    `;
    return;
  }
  
  tableBody.innerHTML = fixedCosts.map((item, index) => {
    return `
      <tr>
        <td>${escapeHtml(item.desc)}</td>
        <td class="mono-cell" style="font-weight: 700;">฿${parseFloat(item.amount).toFixed(2)}</td>
        <td style="text-align: center;">
          <button type="button" class="btn-secondary delete-fixed-cost-btn" data-index="${index}" style="padding: 4px 8px; margin: 0; background-color: var(--alert-error-bg); border-color: var(--alert-error-border); color: var(--alert-error-text);" aria-label="ลบรายการ">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:16px;height:16px;">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </td>
      </tr>
    `;
  }).join('');
  
  // Bind delete button events
  tableBody.querySelectorAll('.delete-fixed-cost-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const index = parseInt(btn.getAttribute('data-index'), 10);
      deleteFixedCost(index);
    });
  });
}

function populateFixedCostDropdown() {
  const dropdown = document.getElementById('fixedCostSelect');
  if (!dropdown) return;
  
  const fixedCosts = getFixedCosts();
  
  // Save current selection to restore if possible
  const currentVal = dropdown.value;
  
  dropdown.innerHTML = '<option value="">-- เลือกรายการ Fix Cost --</option>';
  
  fixedCosts.forEach((item, index) => {
    const option = document.createElement('option');
    option.value = index;
    option.textContent = `${item.desc} (${parseFloat(item.amount).toFixed(2)} บาท)`;
    dropdown.appendChild(option);
  });
  
  // Try to restore previous selection
  if (currentVal !== "" && parseInt(currentVal, 10) < fixedCosts.length) {
    dropdown.value = currentVal;
  }
}

function handleFixedCostSelectChange() {
  const dropdown = document.getElementById('fixedCostSelect');
  if (!dropdown) return;
  
  const indexVal = dropdown.value;
  const expDescEl = document.getElementById('expDesc');
  const expAmountEl = document.getElementById('expAmount');
  
  if (!expDescEl || !expAmountEl) return;
  
  if (indexVal === "") {
    return;
  }
  
  const index = parseInt(indexVal, 10);
  const fixedCosts = getFixedCosts();
  const selectedItem = fixedCosts[index];
  
  if (selectedItem) {
    expDescEl.value = selectedItem.desc;
    expAmountEl.value = selectedItem.amount;
  }
}

async function handleBatchFixedCostsSubmit() {
  const fixedCosts = getFixedCosts();
  if (fixedCosts.length === 0) {
    alert('ไม่มีรายการ Fix Cost มาตรฐานที่จะบันทึกนะแก ไปเพิ่มในหน้าการตั้งค่าก่อนนะ');
    return;
  }
  
  if (!confirm(`คุณแน่ใจนะแกที่จะบันทึก Fix Cost ทั้งหมด (${fixedCosts.length} รายการ) ลง Google Sheets ประจำวันนี้?`)) {
    return;
  }
  
  const expDesc = fixedCosts.map(item => `${item.desc} (${parseFloat(item.amount).toFixed(2)})`).join('\n');
  const amountFormula = '=' + fixedCosts.map(item => item.amount).join('+');
  
  let rawDate = document.getElementById('expDate').value;
  let time = document.getElementById('expTime').value;
  
  if (!rawDate || !time) {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    rawDate = rawDate || `${yyyy}-${mm}-${dd}`;
    
    const hh = String(today.getHours()).padStart(2, '0');
    const min = String(today.getMinutes()).padStart(2, '0');
    time = time || `${hh}:${min}`;
  }
  
  const dateFormatted = formatDateToDMY(rawDate);
  const scriptUrl = localStorage.getItem('income_tracker_gas_url');
  const generalSheetId = localStorage.getItem('income_tracker_general_sheet_id') || '';
  
  let payload = {
    type: 'expense',
    spreadsheetId: generalSheetId,
    timestamp: new Date().toISOString(),
    date: dateFormatted,
    time: time,
    expDesc: expDesc,
    amount: amountFormula
  };
  
  const submitBtn = document.getElementById('btnSubmitAllFixedCosts');
  if (!submitBtn) return;
  
  const originalBtnHtml = submitBtn.innerHTML;
  submitBtn.disabled = true;
  submitBtn.innerHTML = `
    <svg class="btn-svg-icon spin-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" style="animation: rotate 1s linear infinite;">
      <circle cx="12" cy="12" r="10" stroke="rgba(255,255,255,0.2)"></circle>
      <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
    </svg>
    กำลังส่งข้อมูล...
  `;
  
  if (!document.getElementById('spinnerStyle')) {
    const style = document.createElement('style');
    style.id = 'spinnerStyle';
    style.innerHTML = `@keyframes rotate { 100% { transform: rotate(360deg); } }`;
    document.head.appendChild(style);
  }
  
  if (!scriptUrl) {
    saveToLocalHistory(payload, 'local_only');
    showPopup(false, 'บันทึกเข้าเครื่องชั่วคราว!', 'แกยังไม่ได้ตั้งค่า Web App URL ในหน้า Settings ข้อมูลจึงถูกบันทึกไว้บนบราวเซอร์ของเครื่องนี้เท่านั้น หากต้องการให้ข้อมูลเข้า Google Sheets อย่าลืมไปใส่ลิงก์เชื่อมต่อนะแก');
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalBtnHtml;
    resetFormInputs('expense');
    return;
  }
  
  try {
    const response = await fetch(scriptUrl, {
      method: 'POST',
      mode: 'cors',
      headers: {
        'Content-Type': 'text/plain;charset=utf-8'
      },
      body: JSON.stringify(payload)
    });
    
    const result = await response.json();
    
    if (result.status === 'success') {
      saveToLocalHistory(payload, 'synced');
      showPopup(true, 'บันทึกข้อมูลสำเร็จ! ฿', result.message || 'ข้อมูล Fix Cost ทั้งหมดถูกบันทึกและซิงค์ลง Google Sheets เรียบร้อยแล้วแก!');
      resetFormInputs('expense');
    } else {
      saveToLocalHistory(payload, 'failed');
      showPopup(false, 'เกิดข้อผิดพลาด ⚠', result.message || 'ไม่สามารถส่งข้อมูลลงตารางได้ เนื่องจากเกิดข้อผิดพลาดทางเทคนิคที่ Google Sheets หรือสคริปต์เชื่อมต่อ โปรดตรวจสอบสถานะการทำงานอีกครั้ง');
    }
  } catch (err) {
    console.error('Fetch Error:', err);
    saveToLocalHistory(payload, 'failed');
    showPopup(false, 'ส่งข้อมูลไม่สำเร็จ ❌', 'ไม่สามารถติดต่อเซิร์ฟเวอร์ Google Apps Script ได้ โปรดตรวจสอบความถูกต้องของลิงก์ URL หรือสถานะการเชื่อมต่ออินเทอร์เน็ตของแกด้วยนะ');
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalBtnHtml;
  }
}

// --- 9. Dashboard Logic & SVG Charting ---

const MOCK_MONTHLY_DATA = [
  { month: 'ม.ค.', income: 45000, expense: 22000, profit: 23000, savings: 4500, fixedCosts: [{ desc: 'ค่าเช่าเซิร์ฟเวอร์ Feltz', amount: 1500 }, { desc: 'ค่าเน็ตสำนักงาน', amount: 799 }] },
  { month: 'ก.พ.', income: 52000, expense: 25000, profit: 27000, savings: 5200, fixedCosts: [{ desc: 'ค่าเช่าเซิร์ฟเวอร์ Feltz', amount: 1500 }, { desc: 'ค่าเน็ตสำนักงาน', amount: 799 }] },
  { month: 'มี.ค.', income: 48000, expense: 28000, profit: 20000, savings: 4800, fixedCosts: [{ desc: 'ค่าเช่าเซิร์ฟเวอร์ Feltz', amount: 1500 }, { desc: 'ค่าเน็ตสำนักงาน', amount: 799 }] },
  { month: 'เม.ย.', income: 60000, expense: 32000, profit: 28000, savings: 6000, fixedCosts: [{ desc: 'ค่าเช่าเซิร์ฟเวอร์ Feltz', amount: 1500 }, { desc: 'ค่าเน็ตสำนักงาน', amount: 799 }] },
  { month: 'พ.ค.', income: 55000, expense: 26000, profit: 29000, savings: 5500, fixedCosts: [{ desc: 'ค่าเช่าเซิร์ฟเวอร์ Feltz', amount: 1500 }, { desc: 'ค่าเน็ตสำนักงาน', amount: 799 }] },
  { month: 'มิ.ย.', income: 58000, expense: 27000, profit: 31000, savings: 5800, fixedCosts: [{ desc: 'ค่าเช่าเซิร์ฟเวอร์ Feltz', amount: 1500 }, { desc: 'ค่าเน็ตสำนักงาน', amount: 799 }] },
  { month: 'ก.ค.', income: 62000, expense: 30000, profit: 32000, savings: 6200, fixedCosts: [{ desc: 'ค่าเช่าเซิร์ฟเวอร์ Feltz', amount: 1500 }, { desc: 'ค่าเน็ตสำนักงาน', amount: 799 }] },
  { month: 'ส.ค.', income: 64000, expense: 31000, profit: 33000, savings: 6400, fixedCosts: [{ desc: 'ค่าเช่าเซิร์ฟเวอร์ Feltz', amount: 1500 }, { desc: 'ค่าเน็ตสำนักงาน', amount: 799 }] },
  { month: 'ก.ย.', income: 61000, expense: 29000, profit: 32000, savings: 6100, fixedCosts: [{ desc: 'ค่าเช่าเซิร์ฟเวอร์ Feltz', amount: 1500 }, { desc: 'ค่าเน็ตสำนักงาน', amount: 799 }] },
  { month: 'ต.ค.', income: 67000, expense: 33000, profit: 34000, savings: 6700, fixedCosts: [{ desc: 'ค่าเช่าเซิร์ฟเวอร์ Feltz', amount: 1500 }, { desc: 'ค่าเน็ตสำนักงาน', amount: 799 }] },
  { month: 'พ.ย.', income: 70000, expense: 35000, profit: 35000, savings: 7000, fixedCosts: [{ desc: 'ค่าเช่าเซิร์ฟเวอร์ Feltz', amount: 1500 }, { desc: 'ค่าเน็ตสำนักงาน', amount: 799 }] },
  { month: 'ธ.ค.', income: 75000, expense: 37000, profit: 38000, savings: 7500, fixedCosts: [{ desc: 'ค่าเช่าเซิร์ฟเวอร์ Feltz', amount: 1500 }, { desc: 'ค่าเน็ตสำนักงาน', amount: 799 }] }
];

async function refreshDashboardData(forceRealSheetData = false) {
  const scriptUrl = localStorage.getItem('income_tracker_gas_url');
  const generalSheetId = localStorage.getItem('income_tracker_general_sheet_id');
  const banner = document.getElementById('dashboardConnectionBanner');
  const btn = document.getElementById('btnRefreshDashboard');
  
  // Check if we have credentials for real data
  const hasConnection = scriptUrl && generalSheetId;
  
  if (!hasConnection) {
    if (banner) banner.style.display = 'block';
    updateKpis(MOCK_MONTHLY_DATA);
    drawSvgChart(MOCK_MONTHLY_DATA);
    calculateAndRenderInsights(MOCK_MONTHLY_DATA);
    renderDashboardFixedCosts(MOCK_MONTHLY_DATA);
    return;
  }
  
  if (banner) banner.style.display = 'none';
  
  let originalBtnHtml = '';
  if (btn) {
    originalBtnHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `
      <svg class="btn-svg-icon spin-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" style="animation: rotate 1s linear infinite; width:16px; height:16px; margin-right:6px;">
        <circle cx="12" cy="12" r="10" stroke="rgba(255,255,255,0.2)"></circle>
        <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
      </svg>
      กำลังโหลดข้อมูล...
    `;
  }
  
  try {
    const response = await fetch(scriptUrl, {
      method: 'POST',
      mode: 'cors',
      headers: {
        'Content-Type': 'text/plain;charset=utf-8'
      },
      body: JSON.stringify({
        type: 'fetch_summary',
        spreadsheetId: generalSheetId
      })
    });
    
    const result = await response.json();
    
    if (result.status === 'success' && result.data && result.data.length > 0) {
      updateKpis(result.data);
      drawSvgChart(result.data);
      calculateAndRenderInsights(result.data);
      renderDashboardFixedCosts(result.data);
    } else {
      throw new Error(result.message || 'ไม่ได้รับข้อมูลที่ถูกต้อง');
    }
  } catch (err) {
    console.error('Fetch Dashboard Error:', err);
    alert('ไม่สามารถดึงข้อมูลจริงจากชีตได้ จึงสลับมาใช้ข้อมูลจำลองแทนจ้าแก: ' + err.message);
    if (banner) banner.style.display = 'block';
    updateKpis(MOCK_MONTHLY_DATA);
    drawSvgChart(MOCK_MONTHLY_DATA);
    calculateAndRenderInsights(MOCK_MONTHLY_DATA);
    renderDashboardFixedCosts(MOCK_MONTHLY_DATA);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalBtnHtml;
    }
  }
}

function updateKpis(data) {
  let totalIncome = 0;
  let totalExpense = 0;
  let netProfit = 0;
  let totalSavings = 0;
  
  data.forEach(m => {
    totalIncome += m.income || 0;
    totalExpense += m.expense || 0;
    netProfit += m.profit || 0;
    totalSavings += m.savings || 0;
  });
  
  document.getElementById('kpiTotalIncome').textContent = `฿${totalIncome.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById('kpiTotalExpense').textContent = `฿${totalExpense.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById('kpiNetProfit').textContent = `฿${netProfit.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById('kpiTotalSavings').textContent = `฿${totalSavings.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function drawSvgChart(data) {
  const wrapper = document.getElementById('chartWrapper');
  if (!wrapper) return;
  
  // Find max value to scale Y axis
  let maxVal = 1000;
  data.forEach(m => {
    if (m.income > maxVal) maxVal = m.income;
    if (m.expense > maxVal) maxVal = m.expense;
  });
  
  // Round up maxVal for clean grid lines
  maxVal = Math.ceil(maxVal / 10000) * 10000;
  
  const width = 800;
  const height = 300;
  const paddingLeft = 60;
  const paddingRight = 20;
  const paddingTop = 30;
  const paddingBottom = 40;
  
  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;
  
  // Theme check for dynamic color values
  const isDark = document.documentElement.classList.contains('dark-theme');
  const shadowColor = isDark ? '#ffffff' : '#0f172a';
  const textColor = isDark ? '#e2e8f0' : '#0f172a';
  const gridColor = isDark ? '#475569' : '#e2e8f0';
  
  const incomeColor = isDark ? '#10b981' : '#10b981';
  const expenseColor = isDark ? '#ef4444' : '#ef4444';
  
  // SVG generation
  let svg = `<svg viewBox="0 0 ${width} ${height}" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" style="font-family: var(--font-heading); font-size: 11px;">`;
  
  // Chart Legend (top right)
  svg += `
    <g transform="translate(${width - paddingRight - 130}, 12)" style="font-size: 11px; font-weight: 600;">
      <!-- Income -->
      <rect x="0" y="0" width="12" height="12" fill="${incomeColor}" stroke="${shadowColor}" stroke-width="1.5" />
      <text x="18" y="10" fill="${textColor}">รายรับ</text>
      <!-- Expense -->
      <rect x="65" y="0" width="12" height="12" fill="${expenseColor}" stroke="${shadowColor}" stroke-width="1.5" />
      <text x="83" y="10" fill="${textColor}">รายจ่าย</text>
    </g>
  `;
  
  // Grid lines (3 lines)
  for (let i = 0; i <= 3; i++) {
    const y = paddingTop + (chartHeight * i) / 3;
    const val = maxVal - (maxVal * i) / 3;
    svg += `
      <line x1="${paddingLeft}" y1="${y}" x2="${width - paddingRight}" y2="${y}" stroke="${gridColor}" stroke-dasharray="3" stroke-width="1" />
      <text x="${paddingLeft - 8}" y="${y + 4}" fill="${textColor}" text-anchor="end" font-family="var(--font-mono)">${(val / 1000).toFixed(0)}k</text>
    `;
  }
  
  const colWidth = chartWidth / data.length;
  const barWidth = 14;
  const barGap = 3;
  
  data.forEach((m, idx) => {
    const x = paddingLeft + (idx * colWidth) + (colWidth - (barWidth * 2 + barGap)) / 2;
    
    // Scale heights
    const incHeight = (m.income / maxVal) * chartHeight;
    const expHeight = (m.expense / maxVal) * chartHeight;
    
    const incY = paddingTop + chartHeight - incHeight;
    const expY = paddingTop + chartHeight - expHeight;
    
    // 1. Income Bar (Green with 3D Solid Shadow)
    if (incHeight > 0) {
      svg += `
        <!-- Shadow -->
        <rect x="${x + 3}" y="${incY + 3}" width="${barWidth}" height="${incHeight}" fill="${shadowColor}" />
        <!-- Actual Bar -->
        <rect x="${x}" y="${incY}" width="${barWidth}" height="${incHeight}" fill="${incomeColor}" stroke="${shadowColor}" stroke-width="1.5" />
      `;
    }
    
    // 2. Expense Bar (Red with 3D Solid Shadow)
    const xExp = x + barWidth + barGap;
    if (expHeight > 0) {
      svg += `
        <!-- Shadow -->
        <rect x="${xExp + 3}" y="${expY + 3}" width="${barWidth}" height="${expHeight}" fill="${shadowColor}" />
        <!-- Actual Bar -->
        <rect x="${xExp}" y="${expY}" width="${barWidth}" height="${expHeight}" fill="${expenseColor}" stroke="${shadowColor}" stroke-width="1.5" />
      `;
    }
    
    // Month label on X Axis
    svg += `
      <text x="${x + barWidth + barGap / 2}" y="${paddingTop + chartHeight + 18}" fill="${textColor}" text-anchor="middle" font-weight="600">${m.month}</text>
    `;
  });
  
  // Baseline (X Axis)
  svg += `<line x1="${paddingLeft}" y1="${paddingTop + chartHeight}" x2="${width - paddingRight}" y2="${paddingTop + chartHeight}" stroke="${shadowColor}" stroke-width="2" />`;
  
  svg += '</svg>';
  wrapper.innerHTML = svg;
}

function calculateAndRenderInsights(data) {
  const container = document.getElementById('dashboardInsightContent');
  if (!container) return;
  
  let totalIncome = 0;
  let totalExpense = 0;
  let maxIncomeMonth = { month: '', val: 0 };
  let maxExpenseMonth = { month: '', val: 0 };
  
  data.forEach(m => {
    totalIncome += m.income || 0;
    totalExpense += m.expense || 0;
    if (m.income > maxIncomeMonth.val) {
      maxIncomeMonth = { month: m.month, val: m.income };
    }
    if (m.expense > maxExpenseMonth.val) {
      maxExpenseMonth = { month: m.month, val: m.expense };
    }
  });
  
  const profit = totalIncome - totalExpense;
  const ratio = totalIncome > 0 ? (totalExpense / totalIncome) * 100 : 0;
  
  let statusBadge = '';
  let statusText = '';
  if (ratio < 40) {
    statusBadge = '<span class="insight-badge positive">สุขภาพการเงินดีเยี่ยม</span>';
    statusText = 'แกบริหารค่าใช้จ่ายได้ยอดเยี่ยมมาก ค่าใช้จ่ายต่ำกว่า 40% ของรายรับ มีความคล่องตัวในการเก็บออมสูง';
  } else if (ratio < 65) {
    statusBadge = '<span class="insight-badge neutral">สุขภาพการเงินปกติ</span>';
    statusText = 'สถานการณ์การเงินอยู่ในระดับสมดุลทั่วไป มีเงินออมเพียงพอ แต่สามารถเพิ่มรายรับหรือคุมค่าใช้จ่ายให้ดีกว่านี้ได้อีกนิดแก';
  } else {
    statusBadge = '<span class="insight-badge negative">ควรเฝ้าระวังค่าใช้จ่าย</span>';
    statusText = 'รายจ่ายสะสมค่อนข้างสูง (เกิน 65% ของรายรับ) ควรพิจารณาลดรายจ่ายที่ไม่จำเป็นหรือ Fix Cost บางส่วนลงบ้างนะแก';
  }
  
  let html = `
    <div class="insight-item">
      <div>${statusBadge}</div>
      <p style="margin-top: 6px;">${statusText}</p>
    </div>
    <div class="insight-item">
      <strong><svg class="emoji-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="width: 16px; height: 16px; color: #fbbf24;"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" /><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" /><path d="M4 22h16" /><path d="M10 14.66V17c0 .55-.45 1-1 1H4v2h16v-2h-5c-.55 0-1-.45-1-1v-2.34" /><path d="M12 2a6 6 0 0 1 6 6v3.5a6 6 0 0 1-6 6 6 6 0 0 1-6-6V8a6 6 0 0 1 6-6z" /></svg> เดือนรายรับสูงสุด:</strong> ${maxIncomeMonth.month} (฿${maxIncomeMonth.val.toLocaleString()})
    </div>
    <div class="insight-item">
      <strong><svg class="emoji-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="width: 16px; height: 16px; color: #ef4444;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg> เดือนรายจ่ายสูงสุด:</strong> ${maxExpenseMonth.month} (฿${maxExpenseMonth.val.toLocaleString()})
    </div>
    <div class="insight-item">
      <strong><svg class="emoji-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="width: 16px; height: 16px; color: #3b82f6;"><line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" /></svg> อัตราส่วนรายจ่ายต่อรายรับ:</strong> ${ratio.toFixed(1)}% (ยอดคงเหลือหลังหักจ่าย ฿${profit.toLocaleString()})
    </div>
  `;
  
  container.innerHTML = html;
}

function renderDashboardFixedCosts(data) {
  const tableBody = document.getElementById('dashboardFixedCostBody');
  if (!tableBody) return;
  
  // Find fixed costs list. Let's merge from the last month that has fixed costs
  let fixedCosts = [];
  for (let i = data.length - 1; i >= 0; i--) {
    if (data[i].fixedCosts && data[i].fixedCosts.length > 0) {
      fixedCosts = data[i].fixedCosts;
      break;
    }
  }
  
  if (fixedCosts.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="2" class="empty-row-msg">ไม่มีข้อมูล Fix Cost ในรอบปีนี้</td>
      </tr>
    `;
    return;
  }
  
  tableBody.innerHTML = fixedCosts.map(item => `
    <tr>
      <td>${escapeHtml(item.desc)}</td>
      <td class="mono-cell" style="font-weight:700;">฿${parseFloat(item.amount).toFixed(2)}</td>
    </tr>
  `).join('');
}

function autoCalculateDueDate() {
  const docDateInput = document.getElementById('docDate');
  const docPaymentTermInput = document.getElementById('docPaymentTerm');
  const docDueDateInput = document.getElementById('docDueDate');
  
  if (!docDateInput || !docPaymentTermInput || !docDueDateInput) return;
  
  const dateVal = docDateInput.value;
  if (!dateVal) return;
  
  const termVal = docPaymentTermInput.value || '';
  const dayMatch = termVal.match(/\d+/);
  let days = 0;
  if (dayMatch) {
    days = parseInt(dayMatch[0], 10);
  } else {
    days = 0;
  }
  
  const parts = dateVal.split('-');
  if (parts.length === 3) {
    const year = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1;
    const day = parseInt(parts[2], 10);
    
    const date = new Date(year, month, day);
    date.setDate(date.getDate() + days);
    
    const dy = date.getFullYear();
    const dm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    
    docDueDateInput.value = `${dy}-${dm}-${dd}`;
  }
}

// --- 10. Financial Documents Generator Module ---
let docItems = [];
let currentDocType = 'quotation'; // quotation, invoice, receipt

function initDocumentGenerator() {
  // Set default date to today
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, '0');
  const dd = String(today.getDate()).padStart(2, '0');
  
  const docDateInput = document.getElementById('docDate');
  if (docDateInput) {
    docDateInput.value = `${yyyy}-${mm}-${dd}`;
  }
  
  // Set default due date to 30 days from today
  const docDueDateInput = document.getElementById('docDueDate');
  if (docDueDateInput) {
    const dueDate = new Date();
    dueDate.setDate(dueDate.getDate() + 30);
    const dy = dueDate.getFullYear();
    const dm = String(dueDate.getMonth() + 1).padStart(2, '0');
    const dd = String(dueDate.getDate()).padStart(2, '0');
    docDueDateInput.value = `${dy}-${dm}-${dd}`;
  }
  
  // Set default items
  docItems = [
    { desc: 'บริการถ่ายภาพโฆษณา Feltz Studio (ครึ่งวัน)', qty: 1, unit: 'ครั้ง', price: 15000 },
    { desc: 'บริการตกแต่งภาพและรีทัชระดับพรีเมียม', qty: 5, unit: 'ภาพ', price: 800 }
  ];

  // Set default doc number
  const docNumInput = document.getElementById('docNumber');
  if (docNumInput) {
    docNumInput.value = autoGenerateDocNumber('quotation');
  }

  // Load seller info from localStorage if exists
  loadSellerSettings();

  // Bind input sync events
  const syncInputs = [
    'docSellerName', 'docSellerTaxId', 'docSellerAddress', 'docSellerPhone', 'docSellerEmail',
    'docClientName', 'docClientAddress', 'docClientTaxId', 'docClientPhone',
    'docNumber', 'docDate', 'docDueDate', 'docPaymentTerm', 'docBankDetails', 'docSignerName', 'docProjectName'
  ];
  
  syncInputs.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', () => {
        if (id === 'docDate' || id === 'docPaymentTerm') {
          autoCalculateDueDate();
        }
        syncDocPreview();
        // Save seller & bank details dynamically
        if (id.startsWith('docSeller') || id === 'docBankDetails' || id === 'docSignerName') {
          saveSellerSettings();
        }
      });
      el.addEventListener('change', () => {
        if (id === 'docDate' || id === 'docPaymentTerm') {
          autoCalculateDueDate();
        }
        syncDocPreview();
        if (id.startsWith('docSeller') || id === 'docBankDetails' || id === 'docSignerName') {
          saveSellerSettings();
        }
      });
    }
  });

  const vatCheck = document.getElementById('docVatCheckbox');
  if (vatCheck) {
    vatCheck.addEventListener('change', syncDocPreview);
  }

  const whtSelect = document.getElementById('docWhtSelect');
  if (whtSelect) {
    whtSelect.addEventListener('change', syncDocPreview);
  }

  const btnAddDocItem = document.getElementById('btnAddDocItem');
  if (btnAddDocItem) {
    btnAddDocItem.addEventListener('click', addDocItem);
  }

  const btnExportDocPdf = document.getElementById('btnExportDocPdf');
  if (btnExportDocPdf) {
    btnExportDocPdf.addEventListener('click', () => {
      // document.title is continuously updated via syncDocPreview/switchToView
      window.print();
    });
  }

  // Calculate default due date on load
  autoCalculateDueDate();

  // Render first time
  setDocType('quotation');
}

function loadSellerSettings() {
  const data = localStorage.getItem('income_tracker_doc_seller');
  if (data) {
    try {
      const parsed = JSON.parse(data);
      // Migration: Update old placeholder defaults in localStorage to the correct personalized values
      if (parsed.sellerName === 'Feltz Studio' || parsed.sellerTaxId === '0105566000000') {
        if (parsed.sellerName === 'Feltz Studio') parsed.sellerName = 'มงคล วงศ์สกุลยานนท์ (Feltz Studio)';
        if (parsed.sellerTaxId === '0105566000000') parsed.sellerTaxId = '3509900218949';
        if (parsed.sellerAddress === '123/45 ถนนพัฒนาการ แขวงพัฒนาการ เขตสวนหลวง กรุงเทพมหานคร 10250') {
          parsed.sellerAddress = '65/1 ถ.ต้นขาม2 ต.ท่าศาลา อ.เมือง จ.เชียงใหม่';
        }
        if (parsed.sellerPhone === '081-234-5678') parsed.sellerPhone = '0895544355';
        if (parsed.sellerEmail === 'contact@feltzstudio.com') parsed.sellerEmail = 'feltzstudio@gmail.com';
        if (parsed.bankDetails === 'ธ.กสิกรไทย เลขที่ 123-4-56789-0 ชื่อบัญชี บจก. เฟลท์ซ สตูดิโอ') {
          parsed.bankDetails = 'ธ.กสิกรไทย เลขที่ 123-4-56789-0 ชื่อบัญชี มงคล วงศ์สกุลยานนท์';
        }
        if (parsed.signerName === 'คุณเก่ง (Keng)') parsed.signerName = 'มงคล วงศ์สกุลยานนท์';
        localStorage.setItem('income_tracker_doc_seller', JSON.stringify(parsed));
      }
      if (parsed.sellerName) document.getElementById('docSellerName').value = parsed.sellerName;
      if (parsed.sellerTaxId) document.getElementById('docSellerTaxId').value = parsed.sellerTaxId;
      if (parsed.sellerAddress) document.getElementById('docSellerAddress').value = parsed.sellerAddress;
      if (parsed.sellerPhone) document.getElementById('docSellerPhone').value = parsed.sellerPhone;
      if (parsed.sellerEmail) document.getElementById('docSellerEmail').value = parsed.sellerEmail;
      if (parsed.bankDetails) document.getElementById('docBankDetails').value = parsed.bankDetails;
      if (parsed.signerName) document.getElementById('docSignerName').value = parsed.signerName;
    } catch (e) {
      console.error('Error loading seller settings', e);
    }
  }
}

function saveSellerSettings() {
  const settings = {
    sellerName: document.getElementById('docSellerName').value,
    sellerTaxId: document.getElementById('docSellerTaxId').value,
    sellerAddress: document.getElementById('docSellerAddress').value,
    sellerPhone: document.getElementById('docSellerPhone').value,
    sellerEmail: document.getElementById('docSellerEmail').value,
    bankDetails: document.getElementById('docBankDetails').value,
    signerName: document.getElementById('docSignerName').value
  };
  localStorage.setItem('income_tracker_doc_seller', JSON.stringify(settings));
}

function autoGenerateDocNumber(type) {
  const now = new Date();
  const yy = now.getFullYear().toString().substring(2);
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const prefix = type === 'quotation' ? 'QT' : (type === 'invoice' ? 'IV' : 'RE');
  return `${prefix}${yy}${mm}-001`;
}

function setDocType(type) {
  currentDocType = type;
  
  // Update UI buttons
  const buttons = {
    quotation: document.getElementById('btnDocTypeQuotation'),
    invoice: document.getElementById('btnDocTypeInvoice'),
    receipt: document.getElementById('btnDocTypeReceipt')
  };
  
  Object.keys(buttons).forEach(key => {
    if (buttons[key]) {
      if (key === type) {
        buttons[key].classList.add('active');
      } else {
        buttons[key].classList.remove('active');
      }
    }
  });

  // Adjust input groups visibility
  const groupDueDate = document.getElementById('groupDocDueDate');
  const groupPaymentTerm = document.getElementById('groupDocPaymentTerm');
  const prevDueDateRow = document.getElementById('prevDocDueDateRow');
  const prevPaymentTermTitle = document.getElementById('prevPaymentTermTitle');
  const prevPaymentTermVal = document.getElementById('prevPaymentTermVal');

  if (type === 'receipt') {
    if (groupDueDate) groupDueDate.style.display = 'none';
    if (groupPaymentTerm) groupPaymentTerm.style.display = 'none';
    if (prevDueDateRow) prevDueDateRow.style.display = 'none';
    if (prevPaymentTermTitle) prevPaymentTermTitle.style.display = 'none';
    if (prevPaymentTermVal) prevPaymentTermVal.style.display = 'none';
  } else {
    if (groupDueDate) groupDueDate.style.display = 'block';
    if (groupPaymentTerm) groupPaymentTerm.style.display = 'block';
    if (prevDueDateRow) prevDueDateRow.style.display = (type === 'quotation') ? 'none' : 'flex';
    if (prevPaymentTermTitle) prevPaymentTermTitle.style.display = 'block';
    if (prevPaymentTermVal) prevPaymentTermVal.style.display = 'block';
  }

  const prevDepositTerms = document.getElementById('prevDepositTermsBlock');
  if (prevDepositTerms) {
    prevDepositTerms.style.display = (type === 'quotation') ? 'block' : 'none';
  }

  // Update document title and number
  const prevTitle = document.getElementById('prevDocTitleText');
  const prevTitleEn = document.getElementById('prevDocTitleEnText');
  const docNumInput = document.getElementById('docNumber');

  if (type === 'quotation') {
    prevTitle.textContent = 'ใบเสนอราคา';
    prevTitleEn.textContent = 'QUOTATION';
  } else if (type === 'invoice') {
    prevTitle.textContent = 'ใบวางบิล / ใบแจ้งหนี้';
    prevTitleEn.textContent = 'INVOICE';
  } else if (type === 'receipt') {
    prevTitle.textContent = 'ใบเสร็จรับเงิน / ใบกำกับภาษี';
    prevTitleEn.textContent = 'RECEIPT / TAX INVOICE';
  }

  if (docNumInput) {
    docNumInput.value = autoGenerateDocNumber(type);
  }

  syncDocPreview();
}

function renderDocItemsTable() {
  const editorBody = document.getElementById('editorItemsBody');
  const prevBody = document.getElementById('prevItemsBody');
  if (!editorBody || !prevBody) return;

  // Render editor rows
  editorBody.innerHTML = docItems.map((item, idx) => `
    <tr>
      <td>
        <input type="text" value="${escapeHtml(item.desc)}" oninput="updateDocItem(${idx}, 'desc', this.value)" style="width:100%; border:none; padding:4px; font-size:12px;" placeholder="รายละเอียดบริการ/สินค้า" required>
      </td>
      <td>
        <input type="number" value="${item.qty}" min="1" step="any" oninput="updateDocItem(${idx}, 'qty', this.value)" style="width:100%; border:none; padding:4px; font-size:12px; text-align:center;" required>
      </td>
      <td>
        <input type="text" value="${escapeHtml(item.unit)}" oninput="updateDocItem(${idx}, 'unit', this.value)" style="width:100%; border:none; padding:4px; font-size:12px; text-align:center;" placeholder="เช่น งาน" required>
      </td>
      <td>
        <input type="number" value="${item.price}" min="0" step="0.01" oninput="updateDocItem(${idx}, 'price', this.value)" style="width:100%; border:none; padding:4px; font-size:12px; text-align:right;" required>
      </td>
      <td style="text-align:center;">
        <button type="button" class="btn-secondary" onclick="deleteDocItem(${idx})" style="padding:2px 6px; font-size:11px; margin:0; background:#fee2e2; color:#b91c1c; border-color:#fee2e2;">ลบ</button>
      </td>
    </tr>
  `).join('');

  // Render preview rows
  if (docItems.length === 0) {
    prevBody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align:center; color:#64748b; font-style:italic; padding: 15px;">ไม่มีรายการสินค้าหรือบริการ</td>
      </tr>
    `;
    return;
  }

  prevBody.innerHTML = docItems.map((item, idx) => {
    const total = (item.qty || 0) * (item.price || 0);
    return `
      <tr>
        <td style="text-align:center;">${idx + 1}</td>
        <td style="text-align:left; white-space: pre-wrap;">${escapeHtml(item.desc)}</td>
        <td style="text-align:center;">${item.qty}</td>
        <td style="text-align:center;">${escapeHtml(item.unit)}</td>
        <td style="text-align:right;">${item.price.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
        <td style="text-align:right;">${total.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
      </tr>
    `;
  }).join('');
}

function addDocItem() {
  docItems.push({ desc: '', qty: 1, unit: 'งาน', price: 0 });
  renderDocItemsTable();
  syncDocPreview();
}

function deleteDocItem(index) {
  docItems.splice(index, 1);
  renderDocItemsTable();
  syncDocPreview();
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
}

function calculateDocTotals() {
  let subtotal = 0;
  docItems.forEach(item => {
    subtotal += (item.qty || 0) * (item.price || 0);
  });

  const vatCheck = document.getElementById('docVatCheckbox');
  const whtSelect = document.getElementById('docWhtSelect');

  let vat = 0;
  if (vatCheck && vatCheck.checked) {
    vat = subtotal * 0.07;
  }

  let whtRate = parseInt(whtSelect ? whtSelect.value : 0);
  let wht = 0;
  if (whtRate > 0) {
    wht = subtotal * (whtRate / 100);
  }

  const grandTotal = subtotal + vat - wht;

  // Update preview table totals
  const prevSubtotal = document.getElementById('prevSubtotalVal');
  if (prevSubtotal) prevSubtotal.textContent = `฿${subtotal.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const prevVatRow = document.getElementById('prevVatRow');
  const prevVat = document.getElementById('prevVatVal');
  if (prevVatRow && prevVat) {
    if (vat > 0) {
      prevVatRow.style.display = 'flex';
      prevVat.textContent = `฿${vat.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    } else {
      prevVatRow.style.display = 'none';
    }
  }

  const prevWhtRow = document.getElementById('prevWhtRow');
  const prevWhtRate = document.getElementById('prevWhtRateVal');
  const prevWht = document.getElementById('prevWhtVal');
  if (prevWhtRow && prevWhtRate && prevWht) {
    if (wht > 0) {
      prevWhtRow.style.display = 'flex';
      prevWhtRate.textContent = whtRate;
      prevWht.textContent = `-฿${wht.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    } else {
      prevWhtRow.style.display = 'none';
    }
  }

  const prevGrandTotal = document.getElementById('prevGrandTotalVal');
  if (prevGrandTotal) prevGrandTotal.textContent = `฿${grandTotal.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  // Update Thai Baht text representation
  const prevBahtText = document.getElementById('prevBahtTextVal');
  if (prevBahtText) {
    prevBahtText.textContent = thaiBahtText(grandTotal);
  }

  // Update live preview list items total values (re-render right side only)
  const prevBody = document.getElementById('prevItemsBody');
  if (prevBody) {
    if (docItems.length === 0) {
      prevBody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align:center; color:#64748b; font-style:italic; padding: 15px;">ไม่มีรายการสินค้าหรือบริการ</td>
        </tr>
      `;
    } else {
      prevBody.innerHTML = docItems.map((item, idx) => {
        const total = (item.qty || 0) * (item.price || 0);
        return `
          <tr>
            <td style="text-align:center;">${idx + 1}</td>
            <td style="text-align:left; white-space: pre-wrap;">${escapeHtml(item.desc)}</td>
            <td style="text-align:center;">${item.qty}</td>
            <td style="text-align:center;">${escapeHtml(item.unit)}</td>
            <td style="text-align:right;">${item.price.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
            <td style="text-align:right;">${total.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
          </tr>
        `;
      }).join('');
    }
  }
}

function syncDocPreview() {
  // Simple mapping ID -> ID
  const mappings = [
    { from: 'docSellerName', to: 'prevSellerName' },
    { from: 'docSellerTaxId', to: 'prevSellerTaxId' },
    { from: 'docSellerAddress', to: 'prevSellerAddress' },
    { from: 'docSellerPhone', to: 'prevSellerPhone' },
    { from: 'docSellerEmail', to: 'prevSellerEmail' },
    
    { from: 'docClientName', to: 'prevClientName' },
    { from: 'docClientTaxId', to: 'prevClientTaxId' },
    { from: 'docClientAddress', to: 'prevClientAddress' },
    { from: 'docClientPhone', to: 'prevClientPhone' },
    
    { from: 'docNumber', to: 'prevDocNoVal' },
    { from: 'docPaymentTerm', to: 'prevPaymentTermVal' },
    { from: 'docBankDetails', to: 'prevBankDetailsVal' },
    { from: 'docSignerName', to: 'prevSignerNameVal' },
    { from: 'docProjectName', to: 'prevProjectNameVal' }
  ];

  mappings.forEach(m => {
    const fromEl = document.getElementById(m.from);
    const toEl = document.getElementById(m.to);
    if (fromEl && toEl) {
      toEl.textContent = fromEl.value || '-';
    }
  });

  // Date mappings with formatting
  const dateVal = document.getElementById('docDate').value;
  document.getElementById('prevDocDateVal').textContent = formatDocDate(dateVal);
  
  const dueDateVal = document.getElementById('docDueDate').value;
  document.getElementById('prevDocDueDateVal').textContent = formatDocDate(dueDateVal);

  // Address newlines to break lines in preview address
  const sellerAddr = document.getElementById('docSellerAddress').value;
  document.getElementById('prevSellerAddress').innerHTML = escapeHtml(sellerAddr).replace(/\n/g, '<br>');

  const clientAddr = document.getElementById('docClientAddress').value;
  document.getElementById('prevClientAddress').innerHTML = escapeHtml(clientAddr || '-').replace(/\n/g, '<br>');

  // Show/hide bank logo or tax ID details
  const prevClientTaxId = document.getElementById('prevClientTaxId');
  const docClientTaxId = document.getElementById('docClientTaxId').value;
  if (prevClientTaxId) {
    if (docClientTaxId) {
      prevClientTaxId.parentNode.style.display = 'block';
      prevClientTaxId.textContent = docClientTaxId;
    } else {
      prevClientTaxId.parentNode.style.display = 'none';
    }
  }

  // Update dynamic elements
  renderDocItemsTable();
  calculateDocTotals();
  
  // Update title dynamically if we are currently viewing the document view
  const docView = document.getElementById('document-view');
  if (docView && docView.classList.contains('active')) {
    updateDynamicDocTitle();
  }
}

function formatDocDate(dateStr) {
  if (!dateStr) return '-';
  const parts = dateStr.split('-');
  if (parts.length === 3) {
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }
  return dateStr;
}

function thaiBahtText(amount) {
  if (isNaN(amount) || amount === null) return 'ศูนย์บาทถ้วน';
  
  // Round to 2 decimal places to avoid floating point issues
  amount = Math.round(amount * 100) / 100;
  
  if (amount === 0) return 'ศูนย์บาทถ้วน';
  
  const textNumbers = ['ศูนย์', 'หนึ่ง', 'สอง', 'สาม', 'สี่', 'ห้า', 'หก', 'เจ็ด', 'แปด', 'เก้า'];
  const textPositions = ['', 'สิบ', 'ร้อย', 'พัน', 'หมื่น', 'แสน', 'ล้าน'];
  
  const parts = amount.toString().split('.');
  const integerPart = parts[0];
  const decimalPart = parts[1] || '';
  
  let bahtStr = '';
  
  // Calculate million group
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
        bahtStr += textPositions[pos % 6];
      }
    }
    if (pos > 0 && pos % 6 === 0) {
      bahtStr += 'ล้าน';
    }
  }
  
  if (bahtStr !== '') bahtStr += 'บาท';
  
  let satangStr = '';
  if (decimalPart !== '') {
    // บังคับให้สตริงทศนิยมมีความยาว 2 หลักเสมอ เช่น .5 -> "50", .05 -> "05"
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

function updateDynamicDocTitle() {
  const docTypeSelect = document.querySelector('input[name="docType"]:checked');
  const docNumberInput = document.getElementById('docNumber');
  const docClientInput = document.getElementById('docClientName');
  
  let docTypeName = 'เอกสารการเงิน';
  if (docTypeSelect) {
    const val = docTypeSelect.value;
    if (val === 'quotation') docTypeName = 'ใบเสนอราคา';
    else if (val === 'invoice') docTypeName = 'ใบวางบิล';
    else if (val === 'receipt') docTypeName = 'ใบเสร็จรับเงิน';
  }
  
  const docNo = docNumberInput ? docNumberInput.value.trim() : '';
  const docClient = docClientInput ? docClientInput.value.trim() : '';
  
  // Clean up client name and document number for safe filename
  const cleanClient = docClient.replace(/[^a-zA-Z0-9ก-๙\s-_]/g, '').replace(/\s+/g, '_');
  const cleanDocNo = docNo.replace(/[^a-zA-Z0-9-_]/g, '');
  
  // Construct title: e.g. ใบเสนอราคา_QT2606-001_ลูกค้า
  let filename = docTypeName;
  if (cleanDocNo) filename += `_${cleanDocNo}`;
  if (cleanClient) filename += `_${cleanClient}`;
  
  document.title = filename;
}

// Expose callback handlers to the global window scope for inline HTML event triggers
window.setDocType = setDocType;
window.addDocItem = addDocItem;
window.deleteDocItem = deleteDocItem;
window.updateDocItem = updateDocItem;
window.initDocumentGenerator = initDocumentGenerator;
