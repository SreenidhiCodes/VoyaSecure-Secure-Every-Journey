from flask import Flask, request, jsonify, send_from_directory
import json
from pathlib import Path
from datetime import datetime
import uuid

app = Flask(__name__)
from communities_backend import communities_api
app.register_blueprint(communities_api)
# -----------------------------
# Paths
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
REPORTS_FILE = BASE_DIR / "assets" / "reports.json"

# Ensure directory exists
REPORTS_FILE.parent.mkdir(parents=True, exist_ok=True)

# Initialize file if missing
if not REPORTS_FILE.exists():
    REPORTS_FILE.write_text("[]", encoding="utf-8")

print("🚀 Server running")
print("📁 Reports file:", REPORTS_FILE)

# -----------------------------
# Pages
# -----------------------------
@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/report")
def report_page():
    return send_from_directory(BASE_DIR, "report.html")

@app.route("/reported")
def reported_page():
    return send_from_directory(BASE_DIR, "reported.html")

# -----------------------------
# API: Get reports
# -----------------------------
@app.route("/api/reports", methods=["GET"])
def get_reports():
    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception as e:
        print("❌ Read error:", e)
        return jsonify([])

# -----------------------------
# API: Save report
# -----------------------------
@app.route("/api/report", methods=["POST"])
def save_report():
    data = request.get_json(force=True)

    report = {
        "id": str(uuid.uuid4()),
        "place": data.get("place"),
        "state": data.get("state"),
        "country": data.get("country", "India"),
        "coordinates": data.get("coordinates", {}),
        "problemType": data.get("problemType"),
        "description": data.get("description"),
        "incidentDate": data.get("incidentDate"),
        "severity": data.get("severity", "Low"),
        "reportedAt": datetime.utcnow().isoformat() + "Z"
    }

    try:
        with open(REPORTS_FILE, "r+", encoding="utf-8") as f:
            reports = json.load(f)
            reports.append(report)
            f.seek(0)
            json.dump(reports, f, indent=2)
            f.truncate()  # Important: remove leftover content
        print("✅ Saved:", report["id"])
        return jsonify({"success": True})
    except Exception as e:
        print("❌ Save error:", e)
        return jsonify({"success": False, "error": str(e)}), 500

# -----------------------------
# Static files (JS/CSS/Images)
# -----------------------------
@app.route("/data/<path:filename>")
def data_files(filename):
    return send_from_directory(BASE_DIR / "data", filename)

@app.route("/css/<path:filename>")
def css_files(filename):
    return send_from_directory(BASE_DIR / "css", filename)

@app.route("/assets/<path:filename>")
def assets_files(filename):
    return send_from_directory(BASE_DIR / "assets", filename)

@app.route("/<path:filename>")
def root_files(filename):
    return send_from_directory(BASE_DIR, filename)

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)