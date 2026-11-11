import urllib.request, urllib.error, json

headers_full = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

# Test 1: Homepage
try:
    req = urllib.request.Request("https://www.financialexpress.com/", headers=headers_full)
    with urllib.request.urlopen(req, timeout=10) as r:
        print("[TEST 1] Homepage:", r.getcode())
except urllib.error.HTTPError as e:
    print("[TEST 1 ERROR] Homepage:", e.code, e.headers)

# Test 2: today.xml
try:
    req = urllib.request.Request("https://www.financialexpress.com/today.xml", headers=headers_full)
    with urllib.request.urlopen(req, timeout=10) as r:
        print("[TEST 2] today.xml:", r.getcode())
except urllib.error.HTTPError as e:
    print("[TEST 2 ERROR] today.xml:", e.code, e.headers)

# Test 3: wp-json with full headers
headers_json = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.financialexpress.com/",
    "Origin": "https://www.financialexpress.com"
}
try:
    req = urllib.request.Request("https://www.financialexpress.com/wp-json/wp/v2/posts?per_page=1", headers=headers_json)
    with urllib.request.urlopen(req, timeout=10) as r:
        print("[TEST 3] wp-json:", r.getcode())
except urllib.error.HTTPError as e:
    print("[TEST 3 ERROR] wp-json:", e.code)
    print("Response headers:", e.headers)
    print("Body snippet:", e.read().decode("utf-8", errors="ignore")[:300])

# Test 4: Article page
try:
    req = urllib.request.Request("https://www.financialexpress.com/market/sensex-nifty-rally-on-bank-auto-gains-fpi-buying-hits-6-year-high-4381703/", headers=headers_full)
    with urllib.request.urlopen(req, timeout=10) as r:
        print("[TEST 4] Article page:", r.getcode())
except urllib.error.HTTPError as e:
    print("[TEST 4 ERROR] Article page:", e.code)
