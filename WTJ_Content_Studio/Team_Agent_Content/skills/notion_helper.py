#!/usr/bin/env python3
import os
import json
import urllib.request
import urllib.parse
import urllib.error
import ssl

def load_env():
    """Load env vars from .env file in the workspace root."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root = current_dir
    while root != os.path.dirname(root):
        if os.path.exists(os.path.join(root, '.env')):
            break
        root = os.path.dirname(root)
    env_path = os.path.join(root, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

class NotionHelper:
    def __init__(self, token=None, database_id=None):
        # Load environment variables if not provided
        load_env()
        self.token = token or os.environ.get("NOTION_TOKEN")
        self.database_id = database_id or os.environ.get("NOTION_DATABASE_ID")
        
        # Clean potential quotes
        if self.token:
            self.token = self.token.strip('"').strip("'")
        if self.database_id:
            self.database_id = self.database_id.strip('"').strip("'")

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        # SSL Context for compatibility (bypassing verification to avoid local certificate issues)
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        self._title_property_name = None

    def _make_request(self, url, method="GET", data=None):
        if not self.token:
            print("❌ Error: NOTION_TOKEN is not set.")
            return None
            
        req_data = None
        if data is not None:
            req_data = json.dumps(data).encode("utf-8")
            
        req = urllib.request.Request(url, data=req_data, headers=self.headers, method=method)
        
        try:
            with urllib.request.urlopen(req, context=self.ssl_context) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            print(f"❌ Notion API HTTP Error {e.code}: {e.reason}")
            print(f"Details: {error_body}")
            return None
        except Exception as e:
            print(f"❌ Notion API connection error: {e}")
            return None

    def query_database(self, filter_params=None):
        """Queries the Notion database. Supports optional filters."""
        url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        data = {}
        if filter_params:
            data["filter"] = filter_params
        return self._make_request(url, method="POST", data=data)

    def get_title_property_name(self):
        """Dynamically retrieves the database's title property name (e.g. 'Name' or 'Transcript')."""
        if self._title_property_name:
            return self._title_property_name
            
        # Default fallback
        self._title_property_name = "Name"
        
        # Query database schema
        url = f"https://api.notion.com/v1/databases/{self.database_id}"
        schema = self._make_request(url, method="GET")
        if schema and "properties" in schema:
            for k, v in schema["properties"].items():
                if v.get("type") == "title":
                    self._title_property_name = k
                    break
        return self._title_property_name

    def fetch_pages_by_status(self, status_name):
        """Fetches all pages with a specific Status select option."""
        filter_params = {
            "property": "Status",
            "select": {
                "equals": status_name
            }
        }
        res = self.query_database(filter_params)
        pages = []
        if res and "results" in res:
            for page in res["results"]:
                page_id = page["id"]
                properties = page["properties"]
                
                # Extract Title (dynamically detected)
                title = "Untitled"
                title_prop_name = self.get_title_property_name()
                name_prop = properties.get(title_prop_name, {})
                if name_prop and name_prop.get("type") == "title" and name_prop.get("title"):
                    title = "".join([t.get("text", {}).get("content", "") for t in name_prop["title"]])
                
                # Extract Platforms
                platforms = []
                platform_prop = properties.get("Platform", {})
                if platform_prop.get("type") == "multi_select" and platform_prop.get("multi_select"):
                    platforms = [item["name"] for item in platform_prop["multi_select"]]
                    
                # Extract Publish Date
                publish_date = None
                date_prop = properties.get("Publish Date", {})
                if date_prop.get("type") == "date" and date_prop.get("date"):
                    publish_date = date_prop["date"].get("start")
                    
                # Extract Approved Copy
                approved_copy = ""
                copy_prop = properties.get("Approved Copy", {})
                if copy_prop.get("type") == "rich_text" and copy_prop.get("rich_text"):
                    approved_copy = "".join([t.get("text", {}).get("content", "") for t in copy_prop["rich_text"]])
                
                pages.append({
                    "id": page_id,
                    "title": title,
                    "platforms": platforms,
                    "publish_date": publish_date,
                    "approved_copy": approved_copy,
                    "created_time": page.get("created_time"),
                    "raw_properties": properties
                })
        return pages

    def create_page(self, title, status_name="1_Ideation", publish_date=None, platform_tags=None):
        """Creates a new page in the database."""
        url = "https://api.notion.com/v1/pages"
        title_prop_name = self.get_title_property_name()
        
        properties = {
            title_prop_name: {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            },
            "Status": {
                "select": {
                    "name": status_name
                }
            }
        }
        if publish_date:
            properties["Publish Date"] = {
                "date": {
                    "start": publish_date
                }
            }
        if platform_tags:
            properties["Platform"] = {
                "multi_select": [{"name": p} for p in platform_tags]
            }
            
        data = {
            "parent": {"database_id": self.database_id},
            "properties": properties
        }
        return self._make_request(url, method="POST", data=data)

    def update_page_status(self, page_id, new_status):
        """Updates the Status property of a page."""
        url = f"https://api.notion.com/v1/pages/{page_id}"
        data = {
            "properties": {
                "Status": {
                    "select": {
                        "name": new_status
                    }
                }
            }
        }
        return self._make_request(url, method="PATCH", data=data)

    def move_page_to_database(self, page_id, target_database_id):
        """Moves a page to a target database by updating its parent."""
        url = f"https://api.notion.com/v1/pages/{page_id}"
        data = {
            "parent": {
                "type": "database_id",
                "database_id": target_database_id
            }
        }
        return self._make_request(url, method="PATCH", data=data)

    def update_page_property_text(self, page_id, property_name, text_value):
        """Updates a text (rich_text) property of a page (e.g. Approved Copy)."""
        url = f"https://api.notion.com/v1/pages/{page_id}"
        data = {
            "properties": {
                property_name: {
                    "rich_text": [
                        {
                            "text": {
                                "content": text_value
                            }
                        }
                    ]
                }
            }
        }
        return self._make_request(url, method="PATCH", data=data)

    def get_page_content_text(self, page_id):
        """Retrieves page text content (combining paragraph block texts)."""
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        res = self._make_request(url, method="GET")
        text_lines = []
        if res and "results" in res:
            for block in res["results"]:
                block_type = block.get("type")
                if block_type == "paragraph":
                    rich_text = block.get("paragraph", {}).get("rich_text", [])
                    line = "".join([t.get("text", {}).get("content", "") for t in rich_text])
                    text_lines.append(line)
                elif block_type == "heading_1" or block_type == "heading_2" or block_type == "heading_3":
                    rich_text = block.get(block_type, {}).get("rich_text", [])
                    line = "".join([t.get("text", {}).get("content", "") for t in rich_text])
                    text_lines.append(f"\n{line}\n")
        return "\n".join(text_lines)

    def write_page_content_text(self, page_id, text_content):
        """Appends text content to a page as paragraph blocks."""
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        
        # Split text into lines/paragraphs
        paragraphs = text_content.split("\n")
        children_blocks = []
        
        for p in paragraphs:
            # Skip empty lines to prevent cluttering block updates, or represent as empty paragraphs
            children_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": p
                            }
                        }
                    ]
                }
            })
            
        # Notion limit for appending blocks is 100 per request, chunk if necessary
        chunk_size = 50
        for i in range(0, len(children_blocks), chunk_size):
            chunk = children_blocks[i:i+chunk_size]
            data = {"children": chunk}
            self._make_request(url, method="PATCH", data=data)
        return True

    def clear_page_content(self, page_id):
        """Deletes all blocks on a page to clean it up before rewriting."""
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        res = self._make_request(url, method="GET")
        if res and "results" in res:
            for block in res["results"]:
                block_id = block["id"]
                del_url = f"https://api.notion.com/v1/blocks/{block_id}"
                self._make_request(del_url, method="DELETE")
        return True

if __name__ == "__main__":
    # Small test when run directly
    print("Testing NotionHelper connection...")
    helper = NotionHelper()
    if helper.token and helper.database_id:
        print("API Credentials found. Fetching database...")
        pages = helper.fetch_pages_by_status("6_Published")
        print(f"Successfully fetched {len(pages)} pages with status '6_Published'")
        for p in pages:
            print(f"- {p['title']} (Platforms: {p['platforms']}, Date: {p['publish_date']})")
    else:
        print("❌ Error: Missing NOTION_TOKEN or NOTION_DATABASE_ID in env.")
