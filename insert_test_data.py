import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY", "your-secret-key-for-esp32")

url = "http://localhost:5000/api/breathing"
headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

test_data = [
    {"patient_id": "PATIENT_001", "rr": 18, "status": "normal"},
    {"patient_id": "PATIENT_001", "rr": 30, "status": "high"},
    {"patient_id": "PATIENT_001", "rr": 7, "status": "low"},
    {"patient_id": "PATIENT_001", "rr": 22, "status": "borderline"},
    {"patient_id": "PATIENT_001", "rr": 15, "status": "normal"},
]

for data in test_data:
    try:
        resp = requests.post(url, json=data, headers=headers)
        print(f"Inserted {data['status']} → {resp.status_code} {resp.json()}")
    except Exception as e:
        print(f"Error: {e}")
        