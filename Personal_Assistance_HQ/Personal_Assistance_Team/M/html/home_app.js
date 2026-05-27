/* 🧑‍💻 Q — Home Portal JS (Veda Behavior & Telemetry System) */

// Protocol check to redirect user from file:// to localhost
if (window.location.protocol === 'file:') {
    if (confirm('⚠️ แกเปิดหน้าเว็บผ่านไฟล์ตรงๆ (file://) ซึ่งจะทำให้ฟังก์ชันบอท/หลังบ้านใช้งานไม่ได้จ้า\n\nต้องการให้ฉันเปลี่ยนเส้นทางไปที่ลิงก์เซิร์ฟเวอร์หลังบ้าน (http://localhost:8000/index.html) ให้โดยออโต้เลยไหมแก?')) {
        window.location.href = 'http://localhost:8000/index.html';
    }
}

let telemetryInterval = null;

function startHUDTelemetryStream() {
    const monitor = document.getElementById('hud-monitor-box');
    if (!monitor) return;
    
    // Clear any existing interval
    if (telemetryInterval) {
        clearInterval(telemetryInterval);
        telemetryInterval = null;
    }
    
    // Set status tag
    const hudStatusTag = document.getElementById('hud-status-tag');
    if (hudStatusTag) {
        hudStatusTag.textContent = "PROCESSING";
        hudStatusTag.className = "alert-tag active";
    }

    monitor.innerHTML = `<div class="hud-telemetry-stream" style="font-family: 'Share Tech Mono', monospace; font-size: 0.75rem; color: var(--text-primary); height: 100%; overflow-y: hidden; display: flex; flex-direction: column; gap: 4px; padding: 5px 0;"></div>`;
    const streamContainer = monitor.querySelector('.hud-telemetry-stream');
    
    const codeLines = [
        "SYS: INITIALIZING VEDA SYSTEM CORRELATION...",
        "NET: LINKING TO NOTION DATABASE SERVER...",
        "DB: QUERYING LATEST WORKFLOW PROCESS NODES...",
        "AGENT[DEER]: ANALYZING IDEA CARD OUTPUTS...",
        "AGENT[NAM]: DESTRUCTURING CONCEPT TIMELINES...",
        "AGENT[CREAM]: RESEARCHING SDK REFERENCE MANUALS...",
        "AGENT[RAY]: COMPILING FACEBOOK POST DRAFTS...",
        "SYS: COMPUTING TOKENS INJECTED: 4212 INPUT, 1204 OUTPUT",
        "SYS: CACHE HIT RATE 94.2% ON ANCESTRAL MEMORY CORE",
        "DB: RETRIEVING WORKFLOW STATUS LOGS...",
        "SYS: RESOLVING OBSIDIAN KNOWLEDGE LINKS...",
        "NET: POSTING METRICS DATA TO DASHBOARD...",
        "SYS: TRANS-AM PACING CALIBRATED TO 100%",
        "DB: WRITING ACTIVE WORKFLOW TARGET ARTIFACTS..."
    ];
    
    let lineIdx = 0;
    telemetryInterval = setInterval(() => {
        if (!streamContainer) return;
        const line = document.createElement('div');
        line.style.opacity = '0';
        line.style.transition = 'opacity 0.2s ease-in';
        line.textContent = `> ${codeLines[lineIdx % codeLines.length]} [${new Date().toLocaleTimeString()}]`;
        streamContainer.appendChild(line);
        
        // Trigger fade-in
        setTimeout(() => { line.style.opacity = '0.85'; }, 10);
        
        // Scroll to bottom
        streamContainer.scrollTop = streamContainer.scrollHeight;
        
        // Remove old lines to prevent overflow
        if (streamContainer.children.length > 10) {
            streamContainer.removeChild(streamContainer.firstChild);
        }
        lineIdx++;
    }, 400);
}

function stopHUDTelemetryStream() {
    if (telemetryInterval) {
        clearInterval(telemetryInterval);
        telemetryInterval = null;
    }
    const monitor = document.getElementById('hud-monitor-box');
    const standbyContent = `
        <div class="hud-placeholder">
            <p class="hud-title-large">VEDA LINK</p>
            <p class="hud-desc-large">SELECT CODES / HOVER SHIP MODULE TO INJECT DIRECT DATA STREAM</p>
            <div class="hud-pulse-ring"></div>
        </div>
    `;
    if (monitor) {
        monitor.innerHTML = standbyContent;
    }
    const hudStatusTag = document.getElementById('hud-status-tag');
    if (hudStatusTag) {
        hudStatusTag.textContent = "STANDBY";
        hudStatusTag.className = "alert-tag standby";
    }
}

