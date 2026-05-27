import urllib.request
import urllib.parse
import re
import ssl

def search_bing_raw(query, keywords):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = 'https://www.bing.com/search?' + urllib.parse.urlencode({'q': query})
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            html = response.read().decode('utf-8')
            # Clean HTML tags slightly
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text)
            
            print(f"=== Raw Snippets for: {query} ===")
            for kw in keywords:
                for match in re.finditer(kw, text, re.IGNORECASE):
                    start = max(0, match.start() - 150)
                    end = min(len(text), match.end() + 150)
                    snippet = text[start:end]
                    print(f"[{kw}] ...{snippet}...")
                    break # Just show one match per keyword to avoid flooding
            print()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    search_bing_raw("best time to post youtube shorts 2026", ["shorts", "pm", "am", "best time", "time to post"])
    print("=" * 80)
    search_bing_raw("best time to post tiktok 2026", ["tiktok", "pm", "am", "best time", "time to post"])
