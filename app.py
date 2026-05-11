import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)  # Allow React frontend to call this API

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_KEY = os.getenv("API_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ----------------------------
# Helper: verify ESP32 API key
# ----------------------------
def verify_api_key():
    auth = request.headers.get("X-API-Key")
    return auth == API_KEY

# ----------------------------
# POST /api/breathing
# Receives data from ESP32 and stores in Supabase
# ----------------------------
@app.route("/api/breathing", methods=["POST"])
def receive_data():
    # Check API key
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    patient_id = data.get("patient_id")
    rr = data.get("rr")
    status = data.get("status")

    if not all([patient_id, rr is not None, status]):
        return jsonify({"error": "Missing fields: patient_id, rr, status"}), 400

    # Insert into Supabase
    try:
        result = supabase.from_("breathing_records").insert({
            "patient_id": patient_id,
            "rr": rr,
            "status": status,
            "recorded_at": datetime.now().isoformat()
        }).execute()
    except Exception as e:
        print("Supabase error:", e)
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": "OK", "id": result.data[0]["id"]}), 201

# ----------------------------
# GET /api/latest
# Returns the 20 most recent records for the dashboard
# ----------------------------
@app.route("/api/latest", methods=["GET"])
def get_latest():
    try:
        result = supabase.from_("breathing_records") \
                         .select("*") \
                         .order("recorded_at", desc=True) \
                         .limit(20) \
                         .execute()
        return jsonify(result.data)
    except Exception as e:
        print("Supabase error:", e)
        return jsonify({"error": str(e)}), 500

# ----------------------------
# Run the development server
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)