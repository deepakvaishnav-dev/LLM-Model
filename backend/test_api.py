import urllib.request
import json
import traceback

req = urllib.request.Request(
    'http://localhost:8000/api/chat/',
    data=json.dumps({"query": "Explain how AI works in a few words"}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    response = urllib.request.urlopen(req)
    print("SUCCESS")
    print(response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("HTTP ERROR:", e.code)
    print(e.read().decode('utf-8'))
except Exception as e:
    print("OTHER ERROR:")
    traceback.print_exc()
