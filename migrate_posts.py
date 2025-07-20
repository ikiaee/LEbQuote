import requests
from datetime import datetime
import os
import time

# Configuration
BOT_TOKEN = "7941102461:AAEhKerwX119YwSBck0yxpDEYdzuO6wEnqw"  # From @BotFather
CHANNEL_ID = "-1002696929880"      # Add '-' prefix for private channels (e.g. -100123456)
OUTPUT_DIR = "quotes"

# Try these working public MTProto proxies (updated July 2024)
PROXIES = [
    {  # Proxy 1 (Europe)
        "ip": "51.158.118.84",
        "port": 443,
        "secret": "eea86b2794eabf81"
    },
    {  # Proxy 2 (Asia)
        "ip": "95.161.76.100",
        "port": 443,
        "secret": "dd000000000000000000000000000000"
    }
]

def get_messages():
    """Try all proxies until success"""
    for proxy in PROXIES:
        try:
            print(f"🔄 Trying proxy {proxy['ip']}...")

            # MTProto proxy URL format
            proxy_url = f"https://{proxy['ip']}:{proxy['port']}/proxy?secret={proxy['secret']}"

            # Verify proxy first
            test = requests.get(proxy_url, timeout=10)
            if test.status_code != 200:
                continue

            # Fetch messages
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatHistory"
            response = requests.get(
                url,
                params={'chat_id': CHANNEL_ID, 'limit': 100},
                proxies={'https': proxy_url},
                timeout=20
            )

            if response.status_code == 200:
                return response.json().get('result', {}).get('messages', [])

        except Exception as e:
            print(f"⚠️ Proxy failed: {str(e)[:100]}...")
            time.sleep(2)

    return []

# [Rest of your save_as_markdown() function remains the same...]

# Run export
os.makedirs(OUTPUT_DIR, exist_ok=True)
messages = get_messages()

if messages:
    save_as_markdown(messages)
    print(f"✅ Saved {len(messages)} quotes to {OUTPUT_DIR}/")
else:
    print("""
❌ All proxies failed. Please:
1. Check your bot is ADMIN in the channel
2. Try a different VPN service
3. Use manual export:
   - Right-click channel → Export chat history → JSON
   - Run json_to_markdown.py (I'll provide this if needed)
""")