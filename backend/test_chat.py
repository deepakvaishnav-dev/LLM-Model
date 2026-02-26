import requests
try:
    res = requests.post("http://localhost:8000/api/chat/", json={"query": "hello"})
    with open("error_output.txt", "w") as f:
        f.write(res.text)
    print("Done writing to error_output.txt")
except Exception as e:
    print(e)