// 1. Theme System Handler
window.setTheme = function(theme) {
    savedTheme = theme; // Keep global savedTheme in sync!
    document.body.className = theme + '-theme';
    document.documentElement.className = theme + '-theme';
    try {
        localStorage.setItem('wtj-theme', theme);
    } catch (e) {
        console.warn('localStorage is not writable:', e);
    }
    document.querySelectorAll('.theme-btn').forEach(btn => btn.classList.remove('active'));
    
    // We match our button IDs: theme-btn-light, theme-btn-dark, theme-btn-color
    const activeBtn = document.getElementById(`theme-btn-${theme}`);
    if (activeBtn) activeBtn.classList.add('active');
};

let savedTheme = 'light';
try {
    savedTheme = localStorage.getItem('wtj-theme') || 'light';
} catch (e) {
    console.warn('localStorage is not accessible:', e);
}

// 2. DOM Ready Initialization
const initializeApp = () => {
    // Apply theme class immediately to body and HTML elements
    window.setTheme(savedTheme);

    // Initial load updates from data package
    initBridgeStatus();
    initTerminalMonitor();
    initNotionTimeline();
    initCryptoTable();

    // 3. Clock Display Update
    const clockDisplay = document.getElementById('system-clock');
    if (clockDisplay) {
        setInterval(() => {
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            clockDisplay.textContent = `${hours}:${minutes}:${seconds}`;
        }, 1000);
    }

    // 4. GN Drive Telemetry simulation fluctuations
    const cpuVal = document.getElementById('telemetry-cpu');
    const memVal = document.getElementById('telemetry-mem');
    const gnVal = document.getElementById('telemetry-gn');
    const cpuBar = document.getElementById('annual-stability-fill');
    const memBar = document.getElementById('active-month-fill');
    const gnBar = document.getElementById('gn-concentration-fill');

    if (cpuBar) cpuBar.style.width = '52.4%';
    if (memBar) memBar.style.width = '64.5%';

    if (cpuVal && memVal && gnVal) {
        setInterval(() => {
            const cpu = (48 + Math.random() * 15).toFixed(1);
            const mem = (10.1 + Math.random() * 0.8).toFixed(1);
            const gnValPercent = (98.1 + Math.random() * 1.5).toFixed(2);
            
            cpuVal.textContent = `${cpu}%`;
            memVal.textContent = `${mem} GB`;
            gnVal.textContent = `${gnValPercent}%`;

            if (cpuBar) cpuBar.style.width = `${cpu}%`;
            if (gnBar) gnBar.style.width = `${gnValPercent}%`;
        }, 4000);
    }

    // 5. Interactive SVG Spaceship HUD Controller
    const shipSections = document.querySelectorAll('.ship-section');
    const hudMonitorBox = document.getElementById('hud-monitor-box');
    const hudStatusTag = document.getElementById('hud-status-tag');

    // Retrieve info stats simulated from M's Data Package
    const hudData = {
        bridge: {
            module: "SECTION 01",
            title: "BRIDGE / WORKFLOW",
            desc: "ศูนย์สั่งการและควบคุมระบบ ประสานเวิร์กโฟลว์ของเอเจนต์ทุกคน คอยสแกนสถานะงาน และอัปเดตไปป์ไลน์อัตโนมัติ",
            stats: [
                { label: "Veda System Status:", value: "STABLE", class: "online" },
                { label: "Active Directives:", value: "5 Units", class: "" },
                { label: "Latest Action Node:", value: "IDLE", class: "online" }
            ],
            link: "workflow_dashboard.html",
            btnText: "CONNECT BRIDGE"
        },
        engine: {
            module: "SECTION 02",
            title: "GN DRIVE / CONTENT CORE",
            desc: "ห้องเครื่องและแกนเตาพลังงานหลัก ขับเคลื่อนสตูดิโอ WTJ Story ด้วยข้อมูลประสิทธิภาพคอนเทนต์, แหล่งวิจัยเชิงลึก และสคริปต์ที่พร้อมผลิต",
            stats: [
                { label: "Trans-Am Pacing:", value: "READY", class: "online" },
                { label: "Content Output:", value: "128 Files", class: "" },
                { label: "Weekly CTR Average:", value: "8.42%", class: "online" }
            ],
            link: "content_dashboard.html",
            btnText: "ACCESS DRIVE"
        },
        briefing: {
            module: "SECTION 03",
            title: "BRIEFING / CALENDAR",
            desc: "ห้องวางแผนและจัดเตรียมตารางเวลา บันทึกกำหนดการโพสต์รายสัปดาห์/รายเดือน เพื่อให้ทีมคอนเทนต์และดีไซเนอร์ทำงานสัมพันธ์กันอย่างสมบูรณ์",
            stats: [
                { label: "Briefing Sync Status:", value: "ONLINE", class: "online" },
                { label: "Next Broadcast:", value: "THU 20:00", class: "" },
                { label: "Scheduled Clips:", value: "8 Videos", class: "online" }
            ],
            link: "wtj_calendar_dashboard.html",
            btnText: "ENTER BRIEFING"
        },
        veda: {
            module: "SECTION 04",
            title: "VEDA CORE / DATABASE",
            desc: "ฐานข้อมูลวิเคราะห์ระบบ Veda แสดงโครงสร้าง Obsidian Graph 3 มิติ และโรงเก็บพอร์ทัลลิงก์ภายนอกไปยังคริปโต บัญชี Grab และเงินออมสะสม",
            stats: [
                { label: "Database Status:", value: "SYNCHRONIZED", class: "online" },
                { label: "Total Knowledge Nodes:", value: "284 Weight", class: "" },
                { label: "Obsidian Core Integrity:", value: "100%", class: "online" }
            ],
            link: "graph_view.html",
            btnText: "QUERY DATABASE"
        }
    };

    const standbyContent = `
        <div class="hud-placeholder">
            <p class="hud-title-large">VEDA LINK</p>
            <p class="hud-desc-large">SELECT CODES / HOVER SHIP MODULE TO INJECT DIRECT DATA STREAM</p>
            <div class="hud-pulse-ring"></div>
        </div>
    `;

    if (hudMonitorBox) {
        shipSections.forEach(section => {
            section.addEventListener('mouseenter', () => {
                const sectKey = section.getAttribute('data-section');
                const data = hudData[sectKey];
                if (!data) return;

                // Stop the telemetry stream temporarily while inspecting details
                if (telemetryInterval) {
                    clearInterval(telemetryInterval);
                    telemetryInterval = null;
                }

                // Update Tag
                if (hudStatusTag) {
                    hudStatusTag.textContent = "ACTIVE LINK";
                    hudStatusTag.className = "alert-tag active";
                }

                // Render Content
                let statsHtml = '';
                data.stats.forEach(st => {
                    const valClass = st.class ? `class="${st.class}"` : '';
                    statsHtml += `
                        <div class="hud-stats-item">
                            <span class="hud-stats-label">${st.label}</span>
                            <span class="hud-stats-value ${st.class}">${st.value}</span>
                        </div>
                    `;
                });

                hudMonitorBox.innerHTML = `
                    <div class="hud-active-content">
                        <div class="hud-header">
                            <div class="hud-module-num">${data.module}</div>
                            <div class="hud-module-title">${data.title}</div>
                        </div>
                        <p class="hud-desc">${data.desc}</p>
                        <div class="hud-stats-list">
                            ${statsHtml}
                        </div>
                        <a href="${data.link}" class="hud-btn">${data.btnText}</a>
                    </div>
                `;
            });
        });

        // Revert to standby or code stream when leaving the module directory panel
        const directoryBody = document.querySelector('.module-directory-body');
        if (directoryBody) {
            directoryBody.addEventListener('mouseleave', () => {
                const isActive = window.workflowStatus && window.workflowStatus.activeNode !== 'idle';
                if (isActive) {
                    startHUDTelemetryStream();
                } else {
                    stopHUDTelemetryStream();
                }
            });
        }
    }

    // 6. Cockpit Button Listeners & Emergency
    const monitor = document.getElementById('terminal-monitor');
    const emergencyBtn = document.getElementById('btn-emergency');
    const mode1Btn = document.getElementById('btn-mode-1');
    const mode2Btn = document.getElementById('btn-mode-2');
    const mode3Btn = document.getElementById('btn-mode-3');

    const updateModeActive = (activeBtn) => {
        [mode1Btn, mode2Btn, mode3Btn].forEach(btn => {
            if (btn) {
                btn.classList.remove('active');
                const indicator = btn.querySelector('.btn-status-indicator');
                if (indicator) indicator.style.background = 'var(--border-color)';
            }
        });
        if (activeBtn) {
            activeBtn.classList.add('active');
            const indicator = activeBtn.querySelector('.btn-status-indicator');
            if (indicator) indicator.style.background = 'var(--text-primary)';
        }
    };

    // Initialize mode active style
    updateModeActive(mode1Btn);

    if (emergencyBtn && monitor) {
        emergencyBtn.addEventListener('click', () => {
            const timeStr = new Date().toTimeString().split(' ')[0];
            addLogEntry(monitor, timeStr, 'SYS', 'WARNING: EMERGENCY INTERRUPT ACTIVATED. COCKPIT SYSTEMS ENFORCED SECURITY ALIGNMENT!');
            
            // Suspend telemetry stream
            if (telemetryInterval) {
                clearInterval(telemetryInterval);
                telemetryInterval = null;
            }
            if (window.workflowStatus) window.workflowStatus.activeNode = 'emergency';
            
            if (hudStatusTag) {
                hudStatusTag.textContent = "EMERGENCY";
                hudStatusTag.className = "alert-tag emergency";
            }
            
            if (hudMonitorBox) {
                hudMonitorBox.innerHTML = `
                    <div class="hud-active-content emergency">
                        <div class="hud-header">
                            <div class="hud-module-num">ALERT CODE: RED</div>
                            <div class="hud-module-title">EMERGENCY HALT</div>
                        </div>
                        <p class="hud-desc">ระบบ Veda เข้าสู่โหมดความปลอดภัยสูงสุด คีย์การประมวลผลและการอัปเดตไฟล์ถูกระงับชั่วคราว รอคำสั่งเคลียร์โค้ดจากผู้บังคับบัญชา</p>
                    </div>
                `;
            }
        });
    }

    if (mode1Btn && monitor) {
        mode1Btn.addEventListener('click', () => {
            updateModeActive(mode1Btn);
            const timeStr = new Date().toTimeString().split(' ')[0];
            addLogEntry(monitor, timeStr, 'SYS', 'VEDA OPERATION: SWITCHED TO INTERVENTION MODE 1 (STABLE).');
            if (window.workflowStatus) window.workflowStatus.activeNode = 'idle';
            stopHUDTelemetryStream();
        });
    }

    if (mode2Btn && monitor) {
        mode2Btn.addEventListener('click', () => {
            updateModeActive(mode2Btn);
            const timeStr = new Date().toTimeString().split(' ')[0];
            addLogEntry(monitor, timeStr, 'SYS', 'VEDA OPERATION: SWITCHED TO GLOBAL MONITORING MODE 2.');
            if (window.workflowStatus) window.workflowStatus.activeNode = 'monitoring';
            startHUDTelemetryStream();
        });
    }

    if (mode3Btn && monitor) {
        mode3Btn.addEventListener('click', () => {
            updateModeActive(mode3Btn);
            const timeStr = new Date().toTimeString().split(' ')[0];
            addLogEntry(monitor, timeStr, 'SYS', 'VEDA OPERATION: SWITCHED TO DIRECT NEURAL STREAM MODE 3 (TRANS-AM READY).');
            if (window.workflowStatus) window.workflowStatus.activeNode = 'neural';
            startHUDTelemetryStream();
        });
    }

    // Real-time PnL Trend fluctuation simulation
    setInterval(() => {
        if (typeof historyData === 'undefined' || Object.keys(coinState).length === 0) return;
        
        const allCoins = Object.keys(historyData.data);
        allCoins.forEach(coin => {
            const state = coinState[coin];
            if (!state) return;

            // Fluctuate the current price by a small random percentage (-0.1% to +0.1%)
            const priceChangePct = (Math.random() - 0.5) * 0.2; // -0.1% to +0.1%
            state.currentPrice = state.currentPrice * (1 + priceChangePct / 100);
            
            // Recalculate PNL percentage based on new current price vs base price
            state.pnlPct = ((state.currentPrice - state.basePrice) / state.basePrice) * 100;

            // Update DOM element for price
            const priceCell = document.getElementById(`pnl-price-${coin}`);
            if (priceCell) {
                priceCell.textContent = state.currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' THB';
            }
            
            // Update DOM element for PNL %
            const pnlCell = document.getElementById(`pnl-val-latest-${coin}`);
            if (pnlCell) {
                pnlCell.textContent = state.pnlPct.toFixed(2) + '%';
                pnlCell.style.color = state.pnlPct >= 0 ? 'var(--text-primary)' : '#d32f2f';
            }
        });
    }, 3000);
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}

