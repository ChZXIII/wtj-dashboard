import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Team_Content_Studio.Team_Agent_Content.skills.notion_helper import NotionHelper

helper = NotionHelper()

# Archive the duplicate page
page_id = "36b1b328-5b0e-81e3-88bc-f5b56bfa50a4"
url = f"https://api.notion.com/v1/pages/{page_id}"
data = {
    "archived": True
}
res = helper._make_request(url, method="PATCH", data=data)

if res:
    print(f"✅ Successfully archived duplicate page {page_id}")
else:
    print(f"❌ Failed to archive duplicate page {page_id}")
