import requests
import json

url = 'http://localhost:8000/submit-candidate/'
payload = {
    "address": "10, Crown Estate, Edo Inside, Ijako, Ogun State",
    "city": "Other",
    "hours_text": "Mon-Sat 7am-10pm",
    "lat": 6.65555,
    "lng": 5.999,
    "name": "Amala Iya Valorant",
    "phone": "+2348023677114",
    "state": "Ogun",
    "tags": ["Amala & Ewedu", "Amala & Gbegiri", "Abula", "Ponmo"]
}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