// 7. Initializers using external Data Packages

function initBridgeStatus() {
    const statusData = window.workflowStatus;
    if (!statusData) return;

    // Active Node text
    const activeNodeEl = document.getElementById('bridge-active-node');
    if (activeNodeEl) {
        activeNodeEl.textContent = statusData.activeNode;
    }

    // Last Updated
    const lastUpdatedEl = document.getElementById('bridge-last-updated');
    if (lastUpdatedEl) {
        lastUpdatedEl.textContent = statusData.lastUpdated;
    }

    // Marquee status text
    const tickerTextEl = document.getElementById('ticker-status-text');
    if (tickerTextEl) {
        tickerTextEl.textContent = `VEDA ONLINE // NODE: ${statusData.activeNode.toUpperCase()} // STATUS: ${statusData.statusText} // LAST PULSE: ${statusData.lastUpdated}`;
    }

    // Latest Artifact Link
    const artifactLinkEl = document.getElementById('bridge-artifact-link');
    if (artifactLinkEl && statusData.artifacts) {
        const artifactNames = Object.keys(statusData.artifacts);
        if (artifactNames.length > 0) {
            const artifactName = artifactNames[0];
            const artifactPath = statusData.artifacts[artifactName];
            artifactLinkEl.innerHTML = `<a href="${artifactPath}" title="${artifactPath}" style="color: var(--text-primary); text-decoration: underline; word-break: break-all;">${artifactName}</a>`;
        }
    }
}

