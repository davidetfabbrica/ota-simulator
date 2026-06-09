# routes/history.py - endpoint for the event log

from flask import Blueprint, jsonify
import db

history_bp = Blueprint("history", __name__)


@history_bp.route("/api/history", methods=["GET"])
def get_history():
    """
    Returns the 50 most recent update events.
    The dashboard calls this every 5 seconds to keep the log current.
    """
    events = db.get_event_history()

    # Convert timestamps to strings for JSON serialisation
    result = []
    for row in events:
        event = dict(row)
        if event.get("created_at"):
            event["created_at"] = event["created_at"].isoformat()
        result.append(event)

    return jsonify(result)