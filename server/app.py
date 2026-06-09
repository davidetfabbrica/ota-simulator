# app.py - the main Flask application entry point
# This file creates the Flask app, registers all the route blueprints,
# and starts the server.

import os
from flask import Flask, send_from_directory

# Import the three blueprint modules we created in routes/
from routes.firmware import firmware_bp
from routes.device import device_bp
from routes.history import history_bp

# Create the Flask application instance
app = Flask(__name__)

# Register each blueprint - this connects all the routes to the app
app.register_blueprint(firmware_bp)
app.register_blueprint(device_bp)
app.register_blueprint(history_bp)


@app.route("/")
def dashboard():
    """
    Serves the dashboard HTML file from the templates folder.
    Serving it through Flask avoids browser CORS restrictions
    that would block API calls from a file opened directly from disk.
    """
    return send_from_directory("templates", "dashboard.html")


if __name__ == "__main__":
    # Read the port from environment or default to 5001
    # (port 5000 is reserved on macOS by AirPlay Receiver)
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
    # host="0.0.0.0" means accept connections from any network interface,
    # not just localhost - required for Docker container networking