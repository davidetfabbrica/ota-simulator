# routes/firmware.py - endpoints for managing firmware versions

from flask import Blueprint, jsonify, request
import db

# A Blueprint is Flask's way of grouping related routes together.
# We import this into the main app.py and register it there.
firmware_bp = Blueprint("firmware", __name__)


@firmware_bp.route("/api/firmware", methods=["GET"])
def list_firmware():
    """
    Returns all available firmware versions as JSON.
    The dashboard calls this to populate the version list.
    """
    versions = db.get_all_firmware()
    # psycopg2 RealDictCursor returns RealDictRow objects - convert to plain list of dicts
    return jsonify([dict(row) for row in versions])


@firmware_bp.route("/api/firmware", methods=["POST"])
def create_firmware():
    """
    Adds a new firmware version.
    Expects JSON body: { "version": "1.3.0", "label": "New features" }
    """
    data = request.get_json()

    # Basic validation - return a 400 error if version is missing
    if not data or "version" not in data:
        return jsonify({"error": "version is required"}), 400

    result = db.add_firmware(
        version=data["version"],
        label=data.get("label", "")   # label is optional
    )

    if result is None:
        # add_firmware returns None if the version already exists
        return jsonify({"error": "version already exists"}), 409

    return jsonify(dict(result)), 201   # 201 = Created