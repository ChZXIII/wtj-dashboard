#!/usr/bin/env python3
"""
📦 WTJ Notion Archiver
Queries Notion for published cards (Status = '6_Published') that are older than a specific number of days,
and moves them to the Archive Database (specified by NOTION_ARCHIVE_DATABASE_ID in env) to keep the main database clean.
"""

import os
import sys
import argparse
import re
from datetime import datetime, timezone, timedelta

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

def load_env():
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

def parse_date(date_str):
    if not date_str:
        return None
    tz_th = timezone(timedelta(hours=7))
    try:
        if "T" in date_str:
            # Handle ISO timestamp: e.g. 2026-05-25T17:25:00.000Z -> 2026-05-25T17:25:00.000+00:00
            # Truncate fractional seconds to max 6 digits to prevent fromisoformat parsing error
            parts = date_str.replace("Z", "+00:00").split(".")
            if len(parts) > 1 and len(parts[1]) > 6:
                # Keep up to 6 digits for microseconds and join with tz offset
                sub_parts = re.split(r'([+\-])', parts[1])
                microsec = sub_parts[0][:6]
                offset = "".join(sub_parts[1:])
                clean_str = f"{parts[0]}.{microsec}{offset}"
            else:
                clean_str = date_str.replace("Z", "+00:00")
            return datetime.fromisoformat(clean_str).astimezone(tz_th)
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return datetime(dt.year, dt.month, dt.day, tzinfo=tz_th)
    except Exception as e:
        print(f"⚠️ Warning: Could not parse date '{date_str}': {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="WTJ Notion Archive System")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Simulate archiving without modifying Notion database")
    parser.add_argument("--days", type=int, default=30, help="Archive cards older than N days (default: 30)")
    args = parser.parse_args()

    load_env()

    archive_db_id = os.environ.get("NOTION_ARCHIVE_DATABASE_ID")

    print("=" * 60)
    print("📦 Starting WTJ Notion Archiving Job")
    print(f"📅 Run Time: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"⏳ Age Threshold: {args.days} days")
    print(f"💡 Dry-run mode: {args.dry_run}")
    print("=" * 60)

    if not archive_db_id:
        print("❌ Error: NOTION_ARCHIVE_DATABASE_ID is not set in environment (.env).")
        print("💡 Please configure it by setting NOTION_ARCHIVE_DATABASE_ID=your_archive_db_id in .env")
        sys.exit(1)

    notion = NotionHelper()
    
    # Check that archive_db_id is not same as primary database
    if archive_db_id.replace("-", "") == notion.database_id.replace("-", ""):
        print("❌ Error: NOTION_ARCHIVE_DATABASE_ID is identical to the main database ID.")
        print("💡 You must use a separate database for archiving.")
        sys.exit(1)

    print("🔍 Fetching cards in status '6_Published'...")
    pages = notion.fetch_pages_by_status("6_Published")

    if not pages:
        print("📭 No cards found in status '6_Published'. Nothing to archive!")
        return

    print(f"📌 Found {len(pages)} published cards. Checking ages...")

    tz_th = timezone(timedelta(hours=7))
    now = datetime.now(tz_th)
    archived_count = 0
    failed_count = 0

    for page in pages:
        title = page.get("title", "Untitled")
        page_id = page.get("id")
        pub_date_str = page.get("publish_date")
        created_time_str = page.get("created_time")

        # Choose the date to evaluate page age (Publish Date preferred, fallback to Created Time)
        eval_date = None
        date_source = ""
        if pub_date_str:
            eval_date = parse_date(pub_date_str)
            date_source = "Publish Date"
        
        if not eval_date and created_time_str:
            eval_date = parse_date(created_time_str)
            date_source = "Creation Time"

        if not eval_date:
            print(f"⚠️ Skipping card '{title}': No valid Publish Date or Creation Time found.")
            continue

        # Calculate page age
        age = now - eval_date
        age_days = age.total_seconds() / (24 * 3600)

        if age_days >= args.days:
            print(f"\n📦 Archiving card: '{title}'")
            print(f"   - Age: {age_days:.1f} days old (evaluated via {date_source}: {pub_date_str or created_time_str})")
            
            if args.dry_run:
                print(f"   💡 [DRY-RUN] Would move page {page_id} to archive database {archive_db_id}")
                archived_count += 1
            else:
                res = notion.move_page_to_database(page_id, archive_db_id)
                if res:
                    print(f"   ✅ Successfully moved page to archive database!")
                    archived_count += 1
                else:
                    print(f"   ❌ Failed to move page. Check API permissions or database schemas.")
                    failed_count += 1
        else:
            # Not old enough
            pass

    print("\n" + "=" * 40)
    print("📊 Archiving Summary:")
    print(f" - Total processed: {archived_count}")
    print(f" - Total failed: {failed_count}")
    print(f" - Main database remains clean!")
    print("=" * 40 + "\n")

if __name__ == "__main__":
    main()
