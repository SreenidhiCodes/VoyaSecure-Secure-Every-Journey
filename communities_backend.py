# communities_backend.py
from flask import Blueprint, request, jsonify
from pathlib import Path
import json, hashlib, uuid
from datetime import datetime

communities_api = Blueprint("communities_api", __name__)

# ---------------- CONFIG ----------------
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_FILE = DATA_DIR / "communities.json"
AUTHOR_SECRET = "VOYA_SECURE_AUTHOR_KEY"  # placeholder; consider env var

DATA_DIR.mkdir(exist_ok=True)
if not DATA_FILE.exists():
    DATA_FILE.write_text("{}", encoding="utf-8")  # dict keyed by community

# ---------------- HELPERS ----------------
def generate_hash(message, timestamp, community, prev_hash):
    raw = f"{message}|{timestamp}|{community}|{prev_hash}"
    return hashlib.sha256(raw.encode()).hexdigest()

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Normalize: must be dict of lists
            if isinstance(data, list):
                # auto-fix: collapse list into dict by community
                fixed = {}
                for entry in data:
                    cid = entry.get("community", "unknown")
                    fixed.setdefault(cid, []).append(entry)
                return fixed
            if not isinstance(data, dict):
                return {}
            # ensure lists for every key
            for k, v in list(data.items()):
                if not isinstance(v, list):
                    data[k] = []
            return data
    except Exception:
        return {}

def save_data(data):
    # atomic write
    tmp = DATA_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(DATA_FILE)

def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def validate_message_payload(payload):
    if not isinstance(payload, dict):
        return "Invalid JSON", None
    message = payload.get("message")
    community = payload.get("community")
    author = payload.get("author")  # optional
    if not community or not isinstance(community, str):
        return "community is required", None
    if not message or not isinstance(message, str) or not message.strip():
        return "message is required", None
    # trim to reasonable length
    msg = message.strip()
    if len(msg) > 5000:
        return "message too long", None
    return None, {"community": community.strip(), "message": msg, "author": (author or "anonymous").strip()}

# ---------------- ROUTES ----------------
@communities_api.route("/api/messages", methods=["GET"])
def get_messages_grouped():
    """
    Returns all messages grouped by community:
    {
      "voya": [ {...}, ... ],
      "1": [ {...}, ... ],
      ...
    }
    """
    data = load_data()
    return jsonify(data)

@communities_api.route("/api/messages/<community>", methods=["GET"])
def get_messages_for_community(community):
    """
    Returns list of messages for a specific community.
    """
    data = load_data()
    return jsonify(data.get(community, []))

@communities_api.route("/api/messages", methods=["POST"])
def add_message():
    """
    Accepts JSON: { "community": "voya", "message": "Hello", "author": "Sreenidhi" }
    Returns the created message with id/hash/timestamp.
    """
    payload = request.get_json(silent=True)
    err, parsed = validate_message_payload(payload)
    if err:
        return jsonify({"error": err}), 400

    community = parsed["community"]
    message = parsed["message"]
    author = parsed["author"]

    data = load_data()
    history = data.get(community, [])

    prev_hash = history[-1]["hash"] if history else ""
    timestamp = now_iso()
    entry_id = str(uuid.uuid4())

    entry = {
        "id": entry_id,
        "community": community,
        "author": author,
        "message": message,
        "timestamp": timestamp,
        "prev_hash": prev_hash,
        "hash": generate_hash(message, timestamp, community, prev_hash),
    }

    history.append(entry)
    data[community] = history
    save_data(data)

    return jsonify(entry), 201

@communities_api.route("/api/messages/<community>/verify", methods=["GET"])
def verify_chain(community):
    """
    Verifies hash chain integrity for a community.
    Returns { "ok": true } or details of the first broken link.
    """
    data = load_data()
    history = data.get(community, [])
    prev = ""
    for i, e in enumerate(history):
        expected = generate_hash(e["message"], e["timestamp"], community, prev)
        if e.get("hash") != expected or e.get("prev_hash") != prev:
            return jsonify({
                "ok": False,
                "index": i,
                "id": e.get("id"),
                "reason": "hash mismatch or prev_hash mismatch"
            }), 200
        prev = e["hash"]
    return jsonify({"ok": True, "count": len(history)}), 200
