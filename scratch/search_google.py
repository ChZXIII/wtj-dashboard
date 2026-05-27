import urllib.request
import urllib.parse
import ssl

headers = {
    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)'
}
url = 'https://www.google.com/search?' + urllib.parse.urlencode({'q': 'best time to post youtube shorts'})
req = urllib.request.Request(url, headers=headers)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

try:
    with urllib.request.urlopen(req, context=ctx) as response:
        html = response.read().decode('utf-8', errors='ignore')
        with open('/Users/chz/Desktop/ChZ_Agent_Corp/scratch/google_test.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"HTML saved, length: {len(html)}")
except Exception as e:
    print(f"Error: {e}")