function initTerminalMonitor() {
    const monitor = document.getElementById('terminal-monitor');
    const statusData = window.workflowStatus;
    if (!monitor || !statusData) return;

    // Render initial logs from workflow status data package
    if (statusData.logs && statusData.logs.length > 0) {
        statusData.logs.forEach(l => {
            addLogEntry(monitor, l.time, l.agent.toUpperCase(), l.message);
        });
    } else {
        // Fallback logs
        addLogEntry(monitor, '13:50:02', 'SYS', 'VEDA SYSTEM CORE INITIALIZED SUCCESSFULLY.');
    }

    // Periodically inject simulated logs
    const randomLogs = [
        { tag: 'SYS', msg: 'ANTIGRAVITY FRAMEWORK POLLING PROCESS RUNNING STABLE.' },
        { tag: 'GRAB', msg: 'JANE EXECUTING NIGHTLY ROLLOVER CLOCK SCHEDULE: READY.' },
        { tag: 'CRYPTO', msg: 'WIN RECALCULATING CRYPTO PORTFOLIO PACING VALUES.' },
        { tag: 'SYS', msg: 'PIE DATA ENGINE ANALYZING RECENT VIDEO RETENTION DRIFT.' },
        { tag: 'SYS', msg: 'FIRST COMPILING WEEKLY TEAM DISPATCH REPORTS.' }
    ];

    setInterval(() => {
        const randomLog = randomLogs[Math.floor(Math.random() * randomLogs.length)];
        const timeStr = new Date().toTimeString().split(' ')[0];
        addLogEntry(monitor, timeStr, randomLog.tag, randomLog.msg);
    }, 12000);
}

