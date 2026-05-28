import sys
import os
# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Team_Content_Studio.Team_Agent_Content.skills.notion_helper import NotionHelper
import json

helper = NotionHelper()
res = helper.query_database()

if not res or "results" not in res:
    print("❌ Cannot query Notion database.")
    exit(1)

pages = res["results"]
import sys
import os
# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Team_Content_Studio.Team_Agent_Content.skills.notion_helper import NotionHelper
import json

helper = NotionHelper()
res = helper.query_database()

if not res or "results" not in res:
    print("❌ Cannot query Notion database.")
    exit(1)

pages = res["results"]
print(f"📊 Found {len(pages)} pages in Notion:")

title_prop_name = helper.get_title_property_name()
print(f"Title property name is: {title_prop_name}")

for idx, page in enumerate(pages, 1):
    props = page["properties"]
    
    # Title
    title = "Untitled"
    name_prop = props.get(title_prop_name, {})
    if name_prop.get("type") == "title" and name_prop.get("title"):
        title = "".join([t.get("text", {}).get("content", "") for t in name_prop["title"]])
        
    # Status
    status = "None"
    status_prop = props.get("Status", {})
    if status_prop.get("type") == "select" and status_prop.get("select"):
        status = status_prop["select"]["name"]
        
    # Publish Date
    pub_date = "None"
    date_prop = props.get("Publish Date", {})
    if date_prop.get("type") == "date" and date_prop.get("date"):
        pub_date = date_prop["date"].get("start")
        
    # Platform
    platforms = []
    platform_prop = props.get("Platform", {})
    if platform_prop.get("type") == "multi_select" and platform_prop.get("multi_select"):
        platforms = [item["name"] for item in platform_prop["multi_select"]]
        
    print(f"\n[{idx}] Title: {title}")
    print(f"    Status: {status}")
    print(f"    Publish Date: {pub_date}")
    print(f"    Platform: {platforms}")
    print(f"    ID: {page['id']}")
