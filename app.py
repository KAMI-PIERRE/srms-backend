import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, verify_jwt_in_request
)
from supabase import create_client, Client
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables from .env file (local development)
load_dotenv()

app = Flask(__name__)

# CORS – restrict to your frontend origin in production via CORS_ORIGIN env var
cors_origin = os.getenv("CORS_ORIGIN", "*")
CORS(app, resources={r"/*": {"origins": cors_origin}})

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
if not app.config['JWT_SECRET_KEY']:
    raise ValueError("JWT_SECRET_KEY must be set in environment variables")

jwt = JWTManager(app)

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_KEY = os.getenv("API_KEY")  # Secret key for ESP32

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ----------------------------
# Helper: verify ESP32 API key
# ----------------------------
def verify_api_key():
    auth_header = request.headers.get("X-API-Key")
    return auth_header == API_KEY

# ----------------------------
# Helper: get current user identity from JWT
# ----------------------------
def current_user():
    return get_jwt_identity()

# ----------------------------
# POST /register
# Register a new user (caregiver or patient only)
# ----------------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "").strip()

    if not all([username, password, role]):
        return jsonify({"error": "Missing fields: username, password, role"}), 400

    if role not in ("caregiver", "patient"):
        return jsonify({"error": "Role must be 'caregiver' or 'patient'"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    password_hash = generate_password_hash(password)

    try:
        # Check if username already exists
        existing = supabase.from_("users").select("id").eq("username", username).execute()
        if existing.data:
            return jsonify({"error": "Username already taken"}), 409

        result = supabase.from_("users").insert({
            "username": username,
            "password_hash": password_hash,
            "role": role
        }).execute()

        new_user_id = result.data[0]["id"]

        # If registering as caregiver, also create a row in caregivers table
        if role == "caregiver":
            existing_cg = supabase.from_("caregivers").select("id").eq("caregiver_id", username).execute()
            if not existing_cg.data:
                supabase.from_("caregivers").insert({
                    "caregiver_id": username,
                    "name": username
                }).execute()

        # If registering as patient, also create a row in patients table
        if role == "patient":
            existing_pt = supabase.from_("patients").select("id").eq("patient_id", username).execute()
            if not existing_pt.data:
                supabase.from_("patients").insert({
                    "patient_id": username,
                    "name": username
                }).execute()

        return jsonify({"message": "User registered successfully"}), 201
    except Exception as e:
        app.logger.error(f"Register error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# POST /login
# Login user, returns JWT + role
# ----------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not all([username, password]):
        return jsonify({"error": "Missing username or password"}), 400

    try:
        result = supabase.from_("users").select("id, username, password_hash, role").eq("username", username).execute()
        if not result.data:
            return jsonify({"error": "Invalid credentials"}), 401

        user = result.data[0]
        if not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid credentials"}), 401

        access_token = create_access_token(
            identity={"id": user["id"], "username": username, "role": user["role"]}
        )
        return jsonify({
            "access_token": access_token,
            "role": user["role"],
            "username": username
        }), 200
    except Exception as e:
        app.logger.error(f"Login error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# GET /api/health
# Health check
# ----------------------------
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200

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

    if status not in ("normal", "low", "high", "borderline"):
        return jsonify({"error": "status must be one of: normal, low, high, borderline"}), 400

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
# Returns the 20 most recent breathing records (all patients)
# Requires JWT (caregiver or admin)
# ----------------------------
@app.route("/api/latest", methods=["GET"])
@jwt_required()
def get_latest():
    identity = current_user()
    if identity.get("role") not in ("caregiver", "admin"):
        return jsonify({"error": "Forbidden"}), 403

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
# GET /api/breathing/patient/<patient_id>
# Returns breathing records for a specific patient
# Requires JWT (patient can only see own data; caregiver/admin can see any)
# ----------------------------
@app.route("/api/breathing/patient/<patient_id>", methods=["GET"])
@jwt_required()
def get_patient_breathing(patient_id):
    identity = current_user()
    role = identity.get("role")
    username = identity.get("username")

    # Patients can only access their own data
    if role == "patient" and username != patient_id:
        return jsonify({"error": "Forbidden"}), 403

    try:
        result = supabase.from_("breathing_records") \
                         .select("*") \
                         .eq("patient_id", patient_id) \
                         .order("recorded_at", desc=True) \
                         .limit(50) \
                         .execute()
        return jsonify(result.data)
    except Exception as e:
        app.logger.error(f"Supabase fetch error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# GET /api/patients
# Get all patients (admin only)
# ----------------------------
@app.route("/api/patients", methods=["GET"])
@jwt_required()
def api_get_patients():
    identity = current_user()
    if identity.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    try:
        result = supabase.from_("patients").select("id, patient_id, name, age, condition, created_at").execute()
        return jsonify(result.data)
    except Exception as e:
        app.logger.error(f"Supabase fetch error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# POST /api/patients
# Register a new patient (admin only)
# ----------------------------
@app.route("/api/patients", methods=["POST"])
@jwt_required()
def api_register_patient():
    identity = current_user()
    if identity.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    patient_id = data.get("patient_id", "").strip()
    name = data.get("name", "").strip()
    age = data.get("age")
    condition = data.get("condition", "")

    if not all([patient_id, name]):
        return jsonify({"error": "Missing required fields: patient_id, name"}), 400

    try:
        # Check duplicate
        existing = supabase.from_("patients").select("id").eq("patient_id", patient_id).execute()
        if existing.data:
            return jsonify({"error": "Patient ID already exists"}), 409

        insert_data = {"patient_id": patient_id, "name": name}
        if age is not None:
            insert_data["age"] = age
        if condition:
            insert_data["condition"] = condition

        result = supabase.from_("patients").insert(insert_data).execute()

        # Also create a user account for the patient with a default password
        existing_user = supabase.from_("users").select("id").eq("username", patient_id).execute()
        if not existing_user.data:
            default_password = "Patient@123"
            supabase.from_("users").insert({
                "username": patient_id,
                "password_hash": generate_password_hash(default_password),
                "role": "patient"
            }).execute()

        return jsonify({
            "message": "Patient registered successfully",
            "id": result.data[0]["id"],
            "default_password": "Patient@123"
        }), 201
    except Exception as e:
        app.logger.error(f"Supabase insert error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# GET /api/caregivers
# Get all caregivers (admin only)
# ----------------------------
@app.route("/api/caregivers", methods=["GET"])
@jwt_required()
def api_get_caregivers():
    identity = current_user()
    if identity.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    try:
        result = supabase.from_("caregivers").select("id, caregiver_id, name, specialization, created_at").execute()
        return jsonify(result.data)
    except Exception as e:
        app.logger.error(f"Supabase fetch error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# POST /api/assign
# Assign caregiver to patient (admin only)
# ----------------------------
@app.route("/api/assign", methods=["POST"])
@jwt_required()
def api_assign_caregiver():
    identity = current_user()
    if identity.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    patient_id = data.get("patient_id", "").strip()
    caregiver_id = data.get("caregiver_id", "").strip()

    if not all([patient_id, caregiver_id]):
        return jsonify({"error": "Missing required fields: patient_id, caregiver_id"}), 400

    try:
        # Check if assignment already exists
        existing = supabase.from_("assignments") \
            .select("id") \
            .eq("patient_id", patient_id) \
            .eq("caregiver_id", caregiver_id) \
            .eq("status", "active") \
            .execute()
        if existing.data:
            return jsonify({"error": "This caregiver is already assigned to this patient"}), 409

        result = supabase.from_("assignments").insert({
            "patient_id": patient_id,
            "caregiver_id": caregiver_id,
            "status": "active"
        }).execute()
        return jsonify({"message": "Caregiver assigned successfully", "id": result.data[0]["id"]}), 201
    except Exception as e:
        app.logger.error(f"Supabase insert error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# GET /api/assignments
# Get all assignments (admin only)
# ----------------------------
@app.route("/api/assignments", methods=["GET"])
@jwt_required()
def api_get_assignments():
    identity = current_user()
    if identity.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    try:
        result = supabase.from_("assignments").select("*").order("assigned_at", desc=True).execute()
        return jsonify(result.data)
    except Exception as e:
        app.logger.error(f"Supabase fetch error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# DELETE /api/assignments/<id>
# Remove an assignment (admin only)
# ----------------------------
@app.route("/api/assignments/<int:assignment_id>", methods=["DELETE"])
@jwt_required()
def api_delete_assignment(assignment_id):
    identity = current_user()
    if identity.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    try:
        supabase.from_("assignments").delete().eq("id", assignment_id).execute()
        return jsonify({"message": "Assignment removed"}), 200
    except Exception as e:
        app.logger.error(f"Supabase delete error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# GET /api/stats
# Get system statistics (admin only)
# ----------------------------
@app.route("/api/stats", methods=["GET"])
@jwt_required()
def api_get_stats():
    identity = current_user()
    if identity.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    try:
        patients_count = supabase.from_("patients").select("*", count="exact").execute().count
        caregivers_count = supabase.from_("caregivers").select("*", count="exact").execute().count
        assignments_count = supabase.from_("assignments").select("*", count="exact").eq("status", "active").execute().count
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
# Get recent breathing records as system activity log (admin only)
# ----------------------------
@app.route("/api/logs", methods=["GET"])
@jwt_required()
def api_get_logs():
    identity = current_user()
    if identity.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403

    try:
        result = supabase.from_("breathing_records") \
            .select("id, patient_id, rr, status, recorded_at") \
            .order("recorded_at", desc=True) \
            .limit(50) \
            .execute()

        logs = [
            {
                "timestamp": record["recorded_at"],
                "event": f"Patient {record['patient_id']} — RR: {record['rr']} bpm — Status: {record['status'].upper()}"
            }
            for record in result.data
        ]
        return jsonify(logs)
    except Exception as e:
        app.logger.error(f"Supabase fetch error: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# Run the development server
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
