// ฐานข้อมูลจำลอง (Mock Data) สำหรับแอปพลิเคชันระบบเครื่องถ่ายเอกสารให้เช่า
const COPIER_DATA = {
  // ข้อมูลช่างซ่อมบำรุง
  technicians: [
    { id: "T01", name: "ช่างสมชาย ใจดี", status: "Available", phone: "081-234-5678", currentJob: null, rating: 4.8 },
    { id: "T02", name: "ช่างวิชัย รักดี", status: "Working", phone: "089-876-5432", currentJob: "ร้านส้มตำเจ๊ไก่", rating: 4.9 },
    { id: "T03", name: "ช่างนพดล เก่งกาจ", status: "Available", phone: "085-111-2222", currentJob: null, rating: 4.7 },
    { id: "T04", name: "ช่างเสกสรร วงศ์ษา", status: "Break", phone: "086-333-4444", currentJob: null, rating: 4.6 },
    { id: "T05", name: "ช่างประวิทย์ สินชัย", status: "Available", phone: "082-555-6666", currentJob: null, rating: 4.9 }
  ],

  // ข้อมูลอะไหล่ในสตอค
  parts: [
    { id: "P01", name: "ลูกยางดึงกระดาษ (Paper Feed Roller)", compatible: "Canon iR-A 4535, Ricoh IM C3000", stock: 12, minStock: 15, unit: "ชิ้น" },
    { id: "P02", name: "ผงหมึกดำ (Toner Black NPG-67)", compatible: "Canon iR-A 4535", stock: 25, minStock: 10, unit: "หลอด" },
    { id: "P03", name: "ชุดดรัมสีน้ำเงิน (Drum Unit Cyan)", compatible: "Ricoh IM C3000", stock: 3, minStock: 5, unit: "ชุด" },
    { id: "P04", name: "ใบมีดปาดหมึก (Drum Cleaning Blade)", compatible: "Canon iR-A 4535, Ricoh IM C3000", stock: 8, minStock: 10, unit: "ชิ้น" },
    { id: "P05", name: "แผ่นความร้อน (Fusing Belt)", compatible: "Ricoh IM C3000, HP LaserJet Managed E82560", stock: 4, minStock: 3, unit: "ชิ้น" },
    { id: "P06", name: "คลัตช์ดึงกระดาษ (Paper Feed Clutch)", compatible: "HP LaserJet Managed E82560", stock: 2, minStock: 5, unit: "ชิ้น" },
    { id: "P07", name: "ผงหมึกสีเหลือง (Toner Yellow IM C3000)", compatible: "Ricoh IM C3000", stock: 8, minStock: 5, unit: "หลอด" },
    { id: "P08", name: "ผงหมึกสีแดง (Toner Magenta IM C3000)", compatible: "Ricoh IM C3000", stock: 2, minStock: 5, unit: "หลอด" },
    { id: "P09", name: "ผงหมึกสีน้ำเงิน (Toner Cyan IM C3000)", compatible: "Ricoh IM C3000", stock: 6, minStock: 5, unit: "หลอด" },
    { id: "P10", name: "ตลับหมึกสีดำ (Toner Black IM C3000)", compatible: "Ricoh IM C3000", stock: 14, minStock: 8, unit: "หลอด" },
    { id: "P11", name: "ชุดลวดประจุประธาน (Corona Wire Unit)", compatible: "Ricoh IM C3000", stock: 1, minStock: 3, unit: "ชุด" },
    { id: "P12", name: "ลูกกลิ้งกดความร้อน (Pressure Roller)", compatible: "Ricoh IM C3000", stock: 5, minStock: 2, unit: "ชิ้น" },
    { id: "P13", name: "เฟืองขับชุดความร้อน (Fuser Drive Gear)", compatible: "Ricoh IM C3000", stock: 12, minStock: 10, unit: "ตัว" },
    { id: "P14", name: "เซนเซอร์ตรวจจับกระดาษ (Paper Pass Sensor)", compatible: "Ricoh IM C3000", stock: 3, minStock: 5, unit: "ตัว" },
    { id: "P15", name: "ลูกกลิ้งทางเข้ากระดาษ (Registration Roller)", compatible: "Ricoh IM C3000", stock: 4, minStock: 3, unit: "ชิ้น" }
  ],

  // ข้อมูลร้านค้าที่ใช้บริการเช่าเครื่องถ่ายเอกสาร
  shops: [
    {
      id: "S01",
      name: "ร้านกาแฟคอฟฟี่มีน (Coffee Mean)",
      address: "12/3 ถ.นิมมานเหมินท์ ซอย 9 ต.สุเทพ อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50200",
      copierModel: "Canon iR-A 4535",
      serialNumber: "CN-98481A",
      lastMaintenance: "2026-05-15",
      maintenanceNotes: "เปลี่ยนลูกยางดึงกระดาษ ทำความสะอาดกระจกสแกน และทดสอบระบบพิมพ์ขาวดำเรียบร้อย",
      nextMaintenance: "2026-08-15",
      mapX: 25,
      mapY: 48
    },
    {
      id: "S02",
      name: "สำนักงานกฎหมาย วีระการบัญชี",
      address: "45/2 ถ.ท่าแพ ต.ช้างคลาน อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50100",
      copierModel: "Ricoh IM C3000",
      serialNumber: "RC-33291F",
      lastMaintenance: "2026-06-02",
      maintenanceNotes: "เปลี่ยนชุดดรัมสีน้ำเงิน (Cyan Drum) เนื่องจากสีเพี้ยน ทดสอบพิมพ์สีผ่านทุกเฉด",
      nextMaintenance: "2026-09-02",
      mapX: 68,
      mapY: 52
    },
    {
      id: "S03",
      name: "ร้านส้มตำเจ๊ไก่ สาขาคูเมืองเชียงใหม่",
      address: "88 ถ.ศรีภูมิ ต.ศรีภูมิ อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50200",
      copierModel: "Canon iR-A 4535",
      serialNumber: "CN-11029B",
      lastMaintenance: "2026-04-20",
      maintenanceNotes: "เป่าฝุ่น ตรวจสอบระดับผงหมึก และเปลี่ยนใบมีดปาดหมึกชำรุด",
      nextMaintenance: "2026-07-20",
      mapX: 47,
      mapY: 42
    },
    {
      id: "S04",
      name: "บริษัท โลจิสติกส์ ไทยแลนด์ สาขาเชียงใหม่",
      address: "99/1 ถ.ช้างเผือก ต.ช้างเผือก อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50300",
      copierModel: "HP LaserJet Managed E82560",
      serialNumber: "HP-88371C",
      lastMaintenance: "2026-03-10",
      maintenanceNotes: "เปลี่ยนคลัตช์ดึงกระดาษเนื่องจากกระดาษไม่ขึ้นถาด 2 และเป่าฝุ่นทำความสะอาดระบบลำเลียงกระดาษ",
      nextMaintenance: "2026-06-10", // เกินกำหนดตรวจเช็ก!
      mapX: 42,
      mapY: 22
    },
    {
      id: "S05",
      name: "โรงเรียนสอนภาษา ก้าวหน้าอินเตอร์",
      address: "71/5 ถ.มหิดล ต.ป่าแดด อ.เมืองเชียงใหม่ จ.เชียงใหม่ 50100",
      copierModel: "Ricoh IM C3000",
      serialNumber: "RC-44821E",
      lastMaintenance: "2026-05-28",
      maintenanceNotes: "แก้ไขอาการกระดาษติดบ่อยที่ชุดทางออกกระดาษ ทำความสะอาดเซนเซอร์จับกระดาษ",
      nextMaintenance: "2026-08-28",
      mapX: 52,
      mapY: 82
    }
  ],

  // คู่มือการซ่อมบำรุงและประวัติปัญหาที่เคยแก้
  manuals: [
    {
      model: "Canon iR-A 4535",
      standardChecklist: [
        "เป่าฝุ่นและทำความสะอาดกระจกสแกน (Slit Glass และ Platen Glass)",
        "เช็กสภาพความสึกหรอของลูกยางดึงกระดาษ (ถาด 1, 2 และถาดบายพาส)",
        "ตรวจสอบหน้าสัมผัสของชุดสร้างภาพ (Drum Unit) และหน้าสัมผัสโคโรนาสไลด์",
        "ตรวจสอบระดับผงหมึก (Toner) และปริมาณกล่องเก็บหมึกเสีย (Waste Toner Box)",
        "ทดสอบปริ้นใบตารางสีเทา (Halftone Grid) เพื่อตรวจเช็กความสม่ำเสมอของหมึก"
      ],
      commonIssues: [
        { issue: "กระดาษติดบ่อยที่ถาด 1 (Paper Jam Tray 1)", fix: "ถอดเปลี่ยนลูกยางดึงกระดาษ (Paper Feed Roller) สามลูกชุดของแท้ ยางมักหมดอายุความฝืด" },
        { issue: "พิมพ์แล้วมีเส้นดำแนวตั้งเส้นเล็กๆ ตลอดแนวกระดาษ", fix: "เช็ดกระจกสแกนเนอร์บานเล็กฝั่งซ้าย (Slit Glass) ด้วยผ้าแห้งสะอาด มักมีคราบลิควิดเปเปอร์ติดอยู่" },
        { issue: "เครื่องฟ้องข้อผิดพลาดโค้ด E000-0000 (ความร้อนหัวฟิวส์พัง)", fix: "ปิดเครื่อง ถอดสายไฟ ทิ้งไว้ 10 นาทีเพื่อระบายความร้อน แล้วเข้าไปที่ Service Mode เคลียร์ Error Code (COPIER > FUNCTION > CLEAR > ERR)" }
      ],
      troubleshootingFlows: [
        {
          id: "canon-jam",
          title: "กระดาษติดบ่อยที่ถาด 1 (Paper Jam Tray 1)",
          startNode: "Q1",
          nodes: {
            "Q1": {
              text: "พบเศษกระดาษชิ้นส่วนเล็กๆ หรือฝุ่นสะสมเกาะอยู่ที่บริเวณลูกยางป้อนกระดาษถาด 1 หรือไม่?",
              yes: "SOL_CLEAN",
              no: "Q2"
            },
            "Q2": {
              text: "ตรวจสอบลูกยางดึงกระดาษ (Feed Roller) มีรอยฉีกขาดหรือยางแข็งเสื่อมสภาพหมดความฝืดหรือไม่?",
              yes: "SOL_REPLACE",
              no: "SOL_CHECK_CLUTCH"
            },
            "SOL_CLEAN": {
              isResult: true,
              text: "ดึงเศษกระดาษออก และใช้ผ้าแห้งสะอาดหรือชุบน้ำหมาดๆ เช็ดทำความสะอาดคราบฝุ่นบนหน้ายางดึงกระดาษถาด 1"
            },
            "SOL_REPLACE": {
              isResult: true,
              text: "แนะนำให้เบิกและเปลี่ยนชุดลูกยางดึงกระดาษ (Paper Feed Roller) สามลูกชุดของแท้ชิ้นใหม่เพื่อทดแทนชิ้นที่หมดความหนืด"
            },
            "SOL_CHECK_CLUTCH": {
              isResult: true,
              text: "อาการอาจเกิดจากชุดคลัตช์ฟีดกระดาษส่งกำลังลื่น แนะนำให้ส่งช่างหน้างานแกะฝาข้างซ้ายทำความสะอาดคลัตช์ฟีดส่งกำลัง"
            }
          }
        },
        {
          id: "canon-line",
          title: "พิมพ์เอกสารแล้วพบเส้นดำแนวตั้งลากยาวตลอดหน้ากระดาษ",
          startNode: "Q1",
          nodes: {
            "Q1": {
              text: "พบเส้นดำเฉพาะตอนถ่ายเอกสารผ่านชุดป้อนกระดาษต้นฉบับอัตโนมัติ (ADF) ใช่หรือไม่?",
              yes: "Q2",
              no: "Q3"
            },
            "Q2": {
              text: "ตรวจสอบกระจกสแกนเนอร์บานเล็กฝั่งซ้าย (Slit Glass) พบรอยคราบหมึกหรือคราบลิควิดติดอยู่หรือไม่?",
              yes: "SOL_GLASS_CLEAN",
              no: "SOL_ADF_ROLLER"
            },
            "Q3": {
              text: "พบเส้นดำเมื่อสั่งพิมพ์งานผ่านเน็ตเวิร์กโดยตรงจากคอมพิวเตอร์ด้วยใช่หรือไม่?",
              yes: "SOL_DRUM_CLEAN",
              no: "SOL_GLASS_MAIN"
            },
            "SOL_GLASS_CLEAN": {
              isResult: true,
              text: "ใช้ผ้าและแอลกอฮอล์เช็ดทำความสะอาดกระจกสแกนบานเล็กฝั่งซ้าย (Slit Glass) จนหมดคราบน้ำยาลบคำผิด"
            },
            "SOL_ADF_ROLLER": {
              isResult: true,
              text: "ทำความสะอาดลูกกลิ้งยางหมุนป้อนกระดาษต้นฉบับของ ADF มักมีคราบเปื้อนขวางแนวแสงสแกนเนอร์"
            },
            "SOL_DRUM_CLEAN": {
              isResult: true,
              text: "หน้าฟิล์มสร้างภาพ Drum Unit Cyan/Black มีรอยขูดขีด แนะนำให้ช่างตรวจสอบหรือเปลี่ยนตลับสร้างภาพ (Drum Unit) ชิ้นใหม่"
            },
            "SOL_GLASS_MAIN": {
              isResult: true,
              text: "ทำความสะอาดกระจกแท่นวางหน้าหลัก (Platen Glass) เนื่องจากมีรอยคราบฝุ่นหรือรอยขีดข่วนสะท้อนแสงหลัก"
            }
          }
        }
      ]
    },
    {
      model: "Ricoh IM C3000",
      standardChecklist: [
        "ทำความสะอาดเลนส์อ่านแสงและกระจกกระจายแสงเลเซอร์",
        "ตรวจวัดแรงดันบอร์ดจ่ายไฟหัวประจุหลัก (Charge Roller Voltage Line)",
        "ตรวจสอบฟิล์มความร้อนชุดฟิวส์ซิ่ง (Fusing Film) และลูกกลิ้งกดรีด",
        "เช็กการทำงานของมอเตอร์ป้อนหมึก และชุดกวนผงหมึก (Developer Unit)",
        "ทำความสะอาดลูกกลิ้งรีจิส (Registration Roller) ป้องกันกระดาษเยื้องศูนย์"
      ],
      commonIssues: [
        { issue: "พิมพ์เอกสารสีแล้วพื้นหลังเลอะเป็นปื้นสีฟ้านวลๆ (Cyan Background Smear)", fix: "บอร์ดจ่ายไฟแรงประจุรั่ว หรือ Drum Unit Cyan ใกล้หมดอายุการใช้งาน ให้ลองสลับชุดดรัมทดสอบ" },
        { issue: "หน้าจอแสดงผลข้อความ 'หมึกหมด' ทั้งที่เพิ่งเปลี่ยนหลอดหมึกใหม่", fix: "ชิป RFID ท้ายหลอดหมึกไม่ตรงรุ่น หรือแกนหมุนมอเตอร์ป้อนหมึกหักขัดข้างใน ให้ใช้ไฟฉายส่องและเปลี่ยนแกนพลาสติกดึงหลอด" },
        { issue: "กระดาษติดในชุดพับสองหน้า (Duplex Jam Error)", fix: "แกะฝาครอบขวา ตรวจเช็กสปริงดึงกลับของตัวสลับทางกระดาษ (Gate Guide Lever) หากล้าหรือหลุดให้ดัดและใส่คืน" }
      ],
      troubleshootingFlows: [
        {
          id: "ricoh-smear",
          title: "พิมพ์เอกสารสีแล้วพื้นหลังเลอะเป็นปื้นสีฟ้านวลๆ (Cyan Background)",
          startNode: "Q1",
          nodes: {
            "Q1": {
              text: "ตรวจวัดแรงดันไฟฟ้าที่บอร์ดประจุหลัก พบว่ากระแสไฟฟ้าชาร์จรั่วหรือไม่ได้มาตรฐานหรือไม่?",
              yes: "SOL_POWER",
              no: "Q2"
            },
            "Q2": {
              text: "ตรวจสอบชุดลูกกลิ้งภาพ Drum Unit Cyan พบว่าหน้าฟิล์มมีรอยสึกหรือขูดขีดหรือไม่?",
              yes: "SOL_DRUM",
              no: "SOL_TONER_DEV"
            },
            "SOL_POWER": {
              isResult: true,
              text: "ปรับแต่งระดับแรงดันกระแสบอร์ดจ่ายไฟหัวประจุหลัก (Charge Roller Voltage Line) หรือดำเนินการซ่อมแซมแผงไฟกำลังประจุ"
            },
            "SOL_DRUM": {
              isResult: true,
              text: "ชุดลูกกลิ้งสร้างภาพดรัมยูนิตสีฟ้า (Drum Unit Cyan) เสื่อมสภาพและชำรุด ให้ถอดเปลี่ยนชุดดรัมยูนิตสีฟ้าชิ้นใหม่"
            },
            "SOL_TONER_DEV": {
              isResult: true,
              text: "ผงหมึกส่วนกวนเสียประสิทธิภาพ แนะนำให้ทำความสะอาดกระปุกชุดกวนผงหมึก (Developer Unit Cyan) และเติมผงกวนใหม่"
            }
          }
        },
        {
          id: "ricoh-toner",
          title: "หน้าจอแสดงผล 'หมึกหมด' ทั้งที่เพิ่งเปลี่ยนหลอดหมึกสีใหม่",
          startNode: "Q1",
          nodes: {
            "Q1": {
              text: "ตรวจสอบแกนเฟืองพลาสติกหลังช่องเสียบหลอดหมึก พบว่ามีรอยหักหรือเฟืองขัดล็อกข้างในใช่หรือไม่?",
              yes: "SOL_GEAR",
              no: "Q2"
            },
            "Q2": {
              text: "หน้าสัมผัสของชิป RFID ท้ายหลอดหมึก มีเศษผงหมึกสกปรกเกาะหรือรหัสไม่ตรงรุ่นใช่หรือไม่?",
              yes: "SOL_RFID",
              no: "SOL_MOTOR"
            },
            "SOL_GEAR": {
              isResult: true,
              text: "แกนหมุนมอเตอร์ป้อนหมึกชำรุดขัดล็อก ให้ทำการถอดตู้และสลับชิ้นส่วนแกนพลาสติกดึงหลอดชุดใหม่ทดแทน"
            },
            "SOL_RFID": {
              isResult: true,
              text: "เช็ดทำความสะอาดหน้าสัมผัสสีทองท้ายหลอด หรือส่งหลอดคืนศูนย์บริการเพื่อเคลมหลอดหมึกที่มีชิป RFID ชุดใหม่"
            },
            "SOL_MOTOR": {
              isResult: true,
              text: "มอเตอร์กวนหมึกท้ายเครื่องชำรุดหรือสายไฟบอร์ดหลักขาด แนะนำให้ตรวจวัดกระแสไฟมอเตอร์และเปลี่ยนมอเตอร์ใหม่"
            }
          }
        }
      ]
    },
    {
      model: "HP LaserJet Managed E82560",
      standardChecklist: [
        "ตรวจสอบอายุการใช้งานของชุดความร้อน (Fuser Kit) และชุดโอนย้ายภาพ (Transfer Belt)",
        "ทำความสะอาดชุดลูกยางหนีบกระดาษหน้าแรก (Pickup/Feed/Separation Rollers)",
        "อัปเกรดเฟิร์มแวร์ระบบเป็นเวอร์ชันล่าสุดเพื่อลดบั๊กตารางส่งงานค้าง",
        "ตรวจสอบฝุ่นบริเวณพัดลมระบายความร้อนบอร์ดหลักและบอร์ดสแกนเนอร์",
        "ทดสอบพิมพ์ตัวอักษรขนาดเล็กเพื่อตรวจวัดการฟุ้งของผงหมึก"
      ],
      commonIssues: [
        { issue: "ส่งงานปริ้นผ่านเน็ตเวิร์กแล้วขึ้น Offline บ่อย หรือพิมพ์ช้ามาก", fix: "เข้าหน้าเว็บแอดมิน ปิดฟังก์ชัน IPv6 ในการตั้งค่าเน็ตเวิร์ก และปรับความเร็วพอร์ต LAN เป็น 100Mbps Full Duplex คงที่" },
        { issue: "กระดาษติดค้างใต้ตลับหมึก (Jam Under Cartridge Area)", fix: "คลัตช์ฟีดกระดาษส่งกำลัง (Registration Clutch) ลื่นหรือชำรุด ทำให้ส่งกระดาษไม่ทันเซนเซอร์ ให้ถอดคลัตช์ออกมาทำความสะอาดคราบน้ำมัน หรือเปลี่ยนชิ้นใหม่" }
      ],
      troubleshootingFlows: [
        {
          id: "hp-offline",
          title: "ส่งงานพิมพ์ผ่านระบบเน็ตเวิร์กแลนแล้วขึ้น Offline บ่อย หรือพิมพ์ช้ามาก",
          startNode: "Q1",
          nodes: {
            "Q1": {
              text: "ทดสอบการ Ping หาไอพีตัวเครื่อง พบว่ามีอาการแพ็คเก็ตหลุดร่วง (Timeout) หรือไม่?",
              yes: "Q2",
              no: "SOL_IPv6"
            },
            "Q2": {
              text: "ตรวจสอบสายแลนแลนบอร์ดหลักหรือพอร์ต LAN Switch ของอาคาร พบว่าหน้าสัมผัสหลวมหรือชำรุดหรือไม่?",
              yes: "SOL_CABLE",
              no: "SOL_PORT_SPEED"
            },
            "SOL_IPv6": {
              isResult: true,
              text: "เข้าไปที่ Web Admin ของตัวเครื่อง ปิดการใช้งานฟังก์ชัน IPv6 และปรับใช้เฉพาะ IPv4 เพื่อลดอาการไอพีชนกัน"
            },
            "SOL_CABLE": {
              isResult: true,
              text: "เบิกสายแลนสายใหม่และย้ำหัวต่อเข้าบอร์ดหลักเครื่องถ่ายเอกสารและช่องสวิตช์แลนใหม่"
            },
            "SOL_PORT_SPEED": {
              isResult: true,
              text: "เข้าไปที่หน้าตั้งค่าเครือข่าย ปรับความเร็ว LAN Port Speed จาก Auto-negotiation เป็น 100Mbps Full Duplex คงที่"
            }
          }
        },
        {
          id: "hp-jam",
          title: "กระดาษติดขัดแน่นและหยุดค้างอยู่บริเวณด้านใต้ชุดตลับหมึกสีดำ",
          startNode: "Q1",
          nodes: {
            "Q1": {
              text: "ตรวจสอบที่ชุดคลัตช์ฟีดส่งกำลัง (Registration Clutch) พบว่าลื่น มีน้ำมันเกาะ หรือชำรุดส่งกำลังไม่ทันหรือไม่?",
              yes: "SOL_CLUTCH",
              no: "Q2"
            },
            "Q2": {
              text: "พบว่ามีเศษฝุ่นกระดาษสะสมจำนวนมากอุดตันขวางตัวกระเดื่องเซนเซอร์ใต้ดรัมหรือไม่?",
              yes: "SOL_SENSOR",
              no: "SOL_ROLLERS"
            },
            "SOL_CLUTCH": {
              isResult: true,
              text: "ถอดชุดคลัตช์ส่งกำลังกระดาษออกมาล้างคราบไขมันสกปรกด้วยน้ำยาขจัดคราบยางมะตอย หรือเบิกเปลี่ยนชุดคลัตช์ชิ้นใหม่"
            },
            "SOL_SENSOR": {
              isResult: true,
              text: "ทำความสะอาดเป่าฝุ่นขจัดเศษขวางและหน้าสัมผัสของเซนเซอร์ตรวจจับการเคลื่อนผ่านกระดาษ (Paper Passage Sensor)"
            },
            "SOL_ROLLERS": {
              isResult: true,
              text: "หน้าสัมผัสชุดความร้อน Fuser Kit ฝืดหรือสายพานโอนย้ายภาพหมดอายุทำให้กระดาษติดขวาง ให้ถอดชุด Fuser ออกมาเช็กและสลับอะไหล่เปลี่ยนใหม่"
            }
          }
        }
      ]
    }
  ],

  // ตั๋วแจ้งซ่อม / ประวัติงานในระบบ
  tickets: [
    {
      id: "TK-001",
      shopId: "S04",
      shopName: "บริษัท โลจิสติกส์ ไทยแลนด์ สาขาเชียงใหม่",
      copierModel: "HP LaserJet Managed E82560",
      issue: "เลยกำหนดวันเช็กระยะประจำปี 6 วัน และกระดาษติดถาด 2 บ่อย",
      assignedTechId: "T03",
      assignedTechName: "ช่างนพดล เก่งกาจ",
      status: "Pending",
      date: "2026-06-16",
      withdrawnParts: [],
      issueFound: "",
      resolution: "",
      actualPartsUsed: []
    },
    {
      id: "TK-002",
      shopId: "S03",
      shopName: "ร้านส้มตำเจ๊ไก่ สาขาคูเมืองเชียงใหม่",
      copierModel: "Canon iR-A 4535",
      issue: "กระดาษป้อนเข้าเครื่องแล้วยับย่นทางขวา มีเสียงดังแก๊กๆ ขณะพิมพ์",
      assignedTechId: "T02",
      assignedTechName: "ช่างวิชัย รักดี",
      status: "In Progress",
      date: "2026-06-17",
      withdrawnParts: [
        { partId: "P01", qty: 2 }
      ],
      issueFound: "",
      resolution: "",
      actualPartsUsed: []
    },
    {
      id: "TK-003",
      shopId: "S01",
      shopName: "ร้านกาแฟคอฟฟี่มีน (Coffee Mean)",
      copierModel: "Canon iR-A 4535",
      issue: "มีเส้นดำแนวตั้งตอนสแกนเอกสารผ่านหน้าฟีดด้านบน (ADF)",
      assignedTechId: null,
      assignedTechName: null,
      status: "Pending",
      date: "2026-06-17",
      withdrawnParts: [],
      issueFound: "",
      resolution: "",
      actualPartsUsed: []
    },
    {
      id: "TK-004",
      shopId: "S02",
      shopName: "สำนักงานกฎหมาย วีระการบัญชี",
      copierModel: "Ricoh IM C3000",
      issue: "สีพิมพ์เพี้ยนสีเหลืองไม่ออก และมีผงสีเลอะติดหลังกระดาษ",
      assignedTechId: "T01",
      assignedTechName: "ช่างสมชาย ใจดี",
      status: "Completed",
      date: "2026-06-10",
      withdrawnParts: [
        { partId: "P03", qty: 1 },
        { partId: "P07", qty: 1 }
      ],
      issueFound: "ฟิล์มเลเซอร์หน้าชุดดรัมสีเหลืองมีรอยขูดขีด และผงหมึกสีเหลืองใกล้หมดคลัง ทำให้จ่ายสีไม่ออก",
      resolution: "เปลี่ยนชุดดรัมสีเหลืองชิ้นใหม่ เป่าทำความสะอาดตู้จ่ายไฟ และเติมหลอดหมึกสีเหลืองสำรอง",
      actualPartsUsed: [
        { partId: "P03", qty: 1 },
        { partId: "P07", qty: 1 }
      ]
    },
    {
      id: "TK-005",
      shopId: "S05",
      shopName: "โรงเรียนสอนภาษา ก้าวหน้าอินเตอร์",
      copierModel: "Ricoh IM C3000",
      issue: "กระดาษติดในชุดพับสองหน้า และหน้าจอทัชสกรีนไม่ตอบสนองบางจุด",
      assignedTechId: "T05",
      assignedTechName: "ช่างประวิทย์ สินชัย",
      status: "Completed",
      date: "2026-06-14",
      withdrawnParts: [
        { partId: "P14", qty: 1 }
      ],
      issueFound: "สปริงดึงกลับของตัวสลับทางกระดาษ (Gate Guide Lever) ล้าและหลุดขัดขวางทางเดินกระดาษ",
      resolution: "ดัดสปริงและยึดคืนเข้าตำแหน่งเดิม ทำความสะอาดล้อรีจิสและเซนเซอร์ทางผ่านกระดาษโดยไม่ได้เปลี่ยนชิ้นส่วนใหม่",
      actualPartsUsed: []
    },
    {
      id: "TK-006",
      shopId: "S01",
      shopName: "ร้านกาแฟคอฟฟี่มีน (Coffee Mean)",
      copierModel: "Canon iR-A 4535",
      issue: "ผงหมึกใกล้หมดต้องการหลอดเติมหมึกสีดำสำรอง",
      assignedTechId: "T01",
      assignedTechName: "ช่างสมชาย ใจดี",
      status: "Pending",
      date: "2026-06-19",
      withdrawnParts: [],
      issueFound: "",
      resolution: "",
      actualPartsUsed: []
    },
    {
      id: "TK-007",
      shopId: "S05",
      shopName: "โรงเรียนสอนภาษา ก้าวหน้าอินเตอร์",
      copierModel: "Ricoh IM C3000",
      issue: "เช็กระยะประจำ 3 เดือน และทำความสะอาดชุดกวนหมึก",
      assignedTechId: "T02",
      assignedTechName: "ช่างวิชัย รักดี",
      status: "In Progress",
      date: "2026-06-18",
      withdrawnParts: [],
      issueFound: "",
      resolution: "",
      actualPartsUsed: []
    }
  ]
};