function initNotionTimeline() {
    const container = document.getElementById('timeline-container');
    if (!container || typeof NOTION_CALENDAR_DATA === 'undefined') return;

    // Process and sort Notion schedule data
    const dataList = [];
    for (const datetime in NOTION_CALENDAR_DATA) {
        // Parse date/time key like "2026-05-27-18:00" -> Date object
        const parts = datetime.split('-');
        if (parts.length < 4) continue;
        const dateStr = `${parts[0]}-${parts[1]}-${parts[2]}T${parts[3]}`;
        const dateObj = new Date(dateStr);
        dataList.push({
            rawKey: datetime,
            date: dateObj,
            formattedDate: `${parts[2]}/${parts[1]}/${parts[0]} ${parts[3]}`,
            title: NOTION_CALENDAR_DATA[datetime].title,
            status: NOTION_CALENDAR_DATA[datetime].status,
            notionStatus: NOTION_CALENDAR_DATA[datetime].notion_status
        });
    }

    // Sort ascending (past to future schedule)
    dataList.sort((a, b) => a.date - b.date);

    // Group into Reels and Videos 3-5 Mins
    const reels = [];
    const videos = [];

    dataList.forEach(item => {
        const titleLower = item.title.toLowerCase();
        if (titleLower.includes('reels') || titleLower.includes('30 sec') || titleLower.includes('short')) {
            reels.push(item);
        } else {
            videos.push(item);
        }
    });

    // Generate HTML layout for grouped timeline
    let timelineHtml = `
        <div class="timeline-columns">
            
            <!-- Reels (Column left) -->
            <div class="timeline-col">
                <div class="timeline-header-block">
                    REELS & SHORTS TIMELINE (< 1 MIN)
                </div>
                <div class="timeline-list">
                    ${reels.map(r => renderTimelineCard(r)).join('')}
                </div>
            </div>

            <!-- Videos 3-5Mins (Column right) -->
            <div class="timeline-col">
                <div class="timeline-header-block">
                    WTJ TALK & STORY (3-5 MINS)
                </div>
                <div class="timeline-list">
                    ${videos.map(v => renderTimelineCard(v)).join('')}
                </div>
            </div>

        </div>
    `;

    container.innerHTML = timelineHtml;

    // Attach tooltip event handlers
    attachTimelineTooltipHandlers();
}

