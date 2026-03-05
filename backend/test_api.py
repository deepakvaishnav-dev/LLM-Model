import urllib.request
import urllib.error
import json

url = "http://127.0.0.1:8000/api/chat/"
data = json.dumps({"query": "hello"}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as resp:
        print("Success:", resp.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8')
    print(f"HTTP {e.code}:\n{body}")
except Exception as e:
    print(e)
