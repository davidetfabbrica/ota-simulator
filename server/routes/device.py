# routes/device.py - endpoints for device registration, status, push, and rollback

from flask import Blueprint, jsonify, request
from datetime import datetime, timezone
import db

device_bp = Blueprint("device", __name__)

# The device ID we are simulating - hardcoded for simplicity in this project.
# A real system would support many devices with dynamic IDs.
DEVICE_ID = "device-001"


@device_bp.route("/api/device/register", methods=["POST"])
def register_device():
    """
    Called by the device simulator on startup.
    Expects JSON body: { "device_id": "device-001", "version": "1.0.0" }
    Creates or updates the device record and logs a register event.
    """
    data = request.get_json()

    if not data or "version" not in data:
        return jsonify({"error": "version is required"}), 400

    device_id = data.get("device_id", DEVICE_ID)
    version = data["version"]

    db.upsert_device_state(device_id, version)
    db.log_event(device_id, "register", to_version=version)

    return jsonify({"status": "registered", "device_id": device_id, "version": version})


@device_bp.route("/api/device/status", methods=["GET"])
def device_status():
    """
    Returns the current state of the device.
    The dashboard calls this every 5 seconds to update the display.
    Also calculates whether the device is online based on last_seen timestamp.
    """
    state = db.get_device_state(DEVICE_ID)

    if state is None:
        return jsonify({"status": "not_registered"})

    state = dict(state)

    # Convert the last_seen timestamp to a string so it can be serialised to JSON
    if state.get("last_seen"):
        state["last_seen"] = state["last_seen"].isoformat()

    # Consider the device offline if it hasn't polled in the last 30 seconds
    last_seen = state.get("last_seen")
    online = False
    if last_seen:
        last_seen_dt = datetime.fromisoformat(last_seen)
        # make sure both datetimes are timezone-aware for comparison
        if last_seen_dt.tzinfo is None:
            last_seen_dt = last_seen_dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        online = (now - last_seen_dt).total_seconds() < 30

    state["online"] = online
    return jsonify(state)


@device_bp.route("/api/device/poll", methods=["POST"])
def poll():
    """
    Called by the device simulator every 10 seconds.
    Expects JSON body: { "device_id": "device-001", "version": "1.0.0" }
    Updates last_seen, logs the poll, and returns any pending update.
    """
    data = request.get_json()

    if not data or "version" not in data:
        return jsonify({"error": "version is required"}), 400

    device_id = data.get("device_id", DEVICE_ID)
    current_version = data["version"]

    # Get existing state so we preserve previous_version
    existing = db.get_device_state(device_id)
    previous = existing["previous_version"] if existing else None

    # Update last_seen and current version
    db.upsert_device_state(device_id, current_version, previous)
    db.log_event(device_id, "poll", from_version=current_version)

    # Check if there is a pending push for this device
    pending = db.get_pending_update(device_id)

    if pending and pending != current_version:
        # There is an update waiting - tell the device what version to apply
        return jsonify({"update_available": True, "target_version": pending})

    return jsonify({"update_available": False})


@device_bp.route("/api/device/apply", methods=["POST"])
def apply_update():
    """
    Called by the device simulator after it has applied an update.
    Expects JSON body: { "device_id": "device-001", "from_version": "1.0.0", "to_version": "1.1.0" }
    Updates device state and logs the apply event.
    """
    data = request.get_json()

    if not data or "from_version" not in data or "to_version" not in data:
        return jsonify({"error": "from_version and to_version are required"}), 400

    device_id = data.get("device_id", DEVICE_ID)
    from_version = data["from_version"]
    to_version = data["to_version"]

    # Store previous version before updating - this enables rollback
    db.upsert_device_state(device_id, to_version, previous_version=from_version)
    db.log_event(device_id, "apply", from_version=from_version, to_version=to_version)

    return jsonify({"status": "applied", "version": to_version})


@device_bp.route("/api/device/push", methods=["POST"])
def push_update():
    """
    Called by the dashboard when the operator clicks Push.
    Expects JSON body: { "version": "1.2.0" }
    Records a pending push that the device will pick up on its next poll.
    """
    data = request.get_json()

    if not data or "version" not in data:
        return jsonify({"error": "version is required"}), 400

    db.set_pending_update(DEVICE_ID, data["version"])

    return jsonify({"status": "push_queued", "target_version": data["version"]})


@device_bp.route("/api/device/rollback", methods=["POST"])
def rollback():
    """
    Called by the dashboard when the operator clicks Rollback.
    Looks up the previous version and queues it as the next update.
    Returns an error if there is no previous version to roll back to.
    """
    state = db.get_device_state(DEVICE_ID)

    if state is None:
        return jsonify({"error": "device not registered"}), 404

    previous = state["previous_version"]

    if not previous:
        return jsonify({"error": "no previous version to roll back to"}), 400

    # Queue the previous version as the next update
    db.set_pending_update(DEVICE_ID, previous)
    db.log_event(DEVICE_ID, "rollback", from_version=state["current_version"], to_version=previous)

    return jsonify({"status": "rollback_queued", "target_version": previous})