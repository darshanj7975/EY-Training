import requests

for i in range(10):
    response = requests.get("http://127.0.0.1:8000/")
    print(
        f"Request {i+1}: "
        f"Status={response.status_code}"
    )