function renderTimelineCard(item) {
    const isPublished = item.notionStatus === '6_Published';
    const statusClass = isPublished ? 'status-published' : 'status-queued';
    
    // Status text and style
    const badgeText = isPublished ? 'PUBLISHED' : 'QUEUED';
    const badgeStyle = isPublished 
        ? 'background: var(--border-color); color: var(--panel-bg); font-weight: bold; border: 1px solid var(--border-color);'
        : 'background: transparent; color: var(--text-primary); border: 1px solid var(--border-color); opacity: 0.7;';
    
    const icon = isPublished ? '✓' : '⧗';

    return `
        <div class="timeline-item-card ${statusClass}" data-title="${item.title}" data-date="${item.formattedDate}" data-status="${item.notionStatus}">
            <div class="timeline-card-date">
                ${item.formattedDate}
            </div>
            <div class="timeline-card-title">
                ${item.title.replace(/\[.*?\]\s*/g, '')}
            </div>
            <div class="timeline-card-footer">
                <span class="timeline-card-badge">
                    ${icon} ${badgeText}
                </span>
                <span class="timeline-card-status">
                    ${item.notionStatus}
                </span>
            </div>
        </div>
    `;
}

function attachTimelineTooltipHandlers() {
    const cards = document.querySelectorAll('.timeline-item-card');
    
    // Create tooltip element if it doesn't exist
    let tooltip = document.getElementById('timeline-tooltip');
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'timeline-tooltip';
        // Styles are fully managed in CSS via #timeline-tooltip
        document.body.appendChild(tooltip);
    }

    cards.forEach(card => {
        card.addEventListener('mouseenter', (e) => {
            const title = card.getAttribute('data-title');
            const date = card.getAttribute('data-date');
            const status = card.getAttribute('data-status');
            
            tooltip.innerHTML = `
                <div class="tooltip-header">NOTION META INFORMATION</div>
                <div><strong>RAW FILE:</strong> ${title}</div>
                <div><strong>SCHEDULED:</strong> ${date}</div>
                <div><strong>NOTION STATUS:</strong> ${status}</div>
                <div class="tooltip-divider">VEDA TELEMETRY VERIFIED</div>
            `;
            tooltip.style.display = 'block';
            card.classList.add('hovered');
        });

        card.addEventListener('mousemove', (e) => {
            tooltip.style.left = (e.pageX + 15) + 'px';
            tooltip.style.top = (e.pageY + 15) + 'px';
        });

        card.addEventListener('mouseleave', () => {
            tooltip.style.display = 'none';
            card.classList.remove('hovered');
        });
    });
}

