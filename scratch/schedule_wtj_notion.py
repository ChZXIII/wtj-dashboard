import sys
import os

# Set up paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(os.path.join(project_root, 'Team_Content_Studio', 'Team_Agent_Content', 'skills'))

from notion_helper import NotionHelper

def main():
    helper = NotionHelper()
    
    # 1. Schedule Reels (Saturdays 19:30)
    reels_schedule = [
        ("[Reels_Under1Min Video Draft] 02 เก่ง wall painting 30 sec.mp4", "2026-05-30T19:30:00+07:00"),
        ("[Reels_Under1Min Video Draft] 03 vokeg 30 sec.mp4", "2026-06-06T19:30:00+07:00"),
        ("[Reels_Under1Min Video Draft] 04 กิฟ infu cycling global 30 sec.mp4", "2026-06-13T19:30:00+07:00")
    ]
    
    # 2. Schedule FB Videos (Wednesdays 18:00)
    videos_schedule = [
        ("[FB_Videos_3-5Min Video Draft] 01   กอฟ อินพลู   3-5 min.mp4", "2026-05-27T18:00:00+07:00"),
        ("[FB_Videos_3-5Min Video Draft] 02 เก่ง wall painting 3-5 min.mp4", "2026-06-03T18:00:00+07:00"),
        ("[FB_Videos_3-5Min Video Draft] 03 vokeg 3-5 min.mp4", "2026-06-10T18:00:00+07:00"),
        ("[FB_Videos_3-5Min Video Draft] 04 กิฟ infu cycling global 3-5 min.mp4", "2026-06-17T18:00:00+07:00")
    ]
    
    print("🚀 เริ่มอัปเดตวันเผยแพร่ (Publish Date) ใน Notion...")
    
    # Get all pages in status 4_Review to find their page IDs
    pages = helper.fetch_pages_by_status("4_Review")
    
    # Map title to page_id
    title_to_id = {p['title'].strip(): p['id'] for p in pages}
    
    updated_count = 0
    
    # Update Reels
    for title, pub_date in reels_schedule:
        title_strip = title.strip()
        if title_strip in title_to_id:
            page_id = title_to_id[title_strip]
            print(f"📅 Setting Publish Date for Reels: '{title}' ➔ {pub_date}")
            url = f"https://api.notion.com/v1/pages/{page_id}"
            data = {
                "properties": {
                    "Publish Date": {
                        "date": {
                            "start": pub_date
                        }
                    }
                }
            }
            res = helper._make_request(url, method="PATCH", data=data)
            if res:
                updated_count += 1
                
    # Update FB Videos
    for title, pub_date in videos_schedule:
        title_strip = title.strip()
        if title_strip in title_to_id:
            page_id = title_to_id[title_strip]
            print(f"📅 Setting Publish Date for Video: '{title}' ➔ {pub_date}")
            url = f"https://api.notion.com/v1/pages/{page_id}"
            data = {
                "properties": {
                    "Publish Date": {
                        "date": {
                            "start": pub_date
                        }
                    }
                }
            }
            res = helper._make_request(url, method="PATCH", data=data)
            if res:
                updated_count += 1
                
    print(f"\n🎉 เสร็จสิ้น! อัปเดตวันเผยแพร่ลง Notion เรียบร้อยทั้งหมด {updated_count} รายการ")

if __name__ == "__main__":
    main()
