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
    {"patient_id": "PATIENT_001", "rr": 28, "status": "normal"},
    {"patient_id": "PATIENT_001", "rr": 35, "status": "high"},
    {"patient_id": "PATIENT_001", "rr": 70, "status": "low"},
    {"patient_id": "PATIENT_001", "rr": 22, "status": "borderline"},
    {"patient_id": "PATIENT_001", "rr": 34, "status": "normal"},
]

for data in test_data:
    try:
        resp = requests.post(url, json=data, headers=headers)
        print(f"Inserted {data['status']} → {resp.status_code} {resp.json()}")
    except Exception as e:
        print(f"Error: {e}")
