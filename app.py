import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from supabase import create_client, Client
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables from .env file (local development)
load_dotenv()

app = Flask(__name__)
CORS(app)  # Allow all origins (for React dashboard)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')

jwt = JWTManager(app)

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_KEY = os.getenv("API_KEY")  # Secret key for ESP32

# Validate that credentials exist
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment variables")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ----------------------------
# POST /register
# Register a new user
# ----------------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    role = data.get("role")  # 'admin', 'caregiver', 'patient'

    if not all([username, password, role]):
        return jsonify({"error": "Missing fields"}), 400

    password_hash = generate_password_hash(password)

    try:
        result = supabase.from_("users").insert({
            "username": username,
            "password_hash": password_hash,
            "role": role
        }).execute()
        return jsonify({"message": "User registered"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------------
# POST /login
# Login user
# ----------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    try:
        result = supabase.from_("users").select("*").eq("username", username).execute()
        if not result.data:
            return jsonify({"error": "Invalid credentials"}), 401

        user = result.data[0]
        if not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid credentials"}), 401

        access_token = create_access_token(identity={"username": username, "role": user["role"]})
        return jsonify({"access_token": access_token, "role": user["role"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------------
# Helper: verify ESP32 API key
# ----------------------------
def verify_api_key():
    auth_header = request.headers.get("X-API-Key")
    return auth_header == API_KEY

# ----------------------------
# POST /api/breathing
# Receives data from ESP32 and stores in Supabase
# ----------------------------
@app.route("/api/breathing", methods=["POST"])
def receive_data():
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    patient_id = data.get("patient_id")
    rr = data.get("rr")
    status = data.get("status")

    if not all([patient_id, rr is not None, status]):
        return jsonify({"error": "Missing required fields: patient_id, rr, status"}), 400

    try:
        result = supabase.from_("breathing_records").insert({
            "patient_id": patient_id,
            "rr": rr,
            "status": status,
            "recorded_at": datetime.now().isoformat()
        }).execute()

        return jsonify({"message": "OK", "id": result.data[0]["id"]}), 201
    except Exception as e:
        app.logger.error(f"Supabase insert error: {e}")
        return jsonify({"error": str(e)}), 500

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
        app.logger.error(f"Supabase fetch error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# GET /api/health (optional)
# Simple health check for Render
# ----------------------------
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200

# ----------------------------
# GET /api/patients
# Get all patients
# ----------------------------
@app.route("/api/patients", methods=["GET"])
def get_patients():
    try:
        result = supabase.from_("patients").select("*").execute()
        return jsonify(result.data)
    except Exception as e:
        app.logger.error(f"Supabase fetch error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# POST /api/patients
# Register a new patient
# ----------------------------
@app.route("/api/patients", methods=["POST"])
def register_patient():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    patient_id = data.get("patient_id")
    name = data.get("name")

    if not all([patient_id, name]):
        return jsonify({"error": "Missing required fields: patient_id, name"}), 400

    try:
        result = supabase.from_("patients").insert({
            "patient_id": patient_id,
            "name": name
        }).execute()
        return jsonify({"message": "Patient registered", "id": result.data[0]["id"]}), 201
    except Exception as e:
        app.logger.error(f"Supabase insert error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# GET /api/caregivers
# Get all caregivers
# ----------------------------
@app.route("/api/caregivers", methods=["GET"])
def get_caregivers():
    try:
        result = supabase.from_("caregivers").select("*").execute()
        return jsonify(result.data)
    except Exception as e:
        app.logger.error(f"Supabase fetch error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# POST /api/caregivers
# Register a new caregiver
# ----------------------------
@app.route("/api/caregivers", methods=["POST"])
def register_caregiver():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    caregiver_id = data.get("caregiver_id")
    name = data.get("name")

    if not all([caregiver_id, name]):
        return jsonify({"error": "Missing required fields: caregiver_id, name"}), 400

    try:
        result = supabase.from_("caregivers").insert({
            "caregiver_id": caregiver_id,
            "name": name
        }).execute()
        return jsonify({"message": "Caregiver registered", "id": result.data[0]["id"]}), 201
    except Exception as e:
        app.logger.error(f"Supabase insert error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# POST /api/assign
# Assign caregiver to patient
# ----------------------------
@app.route("/api/assign", methods=["POST"])
def assign_caregiver():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    patient_id = data.get("patient_id")
    caregiver_id = data.get("caregiver_id")

    if not all([patient_id, caregiver_id]):
        return jsonify({"error": "Missing required fields: patient_id, caregiver_id"}), 400

    try:
        result = supabase.from_("assignments").insert({
            "patient_id": patient_id,
            "caregiver_id": caregiver_id
        }).execute()
        return jsonify({"message": "Assignment created", "id": result.data[0]["id"]}), 201
    except Exception as e:
        app.logger.error(f"Supabase insert error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# GET /api/stats
# Get system statistics
# ----------------------------
@app.route("/api/stats", methods=["GET"])
def get_stats():
    try:
        patients_count = supabase.from_("patients").select("*", count="exact").execute().count
        caregivers_count = supabase.from_("caregivers").select("*", count="exact").execute().count
        assignments_count = supabase.from_("assignments").select("*", count="exact").execute().count
        readings_count = supabase.from_("breathing_records").select("*", count="exact").execute().count
        return jsonify({
            "patients": patients_count,
            "caregivers": caregivers_count,
            "assignments": assignments_count,
            "readings": readings_count
        })
    except Exception as e:
        app.logger.error(f"Supabase fetch error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# GET /api/logs
# Get system logs (mock for now)
# ----------------------------
@app.route("/api/logs", methods=["GET"])
def get_logs():
    # Mock logs - in real app, fetch from database or log files
    logs = [
        {"timestamp": "2026-05-14T10:00:00Z", "event": "Patient PATIENT_001 registered"},
        {"timestamp": "2026-05-14T10:05:00Z", "event": "Caregiver assigned to PATIENT_001"},
        {"timestamp": "2026-05-14T10:10:00Z", "event": "Breathing data received for PATIENT_001"},
    ]
    return jsonify(logs)

# ----------------------------
# Run the development server
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)