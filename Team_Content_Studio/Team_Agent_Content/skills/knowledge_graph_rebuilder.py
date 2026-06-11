import os
import json
import re
import sys

# Add current dir to path to allow importing skills siblings
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import config

# Find project root dynamically
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = current_dir
while PROJECT_ROOT != os.path.dirname(PROJECT_ROOT):
    if os.path.exists(os.path.join(PROJECT_ROOT, '.git')) or os.path.exists(os.path.join(PROJECT_ROOT, '.env')):
        break
    PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)

BASE_DIR = PROJECT_ROOT
IGNORE_DIRS = {'.git', 'venv', '__pycache__', '.gemini'}
IGNORE_FILES = {'.DS_Store', 'graph_data.js', 'token.json', 'token_sheets.json', 'client_secret.json'}

def get_file_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.py': return 'python'
    if ext == '.html': return 'html'
    if ext == '.md': return 'markdown'
    if ext == '.js': return 'javascript'
    if ext == '.json': return 'json'
    if ext == '.sh': return 'shell'
    return 'other'

def scan_project():
    nodes = []
    links = []
    path_to_id = {}

    # Add Root Node
    nodes.append({"id": "root", "label": "1st Agent", "type": "directory", "val": 20})
    path_to_id[BASE_DIR] = "root"

    for root, dirs, files in os.walk(BASE_DIR):
        # Filter directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for d in dirs:
            dir_path = os.path.join(root, d)
            dir_id = dir_path.replace(BASE_DIR, "").strip(os.sep)
            parent_path = os.path.dirname(dir_path)
            parent_id = path_to_id.get(parent_path, "root")
            
            nodes.append({"id": dir_id, "label": d, "type": "directory", "val": 15})
            links.append({"source": parent_id, "target": dir_id, "type": "contains"})
            path_to_id[dir_path] = dir_id

        for f in files:
            if f in IGNORE_FILES: continue
            
            file_path = os.path.join(root, f)
            file_id = file_path.replace(BASE_DIR, "").strip(os.sep)
            parent_id = path_to_id.get(root, "root")
            
            file_type = get_file_type(f)
            nodes.append({"id": file_id, "label": f, "type": file_type, "val": 10})
            links.append({"source": parent_id, "target": file_id, "type": "contains"})
            
            # Basic Relationship Detection (Imports/Links)
            if file_type == 'python':
                try:
                    with open(file_path, 'r', encoding='utf-8') as content:
                        text = content.read()
                        # Detect internal module imports
                        imports = re.findall(r'from ([\w_]+) import|import ([\w_]+)', text)
                        for imp in imports:
                            imp_name = imp[0] or imp[1]
                            target_f = imp_name + ".py"
                            # Search if this target file exists in our project
                            for node in nodes:
                                if node['label'] == target_f:
                                    links.append({"source": file_id, "target": node['id'], "type": "references"})
                except: pass
            
            if file_type == 'markdown':
                try:
                    with open(file_path, 'r', encoding='utf-8') as content:
                        text = content.read()
                        # Detect [link](file)
                        md_links = re.findall(r'\[.*?\]\((file:///.*?|.*?\.[\w]+)\)', text)
                        for l in md_links:
                            target_name = os.path.basename(l.split('#')[0])
                            for node in nodes:
                                if node['label'] == target_name:
                                    links.append({"source": file_id, "target": node['id'], "type": "references"})
                except: pass

    return {"nodes": nodes, "links": links}

if __name__ == "__main__":
    data = scan_project()
    output_path = os.path.join(config.LOCAL_DASHBOARD_DIR, 'graph_data.js')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"const graphData = {json.dumps(data, indent=2)};")
    print(f"Generated graph data for {len(data['nodes'])} nodes in {output_path}")
