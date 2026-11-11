#!/bin/bash
echo "=== 1. Standard curl ==="
curl -s -I "https://www.financialexpress.com/" | head -n 5

echo "=== 2. curl with Chrome User Agent & HTTP/2 ==="
curl -s -I --http2 -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" "https://www.financialexpress.com/" | head -n 5

echo "=== 3. curl with Googlebot User Agent ==="
curl -s -I -H "User-Agent: Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)" "https://www.financialexpress.com/" | head -n 5

echo "=== 4. curl with Googlebot on wp-json ==="
curl -s -I -H "User-Agent: Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)" "https://www.financialexpress.com/wp-json/wp/v2/posts?per_page=1" | head -n 5

echo "=== 5. curl with Googlebot on today.xml ==="
curl -s -I -H "User-Agent: Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)" "https://www.financialexpress.com/today.xml" | head -n 5

echo "=== 6. curl with Twitterbot ==="
curl -s -I -H "User-Agent: Twitterbot/1.0" "https://www.financialexpress.com/wp-json/wp/v2/posts?per_page=1" | head -n 5
