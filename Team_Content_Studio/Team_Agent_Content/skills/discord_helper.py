#!/usr/bin/env python3
import os
import json
import urllib.request
import urllib.parse
import ssl
from datetime import datetime, timezone

def load_env():
    """Load environment variables from .env file in the workspace root."""
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

class DiscordHelper:
    def __init__(self, webhook_url=None):
        load_env()
        self.webhook_url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")
        if self.webhook_url:
            self.webhook_url = self.webhook_url.strip('"').strip("'")
            
        # SSL Context for compatibility (bypassing verification to avoid local certificate issues)
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def send_message(self, content=None, embeds=None, username="WTJ Content Manager", avatar_url=None):
        """Sends a text message and/or embeds to Discord Webhook."""
        if not self.webhook_url:
            print("❌ Discord Webhook Error: DISCORD_WEBHOOK_URL is not set.")
            return False

        payload = {}
        if content:
            payload["content"] = content
        if embeds:
            payload["embeds"] = embeds
        if username:
            payload["username"] = username
        if avatar_url:
            payload["avatar_url"] = avatar_url

        if not payload:
            print("⚠️ Discord Webhook Warning: Empty payload.")
            return False

        req_data = json.dumps(payload).encode("utf-8")
        
        # User-Agent is required by Discord to avoid 403 Forbidden
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        req = urllib.request.Request(
            self.webhook_url,
            data=req_data,
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, context=self.ssl_context) as response:
                # Discord webhook returns 204 No Content on success
                if response.status in [200, 204]:
                    return True
                return False
        except Exception as e:
            print(f"❌ Discord Webhook Connection Error: {e}")
            return False

    def send_info(self, title, description, fields=None, username="WTJ Content Manager"):
        """Sends an Info alert (Blue embed) to Discord."""
        embed = {
            "title": f"ℹ️ {title}",
            "description": description,
            "color": 3447003,  # Blue hex: 0x3498db
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        if fields:
            embed["fields"] = fields
        return self.send_message(embeds=[embed], username=username)

    def send_success(self, title, description, fields=None, username="WTJ Content Manager"):
        """Sends a Success alert (Green embed) to Discord."""
        embed = {
            "title": f"✅ {title}",
            "description": description,
            "color": 3066993,  # Green hex: 0x2ecc71
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        if fields:
            embed["fields"] = fields
        return self.send_message(embeds=[embed], username=username)

    def send_warning(self, title, description, fields=None, username="WTJ Content Manager"):
        """Sends a Warning alert (Yellow embed) to Discord."""
        embed = {
            "title": f"⚠️ {title}",
            "description": description,
            "color": 15857167,  # Yellow hex: 0xf1c40f
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        if fields:
            embed["fields"] = fields
        return self.send_message(embeds=[embed], username=username)

    def send_error(self, title, description, fields=None, username="WTJ Content Manager"):
        """Sends an Error/Bug alert (Red embed) to Discord."""
        embed = {
            "title": f"🚨 {title}",
            "description": description,
            "color": 15158396,  # Red hex: 0xe74c3c
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        if fields:
            embed["fields"] = fields
        return self.send_message(embeds=[embed], username=username)

if __name__ == "__main__":
    # Test notification when run directly
    print("Testing DiscordHelper connection...")
    helper = DiscordHelper()
    if helper.webhook_url:
        print(f"Webhook URL found: {helper.webhook_url[:40]}...")
        success = helper.send_info(
            "บอท WTJ เริ่มต้นการใช้งาน",
            "ทดสอบระบบแจ้งเตือนผ่าน Discord Webhook สำเร็จแล้วจ้าแก!",
            fields=[
                {"name": "สถานะ", "value": "ออนไลน์ 🟢", "inline": True},
                {"name": "เวอร์ชัน", "value": "v1.0.0", "inline": True}
            ]
        )
        if success:
            print("✅ Test message sent successfully!")
        else:
            print("❌ Failed to send test message.")
    else:
        print("❌ Error: Missing DISCORD_WEBHOOK_URL in environment.")
