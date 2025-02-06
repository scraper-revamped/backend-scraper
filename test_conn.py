import requests

url = "https://tenders.etimad.sa/Tender/AllTendersForVisitor?PageNumber=1"
timeout_seconds = 60  # adjust as needed

try:
    response = requests.get(url, timeout=timeout_seconds)
    print("Status Code:", response.status_code)
    print("Response length:", len(response.text))
except Exception as e:
    print("Error:", e)

