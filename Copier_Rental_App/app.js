// ลอจิกการทำงานของระบบเช่าและซ่อมบำรุงเครื่องถ่ายเอกสาร - Main SaaS Theme
document.addEventListener("DOMContentLoaded", () => {
  let appData = { ...COPIER_DATA };

  // ==========================================
  // STATE & MAP CONFIG
  // ==========================================
  let currentCalendarDate = new Date(2026, 5, 17); // 17 June 2026 (matching system date context)
  let currentCalendarView = "month";
  let activeDrawerModel = null;
  let selectedShopId = null;

  const MAP_COORDINATES = {
    "S01": { x: 150, y: 270, tambon: "tambon-suthep" },
    "S02": { x: 410, y: 270, tambon: "tambon-watket" },
    "S03": { x: 270, y: 240, tambon: "tambon-moat" },
    "S04": { x: 280, y: 120, tambon: "tambon-changphueak" },
    "S05": { x: 240, y: 410, tambon: "tambon-padaet" }
  };

  const sidebarLinks = document.querySelectorAll(".menu-item");
  const viewSections = document.querySelectorAll(".view-section");
  const menuToggle = document.getElementById("menuToggle");
  const sidebar = document.getElementById("sidebar");

  const selectFilterTicket = document.getElementById("filterTicketStatus");
  if (selectFilterTicket) {
    selectFilterTicket.addEventListener("change", () => {
      renderTickets();
    });
  }

  if (menuToggle && sidebar) {
    menuToggle.addEventListener("click", () => {
      sidebar.classList.toggle("open");
    });
  }

  sidebarLinks.forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const targetView = link.getAttribute("data-view");
      
      sidebarLinks.forEach(l => l.classList.remove("active"));
      link.classList.add("active");

      viewSections.forEach(section => {
        section.classList.remove("active");
        if (section.id === targetView) {
          section.classList.add("active");
        }
      });

      if (sidebar && sidebar.classList.contains("open")) {
        sidebar.classList.remove("open");
      }

      renderView(targetView);
    });
  });

  function renderView(viewName) {
    switch (viewName) {
      case "dashboard-view":
        renderDashboard();
        break;
      case "tech-view":
        renderTechnicians();
        renderTickets();
        break;
      case "parts-view":
        renderParts();
        break;
      case "shops-view":
        renderShops();
        break;
      case "manuals-view":
        renderManuals();
        break;
    }
  }

  // ==========================================
  // 1. DASHBOARD VIEW
  // ==========================================
  function renderDashboard() {
    const today = new Date();
    const freeTechsCount = appData.technicians.filter(t => t.status === "Available").length;
    const activeJobsCount = appData.tickets.filter(t => t.status === "In Progress").length;
    const lowStockParts = appData.parts.filter(p => p.stock <= p.minStock).length;
    const overdueShopsCount = appData.shops.filter(s => {
      const nextDate = new Date(s.nextMaintenance);
      return nextDate < today;
    }).length;

    document.getElementById("statFreeTechs").innerText = `${freeTechsCount} / ${appData.technicians.length}`;
    document.getElementById("statActiveJobs").innerText = activeJobsCount;
    document.getElementById("statLowStock").innerText = lowStockParts;
    document.getElementById("statOverdue").innerText = overdueShopsCount;

    const alertProgress = document.getElementById("alertProgress");
    const alertLabel = document.getElementById("alertLabel");
    if (overdueShopsCount > 0) {
      const percent = Math.min(100, Math.round((overdueShopsCount / appData.shops.length) * 100));
      alertProgress.style.width = `${percent}%`;
      alertLabel.innerText = `มีเครื่องถ่ายเอกสารที่ขาดกำหนดเช็กระยะ ${percent}% (รวม ${overdueShopsCount} เครื่อง)`;
      document.getElementById("alertCardTitle").innerText = "ตรวจพบคงค้างเช็กระยะ!";
      document.getElementById("alertCardTitle").style.color = "#ef4444";
    } else {
      alertProgress.style.width = "100%";
      alertLabel.innerText = "เครื่องเช่าบำรุงรักษาครบตามกำหนดเรียบร้อย";
      document.getElementById("alertCardTitle").innerText = "ระบบปกติ";
      document.getElementById("alertCardTitle").style.color = "#10b981";
    }

    const activeJobsList = document.getElementById("dashActiveJobsList");
    activeJobsList.innerHTML = "";
    
    const activeTickets = appData.tickets.filter(t => t.status !== "Completed");
    if (activeTickets.length === 0) {
      activeJobsList.innerHTML = `<div class="row-sub-text" style="padding: 16px; text-align: center;">ไม่มีใบแจ้งซ่อมค้าง ณ ขณะนี้</div>`;
    } else {
      activeTickets.forEach(ticket => {
        const row = document.createElement("div");
        row.className = "row-card";
        row.style.gridTemplateColumns = "1.8fr 1.2fr 1fr";
        row.innerHTML = `
          <div class="row-card-title">
            <div class="row-icon">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:20px;height:20px;">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <div>
              <div class="row-main-text">${ticket.shopName}</div>
              <div class="row-sub-text">${ticket.issue}</div>
            </div>
          </div>
          <div class="row-info-block">
            <span class="row-info-label">ช่างที่รับผิดชอบ</span>
            <span class="row-info-value">${ticket.assignedTechName || "ยังไม่จ่ายงาน"}</span>
          </div>
          <div>
            <span class="badge ${ticket.status === 'In Progress' ? 'working' : 'danger'}">${ticket.status === 'In Progress' ? 'กำลังดำเนินการ' : 'รอมอบหมาย'}</span>
          </div>
        `;
        row.addEventListener("click", () => {
          document.querySelector('[data-view="tech-view"]').click();
        });
        activeJobsList.appendChild(row);
      });
    }
  }

  // ==========================================
  // 2. TECHNICIANS & CALENDAR VIEW
  // ==========================================
  // Bind calendar events
  const calPrevBtn = document.getElementById("calPrevBtn");
  const calNextBtn = document.getElementById("calNextBtn");
  const calTodayBtn = document.getElementById("calTodayBtn");
  const btnViewMonth = document.getElementById("btnViewMonth");
  const btnViewWeek = document.getElementById("btnViewWeek");
  const btnViewDay = document.getElementById("btnViewDay");

  if (calPrevBtn) calPrevBtn.addEventListener("click", () => adjustCalendarDate(-1));
  if (calNextBtn) calNextBtn.addEventListener("click", () => adjustCalendarDate(1));
  if (calTodayBtn) calTodayBtn.addEventListener("click", () => {
    currentCalendarDate = new Date(2026, 5, 17);
    renderCalendar();
  });

  const calendarToggleBtns = [btnViewMonth, btnViewWeek, btnViewDay];
  calendarToggleBtns.forEach(btn => {
    if (btn) {
      btn.addEventListener("click", () => {
        const view = btn.getAttribute("data-view");
        currentCalendarView = view;
        
        calendarToggleBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        
        document.querySelectorAll(".calendar-view-panel").forEach(p => p.classList.remove("active"));
        if (view === "month") document.getElementById("calendarMonthView").classList.add("active");
        if (view === "week") document.getElementById("calendarWeekView").classList.add("active");
        if (view === "day") document.getElementById("calendarDayView").classList.add("active");
        
        renderCalendar();
      });
    }
  });

  function adjustCalendarDate(direction) {
    if (currentCalendarView === "month") {
      currentCalendarDate.setMonth(currentCalendarDate.getMonth() + direction);
    } else if (currentCalendarView === "week") {
      currentCalendarDate.setDate(currentCalendarDate.getDate() + (direction * 7));
    } else if (currentCalendarView === "day") {
      currentCalendarDate.setDate(currentCalendarDate.getDate() + direction);
    }
    renderCalendar();
  }

  function renderCalendar() {
    const title = document.getElementById("calendarTitle");
    if (!title) return;
    const thaiMonths = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"];
    
    if (currentCalendarView === "month") {
      const monthName = thaiMonths[currentCalendarDate.getMonth()];
      const yearName = currentCalendarDate.getFullYear() + 543;
      title.innerText = `${monthName} ${yearName}`;
      renderMonthCalendar();
    } else if (currentCalendarView === "week") {
      const startOfWeek = new Date(currentCalendarDate);
      startOfWeek.setDate(currentCalendarDate.getDate() - currentCalendarDate.getDay());
      const endOfWeek = new Date(startOfWeek);
      endOfWeek.setDate(startOfWeek.getDate() + 6);
      
      const startDay = startOfWeek.getDate();
      const startMonth = thaiMonths[startOfWeek.getMonth()];
      const endDay = endOfWeek.getDate();
      const endMonth = thaiMonths[endOfWeek.getMonth()];
      const year = startOfWeek.getFullYear() + 543;
      
      title.innerText = `${startDay} ${startMonth} - ${endDay} ${endMonth} ${year}`;
      renderWeekCalendar(startOfWeek);
    } else if (currentCalendarView === "day") {
      const dayName = ["อาทิตย์", "จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์"][currentCalendarDate.getDay()];
      const dateStr = currentCalendarDate.getDate();
      const monthStr = thaiMonths[currentCalendarDate.getMonth()];
      const yearStr = currentCalendarDate.getFullYear() + 543;
      title.innerText = `วัน${dayName}ที่ ${dateStr} ${monthStr} ${yearStr}`;
      renderDayCalendar();
    }
  }

  function renderMonthCalendar() {
    const grid = document.getElementById("calendarDaysGrid");
    if (!grid) return;
    grid.innerHTML = "";
    
    const year = currentCalendarDate.getFullYear();
    const month = currentCalendarDate.getMonth();
    
    const firstDay = new Date(year, month, 1).getDay();
    const numDays = new Date(year, month + 1, 0).getDate();
    const prevNumDays = new Date(year, month, 0).getDate();
    
    // Previous month padding
    for (let i = firstDay - 1; i >= 0; i--) {
      const cell = document.createElement("div");
      cell.className = "calendar-day-cell inactive";
      cell.innerHTML = `<span class="day-number">${prevNumDays - i}</span>`;
      grid.appendChild(cell);
    }
    
    // Current month days
    for (let d = 1; d <= numDays; d++) {
      const cell = document.createElement("div");
      const isToday = d === 17 && month === 5 && year === 2026;
      cell.className = `calendar-day-cell${isToday ? ' today' : ''}`;
      cell.innerHTML = `<span class="day-number">${d}</span><div class="calendar-day-jobs"></div>`;
      
      cell.addEventListener("click", () => {
        currentCalendarDate = new Date(year, month, d);
        currentCalendarView = "day";
        
        calendarToggleBtns.forEach(b => b.classList.remove("active"));
        btnViewDay.classList.add("active");
        
        document.querySelectorAll(".calendar-view-panel").forEach(p => p.classList.remove("active"));
        document.getElementById("calendarDayView").classList.add("active");
        
        renderCalendar();
      });

      const dateString = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      const dayJobs = appData.tickets.filter(t => t.date === dateString);
      const jobsContainer = cell.querySelector(".calendar-day-jobs");
      
      dayJobs.forEach(job => {
        const badge = document.createElement("div");
        badge.className = `calendar-job-badge ${job.status.replace(" ", "-")}`;
        badge.title = `${job.shopName}: ${job.issue}`;
        badge.innerText = `${job.assignedTechName ? job.assignedTechName.split(" ")[1] : 'ยังไม่ระบุช่าง'}`;
        jobsContainer.appendChild(badge);
      });
      
      grid.appendChild(cell);
    }
    
    // Next month padding
    const totalCells = firstDay + numDays;
    const nextPadding = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
    for (let i = 1; i <= nextPadding; i++) {
      const cell = document.createElement("div");
      cell.className = "calendar-day-cell inactive";
      cell.innerHTML = `<span class="day-number">${i}</span>`;
      grid.appendChild(cell);
    }
  }

  function renderWeekCalendar(startOfWeek) {
    const grid = document.getElementById("calendarWeekGrid");
    if (!grid) return;
    grid.innerHTML = "";
    
    const weekdays = ["อา.", "จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส."];
    
    for (let i = 0; i < 7; i++) {
      const day = new Date(startOfWeek);
      day.setDate(startOfWeek.getDate() + i);
      
      const col = document.createElement("div");
      col.className = "calendar-week-col";
      
      const isToday = day.getDate() === 17 && day.getMonth() === 5 && day.getFullYear() === 2026;
      
      col.innerHTML = `
        <div class="calendar-week-header${isToday ? ' today' : ''}">
          <div>${weekdays[i]}</div>
          <div style="font-size: 16px; margin-top:2px;">${day.getDate()}</div>
        </div>
        <div class="calendar-week-body"></div>
      `;
      
      const dateString = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`;
      const dayJobs = appData.tickets.filter(t => t.date === dateString);
      const body = col.querySelector(".calendar-week-body");
      
      if (dayJobs.length === 0) {
        body.innerHTML = `<div style="font-size:10px; color:var(--ink-muted); text-align:center; margin-top:12px;">ไม่มีงาน</div>`;
      } else {
        dayJobs.forEach(job => {
          const card = document.createElement("div");
          card.className = "calendar-week-job";
          
          let statusColor = "var(--status-danger-text)";
          let statusBg = "var(--status-danger-bg)";
          if (job.status === "In Progress") {
            statusColor = "var(--status-working-text)";
            statusBg = "var(--status-working-bg)";
          } else if (job.status === "Completed") {
            statusColor = "var(--status-available-text)";
            statusBg = "var(--status-available-bg)";
          }
          
          card.innerHTML = `
            <div class="calendar-week-job-time">เคสซ่อมด่วน</div>
            <div class="calendar-week-job-title" style="color:var(--ink-dark);">${job.shopName}</div>
            <div style="font-size: 10px; color:var(--ink-muted); margin-top:2px;">ช่าง: ${job.assignedTechName || 'ยังไม่ระบุ'}</div>
            <div style="margin-top:6px;">
              <span class="badge" style="background-color:${statusBg}; color:${statusColor}; font-size:9px; padding:2px 6px; border:1.5px solid var(--ink-dark);">${job.status === 'In Progress' ? 'กำลังซ่อม' : (job.status === 'Completed' ? 'เสร็จสิ้น' : 'รอมอบหมาย')}</span>
            </div>
          `;
          card.addEventListener("click", () => {
            document.querySelector('[data-view="tech-view"]').click();
          });
          body.appendChild(card);
        });
      }
      grid.appendChild(col);
    }
  }

  function renderDayCalendar() {
    const container = document.getElementById("calendarDaySchedule");
    if (!container) return;
    container.innerHTML = "";
    
    const dateString = `${currentCalendarDate.getFullYear()}-${String(currentCalendarDate.getMonth() + 1).padStart(2, '0')}-${String(currentCalendarDate.getDate()).padStart(2, '0')}`;
    const dayJobs = appData.tickets.filter(t => t.date === dateString);
    
    // Create Header with "+ เพิ่มงานวันนี้" button
    const headerDiv = document.createElement("div");
    headerDiv.style.display = "flex";
    headerDiv.style.justify = "space-between";
    headerDiv.style.alignItems = "center";
    headerDiv.style.marginBottom = "20px";
    headerDiv.style.paddingBottom = "12px";
    headerDiv.style.borderBottom = "1.5px dashed var(--ink-dark)";
    headerDiv.innerHTML = `
      <span style="font-weight:700; font-size:14px; color:var(--ink-dark);">ตารางตั๋วงานประจำวัน</span>
      <button class="btn-primary" id="btnNewTicketForDay" style="padding:6px 12px; font-size:12px; margin-bottom:0; box-shadow: 2px 2px 0px var(--ink-dark); display: flex; align-items: center; gap: 4px;">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:14px;height:14px;">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4" />
        </svg>
        + เพิ่มงานวันนี้
      </button>
    `;
    container.appendChild(headerDiv);
    
    const btnNewTicketForDay = headerDiv.querySelector("#btnNewTicketForDay");
    if (btnNewTicketForDay) {
      btnNewTicketForDay.addEventListener("click", () => {
        openNewTicketModalWithDate(dateString);
      });
    }
    
    if (dayJobs.length === 0) {
      const emptyDiv = document.createElement("div");
      emptyDiv.style.textAlign = "center";
      emptyDiv.style.padding = "40px";
      emptyDiv.style.color = "var(--ink-muted)";
      emptyDiv.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:48px;height:48px;margin:0 auto 16px;color:#cbd5e1;">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <div style="font-size:14px; font-weight:600;">ไม่มีใบแจ้งซ่อมถูกนัดหมายการทำงานในวันนี้</div>
      `;
      container.appendChild(emptyDiv);
    } else {
      dayJobs.forEach(job => {
        const card = document.createElement("div");
        card.className = "calendar-day-job-card";
        
        let statusClass = "danger";
        let statusTh = "รอมอบหมาย";
        if (job.status === "In Progress") {
          statusClass = "working";
          statusTh = "กำลังปฏิบัติงาน";
        } else if (job.status === "Completed") {
          statusClass = "available";
          statusTh = "เสร็จสิ้นงาน";
        }
        
        card.innerHTML = `
          <div>
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="badge ${statusClass}">${statusTh}</span>
              <span style="font-family:var(--font-mono); font-size:11px; color:var(--ink-muted);">${job.id}</span>
            </div>
            <h3 style="font-size:16px; margin:8px 0 4px;">${job.shopName}</h3>
            <p class="row-sub-text">อาการเสีย: ${job.issue} | รุ่นเครื่อง: ${job.copierModel}</p>
          </div>
          <div style="text-align:right;">
            <div style="font-size:11px; color:var(--ink-muted);">ช่างเทคนิค</div>
            <div style="font-weight:700; margin-top:2px;">${job.assignedTechName || 'ยังไม่ได้มอบหมาย'}</div>
          </div>
        `;
        card.addEventListener("click", () => {
          document.querySelector('[data-view="tech-view"]').click();
        });
        container.appendChild(card);
      });
    }
  }

  function renderTechnicians() {
    const techList = document.getElementById("techList");
    if (!techList) return;
    techList.innerHTML = "";

    appData.technicians.forEach(tech => {
      const card = document.createElement("div");
      card.className = "row-card";
      card.style.gridTemplateColumns = "1.5fr 1fr 1fr 1.2fr";
      
      let badgeClass = "available";
      let statusTh = "ว่างพร้อมทำงาน";
      if (tech.status === "Working") {
        badgeClass = "working";
        statusTh = `ซ่อมบำรุง: ${tech.currentJob || "หน้างานเช่า"}`;
      } else if (tech.status === "Break") {
        badgeClass = "break";
        statusTh = "พักผ่อน";
      }

      card.innerHTML = `
        <div class="row-card-title">
          <div class="row-icon">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:20px;height:20px;">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <div>
            <div class="row-main-text">${tech.name}</div>
            <div class="row-sub-text">รหัสช่าง: ${tech.id} | เบอร์โทร: ${tech.phone}</div>
          </div>
        </div>
        <div class="row-info-block">
          <span class="row-info-label">สถานะปัจจุบัน</span>
          <span class="badge ${badgeClass}" style="margin-top: 4px;">${statusTh}</span>
        </div>
        <div class="row-info-block">
          <span class="row-info-label">รีวิวการซ่อม</span>
          <span class="row-info-value">⭐ ${tech.rating} / 5.0</span>
        </div>
        <div style="display:flex; justify-content: flex-end;">
          <select class="filter-select select-tech-status" data-tech-id="${tech.id}" style="padding: 6px 12px; border-radius:10px;">
            <option value="Available" ${tech.status === 'Available' ? 'selected' : ''}>ว่าง</option>
            <option value="Working" ${tech.status === 'Working' ? 'selected' : ''}>ซ่อมงาน</option>
            <option value="Break" ${tech.status === 'Break' ? 'selected' : ''}>พัก</option>
          </select>
        </div>
      `;

      const selectStatus = card.querySelector(".select-tech-status");
      selectStatus.addEventListener("change", (e) => {
        const newStatus = e.target.value;
        const techId = e.target.getAttribute("data-tech-id");
        updateTechStatus(techId, newStatus);
      });

      techList.appendChild(card);
    });

    renderCalendar();
  }

  function updateTechStatus(techId, status) {
    const tech = appData.technicians.find(t => t.id === techId);
    if (tech) {
      tech.status = status;
      if (status !== "Working") {
        tech.currentJob = null;
      }
      renderTechnicians();
      renderDashboard();
    }
  }

  // ==========================================
  // 3. SPARE PARTS INVENTORY VIEW (drawer cabinet)
  // ==========================================
  const drawers = document.querySelectorAll(".cabinet-drawer");

  drawers.forEach(drawer => {
    drawer.addEventListener("click", () => {
      const model = drawer.getAttribute("data-model");
      toggleCabinetDrawer(model);
    });
  });

  // Bind close buttons inside dropdowns
  document.querySelectorAll(".btn-close-drawer-inside").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      closeDrawer();
    });
  });

  function toggleCabinetDrawer(model) {
    if (activeDrawerModel === model) {
      closeDrawer();
      return;
    }
    
    closeDrawer(); // close any currently open first
    activeDrawerModel = model;
    
    // Find drawer element and slot group
    const targetDrawer = document.querySelector(`.cabinet-drawer[data-model="${model}"]`);
    if (targetDrawer) {
      targetDrawer.classList.add("active");
    }
    
    // Open the corresponding dropdown details
    const dropdownId = getDropdownIdByModel(model);
    const dropdown = document.getElementById(dropdownId);
    if (dropdown) {
      dropdown.classList.add("open");
    }
    
    renderDrawerPartsList();
  }

  function getDropdownIdByModel(model) {
    if (model.includes("Canon")) return "details-canon";
    if (model.includes("Ricoh")) return "details-ricoh";
    return "details-hp";
  }

  function getListIdByModel(model) {
    if (model.includes("Canon")) return "list-canon";
    if (model.includes("Ricoh")) return "list-ricoh";
    return "list-hp";
  }

  function closeDrawer() {
    activeDrawerModel = null;
    drawers.forEach(d => d.classList.remove("active"));
    document.querySelectorAll(".drawer-dropdown-details").forEach(d => {
      d.classList.remove("open");
    });
  }

  function updateDrawerSummaries() {
    const models = [
      { id: "summary-canon", name: "Canon iR-A 4535" },
      { id: "summary-ricoh", name: "Ricoh IM C3000" },
      { id: "summary-hp", name: "HP LaserJet Managed E82560" }
    ];
    
    models.forEach(model => {
      const element = document.getElementById(model.id);
      if (!element) return;
      
      const modelParts = appData.parts.filter(p => p.compatible.includes(model.name));
      const lowStockCount = modelParts.filter(p => p.stock <= p.minStock).length;
      
      if (lowStockCount > 0) {
        element.innerText = `อะไหล่ใกล้หมด (${lowStockCount})`;
        element.className = "drawer-stock-indicator badge danger";
      } else {
        element.innerText = `มีของพอดี (${modelParts.length})`;
        element.className = "drawer-stock-indicator badge available";
      }
    });
  }

  function renderDrawerPartsList() {
    if (!activeDrawerModel) return;
    
    const listId = getListIdByModel(activeDrawerModel);
    const list = document.getElementById(listId);
    if (!list) return;
    list.innerHTML = "";
    
    const searchVal = document.getElementById("searchPartsInput").value.toLowerCase();
    const filterLow = document.getElementById("filterPartsStock").value;
    
    let modelParts = appData.parts.filter(p => p.compatible.includes(activeDrawerModel));
    
    let filteredParts = modelParts.filter(part => {
      const matchSearch = part.name.toLowerCase().includes(searchVal) || part.compatible.toLowerCase().includes(searchVal);
      if (filterLow === "low") {
        return matchSearch && part.stock <= part.minStock;
      }
      return matchSearch;
    });
    
    if (filteredParts.length === 0) {
      list.innerHTML = `<div class="row-sub-text" style="padding: 16px; text-align: center;">ไม่พบชิ้นส่วนอะไหล่ที่ตรงตามคำค้นหาในลิ้นชักนี้</div>`;
      return;
    }
    
    const table = document.createElement("table");
    table.className = "parts-table";
    table.innerHTML = `
      <thead>
        <tr>
          <th style="text-align: left;">ชื่อชิ้นส่วนอะไหล่</th>
          <th style="text-align: center; width: 100px;">คงเหลือ</th>
          <th style="text-align: center; width: 120px;">สถานะ</th>
          <th style="text-align: right; width: 140px;">ปรับจำนวน</th>
        </tr>
      </thead>
      <tbody>
      </tbody>
    `;
    
    const tbody = table.querySelector("tbody");
    
    filteredParts.forEach(part => {
      const isLow = part.stock <= part.minStock;
      const tr = document.createElement("tr");
      if (isLow) {
        tr.className = "low-stock-row";
      }
      
      tr.innerHTML = `
        <td>
          <div style="font-weight: 600; color: var(--ink-dark);">${part.name}</div>
          <div style="font-size: 11px; color: var(--ink-muted); margin-top: 2px;">รุ่นเครื่อง: ${part.compatible}</div>
        </td>
        <td style="text-align: center;">
          <span style="font-family: var(--font-mono); font-weight: 700; color: ${isLow ? '#ef4444' : 'var(--ink-dark)'}; font-size: 14px;">
            ${part.stock}
          </span>
          <span style="font-size: 11px; color: var(--ink-muted);"> ${part.unit}</span>
        </td>
        <td style="text-align: center;">
          <span class="badge ${isLow ? 'danger' : 'available'}" style="font-size: 10px; padding: 2px 8px;">
            ${isLow ? 'ใกล้หมดคลัง' : 'มีเพียงพอ'}
          </span>
          <div style="font-size: 9px; color: var(--ink-muted); margin-top: 2px;">(ขั้นต่ำ ${part.minStock})</div>
        </td>
        <td style="text-align: right;">
          <div style="display: flex; gap: 6px; justify-content: flex-end;">
            <button class="btn-secondary btn-stock-adjust" data-part-id="${part.id}" data-action="decrease" style="padding: 4px 8px; font-size: 11px; margin-bottom: 0; box-shadow: 1px 1px 0px var(--ink-dark); font-weight: 700;">-1</button>
            <button class="btn-secondary btn-stock-adjust" data-part-id="${part.id}" data-action="increase" style="padding: 4px 8px; font-size: 11px; margin-bottom: 0; box-shadow: 1px 1px 0px var(--ink-dark); font-weight: 700;">+1</button>
          </div>
        </td>
      `;
      
      const btnAdjusts = tr.querySelectorAll(".btn-stock-adjust");
      btnAdjusts.forEach(btn => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const action = btn.getAttribute("data-action");
          const partId = btn.getAttribute("data-part-id");
          adjustStock(partId, action);
        });
      });
      
      tbody.appendChild(tr);
    });
    
    list.appendChild(table);
  }

  function renderParts() {
    updateDrawerSummaries();
    if (activeDrawerModel) {
      renderDrawerPartsList();
    }
  }

  function adjustStock(partId, action) {
    const part = appData.parts.find(p => p.id === partId);
    if (part) {
      if (action === "increase") {
        part.stock += 1;
      } else if (action === "decrease" && part.stock > 0) {
        part.stock -= 1;
      }
      renderParts();
      renderDashboard();
    }
  }

  document.getElementById("searchPartsInput").addEventListener("input", renderParts);
  document.getElementById("filterPartsStock").addEventListener("change", renderParts);

  // ==========================================
  // 4. RENTAL SHOPS & CHIANG MAI MAP VIEW
  // ==========================================
  function renderShopsMap() {
    const pinsGroup = document.getElementById("mapPinsGroup");
    if (!pinsGroup) return;
    pinsGroup.innerHTML = "";
    
    const today = new Date();
    
    appData.shops.forEach(shop => {
      const coords = MAP_COORDINATES[shop.id];
      if (!coords) return;
      
      const nextDate = new Date(shop.nextMaintenance);
      const isOverdue = nextDate < today;
      
      const pinG = document.createElementNS("http://www.w3.org/2000/svg", "g");
      pinG.setAttribute("class", "map-pin-group");
      pinG.setAttribute("data-shop-id", shop.id);
      
      const pulseCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      pulseCircle.setAttribute("cx", coords.x);
      pulseCircle.setAttribute("cy", coords.y);
      pulseCircle.setAttribute("r", isOverdue ? 14 : 11);
      pulseCircle.setAttribute("class", "map-pin-pulse");
      pulseCircle.setAttribute("fill", isOverdue ? "rgba(239, 68, 68, 0.45)" : "rgba(34, 197, 94, 0.45)");
      
      const coreCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      coreCircle.setAttribute("cx", coords.x);
      coreCircle.setAttribute("cy", coords.y);
      coreCircle.setAttribute("r", 7);
      coreCircle.setAttribute("class", "map-pin-core");
      coreCircle.setAttribute("fill", isOverdue ? "#ef4444" : "#22c55e");
      coreCircle.setAttribute("stroke", "#0f172a");
      coreCircle.setAttribute("stroke-width", "1.5");
      
      const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
      title.textContent = `${shop.name} (${shop.copierModel})`;
      pinG.appendChild(title);
      
      pinG.appendChild(pulseCircle);
      pinG.appendChild(coreCircle);
      
      pinG.addEventListener("click", () => {
        selectShopOnMap(shop.id);
      });
      
      pinsGroup.appendChild(pinG);
    });
  }

  function selectShopOnMap(shopId) {
    selectedShopId = shopId;
    
    // Highlight pin on map
    const pins = document.querySelectorAll(".map-pin-group");
    pins.forEach(pin => {
      const isSelected = pin.getAttribute("data-shop-id") === shopId;
      const core = pin.querySelector(".map-pin-core");
      if (core) {
        if (isSelected) {
          core.setAttribute("stroke-width", "3");
          core.setAttribute("stroke", "var(--primary)");
          core.setAttribute("r", "9");
        } else {
          core.setAttribute("stroke-width", "1.5");
          core.setAttribute("stroke", "#0f172a");
          core.setAttribute("r", "7");
        }
      }
    });

    // Highlight Tambon path in SVG
    const shopCoords = MAP_COORDINATES[shopId];
    document.querySelectorAll(".map-tambon").forEach(t => t.classList.remove("selected"));
    if (shopCoords && shopCoords.tambon) {
      const tambonPath = document.getElementById(shopCoords.tambon);
      if (tambonPath) {
        tambonPath.classList.add("selected");
      }
    }
    
    // Render detail card
    const detailCard = document.getElementById("selectedShopDetailCard");
    const shop = appData.shops.find(s => s.id === shopId);
    if (shop && detailCard) {
      const today = new Date();
      const nextDate = new Date(shop.nextMaintenance);
      const isOverdue = nextDate < today;
      
      // Query active tickets for this shop
      const activeTickets = appData.tickets.filter(t => t.shopId === shopId && t.status !== "Completed");
      let activeTicketsHTML = "";
      if (activeTickets.length > 0) {
        activeTicketsHTML = `
          <div style="background:#fee2e2; border:1.5px solid var(--ink-dark); padding:10px; border-radius:8px; margin-top:4px; box-shadow:2px 2px 0px var(--ink-dark);">
            <strong style="color:var(--status-danger-text); font-size:11px; text-transform:uppercase;">ตั๋วแจ้งซ่อมค้างในระบบ:</strong>
            <div style="display:flex; flex-direction:column; gap:6px; margin-top:4px;">
              ${activeTickets.map(t => `
                <div style="font-size:12px; display:flex; justify-content:space-between; align-items:center;">
                  <span style="font-weight:600;">${t.id}: <span style="font-weight:400; color:var(--ink-muted);">${t.issue}</span></span>
                  <span class="badge ${t.status === 'In Progress' ? 'working' : 'danger'}" style="font-size:9px; padding:2px 6px; margin-left:4px; flex-shrink:0;">${t.status === 'In Progress' ? 'กำลังซ่อม' : 'รอช่าง'}</span>
                </div>
              `).join("")}
            </div>
          </div>
        `;
      }
      
      detailCard.style.display = "block";
      detailCard.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom: 1.5px dashed var(--ink-dark); padding-bottom:12px; margin-bottom:16px;">
          <div>
            <span class="badge ${isOverdue ? 'danger' : 'available'}" style="margin-bottom:6px;">${isOverdue ? 'เลยกำหนดเช็กระยะ' : 'ปกติ'}</span>
            <h3 style="font-size:16px;">${shop.name}</h3>
          </div>
          <button class="btn-secondary" id="btnCloseShopDetail" style="padding:4px 8px; font-size:11px; margin-bottom:0;">ปิด</button>
        </div>
        <div style="font-size:13px; display:flex; flex-direction:column; gap:10px;">
          <div>
            <strong>ที่อยู่:</strong> <span class="row-sub-text" style="display:inline; color:var(--ink-dark);">${shop.address}</span>
          </div>
          <div>
            <strong>เครื่องเช่า:</strong> <span class="row-info-value" style="color:var(--primary); font-weight:700;">${shop.copierModel}</span> <span style="font-family:var(--font-mono); font-size:11px;">(S/N: ${shop.serialNumber})</span>
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:4px;">
            <div class="row-info-block" style="background:#f8fafc; padding:8px; border:1.5px solid var(--ink-dark); border-radius:8px; box-shadow:2px 2px 0px var(--ink-dark);">
              <span class="row-info-label">ทำรอบล่าสุด</span>
              <span class="row-info-value">${formatThaiDate(shop.lastMaintenance)}</span>
            </div>
            <div class="row-info-block" style="background:#f8fafc; padding:8px; border:1.5px solid var(--ink-dark); border-radius:8px; box-shadow:2px 2px 0px var(--ink-dark);">
              <span class="row-info-label">กำหนดตรวจถัดไป</span>
              <span class="row-info-value ${isOverdue ? 'badge danger' : ''}" style="width:fit-content; font-size:12px; margin-top:4px;">${formatThaiDate(shop.nextMaintenance)}</span>
            </div>
          </div>
          <div style="background:#fffbeb; border:1.5px solid var(--ink-dark); padding:10px; border-radius:8px; margin-top:4px; box-shadow:2px 2px 0px var(--ink-dark);">
            <strong style="color:#b45309; font-size:11px; text-transform:uppercase;">บันทึกอาการซ่อมบำรุงล่าสุด:</strong>
            <p style="font-size:12px; color:#92400e; margin-top:2px; line-height:1.4;">${shop.maintenanceNotes}</p>
          </div>
          ${activeTicketsHTML}
          <div style="display:flex; gap:12px; margin-top:8px;">
            <button class="btn-primary btn-qr-shop-inside" data-shop-id="${shop.id}" style="flex:1; justify-content:center; padding:8px; font-size:12px; margin-bottom:0;">
              สแกน QR หน้างาน
            </button>
            <button class="btn-secondary btn-create-ticket-for-shop" data-shop-id="${shop.id}" style="justify-content:center; padding:8px; font-size:12px; margin-bottom:0; box-shadow: 2px 2px 0px var(--ink-dark);">
              แจ้งซ่อม
            </button>
          </div>
        </div>
      `;
      
      detailCard.querySelector(".btn-qr-shop-inside").addEventListener("click", () => {
        openQRModal(shop.id);
      });
      
      detailCard.querySelector(".btn-create-ticket-for-shop").addEventListener("click", () => {
        openCreateTicketForShop(shop.id);
      });
      
      detailCard.querySelector("#btnCloseShopDetail").addEventListener("click", () => {
        detailCard.style.display = "none";
        selectedShopId = null;
        pins.forEach(pin => {
          const core = pin.querySelector(".map-pin-core");
          if (core) {
            core.setAttribute("stroke-width", "1.5");
            core.setAttribute("stroke", "#0f172a");
            core.setAttribute("r", "7");
          }
        });
        document.querySelectorAll(".map-tambon").forEach(t => t.classList.remove("selected"));
        renderShopsList();
      });
      
      detailCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    renderShopsList();
  }

  // Helper function to get common issues based on copier model
  function getCommonIssuesForModel(model) {
    const manual = appData.manuals.find(m => m.model === model);
    const issues = [];
    
    // Add default general items first
    issues.push("รอบเช็กระยะประจำ 3 เดือน");
    issues.push("ผงหมึกใกล้หมดต้องการหลอดหมึกสีดำสำรอง");
    
    // Add model-specific common issues
    if (manual && manual.commonIssues) {
      manual.commonIssues.forEach(item => {
        issues.push(item.issue);
      });
    }
    
    // Add other option at the end
    issues.push("อื่นๆ (พิมพ์ระบุอาการด้วยตนเอง)");
    return issues;
  }

  function openCreateTicketForShop(shopId) {
    const shop = appData.shops.find(s => s.id === shopId);
    if (!shop) return;
    
    document.getElementById("modalOverlay").style.display = "flex";
    document.getElementById("modalBody").innerHTML = `
      <h3 style="margin-bottom:16px; font-family:var(--font-title);">สร้างใบแจ้งซ่อมด่วน</h3>
      <div style="display:flex; flex-direction:column; gap:16px;">
        <div class="form-group">
          <label class="form-label">ร้านค้าเช่าเครื่องถ่ายเอกสาร</label>
          <input type="text" class="form-control" value="${shop.name}" disabled style="background:#f1f5f9; border: 1.5px solid var(--ink-dark);">
        </div>
        <div class="form-group">
          <label class="form-label">วันที่ต้องการนัดหมายเข้าซ่อม</label>
          <input type="date" class="form-control" id="newTicketDate" value="${new Date().toISOString().split("T")[0]}" style="border: 1.5px solid var(--ink-dark);">
        </div>
        <div class="form-group">
          <label class="form-label">ระบุรายละเอียดอาการเสียหาย</label>
          <select class="filter-select" id="newTicketIssueSelect" style="width:100%; border: 1.5px solid var(--ink-dark); margin-bottom: 12px;"></select>
          <textarea class="form-control" id="newTicketIssue" rows="3" placeholder="ระบุอาการชำรุดเพิ่มเติม..." style="resize:none; font-family:inherit; border: 1.5px solid var(--ink-dark); display:none;"></textarea>
        </div>
        <button class="btn-primary" id="btnSubmitNewTicket" style="justify-content:center; box-shadow: 3px 3px 0px #000;">บันทึกตั๋วแจ้งซ่อม</button>
      </div>
    `;
    
    const issueSelect = document.getElementById("newTicketIssueSelect");
    const issueTextarea = document.getElementById("newTicketIssue");
    
    const issues = getCommonIssuesForModel(shop.copierModel);
    issueSelect.innerHTML = issues.map(issue => `<option value="${issue}">${issue}</option>`).join("");
    
    function toggleTextarea() {
      if (issueSelect.value.startsWith("อื่นๆ")) {
        issueTextarea.style.display = "block";
        issueTextarea.required = true;
        issueTextarea.placeholder = "พิมพ์ระบุอาการชำรุดด้วยตนเอง...";
      } else {
        issueTextarea.style.display = "none";
        issueTextarea.required = false;
        issueTextarea.value = "";
      }
    }
    
    issueSelect.addEventListener("change", toggleTextarea);
    toggleTextarea();
    
    document.getElementById("btnSubmitNewTicket").addEventListener("click", () => {
      const selectedIssue = issueSelect.value;
      const customIssue = issueTextarea.value.trim();
      const date = document.getElementById("newTicketDate").value;
      
      let finalIssue = selectedIssue;
      if (selectedIssue.startsWith("อื่นๆ")) {
        if (!customIssue) {
          alert("กรุณากรอกอาการชำรุด");
          return;
        }
        finalIssue = customIssue;
      }
      
      const newId = `TK-${String(appData.tickets.length + 1).padStart(3, "0")}`;
      const newTicket = {
        id: newId,
        shopId: shop.id,
        shopName: shop.name,
        copierModel: shop.copierModel,
        issue: finalIssue,
        assignedTechId: null,
        assignedTechName: null,
        status: "Pending",
        date: date || new Date().toISOString().split("T")[0]
      };
      
      appData.tickets.push(newTicket);
      closeModal();
      renderDashboard();
      renderTechnicians(); // Sync to calendar!
      renderShopsMap();    // Sync map details!
      renderShops();       // Refresh shop details card!
      
      const ticketLink = document.querySelector('[data-view="tech-view"]');
      if (ticketLink) ticketLink.click();
    });
  }

  function renderShopsList() {
    const list = document.getElementById("shopsList");
    if (!list) return;
    list.innerHTML = "";
    
    const searchVal = document.getElementById("searchShopsInput").value.toLowerCase();
    const today = new Date();
    
    let filteredShops = appData.shops.filter(shop => {
      return shop.name.toLowerCase().includes(searchVal) || 
             shop.copierModel.toLowerCase().includes(searchVal) || 
             shop.serialNumber.toLowerCase().includes(searchVal);
    });
    
    filteredShops.forEach(shop => {
      const nextDate = new Date(shop.nextMaintenance);
      const isOverdue = nextDate < today;
      const isSelected = selectedShopId === shop.id;
      
      const card = document.createElement("div");
      card.className = "row-card";
      card.style.gridTemplateColumns = "2.2fr 1.2fr 1.2fr 0.8fr";
      if (isSelected) {
        card.style.borderColor = "var(--primary)";
        card.style.boxShadow = "var(--solid-shadow-hover)";
        card.style.transform = "translate(-2px, -2px)";
      } else if (isOverdue) {
        card.style.borderColor = "#ef4444";
      }

      card.innerHTML = `
        <div class="row-card-title">
          <div class="row-icon">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:20px;height:20px;">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
          </div>
          <div>
            <div class="row-main-text">${shop.name}</div>
            <div class="row-sub-text" style="font-size:11px;">${shop.address.substring(0, 35)}...</div>
            <div class="row-sub-text" style="color:var(--primary); font-weight:600; margin-top:4px;">
              เครื่อง: ${shop.copierModel}
            </div>
          </div>
        </div>
        <div class="row-info-block">
          <span class="row-info-label">ทำรอบล่าสุด</span>
          <span class="row-info-value" style="font-size:12px;">${formatThaiDate(shop.lastMaintenance)}</span>
        </div>
        <div class="row-info-block">
          <span class="row-info-label">กำหนดตรวจถัดไป</span>
          <span class="row-info-value ${isOverdue ? 'badge danger' : ''}" style="width:fit-content; margin-top:2px; font-size:11px;">
            ${formatThaiDate(shop.nextMaintenance)}
          </span>
        </div>
        <div style="display:flex; justify-content: flex-end;">
          <button class="btn-secondary btn-select-shop" style="padding:6px 12px; font-size:12px; border-radius:10px; margin-bottom:0; box-shadow:2px 2px 0px var(--ink-dark);">
            ดูพิกัด
          </button>
        </div>
      `;

      card.querySelector(".btn-select-shop").addEventListener("click", (e) => {
        e.stopPropagation();
        selectShopOnMap(shop.id);
      });
      
      card.addEventListener("click", () => {
        selectShopOnMap(shop.id);
      });

      list.appendChild(card);
    });
  }

  function renderShops() {
    renderShopsList();
    renderShopsMap();
    
    // Auto highlight path if selected
    if (selectedShopId) {
      const coords = MAP_COORDINATES[selectedShopId];
      if (coords && coords.tambon) {
        const path = document.getElementById(coords.tambon);
        if (path) path.classList.add("selected");
      }
    }
  }

  document.getElementById("searchShopsInput").addEventListener("input", renderShops);

  function renderTickets() {
    const ticketsList = document.getElementById("ticketsList");
    if (!ticketsList) return;
    ticketsList.innerHTML = "";
    const filterVal = typeof selectFilterTicket !== 'undefined' ? selectFilterTicket.value : "all";
    let filteredTickets = appData.tickets;

    if (filterVal !== "all") {
      filteredTickets = appData.tickets.filter(t => t.status === filterVal);
    }

    filteredTickets.forEach(ticket => {
      const card = document.createElement("div");
      card.className = "row-card";
      card.style.gridTemplateColumns = "2fr 1fr 1.2fr";
      
      let badgeClass = "danger";
      let statusTh = "รอมอบหมายช่าง";
      if (ticket.status === "In Progress") {
        badgeClass = "working";
        statusTh = `กำลังซ่อมแซม`;
      } else if (ticket.status === "Completed") {
        badgeClass = "available";
        statusTh = "เสร็จสิ้นงาน";
      }

      // Format parts withdrawn if any
      let withdrawnHtml = "";
      if (ticket.withdrawnParts && ticket.withdrawnParts.length > 0) {
        const items = ticket.withdrawnParts.map(wp => {
          const part = appData.parts.find(p => p.id === wp.partId);
          return part ? `${part.name.split(" (")[0]} x${wp.qty}` : "";
        }).filter(Boolean).join(", ");
        withdrawnHtml = `<div class="row-sub-text" style="color:var(--primary); font-size:11px; margin-top:2px; font-weight:600;">📦 อะไหล่ที่เบิกสำรอง: ${items}</div>`;
      }

      // Format completed fields if any
      let completedHtml = "";
      if (ticket.status === "Completed") {
        let partsUsedText = "ไม่มีการเปลี่ยนอะไหล่";
        if (ticket.actualPartsUsed && ticket.actualPartsUsed.length > 0) {
          partsUsedText = ticket.actualPartsUsed.map(up => {
            const part = appData.parts.find(p => p.id === up.partId);
            return part ? `${part.name.split(" (")[0]} x${up.qty}` : "";
          }).filter(Boolean).join(", ");
        }
        completedHtml = `
          <div style="margin-top:6px; padding:8px; background-color:var(--light-bg); border-left:3px solid var(--primary); border-radius:4px; font-size:11px;">
            <div><strong>ปัญหาที่พบ:</strong> ${ticket.issueFound || "-"}</div>
            <div style="margin-top:2px;"><strong>วิธีแก้:</strong> ${ticket.resolution || "-"}</div>
            <div style="margin-top:2px; color:var(--ink-muted);"><strong>อะไหล่ที่ใช้:</strong> ${partsUsedText}</div>
          </div>
        `;
      }

      card.innerHTML = `
        <div class="row-card-title">
          <div class="row-icon">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:20px;height:20px;">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </div>
          <div>
            <div class="row-main-text" style="display:flex; align-items:center; gap:6px;">
              ${ticket.shopName}
              <span style="font-family:var(--font-mono); font-size:10px; color:var(--ink-muted); font-weight:400;">(${ticket.id})</span>
            </div>
            <div class="row-sub-text"><strong>อาการเสีย:</strong> ${ticket.issue}</div>
            ${withdrawnHtml}
            <div class="row-sub-text" style="color:var(--ink-muted); font-size:11px; margin-top:2px;">
              รุ่นเครื่อง: ${ticket.copierModel} | แจ้งเมื่อ: ${formatThaiDate(ticket.date)}
            </div>
            ${completedHtml}
          </div>
        </div>
        <div class="row-info-block">
          <span class="row-info-label">ช่างที่เข้าซ่อม</span>
          <span class="row-info-value" style="font-weight: 600;">
            ${ticket.assignedTechName || `<button class="btn-secondary btn-assign-tech" data-ticket-id="${ticket.id}" style="padding: 4px 10px; font-size:12px; margin-top: 4px; box-shadow: 2px 2px 0px #000;">มอบหมาย</button>`}
          </span>
        </div>
        <div style="display:flex; flex-direction:column; gap:6px; align-items:flex-end; justify-content:center;">
          <span class="badge ${badgeClass}">${statusTh}</span>
          <div style="display:flex; gap:6px; margin-top:4px;">
            ${(ticket.status === "Pending" || ticket.status === "In Progress") ? `<button class="btn-secondary btn-withdraw-parts" data-ticket-id="${ticket.id}" style="padding: 4px 10px; font-size:12px; box-shadow: 2px 2px 0px #000;">เบิกอะไหล่</button>` : ''}
            ${ticket.status === "In Progress" ? `<button class="btn-secondary btn-complete-job" data-ticket-id="${ticket.id}" style="padding: 4px 10px; font-size:12px; box-shadow: 2px 2px 0px #000;">ปิดงาน</button>` : ''}
          </div>
        </div>
      `;

      const btnAssign = card.querySelector(".btn-assign-tech");
      if (btnAssign) {
        btnAssign.addEventListener("click", () => {
          const ticketId = btnAssign.getAttribute("data-ticket-id");
          openAssignModal(ticketId);
        });
      }

      const btnComplete = card.querySelector(".btn-complete-job");
      if (btnComplete) {
        btnComplete.addEventListener("click", () => {
          const ticketId = btnComplete.getAttribute("data-ticket-id");
          openCompleteJobModal(ticketId);
        });
      }

      ticketsList.appendChild(card);
    });
  }

  const modalOverlay = document.getElementById("modalOverlay");
  const modalBody = document.getElementById("modalBody");
  const modalCloseBtn = document.getElementById("modalClose");

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener("click", closeModal);
  }

  function closeModal() {
    modalOverlay.style.display = "none";
    modalBody.innerHTML = "";
  }

  function openAssignModal(ticketId) {
    const ticket = appData.tickets.find(t => t.id === ticketId);
    if (!ticket) return;

    modalOverlay.style.display = "flex";
    modalBody.innerHTML = `
      <h3 style="margin-bottom:16px; font-family:var(--font-title);">มอบหมายช่างให้กับ: ${ticket.shopName}</h3>
      <p style="font-size:13px; color:var(--ink-muted); margin-bottom:16px;">
        ปัญหา: ${ticket.issue} (${ticket.copierModel})
      </p>
      <div class="form-group">
        <label class="form-label">เลือกช่างซ่อมบำรุงที่ว่างงาน</label>
        <select class="filter-select" id="techSelectField" style="width:100%;">
          ${appData.technicians
            .filter(t => t.status === "Available")
            .map(t => `<option value="${t.id}">${t.name} (⭐ ${t.rating})</option>`)
            .join("") || `<option value="" disabled>ไม่มีช่างว่างในขณะนี้</option>`}
        </select>
      </div>
      <button class="btn-primary" id="submitAssignTech" style="width:100%; margin-top:20px; justify-content:center; box-shadow: 3px 3px 0px #000;">ยืนยันมอบหมายงาน</button>
    `;

    const btnSubmit = document.getElementById("submitAssignTech");
    const techSelect = document.getElementById("techSelectField");

    btnSubmit.addEventListener("click", () => {
      const selectedTechId = techSelect.value;
      if (!selectedTechId) {
        alert("กรุณาเลือกช่างซ่อมบำรุง");
        return;
      }
      assignTechToTicket(ticketId, selectedTechId);
      closeModal();
    });
  }

  function assignTechToTicket(ticketId, techId) {
    const ticket = appData.tickets.find(t => t.id === ticketId);
    const tech = appData.technicians.find(t => t.id === techId);

    if (ticket && tech) {
      ticket.assignedTechId = techId;
      ticket.assignedTechName = tech.name;
      ticket.status = "In Progress";
      tech.status = "Working";
      tech.currentJob = ticket.shopName;

      renderTickets();
      renderDashboard();
      renderTechnicians(); // Sync calendar and technician list!
      renderShopsMap();    // Sync map pin colors!
      renderShops();       // Refresh shop details card!
    }
  }

  function openQRModal(shopId) {
    const shop = appData.shops.find(s => s.id === shopId);
    if (!shop) return;

    modalOverlay.style.display = "flex";
    modalBody.innerHTML = `
      <h3 style="margin-bottom:16px; text-align:center; font-family:var(--font-title);">จำลองระบบสแกน QR Code หน้าเครื่อง</h3>
      <div class="qr-scanner-box">
        <svg class="qr-placeholder-svg" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 4v1m0 11v1m5-6h-1m-4 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p style="font-size:14px; font-weight:700; color:var(--ink-dark)">QR CODE FOUND</p>
        <p style="font-size:12px; color:var(--ink-muted); line-height:1.4;">
          ASSET SN: ${shop.serialNumber} | MODEL: ${shop.copierModel}<br>
          LOCATION: ${shop.name}
        </p>
      </div>
      <button class="btn-primary" id="btnConfirmScan" style="width:100%; justify-content:center; box-shadow: 3px 3px 0px #000; margin-top:10px;">
        สแกนดึงข้อมูลคู่มือซ่อม
      </button>
    `;

    const btnConfirm = document.getElementById("btnConfirmScan");
    btnConfirm.addEventListener("click", () => {
      closeModal();
      const manualLink = document.querySelector('[data-view="manuals-view"]');
      if (manualLink) {
        manualLink.click();
        const manualSelect = document.getElementById("manualModelSelect");
        if (manualSelect) {
          manualSelect.value = shop.copierModel;
          renderManuals();
        }
      }
    });
  }

  // Open ticket modal with prefilled date
  function openNewTicketModalWithDate(dateString) {
    modalOverlay.style.display = "flex";
    modalBody.innerHTML = `
      <h3 style="margin-bottom:16px; font-family:var(--font-title);">สร้างใบแจ้งซ่อมบำรุงใหม่</h3>
      <div style="display:flex; flex-direction:column; gap:16px;">
        <div class="form-group">
          <label class="form-label">เลือกร้านค้าเช่าเครื่องถ่ายเอกสาร</label>
          <select class="filter-select" id="newTicketShopSelect" style="width:100%;">
            ${appData.shops.map(s => `<option value="${s.id}" data-model="${s.copierModel}">${s.name} (${s.copierModel})</option>`).join("")}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">วันที่ต้องการนัดหมายเข้าซ่อม</label>
          <input type="date" class="form-control" id="newTicketDate" value="${dateString || new Date().toISOString().split("T")[0]}" style="border: 1.5px solid var(--ink-dark);">
        </div>
        <div class="form-group">
          <label class="form-label">ระบุรายละเอียดอาการเสียหาย</label>
          <select class="filter-select" id="newTicketIssueSelect" style="width:100%; border: 1.5px solid var(--ink-dark); margin-bottom: 12px;"></select>
          <textarea class="form-control" id="newTicketIssue" rows="3" placeholder="ระบุอาการชำรุดเพิ่มเติม..." style="resize:none; font-family:inherit; border: 1.5px solid var(--ink-dark); display:none;"></textarea>
        </div>
        <button class="btn-primary" id="btnSubmitNewTicket" style="justify-content:center; box-shadow: 3px 3px 0px #000;">บันทึกตั๋วแจ้งซ่อม</button>
      </div>
    `;

    const shopSelect = document.getElementById("newTicketShopSelect");
    const issueSelect = document.getElementById("newTicketIssueSelect");
    const issueTextarea = document.getElementById("newTicketIssue");

    function updateIssueOptions() {
      const selectedOption = shopSelect.options[shopSelect.selectedIndex];
      const model = selectedOption.getAttribute("data-model");
      const issues = getCommonIssuesForModel(model);
      
      issueSelect.innerHTML = issues.map(issue => `<option value="${issue}">${issue}</option>`).join("");
      
      // Initially hide/show textarea based on selected option
      toggleTextarea();
    }

    function toggleTextarea() {
      if (issueSelect.value.startsWith("อื่นๆ")) {
        issueTextarea.style.display = "block";
        issueTextarea.required = true;
        issueTextarea.placeholder = "พิมพ์ระบุอาการชำรุดด้วยตนเอง...";
      } else {
        issueTextarea.style.display = "none";
        issueTextarea.required = false;
        issueTextarea.value = "";
      }
    }

    shopSelect.addEventListener("change", updateIssueOptions);
    issueSelect.addEventListener("change", toggleTextarea);

    // Initial load
    updateIssueOptions();

    const btnSubmit = document.getElementById("btnSubmitNewTicket");
    btnSubmit.addEventListener("click", () => {
      const shopId = shopSelect.value;
      const shopName = shopSelect.options[shopSelect.selectedIndex].text.split(" (")[0];
      const copierModel = shopSelect.options[shopSelect.selectedIndex].getAttribute("data-model");
      
      const selectedIssue = issueSelect.value;
      const customIssue = issueTextarea.value.trim();
      const selectedDate = document.getElementById("newTicketDate").value;

      let finalIssue = selectedIssue;
      if (selectedIssue.startsWith("อื่นๆ")) {
        if (!customIssue) {
          alert("กรุณากรอกอาการชำรุด");
          return;
        }
        finalIssue = customIssue;
      }

      const newId = `TK-${String(appData.tickets.length + 1).padStart(3, "0")}`;
      const newTicket = {
        id: newId,
        shopId: shopId,
        shopName: shopName,
        copierModel: copierModel,
        issue: finalIssue,
        assignedTechId: null,
        assignedTechName: null,
        status: "Pending",
        date: selectedDate || new Date().toISOString().split("T")[0]
      };

      appData.tickets.push(newTicket);
      closeModal();
      renderTickets();
      renderDashboard();
      renderTechnicians(); // Sync to calendar and tech view!
      renderShopsMap();    // Sync map details!
      renderShops();       // Refresh shop details card!
    });
  }

  // Bind the desktop ticket button to open ticket modal
  const btnNewTicket = document.getElementById("btnOpenNewTicketModal");
  if (btnNewTicket) {
    btnNewTicket.addEventListener("click", () => {
      openNewTicketModalWithDate(new Date().toISOString().split("T")[0]);
    });
  }

  // Bind the export CSV button
  const btnExportCSV = document.getElementById("btnExportTicketsCSV");
  if (btnExportCSV) {
    btnExportCSV.addEventListener("click", exportTicketsCSV);
  }

  // ==========================================
  // 5. MAINTENANCE MANUALS VIEW SETUP
  // ==========================================
  let activeTroubleshootingSteps = [];

  const modelSelect = document.getElementById("manualModelSelect");
  if (modelSelect) {
    modelSelect.innerHTML = "";
    appData.manuals.forEach(manual => {
      const opt = document.createElement("option");
      opt.value = manual.model;
      opt.innerText = manual.model;
      modelSelect.appendChild(opt);
    });
    
    modelSelect.addEventListener("change", renderManuals);

    const issueSelect = document.getElementById("manualIssueSelect");
    if (issueSelect) {
      issueSelect.addEventListener("change", initTroubleshooting);
    }
    
    const btnTsReset = document.getElementById("btnTsReset");
    if (btnTsReset) {
      btnTsReset.addEventListener("click", initTroubleshooting);
    }
  }

  function renderManuals() {
    const selectedModel = modelSelect.value;
    const manual = appData.manuals.find(m => m.model === selectedModel);
    if (!manual) return;

    // Populate Issues Dropdown & Initialize Flow
    populateIssuesDropdown(manual);
    initTroubleshooting();

    const checklistDiv = document.getElementById("manualChecklist");
    checklistDiv.innerHTML = "";
    manual.standardChecklist.forEach(item => {
      const div = document.createElement("div");
      div.className = "manual-checklist-item";
      div.innerHTML = `
        <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:18px;height:18px;">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" />
        </svg>
        <span class="row-info-value" style="font-weight:400; font-size:13px;">${item}</span>
      `;
      checklistDiv.appendChild(div);
    });

    const issuesDiv = document.getElementById("manualIssues");
    issuesDiv.innerHTML = "";
    manual.commonIssues.forEach(issue => {
      const div = document.createElement("div");
      div.className = "manual-issue-item";
      div.innerHTML = `
        <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:18px;height:18px;">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <div class="manual-text-wrap">
          <span class="manual-issue-title">${issue.issue}</span>
          <span class="manual-issue-solution">👉 <strong>วิธีแก้:</strong> ${issue.fix}</span>
        </div>
      `;
      issuesDiv.appendChild(div);
    });
  }

  function populateIssuesDropdown(manual) {
    const issueSelect = document.getElementById("manualIssueSelect");
    if (!issueSelect) return;
    issueSelect.innerHTML = "";

    if (manual.troubleshootingFlows && manual.troubleshootingFlows.length > 0) {
      document.getElementById("troubleshooterContainer").parentElement.style.display = "block";
      manual.troubleshootingFlows.forEach(flow => {
        const opt = document.createElement("option");
        opt.value = flow.id;
        opt.innerText = flow.title;
        issueSelect.appendChild(opt);
      });
    } else {
      document.getElementById("troubleshooterContainer").parentElement.style.display = "none";
    }
  }

  function initTroubleshooting() {
    const selectedModel = modelSelect.value;
    const manual = appData.manuals.find(m => m.model === selectedModel);
    if (!manual || !manual.troubleshootingFlows || manual.troubleshootingFlows.length === 0) return;

    const issueSelect = document.getElementById("manualIssueSelect");
    const selectedIssueId = issueSelect.value;
    const flow = manual.troubleshootingFlows.find(f => f.id === selectedIssueId);
    if (!flow) return;

    activeTroubleshootingSteps = [{ nodeId: flow.startNode, choice: null }];
    renderTroubleshootingTimeline();
  }

  function renderTroubleshootingTimeline() {
    const timelineContainer = document.getElementById("tsStepsTimeline");
    if (!timelineContainer) return;
    timelineContainer.innerHTML = "";

    const selectedModel = modelSelect.value;
    const manual = appData.manuals.find(m => m.model === selectedModel);
    if (!manual || !manual.troubleshootingFlows) return;

    const issueSelect = document.getElementById("manualIssueSelect");
    const selectedIssueId = issueSelect.value;
    const flow = manual.troubleshootingFlows.find(f => f.id === selectedIssueId);
    if (!flow) return;

    activeTroubleshootingSteps.forEach((step, index) => {
      const node = flow.nodes[step.nodeId];
      if (!node) return;

      // Add a down arrow connector before steps (except the first step)
      if (index > 0) {
        const connector = document.createElement("div");
        connector.style.display = "flex";
        connector.style.justifyContent = "center";
        connector.style.margin = "-6px 0";
        connector.style.color = "var(--primary)";
        connector.innerHTML = `
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:20px;height:20px;">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 13l-7 7-7-7m14-6l-7 7-7-7" />
          </svg>
        `;
        timelineContainer.appendChild(connector);
      }

      const card = document.createElement("div");
      card.className = "card";
      card.style.margin = "0";
      card.style.padding = "18px 22px";
      card.style.border = "var(--card-border)";
      card.style.boxShadow = "2px 2px 0px var(--ink-dark)";
      card.style.background = "var(--card-bg)";

      if (node.isResult) {
        // Result layout style
        card.style.background = "rgba(255, 69, 0, 0.04)";
        card.style.borderColor = "var(--primary)";
        card.style.boxShadow = "3px 3px 0px var(--primary)";
        card.innerHTML = `
          <div style="font-family:var(--font-mono); font-size:11px; color:#ff4500; font-weight:700; margin-bottom:6px;">💡 ข้อวินิจฉัยและแนวทางแก้ไขที่แนะนำ</div>
          <div style="font-size:14px; font-weight:600; line-height:1.6; color:var(--ink-dark);">${node.text}</div>
        `;
      } else {
        // Question layout style
        const stepNum = index + 1;
        
        let yesBtnStyle = "padding:6px 16px; font-size:12px; box-shadow:2px 2px 0px var(--ink-dark); margin-bottom:0;";
        let noBtnStyle = "padding:6px 16px; font-size:12px; box-shadow:2px 2px 0px var(--ink-dark); margin-bottom:0;";
        
        let yesBtnClass = "btn-secondary";
        let noBtnClass = "btn-secondary";

        if (step.choice === "yes") {
          yesBtnClass = "btn-primary";
          noBtnStyle += " opacity: 0.4; pointer-events: none;";
        } else if (step.choice === "no") {
          noBtnClass = "btn-primary";
          yesBtnStyle += " opacity: 0.4; pointer-events: none;";
        }

        card.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap;">
            <div style="flex:1; min-width:260px;">
              <span style="font-family:var(--font-mono); font-size:10px; color:var(--primary); font-weight:700; text-transform:uppercase;">ขั้นตอนตรวจสอบที่ ${stepNum}</span>
              <div style="font-size:13px; font-weight:600; color:var(--ink-dark); margin-top:4px; line-height:1.5;">${node.text}</div>
            </div>
            <div style="display:flex; gap:10px; align-items:center;">
              <button class="${yesBtnClass} btn-ts-choice" data-choice="yes" style="${yesBtnStyle}">ใช่ (Yes)</button>
              <button class="${noBtnClass} btn-ts-choice" data-choice="no" style="${noBtnStyle}">ไม่ใช่ (No)</button>
            </div>
          </div>
        `;

        const yesBtn = card.querySelector('.btn-ts-choice[data-choice="yes"]');
        const noBtn = card.querySelector('.btn-ts-choice[data-choice="no"]');

        yesBtn.addEventListener("click", () => selectStepChoice(index, "yes"));
        noBtn.addEventListener("click", () => selectStepChoice(index, "no"));
      }

      timelineContainer.appendChild(card);
    });
  }

  function selectStepChoice(stepIndex, choice) {
    activeTroubleshootingSteps[stepIndex].choice = choice;
    activeTroubleshootingSteps = activeTroubleshootingSteps.slice(0, stepIndex + 1);

    const selectedModel = modelSelect.value;
    const manual = appData.manuals.find(m => m.model === selectedModel);
    if (!manual || !manual.troubleshootingFlows) return;

    const issueSelect = document.getElementById("manualIssueSelect");
    const selectedIssueId = issueSelect.value;
    const flow = manual.troubleshootingFlows.find(f => f.id === selectedIssueId);
    if (!flow) return;

    const currentNode = flow.nodes[activeTroubleshootingSteps[stepIndex].nodeId];
    if (!currentNode) return;

    const nextNodeId = currentNode[choice];
    if (nextNodeId && flow.nodes[nextNodeId]) {
      activeTroubleshootingSteps.push({ nodeId: nextNodeId, choice: null });
    }

    renderTroubleshootingTimeline();
  }

  function formatThaiDate(dateString) {
    const parts = dateString.split("-");
    if (parts.length !== 3) return dateString;
    const year = parseInt(parts[0]);
    const month = parseInt(parts[1]) - 1;
    const day = parseInt(parts[2]);
    const thaiMonths = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."];
    return `${day} ${thaiMonths[month]} ${year + 543}`;
  }

  function openRequisitionModal(ticketId) {
    const ticket = appData.tickets.find(t => t.id === ticketId);
    if (!ticket) return;

    const compatibleParts = appData.parts.filter(p => p.compatible.includes(ticket.copierModel));

    modalOverlay.style.display = "flex";
    
    let partsRowsHtml = "";
    if (compatibleParts.length === 0) {
      partsRowsHtml = `<tr><td colspan="3" style="text-align:center; padding:16px; color:var(--ink-muted);">ไม่มีอะไหล่ที่รองรับรุ่นนี้ในคลัง</td></tr>`;
    } else {
      compatibleParts.forEach(part => {
        const alreadyWithdrawn = ticket.withdrawnParts ? (ticket.withdrawnParts.find(wp => wp.partId === part.id)?.qty || 0) : 0;
        partsRowsHtml += `
          <tr class="req-parts-row" data-part-id="${part.id}">
            <td style="padding:10px 8px;">
              <div style="font-weight:600; font-size:13px;">${part.name}</div>
              <div style="font-size:11px; color:var(--ink-muted);">เบิกไว้แล้ว: ${alreadyWithdrawn} ${part.unit}</div>
            </td>
            <td style="text-align:center; padding:10px 8px; font-family:var(--font-mono); font-weight:700;">
              ${part.stock} ${part.unit}
            </td>
            <td style="text-align:right; padding:10px 8px;">
              <input type="number" class="form-control req-qty-input" min="0" max="${part.stock}" value="0" style="width:70px; display:inline-block; text-align:center; font-family:var(--font-mono); font-weight:700; border:1.5px solid var(--ink-dark); padding:4px;">
            </td>
          </tr>
        `;
      });
    }

    modalBody.innerHTML = `
      <h3 style="margin-bottom:12px; font-family:var(--font-title);">เบิกอะไหล่ไปหน้าร้าน (${ticket.id})</h3>
      <p style="font-size:13px; color:var(--ink-muted); margin-bottom:16px;">
        ร้านค้า: <strong>${ticket.shopName}</strong> | รุ่นเครื่อง: <strong>${ticket.copierModel}</strong>
      </p>
      
      <div style="max-height:300px; overflow-y:auto; border:1.5px solid var(--ink-dark); border-radius:8px; margin-bottom:16px;">
        <table style="width:100%; border-collapse:collapse; background:#fff;">
          <thead>
            <tr style="background:#f1f5f9; border-bottom:1.5px solid var(--ink-dark);">
              <th style="text-align:left; padding:8px;">ชื่อชิ้นส่วนอะไหล่</th>
              <th style="text-align:center; padding:8px; width:100px;">คลังเหลือ</th>
              <th style="text-align:right; padding:8px; width:100px;">จำนวนที่เบิก</th>
            </tr>
          </thead>
          <tbody>
            ${partsRowsHtml}
          </tbody>
        </table>
      </div>

      <div style="display:flex; gap:12px;">
        <button class="btn-secondary" id="btnCancelRequisition" style="flex:1; justify-content:center; box-shadow:2px 2px 0px var(--ink-dark); margin-bottom:0;">ยกเลิก</button>
        <button class="btn-primary" id="btnSubmitRequisition" style="flex:2; justify-content:center; box-shadow:3px 3px 0px var(--ink-dark); margin-bottom:0;">ยืนยันการเบิกอะไหล่</button>
      </div>
    `;

    document.getElementById("btnCancelRequisition").addEventListener("click", closeModal);
    
    document.getElementById("btnSubmitRequisition").addEventListener("click", () => {
      const inputs = modalBody.querySelectorAll(".req-qty-input");
      let totalWithdrawn = 0;
      
      // First validation loop
      for (const input of inputs) {
        const qty = parseInt(input.value) || 0;
        const tr = input.closest("tr");
        const partId = tr.getAttribute("data-part-id");
        const part = appData.parts.find(p => p.id === partId);
        
        if (qty > 0) {
          if (qty > part.stock) {
            alert(`ไม่สามารถเบิก ${part.name} จำนวน ${qty} ชิ้นได้ เนื่องจากคลังเหลือเพียง ${part.stock} ชิ้น`);
            return;
          }
          totalWithdrawn += qty;
        }
      }
      
      if (totalWithdrawn === 0) {
        alert("กรุณาระบุจำนวนอะไหล่ที่ต้องการเบิกอย่างน้อย 1 ชิ้น");
        return;
      }
      
      // Perform updates
      if (!ticket.withdrawnParts) {
        ticket.withdrawnParts = [];
      }
      
      inputs.forEach(input => {
        const qty = parseInt(input.value) || 0;
        if (qty > 0) {
          const tr = input.closest("tr");
          const partId = tr.getAttribute("data-part-id");
          const part = appData.parts.find(p => p.id === partId);
          
          // Decrement inventory stock
          part.stock -= qty;
          
          // Add to withdrawn parts
          const existing = ticket.withdrawnParts.find(wp => wp.partId === partId);
          if (existing) {
            existing.qty += qty;
          } else {
            ticket.withdrawnParts.push({ partId, qty });
          }
        }
      });
      
      closeModal();
      renderTickets();
      renderDashboard();
      renderParts(); // Sync spare parts view drawer stock indicators
    });
  }

  function openCompleteJobModal(ticketId) {
    const ticket = appData.tickets.find(t => t.id === ticketId);
    if (!ticket) return;

    modalOverlay.style.display = "flex";
    
    let partsTableHtml = "";
    const hasWithdrawnParts = ticket.withdrawnParts && ticket.withdrawnParts.length > 0;
    
    if (hasWithdrawnParts) {
      partsTableHtml = `
        <div style="margin-top:12px; margin-bottom:16px;">
          <label class="form-label" style="margin-bottom:8px;">รายละเอียดการใช้อะไหล่และคืนคลัง</label>
          <div style="border:1.5px solid var(--ink-dark); border-radius:8px; overflow:hidden;">
            <table style="width:100%; border-collapse:collapse; background:#fff; font-size:12px;">
              <thead>
                <tr style="background:#f1f5f9; border-bottom:1.5px solid var(--ink-dark);">
                  <th style="text-align:left; padding:8px;">อะไหล่</th>
                  <th style="text-align:center; padding:8px; width:70px;">เบิกไป</th>
                  <th style="text-align:center; padding:8px; width:80px;">ใช้จริง</th>
                  <th style="text-align:center; padding:8px; width:80px;">คืนคลัง</th>
                </tr>
              </thead>
              <tbody>
      `;
      
      ticket.withdrawnParts.forEach(wp => {
        const part = appData.parts.find(p => p.id === wp.partId);
        const partName = part ? part.name.split(" (")[0] : `อะไหล่ ${wp.partId}`;
        partsTableHtml += `
          <tr class="complete-parts-row" data-part-id="${wp.partId}" data-withdrawn="${wp.qty}">
            <td style="padding:8px; font-weight:600;">${partName}</td>
            <td style="text-align:center; padding:8px; font-family:var(--font-mono); font-weight:700;">${wp.qty}</td>
            <td style="text-align:center; padding:8px;">
              <input type="number" class="form-control complete-used-input" min="0" max="${wp.qty}" value="${wp.qty}" style="width:60px; text-align:center; font-family:var(--font-mono); font-weight:700; border:1.5px solid var(--ink-dark); padding:2px; display:inline-block;">
            </td>
            <td style="text-align:center; padding:8px; font-family:var(--font-mono); font-weight:700;" class="complete-returned-text">0</td>
          </tr>
        `;
      });
      
      partsTableHtml += `
              </tbody>
            </table>
          </div>
          <div class="row-sub-text" style="font-size:11px; color:var(--primary); margin-top:6px; font-weight:600;">
            💡 ระบบจะคำนวณจำนวนส่งคืนคลังให้อัตโนมัติ (จำนวนคืน = จำนวนเบิก - จำนวนใช้จริง)
          </div>
        </div>
      `;
    } else {
      partsTableHtml = `
        <div style="background:#f8fafc; border:1.5px dashed var(--ink-dark); border-radius:8px; padding:12px; text-align:center; font-size:12px; color:var(--ink-muted); margin-bottom:16px;">
          ไม่มีการเบิกอะไหล่สำหรับเคสซ่อมนี้
        </div>
      `;
    }

    modalBody.innerHTML = `
      <h3 style="margin-bottom:12px; font-family:var(--font-title);">บันทึกปิดงานซ่อมบำรุง (${ticket.id})</h3>
      <p style="font-size:13px; color:var(--ink-muted); margin-bottom:16px;">
        ร้านค้า: <strong>${ticket.shopName}</strong> | ผู้รับผิดชอบ: <strong>${ticket.assignedTechName || '-'}</strong>
      </p>

      <div style="display:flex; flex-direction:column; gap:12px; margin-bottom:16px;">
        <div class="form-group">
          <label class="form-label">ปัญหาที่พบจริงจากการตรวจสอบหน้างาน</label>
          <textarea class="form-control" id="completeIssueFound" rows="2" placeholder="ระบุอาการชำรุดจริง เช่น ยางดึงกระดาษเสื่อมสภาพ, ผงคาร์บอนเลอะ..." style="resize:none; font-family:inherit; border:1.5px solid var(--ink-dark); font-size:13px;" required></textarea>
        </div>
        <div class="form-group">
          <label class="form-label">วิธีการแก้ไขปัญหา</label>
          <textarea class="form-control" id="completeResolution" rows="2" placeholder="ระบุวิธีแก้ เช่น ดำเนินการเปลี่ยนลูกยางชิ้นใหม่ เป่าฝุ่นและทดลองพิมพ์..." style="resize:none; font-family:inherit; border:1.5px solid var(--ink-dark); font-size:13px;" required></textarea>
        </div>
      </div>

      ${partsTableHtml}

      <div style="display:flex; gap:12px;">
        <button class="btn-secondary" id="btnCancelComplete" style="flex:1; justify-content:center; box-shadow:2px 2px 0px var(--ink-dark); margin-bottom:0;">ยกเลิก</button>
        <button class="btn-primary" id="btnSaveComplete" style="flex:2; justify-content:center; box-shadow:3px 3px 0px var(--ink-dark); margin-bottom:0;">บันทึกปิดงาน</button>
      </div>
    `;

    // Add input event listeners to calculate returned qty
    if (hasWithdrawnParts) {
      const rows = modalBody.querySelectorAll(".complete-parts-row");
      rows.forEach(row => {
        const withdrawn = parseInt(row.getAttribute("data-withdrawn")) || 0;
        const usedInput = row.querySelector(".complete-used-input");
        const returnedText = row.querySelector(".complete-returned-text");
        
        const updateReturned = () => {
          let used = parseInt(usedInput.value);
          if (isNaN(used)) used = 0;
          if (used < 0) {
            used = 0;
            usedInput.value = 0;
          }
          if (used > withdrawn) {
            used = withdrawn;
            usedInput.value = withdrawn;
          }
          returnedText.innerText = withdrawn - used;
        };

        usedInput.addEventListener("input", updateReturned);
        updateReturned(); // Init
      });
    }

    document.getElementById("btnCancelComplete").addEventListener("click", closeModal);

    document.getElementById("btnSaveComplete").addEventListener("click", () => {
      const issueFound = document.getElementById("completeIssueFound").value.trim();
      const resolution = document.getElementById("completeResolution").value.trim();

      if (!issueFound || !resolution) {
        alert("กรุณากรอกปัญหาที่พบและวิธีแก้ไขปัญหา");
        return;
      }

      // Process parts return and actual used parts
      const actualPartsUsed = [];
      if (hasWithdrawnParts) {
        const rows = modalBody.querySelectorAll(".complete-parts-row");
        for (const row of rows) {
          const partId = row.getAttribute("data-part-id");
          const withdrawn = parseInt(row.getAttribute("data-withdrawn")) || 0;
          const usedInput = row.querySelector(".complete-used-input");
          let used = parseInt(usedInput.value);
          if (isNaN(used)) used = 0;
          
          if (used < 0 || used > withdrawn) {
            alert("กรุณากรอกจำนวนที่ใช้จริงให้ถูกต้อง (ต้องอยู่ระหว่าง 0 ถึงจำนวนเบิก)");
            return;
          }

          const returned = withdrawn - used;
          const part = appData.parts.find(p => p.id === partId);

          // Return back to stock
          if (returned > 0 && part) {
            part.stock += returned;
          }

          if (used > 0) {
            actualPartsUsed.push({ partId, qty: used });
          }
        }
      }

      // Update ticket fields
      ticket.issueFound = issueFound;
      ticket.resolution = resolution;
      ticket.actualPartsUsed = actualPartsUsed;
      ticket.status = "Completed";

      // Update shop details
      const shop = appData.shops.find(s => s.id === ticket.shopId);
      if (shop) {
        shop.lastMaintenance = new Date().toISOString().split("T")[0];
        shop.maintenanceNotes = `ซ่อมบำรุง: ${ticket.issue} (ปัญหา: ${issueFound} | วิธีแก้: ${resolution}) โดย ${ticket.assignedTechName}`;
        
        const nextDate = new Date();
        nextDate.setMonth(nextDate.getMonth() + 3);
        shop.nextMaintenance = nextDate.toISOString().split("T")[0];
      }

      // Free technician
      if (ticket.assignedTechId) {
        const tech = appData.technicians.find(t => t.id === ticket.assignedTechId);
        if (tech) {
          tech.status = "Available";
          tech.currentJob = null;
        }
      }

      closeModal();
      renderTickets();
      renderDashboard();
      renderTechnicians();
      renderShops();
      renderParts();
    });
  }

  function exportTicketsCSV() {
    const headers = [
      "รหัสใบงาน",
      "ร้านค้า",
      "รุ่นเครื่องถ่ายเอกสาร",
      "อาการที่แจ้งซ่อม",
      "วันที่แจ้งซ่อม",
      "ช่างเทคนิคที่ดูแล",
      "สถานะใบงาน",
      "อะไหล่ที่เบิก",
      "อะไหล่ที่ใช้จริง",
      "ปัญหาที่พบจริง",
      "วิธีการแก้ไข"
    ];

    let csvContent = "\uFEFF"; // BOM prefix for Excel Thai compatibility
    csvContent += headers.map(h => `"${h.replace(/"/g, '""')}"`).join(",") + "\n";

    appData.tickets.forEach(t => {
      // Format withdrawn parts
      const withdrawnStr = (t.withdrawnParts && t.withdrawnParts.length > 0)
        ? t.withdrawnParts.map(wp => {
            const part = appData.parts.find(p => p.id === wp.partId);
            return part ? `${part.name.split(" (")[0]} x${wp.qty}` : `อะไหล่ ${wp.partId} x${wp.qty}`;
          }).join("; ")
        : "-";

      // Format actual used parts
      const usedStr = (t.actualPartsUsed && t.actualPartsUsed.length > 0)
        ? t.actualPartsUsed.map(up => {
            const part = appData.parts.find(p => p.id === up.partId);
            return part ? `${part.name.split(" (")[0]} x${up.qty}` : `อะไหล่ ${up.partId} x${up.qty}`;
          }).join("; ")
        : "-";

      let statusText = "รอมอบหมายช่าง";
      if (t.status === "In Progress") statusText = "กำลังดำเนินการ";
      if (t.status === "Completed") statusText = "เสร็จสิ้นงาน";

      const row = [
        t.id,
        t.shopName,
        t.copierModel,
        t.issue,
        t.date,
        t.assignedTechName || "ยังไม่ระบุ",
        statusText,
        withdrawnStr,
        usedStr,
        t.issueFound || "-",
        t.resolution || "-"
      ];

      csvContent += row.map(val => `"${val.replace(/"/g, '""')}"`).join(",") + "\n";
    });

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `รายงานตั๋วแจ้งซ่อม_${new Date().toISOString().split("T")[0]}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // ==========================================
  // DARK MODE TOGGLE LOGIC
  // ==========================================
  const darkModeToggle = document.getElementById("darkModeToggle");
  const darkModeToggleText = document.getElementById("darkModeToggleText");

  function updateThemeUI(isDark) {
    if (isDark) {
      document.body.classList.add("dark-mode");
      if (darkModeToggleText) darkModeToggleText.innerText = "โหมดสว่าง";
      if (darkModeToggle) {
        const svg = darkModeToggle.querySelector("svg");
        if (svg) {
          svg.innerHTML = `<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>`;
        }
      }
    } else {
      document.body.classList.remove("dark-mode");
      if (darkModeToggleText) darkModeToggleText.innerText = "โหมดมืด";
      if (darkModeToggle) {
        const svg = darkModeToggle.querySelector("svg");
        if (svg) {
          svg.innerHTML = `<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="4.22" x2="19.78" y2="5.64"></line>`;
        }
      }
    }
  }

  // Initial load theme checks
  const savedTheme = localStorage.getItem("copier-theme");
  const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const initDark = savedTheme === "dark" || (!savedTheme && systemPrefersDark);
  updateThemeUI(initDark);

  if (darkModeToggle) {
    darkModeToggle.addEventListener("click", () => {
      const isDark = document.body.classList.contains("dark-mode");
      updateThemeUI(!isDark);
      localStorage.setItem("copier-theme", !isDark ? "dark" : "light");
    });
  }

  renderView("dashboard-view");
});
