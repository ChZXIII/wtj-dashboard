import sys
import os

sys.path.append(os.path.join('/Users/chz/Desktop/ChZ_Agent_Corp/', 'WTJ_Content_Studio', 'Team_Agent_Content', 'skills'))
from notion_helper import NotionHelper

helper = NotionHelper()
page_id = "36b1b328-5b0e-8154-bb80-e1200e4c7f10"
url = f"https://api.notion.com/v1/pages/{page_id}"

data = {
    "properties": {
        "Publish Date": {
            "date": {
                "start": "2026-05-26T12:00:00.000+07:00"
            }
        },
        "Status": {
            "select": {
                "name": "5_Approved"
            }
        }
    }
}

res = helper._make_request(url, method="PATCH", data=data)
if res:
    print("✅ Notion card updated successfully: Publish Date set to 12:00 PM and Status set to 5_Approved!")
else:
    print("❌ Failed to update Notion card.")
