#!/usr/bin/env python3
import os
import sys
import json
import urllib.parse
import http.server
import socketserver
from datetime import datetime

# Find project root dynamically
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
if current_dir not in sys.path:
    sys.path.append(current_dir)

from notion_helper import NotionHelper
import config

HTML_DIR = config.LOCAL_DASHBOARD_DIR

# Knowledge Base Paths
KB_DIR = os.path.join(PROJECT_ROOT, "knowledge_base")
QUEUE_FILE = os.path.join(KB_DIR, "ingest_queue", "urls_to_ingest.txt")
MY_STYLE_DIR = os.path.join(KB_DIR, "my_style")
AI_REF_DIR = os.path.join(KB_DIR, "ai_references")
WTJ_PROJ_DIR = os.path.join(KB_DIR, "wtj_project")
SYSTEM_MANUALS_DIR = os.path.join(KB_DIR, "system_manuals")
RUN_LOG_FILE = os.path.join(PROJECT_ROOT, "Agent_Lab", "logs", "ingest_run.log")
INGEST_SCRIPT = os.path.join(KB_DIR, "ingest_sources.py")

class DashboardHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve static files from the dashboard HTML folder
        super().__init__(*args, directory=HTML_DIR, **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        if self.path == '/api/notion_data':
            self.handle_api_notion_data()
        elif self.path == '/api/knowledge_status':
            self.handle_api_knowledge_status()
        elif self.path.startswith('/api/view_file'):
            self.handle_api_view_file()
        elif self.path == '/api/ingest_logs':
            self.handle_api_ingest_logs()
        elif self.path == '/api/pipeline_logs':
            self.handle_api_pipeline_logs()
        else:
            super().do_GET()

    def handle_api_view_file(self):
        try:
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            folder = query_params.get("folder", [""])[0]
            filename = query_params.get("filename", [""])[0]
            
            if ".." in folder or ".." in filename or folder.startswith("/") or filename.startswith("/"):
                self.send_error(400, "Bad Request")
                return
                
            target_dir = MY_STYLE_DIR if folder == "my_style" else AI_REF_DIR
            if folder == "wtj_project":
                target_dir = WTJ_PROJ_DIR
            elif folder not in ["my_style", "ai_references"]:
                target_dir = os.path.join(KB_DIR, folder)
                
            filepath = os.path.join(target_dir, filename)
            
            if os.path.exists(filepath) and os.path.isfile(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                response_bytes = json.dumps({"content": content}, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', len(response_bytes))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response_bytes)
            else:
                self.send_error(404, "File Not Found")
        except Exception as e:
            self.send_error(500, str(e))

    def do_POST(self):
        if self.path == '/api/ingest':
            self.handle_api_ingest()
        elif self.path == '/api/run_ingest':
            self.handle_api_run_ingest()
        elif self.path == '/api/run_pipeline':
            self.handle_api_run_pipeline()
        elif self.path == '/api/create_note':
            self.handle_api_create_note()
        elif self.path == '/api/ingest_now':
            self.handle_api_ingest_now()
        elif self.path == '/api/save_bookmark':
            self.handle_api_save_bookmark()
        else:
            self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def read_post_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return None
        body = self.rfile.read(content_length)
        return body.decode('utf-8')

    def handle_api_knowledge_status(self):
        try:
            # 1. Scan files in my_style
            my_style_files = []
            if os.path.exists(MY_STYLE_DIR):
                for f in os.listdir(MY_STYLE_DIR):
                    p = os.path.join(MY_STYLE_DIR, f)
                    if os.path.isfile(p) and not f.startswith('.'):
                        stat = os.stat(p)
                        my_style_files.append({
                            "name": f,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        })
            
            # 2. Scan files in ai_references
            ai_ref_files = []
            if os.path.exists(AI_REF_DIR):
                for f in os.listdir(AI_REF_DIR):
                    p = os.path.join(AI_REF_DIR, f)
                    if os.path.isfile(p) and not f.startswith('.'):
                        stat = os.stat(p)
                        ai_ref_files.append({
                            "name": f,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        })
            
            # 3. Scan files in wtj_project
            wtj_proj_files = []
            if os.path.exists(WTJ_PROJ_DIR):
                for f in os.listdir(WTJ_PROJ_DIR):
                    p = os.path.join(WTJ_PROJ_DIR, f)
                    if os.path.isfile(p) and not f.startswith('.'):
                        stat = os.stat(p)
                        wtj_proj_files.append({
                            "name": f,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        })
            
            # 3.5. Scan files in system_manuals
            system_manuals_files = []
            if os.path.exists(SYSTEM_MANUALS_DIR):
                for f in os.listdir(SYSTEM_MANUALS_DIR):
                    p = os.path.join(SYSTEM_MANUALS_DIR, f)
                    if os.path.isfile(p) and not f.startswith('.'):
                        stat = os.stat(p)
                        system_manuals_files.append({
                            "name": f,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        })

            # 4. Read queue
            queue_urls = []
            if os.path.exists(QUEUE_FILE):
                with open(QUEUE_FILE, "r", encoding="utf-8") as file:
                    for line in file:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            queue_urls.append(line)
                            
            response_data = {
                "my_style_count": len(my_style_files),
                "my_style_files": my_style_files,
                "ai_references_count": len(ai_ref_files),
                "ai_references_files": ai_ref_files,
                "wtj_project_count": len(wtj_proj_files),
                "wtj_project_files": wtj_proj_files,
                "system_manuals_count": len(system_manuals_files),
                "system_manuals_files": system_manuals_files,
                "queue_count": len(queue_urls),
                "queue_urls": queue_urls
            }
            
            response_bytes = json.dumps(response_data, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', len(response_bytes))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response_bytes)
        except Exception as e:
            self.send_error(500, str(e))

    def handle_api_ingest(self):
        try:
            body = self.read_post_body()
            data = json.loads(body)
            urls = data.get("urls", "")
            folder = data.get("folder", "ai_references")
            
            # Write to queue file
            os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
            with open(QUEUE_FILE, "a", encoding="utf-8") as f:
                for url in urls.split('\n'):
                    url = url.strip()
                    if url:
                        if folder != "ai_references":
                            f.write(f"[{folder}] {url}\n")
                        else:
                            f.write(f"{url}\n")
                            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_api_create_note(self):
        try:
            body = self.read_post_body()
            data = json.loads(body)
            filename = data.get("filename", "").strip()
            folder = data.get("folder", "ai_references")
            content = data.get("content", "")
            
            if not filename:
                self.send_error(400, "Filename is required")
                return
                
            # Ensure it ends with .md or .txt
            if not (filename.endswith('.md') or filename.endswith('.txt')):
                filename += '.md'
                
            # Sanitize filename
            import re
            filename = re.sub(r'[^\w\s\-\.]', '', filename)
            filename = filename.replace(' ', '_')
            
            target_dir = AI_REF_DIR
            if folder == "my_style":
                target_dir = MY_STYLE_DIR
            elif folder == "wtj_project":
                target_dir = WTJ_PROJ_DIR
            elif folder != "ai_references":
                target_dir = os.path.join(KB_DIR, folder)
                
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
                
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "filename": filename}).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_api_ingest_now(self):
        try:
            body = self.read_post_body()
            data = json.loads(body)
            url = data.get("url", "").strip()
            folder = data.get("folder", "ai_references")
            delete_bookmark = data.get("delete_bookmark", "").strip()
            
            if not url:
                self.send_error(400, "URL is required")
                return
                
            # Import ingest_sources dynamically
            if KB_DIR not in sys.path:
                sys.path.append(KB_DIR)
            import ingest_sources
            
            # Map folder
            target_folder = AI_REF_DIR
            if folder == "my_style":
                target_folder = MY_STYLE_DIR
            elif folder == "wtj_project":
                target_folder = WTJ_PROJ_DIR
            elif folder != "ai_references":
                target_folder = os.path.join(KB_DIR, folder)
                
            os.makedirs(target_folder, exist_ok=True)
            
            # Run ingestion function synchronously based on URL type
            if "youtube.com" in url or "youtu.be" in url:
                success, result = ingest_sources.ingest_youtube(url, target_folder)
            else:
                success, result = ingest_sources.ingest_web(url, target_folder)
                
            if success:
                # Delete bookmark if exists
                if delete_bookmark:
                    if not (".." in delete_bookmark or delete_bookmark.startswith("/")):
                        bookmark_path = os.path.join(target_folder, delete_bookmark)
                        if os.path.exists(bookmark_path):
                            os.remove(bookmark_path)
                            
                response_bytes = json.dumps({"status": "success", "filename": result}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response_bytes)
            else:
                self.send_error(500, result)
        except Exception as e:
            self.send_error(500, str(e))

    def handle_api_save_bookmark(self):
        try:
            body = self.read_post_body()
            data = json.loads(body)
            url = data.get("url", "").strip()
            folder = data.get("folder", "ai_references")
            
            if not url:
                self.send_error(400, "URL is required")
                return
                
            title = self.fetch_url_title(url)
            
            # Import ingest_sources dynamically
            if KB_DIR not in sys.path:
                sys.path.append(KB_DIR)
            import ingest_sources
            
            filename = f"bookmark_{ingest_sources.sanitize_filename(title)}.md"
            
            # Map folder
            target_folder = AI_REF_DIR
            if folder == "my_style":
                target_folder = MY_STYLE_DIR
            elif folder == "wtj_project":
                target_folder = WTJ_PROJ_DIR
            elif folder != "ai_references":
                target_folder = os.path.join(KB_DIR, folder)
                
            os.makedirs(target_folder, exist_ok=True)
            filepath = os.path.join(target_folder, filename)
            
            content = f"""# {title}

- **Source URL:** {url}
- **Status:** ⏳ Unprocessed Bookmark

*หมายเหตุ: ไฟล์นี้เป็นเพียงลิงก์อ้างอิงดิบที่บันทึกไว้ในคลังความรู้ หากแกต้องการดึงข้อมูลสรุปเนื้อหาหรือทรานสคริปต์คลิปเต็ม กรุณากดปุ่มดึงข้อมูล [Ingest] ด้านบนจ้า*
"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
                
            response_bytes = json.dumps({"status": "success", "filename": filename, "title": title}).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response_bytes)
        except Exception as e:
            self.send_error(500, str(e))

    def fetch_url_title(self, url):
        try:
            import urllib.request
            import urllib.parse
            import ssl
            import re
            
            if "youtube.com" in url or "youtu.be" in url:
                if KB_DIR not in sys.path:
                    sys.path.append(KB_DIR)
                import ingest_sources
                meta = ingest_sources.fetch_yt_metadata(url)
                if meta and meta.get('title'):
                    return meta['title']
            
            context = ssl._create_unverified_context()
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            with urllib.request.urlopen(req, context=context, timeout=5) as response:
                html = response.read().decode('utf-8', errors='ignore')
            match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            if match:
                import html as html_parser
                return html_parser.unescape(match.group(1).strip())
        except Exception as e:
            print(f"⚠️ fetch_url_title error: {e}")
            
        try:
            parsed = urllib.parse.urlparse(url)
            return f"Link from {parsed.netloc}{parsed.path[:20]}"
        except:
            return "New URL Bookmark"

    def handle_api_run_ingest(self):
        try:
            import subprocess
            # Ensure log directory exists
            os.makedirs(os.path.dirname(RUN_LOG_FILE), exist_ok=True)
            
            # Start script in background and redirect output to log file
            log_file = open(RUN_LOG_FILE, "w", encoding="utf-8")
            
            # Use same Python virtualenv interpreter
            python_exec = os.path.join(PROJECT_ROOT, "venv", "bin", "python")
            if not os.path.exists(python_exec):
                python_exec = sys.executable
                
            subprocess.Popen(
                [python_exec, INGEST_SCRIPT],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=PROJECT_ROOT
            )
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "Ingestion started in background."}).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_api_ingest_logs(self):
        try:
            logs = ""
            if os.path.exists(RUN_LOG_FILE):
                with open(RUN_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                    # Return last 50 lines
                    logs = "".join(lines[-50:])
            else:
                logs = "No log file found. Click 'RUN PIPELINE' to start the process."
                
            response_bytes = json.dumps({"logs": logs}, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', len(response_bytes))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response_bytes)
        except Exception as e:
            self.send_error(500, str(e))

    def handle_api_run_pipeline(self):
        try:
            body = self.read_post_body()
            project = "story"
            if body:
                try:
                    data = json.loads(body)
                    project = data.get("project", "story")
                except:
                    pass

            import subprocess
            
            # Use same Python virtualenv interpreter
            python_exec = os.path.join(PROJECT_ROOT, "venv", "bin", "python")
            if not os.path.exists(python_exec):
                python_exec = sys.executable
                
            script_path = os.path.join(PROJECT_ROOT, "Team_Content_Studio", "Team_Agent_Content", "skills", "video_draft_generator.py")
            
            # Setup log path
            log_dir = os.path.join(PROJECT_ROOT, "Agent_Lab", "logs")
            os.makedirs(log_dir, exist_ok=True)
            run_log_file = os.path.join(log_dir, "video_draft_run.log")
            
            # Start script in background (-u = unbuffered so logs appear immediately)
            log_file = open(run_log_file, "w", encoding="utf-8")
            subprocess.Popen(
                [python_exec, "-u", script_path, "--project", project],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=PROJECT_ROOT
            )
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": f"Pipeline for {project} started."}).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_api_pipeline_logs(self):
        try:
            log_path = os.path.join(PROJECT_ROOT, "Agent_Lab", "logs", "video_draft_run.log")
            logs = ""
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                    logs = "".join(lines[-55:])
            else:
                logs = "ยังไม่มีประวัติการรันบอทสแกนล่าสุด กดเริ่มทำงานเพื่อรันบอทเลยแก"
                
            response_bytes = json.dumps({"logs": logs}, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', len(response_bytes))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response_bytes)
        except Exception as e:
            self.send_error(500, str(e))

    def handle_api_notion_data(self):
        print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] GET /api/notion_data - Fetching from Notion...")
        try:
            notion = NotionHelper()
            
            # Query all pages in the database
            res = notion.query_database()
            if not res or "results" not in res:
                self.send_error(500, "Failed to query Notion database")
                return

            pages = res["results"]
            calendar_data = {}
            
            for page in pages:
                properties = page.get("properties", {})
                
                # Extract title
                title = "Untitled"
                title_prop_name = notion.get_title_property_name()
                name_prop = properties.get(title_prop_name, {})
                if name_prop and name_prop.get("type") == "title" and name_prop.get("title"):
                    title = "".join([t.get("text", {}).get("content", "") for t in name_prop["title"]])
                    
                # Extract Status name
                status_name = "1_Ideation"
                status_prop = properties.get("Status", {})
                if status_prop.get("type") == "select" and status_prop.get("select"):
                    status_name = status_prop["select"]["name"]
                    
                # Extract Publish Date
                publish_date_str = None
                date_prop = properties.get("Publish Date", {})
                if date_prop.get("type") == "date" and date_prop.get("date"):
                    publish_date_str = date_prop["date"].get("start")
                    
                if not publish_date_str:
                    continue
                    
                # Parse publish date to dateKey (YYYY-MM-DD) and timeKey (HH:MM)
                date_key = ""
                time_key = "19:30" # Default slot time
                
                if "T" in publish_date_str:
                    date_part, time_part = publish_date_str.split("T")
                    date_key = date_part
                    time_key = time_part[:5]
                else:
                    date_key = publish_date_str
                    
                # Define slot key matching dashboard: "YYYY-MM-DD-HH:MM"
                slot_key = f"{date_key}-{time_key}"
                
                # Map Status to ready/missing
                is_ready = status_name in ["5_Approved", "6_Published"]
                
                calendar_data[slot_key] = {
                    "title": title,
                    "status": "ready" if is_ready else "missing",
                    "notion_status": status_name
                }
            
            # Write to static JS file for backup/fallback in both directories
            js_content = f"// Generated automatically by WTJ Sync Agent\nconst NOTION_CALENDAR_DATA = {json.dumps(calendar_data, indent=4, ensure_ascii=False)};\n"
            
            paths_to_save = [
                os.path.join(config.LOCAL_DASHBOARD_DIR, "notion_calendar_data.js"),
                os.path.join(config.GITHUB_DASHBOARD_DIR, "notion_calendar_data.js")
            ]
            for path in paths_to_save:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(js_content)
                
            # Send JSON response
            response_bytes = json.dumps(calendar_data, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', len(response_bytes))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response_bytes)
            print(f"✅ Served {len(calendar_data)} slots from Notion.")
            
        except Exception as e:
            print(f"❌ Error fetching from Notion: {e}")
            self.send_error(500, str(e))

def run_server(port=8000):
    handler = DashboardHTTPRequestHandler
    # Allow port reuse to avoid address already in use errors
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    
    with socketserver.ThreadingTCPServer(("", port), handler) as httpd:
        print("==================================================")
        print(f"🚀 VEDA DASHBOARD LIVE SYNC SERVER RUNNING...")
        print(f"📍 URL: http://localhost:{port}/wtj_calendar_dashboard.html")
        print(f"📂 Serving static files from: {HTML_DIR}")
        print("==================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Server stopped.")

if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
