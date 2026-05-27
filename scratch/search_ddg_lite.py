import urllib.request
import urllib.parse
import re
import ssl

def search_ddg_lite_get(query):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = 'https://lite.duckduckgo.com/lite/?' + urllib.parse.urlencode({'q': query})
    req = urllib.request.Request(url, headers=headers, method='GET')
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            html = response.read().decode('utf-8', errors='ignore')
            print(f"HTML Length: {len(html)}")
            
            snippets = re.findall(r'<td class="result-snippet"[^>]*>(.*?)</td>', html, re.DOTALL)
            print(f"=== DDG Lite Search Results for: {query} ===")
            count = 0
            for snippet in snippets:
                clean = re.sub(r'<[^>]+>', ' ', snippet)
                clean = re.sub(r'\s+', ' ', clean).strip()
                if len(clean) > 30:
                    print(f"- {clean}")
                    count += 1
                    if count >= 8:
                        break
            print()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    search_ddg_lite_get("best time to post youtube shorts 2026")