// 8. Crypto PnL Table Setup (Holdings & Price Real-time Telemetry)

const COIN_HOLDINGS = {
    'BTC': { amount: 0.04500000, basePrice: 2350000.0 },
    'BNB': { amount: 1.25000000, basePrice: 20500.0 },
    'ASTER': { amount: 5400.0, basePrice: 3.50 },
    'XRP': { amount: 850.0, basePrice: 17.80 },
    'SOL': { amount: 3.20, basePrice: 5800.0 },
    'ETH': { amount: 0.75000000, basePrice: 115000.0 },
    'Thyme_KUB': { amount: 120.0, basePrice: 85.50 },
    'Mod_BTC': { amount: 0.00150000, basePrice: 2350000.0 }
};

let coinState = {};

function initCryptoTable() {
    if (typeof historyData === 'undefined') return;

    const tableBody = document.getElementById('pnl-table-body');
    if (!tableBody) return;

    let tableRowsHtml = '';
    const allCoins = Object.keys(historyData.data);

    allCoins.forEach(coin => {
        const holdings = COIN_HOLDINGS[coin] || { amount: 0.0, basePrice: 100.0 };
        const initialPnl = historyData.data[coin][4]; // latest PNL index from history_data.js
        const initialPrice = holdings.basePrice * (1 + initialPnl / 100);

        coinState[coin] = {
            amount: holdings.amount,
            basePrice: holdings.basePrice,
            currentPrice: initialPrice,
            pnlPct: initialPnl
        };

        const formattedAmount = coin.includes('BTC') || coin.includes('ETH') || coin.includes('BNB') 
            ? coinState[coin].amount.toFixed(8) 
            : coinState[coin].amount.toFixed(2);
            
        const formattedPrice = coinState[coin].currentPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' THB';
        const formattedPnl = coinState[coin].pnlPct.toFixed(2) + '%';
        const pnlColor = coinState[coin].pnlPct >= 0 ? 'color: var(--text-primary);' : 'color: #d32f2f;';

        tableRowsHtml += `
            <tr style="border-bottom: 1px dashed var(--telemetry-border);">
                <td style="text-align: left; padding: 8px; font-weight: bold; color: var(--text-primary);">${coin}</td>
                <td style="padding: 8px; color: var(--text-primary); font-family: 'Share Tech Mono', monospace;">${formattedAmount}</td>
                <td id="pnl-price-${coin}" style="padding: 8px; color: var(--text-primary); font-family: 'Share Tech Mono', monospace;">${formattedPrice}</td>
                <td id="pnl-val-latest-${coin}" style="padding: 8px; ${pnlColor} font-family: 'Share Tech Mono', monospace; font-weight: bold;">${formattedPnl}</td>
            </tr>
        `;
    });

    tableBody.innerHTML = tableRowsHtml;
}

function addLogEntry(container, time, tag, msg) {
    const line = document.createElement('div');
    line.className = 'terminal-line';
    
    // Warning or emergency logs are highlighted in red as a visual gimmick
    const isWarning = msg.toUpperCase().includes('WARNING') || 
                      msg.toUpperCase().includes('EMERGENCY') || 
                      tag.toUpperCase() === 'WARN' || 
                      tag.toUpperCase() === 'ERR';
    if (isWarning) {
        line.style.color = '#d32f2f';
    }
    
    const timeSpan = document.createElement('span');
    timeSpan.className = 'terminal-time';
    timeSpan.textContent = `[${time}]`;
    
    const tagSpan = document.createElement('span');
    tagSpan.className = `terminal-tag ${tag.toLowerCase()}`;
    tagSpan.textContent = `[${tag}]`;
    
    const msgSpan = document.createElement('span');
    msgSpan.className = 'terminal-msg';
    msgSpan.textContent = msg;
    
    line.appendChild(timeSpan);
    line.appendChild(tagSpan);
    line.appendChild(msgSpan);
    
    container.appendChild(line);
    
    // Auto scroll to bottom
    container.scrollTop = container.scrollHeight;
    
    // Limit lines inside console to avoid memory issues
    if (container.children.length > 50) {
        container.removeChild(container.firstChild);
    }
}
