// 0. THEME INITIALIZATION (Veda Mode)
window.setTheme = function(theme) {
    document.body.className = theme + '-theme';
    document.documentElement.className = theme + '-theme';
    try {
        localStorage.setItem('wtj-theme', theme);
    } catch (e) {
        console.warn('localStorage is not writable:', e);
    }
    document.querySelectorAll('.theme-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById(`theme-btn-${theme}`);
    if (activeBtn) activeBtn.classList.add('active');
};

let savedThemeVal = 'light';
try {
    savedThemeVal = localStorage.getItem('wtj-theme') || 'light';
} catch (e) {
    console.warn('localStorage is not readable:', e);
}
document.body.className = savedThemeVal + '-theme';
document.documentElement.className = savedThemeVal + '-theme';

document.addEventListener('DOMContentLoaded', () => {
    // Sync UI buttons on load
    const activeBtn = document.getElementById(`theme-btn-${savedThemeVal}`);
    if (activeBtn) {
        document.querySelectorAll('.theme-btn').forEach(btn => btn.classList.remove('active'));
        activeBtn.classList.add('active');
    }
});

// Sync display times from hidden badges updated by Python/M
function syncDisplayTimes() {
    const days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
    days.forEach(day => {
        const badge = document.getElementById(`opt-time-${day}`);
        const display = document.getElementById(`display-time-${day}`);
        if (badge && display) {
            const span = badge.querySelector('span');
            if (span) {
                const text = span.textContent;
                const match = text.match(/Time to Post:\s*(\d{2}:\d{2})/i);
                if (match) {
                    display.textContent = match[1];
                }
            }
        }
    });
}
syncDisplayTimes();

// 1. LIVE CLOCK SYSTEM (Tactical Time Readout)
function updateClock() {
    const clockElement = document.getElementById('system-clock');
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    clockElement.textContent = `${hours}:${minutes}:${seconds}`;
}
setInterval(updateClock, 1000);
updateClock();

// 2. WINDOW CONTROLS (Veda Floating Interface)
let highestZIndex = 100;

function switchTab(tabId) {
    if (tabId === 'calendar') {
        // If calendar is clicked, maybe close all floating windows to show base
        document.querySelectorAll('.floating-window').forEach(pane => pane.classList.remove('active'));
        document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelector('.nav-btn[onclick*="calendar"]').classList.add('active');
        return;
    }
    
    // For other tabs, it acts as a toggle popup
    const targetPane = document.getElementById(`tab-${tabId}`);
    const targetBtn = Array.from(document.querySelectorAll('.nav-btn')).find(btn => 
        btn.getAttribute('onclick').includes(tabId)
    );
    
    if (targetPane) {
        if (targetPane.classList.contains('active')) {
            // Close it
            targetPane.classList.remove('active');
            if (targetBtn) targetBtn.classList.remove('active');
        } else {
            // Open it and bring to front
            highestZIndex++;
            targetPane.style.zIndex = highestZIndex;
            targetPane.classList.add('active');
            if (targetBtn) targetBtn.classList.add('active');
        }
    }
}

// 3. MOCK DRAFTS DATA (Based on exact processed outputs)
const draftsData = {
    'wedding-photographer': `อาชีพช่างภาพ - แค่กดชัตเตอร์แปบๆก็ได้เงิน? 📸💸

หลายคนอาจจะเห็นแค่ภาพสวยๆ หน้างาน ยืนกดชัตเตอร์แปบๆ ก็รับเงินกลับบ้าน... แต่เบื้องหลังที่ไม่มีใครรู้คือ อาชีพนี้คือการแบกรับความคาดหวังระดับชาติ ที่ห้ามพลาดเด็ดขาด

วันนี้ทางเราทีมงาน What the job ได้ชวนพี่เก่ง (Vokeng Photographer) ช่างภาพ Wedding ที่อยู่ในวงการมานาน มานั่งพูดคุยกัน และนี่ส่วนหนึ่งที่ทำให้รู้ว่า อาชีพนี้ไม่ง่ายอย่างที่คิด:

1️⃣ เวลาในการทำงานไม่ใช่วันละ 4-5 ชั่วโมง:
ต้องตื่นตั้งแต่ตี 2 เพื่อไปเตรียมตัวถ่ายงานตอนตี 5 แล้วลากยาวไปจนถึง 5 ทุ่ม... แถมพอกลับบ้านไป ยังต้องมานั่งโหลดการ์ดและทำภาพไฮไลต์ให้ลูกค้าต่อ (สรุปว่าไม่ได้นอน!)

2️⃣ ต้องเป็นนักจิตวิทยามากกว่าตากล้อง:
ปัญหาหน้างานไม่ใช่อุปกรณ์พัง หรือฝนตก แต่คือ ความกังวลของคน ช่างภาพหลักต้องคอย ละลายพฤติกรรม บ่าวสาวที่กำลังเครียด หรือจัดการอารมณ์ทีมงานหลายฝ่ายให้งานออกมาสมูทที่สุด

3️⃣ อาชีพที่ไม่มีคำว่า เกษียณ:
ใครบอกว่าแก่แล้วแบกกล้องไม่ไหว? พี่เก่งบอกว่า ถ้าใจมันได้ แรงมันมี 60-70 ก็ยังถ่ายได้ เพราะมันคือศิลปะและประสบการณ์ที่ยิ่งทำยิ่งเก๋า!

ความลับอีกอย่างคือ Connection สำคัญกว่าการดั๊มพ์ราคาแข่งกัน! ใครอยากรู้เบื้องลึกเบื้องหลังแบบเต็มๆ ตามไปดูคลิปสัมภาษณ์พี่เก่งได้เลยบ้านแดงของเราที่ลิ้งใต้คอมเม้นจ้า

🔗 https://www.youtube.com/watch?v=2SG1BAItYMg

#WTJStory #WhatTheJob #ช่างภาพงานแต่ง #WeddingPhotographer #เบื้องหลังคนทำงาน`,

    'muscari': `จุดเริ่มต้นคนปั่นจักรยาน - จากแอร์โฮสเตสสู่นักปั่นระดับ Global Brand Ambassador ทำได้ยังไง? 🚴‍♀️✨

หลายคนอาจจะคิดว่าการเป็น Brand Ambassador ให้กับแบรนด์กีฬาระดับโลก ต้องเป็นนักกีฬาอาชีพที่มีรางวัลการันตีมากมาย หรือต้องทำคอนเทนต์รีวิวขายของแบบหนักๆ... แต่เบื้องหลังความสำเร็จที่แท้จริง อาจเริ่มจากแค่ "ความหลงใหล" และ "ความสม่ำเสมอ" เท่านั้น

วันนี้ทางเราทีมงาน What the job ได้ชวน คุณกิ๊บ (Muscari / มุสคารี่) นักปั่นสาวสุดสตรองที่อยู่ในวงการมานานกว่า 10 ปี มานั่งพูดคุยกัน และนี่ส่วนหนึ่งที่ทำให้รู้ว่า อาชีพนี้ไม่ง่ายอย่างที่คิด:

1️⃣ ความสม่ำเสมอ (Consistency) คือกุญแจสำคัญ:
จากอาชีพแอร์โฮสเตสที่เวลานอนแทบไม่มี แต่ก็ยังแบ่งเวลามาปั่นจักรยานทุกวัน การทำสิ่งที่รักอย่างสม่ำเสมอทำให้แบรนด์ระดับโลกอย่าง Rapha มองเห็น และเลือกให้เป็น Brand Ambassador มายาวนานถึง 10 ปีเต็ม!

2️⃣ ความจริงใจ (Authenticity) ชนะการขายของ:
การทำงานกับ Global Brands ไม่ใช่แค่การรับของมาถ่ายรูปลงโซเชียล แต่คือการนำสินค้าเข้าไปเป็นส่วนหนึ่งของ Lifestyle จริงๆ ปั่นจริง ใช้จริง 100 กิโลเมตรเพื่อแค่ถ่ายรูปให้เห็นว่าเรา "อิน" กับมันจริงๆ

3️⃣ แบรนด์ระดับโลกให้คุณค่ากับ "ความพยายาม":
การดีลงานกับแบรนด์ใหญ่ (เช่น UAG หรือแบรนด์จักรยานต่างๆ) พวกเขาเข้าใจต้นทุนของการทำ Production ที่มีคุณภาพ และให้เกียรติการทำงานของ Creator เสมอ โดยไม่เคยกดราคาเลยสักครั้ง!

ความลับอีกอย่างคือ ถนนในประเทศไทยนี่แหละใจดีกับนักปั่นที่สุดในเอเชียแล้ว! ใครอยากรู้เบื้องลึกเบื้องหลังแบบเต็มๆ ตามไปดูคลิปสัมภาษณ์เต็มๆ ได้เลยบ้านแดงของเราที่ลิ้งใต้คอมเม้นจ้า👇

🔗 https://www.youtube.com/watch?v=Gwz7rBrIhxQ

#WTJStory #WhatTheJob #Muscari #CyclingLife #BrandAmbassador #ปั่นจักรยาน`,

    'wall-painter': `งานศิลปะบนกำแพงตึก - วาดคนเดียวบนนั่งร้านที่สูงลิบ เขากะสัดส่วนได้ยังไง? 🎨🏗️

หลายคนเวลาเดินผ่านโรงแรมหรือคาเฟ่แล้วเห็นภาพวาดบนกำแพงสวยๆ อาจจะคิดว่าศิลปินก็แค่วาดรูปไซส์ใหญ่ขึ้น... แต่ความจริงเบื้องหลัง "Wall Painting" มันดุเดือดกว่านั้นเยอะ!

วันนี้ทางเราทีมงาน What the job ได้ชวน พี่เก่ง ภูมิไทย (เพจ ต้นสี Wall Painting) ศิลปินนักวาดภาพฝาผนังตัวจริง มานั่งพูดคุยกันถึงเบื้องหลังงานสเกลยักษ์ที่น้อยคนจะเคยเห็น

พี่เก่งเล่าให้ฟังว่า การวาดรูปบนกำแพงใหญ่ๆ มันไม่เหมือนการวาดบนเฟรมผ้าใบในห้องแอร์เลยสักนิด! เพราะที่หน้างาน คุณต้องเจอกับแสงแดดเปรี้ยงๆ ฝุ่นควัน กลิ่นทินเนอร์ และบางทีต้องทำงานแข่งกับช่างปูนช่างเหล็กข้างๆ 

แต่ความพีคที่สุดคือ "สเกลที่ใหญ่เกินกว่าจะมองเห็น" 
เวลาคุณปีนขึ้นไปอยู่บนนั่งร้านแคบๆ มือขวาจับพู่กัน มือซ้ายเกาะเสาเพื่อความปลอดภัย... ภาพตรงหน้ามันใหญ่จน "สุดมือเอื้อม" คุณจะมองไม่เห็นภาพรวมเลยว่าตาอยู่ตรงไหน หูอยู่ตรงไหน! งานนี้เลยทำคนเดียวไม่ได้ ต้องมีทีมงานอีกคนยืนอยู่ข้างล่าง คอยตะโกนบอกว่า "ขยับซ้ายอีกนิด! ลงล่างอีกหน่อย!" เพื่อกะสัดส่วนให้พอดี

ถึงสภาพแวดล้อมจะโหดและกดดันขนาดไหน แต่สำหรับพี่เก่ง การวาดรูปไม่เคยทำให้เครียดเลย พี่เก่งบอกว่า "มันเป็นธรรมชาติไปแล้ว เหมือนเรานั่งวาดสนุกๆ เล่นๆ แล้วเราก็ได้เงินไง" 

ใครอยากรู้เบื้องลึกเบื้องหลังและเทคนิคการรับงานสายอาร์ตแบบเต็มๆ ตามไปดูคลิปสัมภาษณ์เต็มๆ ได้เลยบ้านแดงของเราที่ลิ้งใต้คอมเม้นจ้า👇

🔗 https://www.youtube.com/watch?v=TUXVwxumHsg

#WTJStory #WhatTheJob #WallPainting #MuralArt #วาดภาพกำแพง #ศิลปินวาดภาพ`
};

// 4. MODAL CONTROLS
function openTextModal(key) {
    const modal = document.getElementById('text-modal');
    const textarea = document.getElementById('modal-textarea');
    const title = document.getElementById('modal-title');
    
    let modalHeader = '';
    if (key === 'wall-painter') modalHeader = 'FACEBOOK POST: พี่เก่ง ภูมิไทย (ต้นสี Wall Painting)';
    else if (key === 'muscari') modalHeader = 'FACEBOOK POST: คุณกิ๊บ Muscari';
    else if (key === 'wedding-photographer') modalHeader = 'FACEBOOK POST: พี่เก่ง โวเก่ง';
    
    title.textContent = modalHeader;
    textarea.value = draftsData[key] || '';
    modal.style.display = 'flex';
}

function closeModal() {
    const modal = document.getElementById('text-modal');
    modal.style.display = 'none';
}

function copyModalText() {
    const textarea = document.getElementById('modal-textarea');
    textarea.select();
    textarea.setSelectionRange(0, 99999); // For mobile devices
    
    navigator.clipboard.writeText(textarea.value).then(() => {
        alert('คัดลอกข้อความลง Clipboard สำเร็จแล้วจ้า! 🎉');
    }).catch(err => {
        console.error('Could not copy text: ', err);
    });
}

// Close modal when clicking outside of the content box
window.onclick = function(event) {
    const modal = document.getElementById('text-modal');
    if (event.target === modal) {
        closeModal();
    }
}

// 5. MOCK PIPELINE CONTROLLER
function triggerPipeline() {
    const urlInput = document.getElementById('yt-url-input');
    const terminal = document.getElementById('terminal-readout');
    
    if (!urlInput.value.trim()) {
        alert('กรุณากรอกลิงก์ YouTube ก่อนกดสั่งการจ้า! ⚠️');
        return;
    }
    
    const url = urlInput.value.trim();
    
    // Add logs to terminal simulation
    appendTerminalLine(`INCOMING ACTION: WTJ ENGINE ACTIVATED FOR URL [${url}]`);
    appendTerminalLine('CREAM (GN-001) -> LAUNCHED. EXTRACTING AUDIO DATA...');
    
    setTimeout(() => {
        appendTerminalLine('✅ CREAM (GN-001) -> TRANSCRIPT RETRIEVED SUCCESSFULLY!');
        appendTerminalLine('ZEE (GN-002) -> LAUNCHED. EXTRACTING TARGET HOOKS & KEY INSIGHTS...');
    }, 1500);

    setTimeout(() => {
        appendTerminalLine('✅ ZEE (GN-002) -> INSIGHT GENERATION COMPLETE.');
        appendTerminalLine('RAY (GN-003) -> LAUNCHED. GENERATING SOCIAL MEDIA DRAFT...');
    }, 3000);

    setTimeout(() => {
        appendTerminalLine('✅ RAY (GN-003) -> DRAFT COMPLETE (STORYTELLING FORMAT APPLIED).');
        appendTerminalLine('CHRIS (GN-005) -> LAUNCHED. RUNNING ACCURACY CHECK...');
    }, 4500);

    setTimeout(() => {
        appendTerminalLine('✅ CHRIS (GN-005) -> CONTENT VERIFIED. NO TONE CORRECTIONS.');
        appendTerminalLine('SYSTEM -> WRITING DATA DIRECTLY TO APPLE NOTES [WTJ Talk -> Facebook]...');
    }, 6000);

    setTimeout(() => {
        appendTerminalLine('🎉 PIPELINE WORKFLOW COMPLETE! WORKSPACE AND NOTES SYNCHRONIZED!', 'success');
        urlInput.value = '';
    }, 7500);
}

function appendTerminalLine(text, className = '') {
    const terminal = document.getElementById('terminal-readout');
    const line = document.createElement('div');
    line.className = 'line ' + className;
    line.innerHTML = `<span class="prompt">></span> ${text}`;
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight; // Auto scroll to bottom
}

// 6. TACTICAL RADAR SWEEP ANIMATION & JITTER EFFECT
function initRadarSweep() {
    const markers = {
        'GN-001': { element: null, angle: 45 },
        'GN-002': { element: null, angle: 230 },
        'GN-003': { element: null, angle: 342 },
        'GN-005': { element: null, angle: 135 }
    };
    
    // Find elements
    const markerElements = document.querySelectorAll('.gundam-marker');
    markerElements.forEach(el => {
        const text = el.textContent.trim();
        if (markers[text]) {
            markers[text].element = el;
        }
    });
    
    const startTime = Date.now();
    
    function updateRadar() {
        const elapsed = (Date.now() - startTime) % 6000; // 6s sweep duration
        const scanAngle = (elapsed / 6000) * 360;
        
        Object.keys(markers).forEach(key => {
            const m = markers[key];
            if (!m.element) return;
            
            // Calculate relative angle difference
            let diff = (scanAngle - m.angle + 360) % 360;
            
            // When leading edge sweeps within 20 degrees
            if (diff < 20) {
                m.element.classList.add('active-scan');
                
                // Subtle organic target acquisition jitter
                const jitterX = (Math.random() - 0.5) * 3;
                const jitterY = (Math.random() - 0.5) * 3;
                m.element.style.transform = `translate(calc(-50% + ${jitterX}px), calc(-50% + ${jitterY}px)) scale(1.08)`;
                m.element.style.filter = 'brightness(1.2) contrast(1.1)';
                m.element.style.borderColor = '#ff3b30';
                m.element.style.boxShadow = '0 0 10px rgba(255, 59, 48, 0.4)';
                m.element.style.transition = 'none'; // Instant reaction
            } else {
                m.element.classList.remove('active-scan');
                
                // Smooth recovery back to calm base state
                m.element.style.transform = 'translate(-50%, -50%) scale(1)';
                m.element.style.filter = 'none';
                m.element.style.borderColor = 'var(--border-color)';
                m.element.style.boxShadow = '0 4px 15px var(--shadow-color)';
                m.element.style.transition = 'transform 0.8s ease, filter 0.8s ease, border-color 0.8s ease, box-shadow 0.8s ease';
            }
        });
        
        requestAnimationFrame(updateRadar);
    }
    
    requestAnimationFrame(updateRadar);
}

// Start radar telemetry system
initRadarSweep();
