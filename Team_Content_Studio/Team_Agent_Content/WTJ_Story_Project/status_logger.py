import os
import json
import datetime

# ค้นหาตำแหน่งไฟล์ workflow_status.js ในโฟลเดอร์ของน้องเอ็ม
current_dir = os.path.dirname(os.path.abspath(__file__))
# ไปยัง root แล้วหาโฟลเดอร์ย่อย Personal_Assistance_Team ของน้องเอ็ม
status_file_path = os.path.abspath(os.path.join(
    current_dir, "..", "..", "..", "Personal_Assistance_HQ", "Personal_Assistance_Team", "M", "html", "workflow_status.js"
))

def update_pipeline_status(active_node, status_text, log_message=None, clear_logs=False):
    """
    อัปเดตสถานะของท่อส่งงาน (Pipeline) ลงในไฟล์ workflow_status.js เพื่อแสดงผลบนแดชบอร์ด
    """
    status = {
        "activeNode": "idle",
        "statusText": "IDLE",
        "lastUpdated": "",
        "logs": [],
        "artifacts": {}
    }
    
    # อ่านไฟล์เดิมถ้ามีอยู่แล้วเพื่อเก็บประวัติ Logs
    if os.path.exists(status_file_path):
        try:
            with open(status_file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                prefix = "window.workflowStatus = "
                if content.startswith(prefix) and content.endswith(";"):
                    json_str = content[len(prefix):-1]
                    status = json.loads(json_str)
        except Exception:
            pass # ถ้าไฟล์มีปัญหา ให้รีเซ็ตค่าเริ่มต้นใหม่
            
    if clear_logs:
        status["logs"] = []
        status["artifacts"] = {}
        
    status["activeNode"] = active_node
    status["statusText"] = status_text
    status["lastUpdated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if log_message:
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        status["logs"].append({
            "time": time_str,
            "agent": active_node,
            "message": log_message
        })
        # เก็บ Log สูงสุด 8 รายการล่าสุดเพื่อไม่ให้หน้าจอรกรุงรัง
        status["logs"] = status["logs"][-8:]
        
    # เขียนบันทึกสถานะกลับเข้าไฟล์ JS
    try:
        os.makedirs(os.path.dirname(status_file_path), exist_ok=True)
        with open(status_file_path, "w", encoding="utf-8") as f:
            f.write(f"window.workflowStatus = {json.dumps(status, ensure_ascii=False)};")
    except Exception as e:
        print(f"Error updating workflow status file: {e}")

def register_artifact(name, rel_path):
    """
    ลงทะเบียนไฟล์ผลงานที่เขียนเสร็จแล้ว เพื่อให้กดคลิกเปิดจากแดชบอร์ดได้
    """
    if os.path.exists(status_file_path):
        try:
            with open(status_file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                prefix = "window.workflowStatus = "
                if content.startswith(prefix) and content.endswith(";"):
                    json_str = content[len(prefix):-1]
                    status = json.loads(json_str)
                    
                    status["artifacts"][name] = rel_path
                    
                    with open(status_file_path, "w", encoding="utf-8") as f:
                        f.write(f"window.workflowStatus = {json.dumps(status, ensure_ascii=False)};")
        except Exception:
            pass
