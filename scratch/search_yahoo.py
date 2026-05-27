import urllib.request
import urllib.parse
import re
import ssl

def search_yahoo(query):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = 'https://search.yahoo.com/search?' + urllib.parse.urlencode({'p': query})
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
            # Yahoo search results are inside divs with class "compText aBc" or similar, or lists with "algo"
            # Let's extract any text within <p> or <span class="fc-falcon">
            snippets = re.findall(r'<div class="compText[^>]*>(.*?)</div>|<span class="fc-falcon[^>]*>(.*?)</span>', html, re.DOTALL)
            
            print(f"=== Yahoo Search Results for: {query} ===")
            count = 0
            for snippet in snippets:
                content = snippet[0] or snippet[1]
                if not content:
                    continue
                clean = re.sub(r'<[^>]+>', ' ', content)
                clean = re.sub(r'\s+', ' ', clean).strip()
                if len(clean) > 40:
                    print(f"- {clean}")
                    count += 1
                    if count >= 8:
                        break
            print()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    search_yahoo("best time to post youtube shorts 2026")
    print("=" * 80)
    search_yahoo("best time to post tiktok 2026")
