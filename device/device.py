# device.py - simulates a connected device that polls for OTA updates
# Runs in an infinite loop, polling the update server every 10 seconds.

import os
import time
import requests   # the requests library makes HTTP calls straightforward

# -----------------------------------------------------------------------
# Configuration - read from environment variables so nothing is hardcoded.
# These are set in docker-compose.yml, not here.
# -----------------------------------------------------------------------

# The base URL of the update server - uses the Docker service name 'server'
# as the hostname, which Docker's internal DNS resolves automatically
SERVER_URL = os.environ.get("SERVER_URL", "http://server:5001")

# The unique identifier for this device
DEVICE_ID = os.environ.get("DEVICE_ID", "device-001")

# How long to wait between polls, in seconds
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "10"))

# The starting firmware version - in a real device this would be read
# from a file on the device's filesystem
INITIAL_VERSION = os.environ.get("INITIAL_VERSION", "1.0.0")


# -----------------------------------------------------------------------
# Device state - held in memory while the process is running
# -----------------------------------------------------------------------

current_version = INITIAL_VERSION


def register():
    """
    Registers this device with the update server on startup.
    Retries every 5 seconds until it succeeds - the server container
    may take a moment to start up after the device container does.
    """
    while True:
        try:
            print(f"[device] Registering with server as {DEVICE_ID} running v{current_version}")
            response = requests.post(
                f"{SERVER_URL}/api/device/register",
                json={"device_id": DEVICE_ID, "version": current_version},
                timeout=5   # don't wait more than 5 seconds for a response
            )
            if response.status_code == 200:
                print(f"[device] Registered successfully")
                return
            else:
                print(f"[device] Registration failed: {response.status_code} - retrying in 5s")
        except requests.exceptions.ConnectionError:
            # Server isn't ready yet - this is normal during startup
            print(f"[device] Server not reachable yet - retrying in 5s")
        except requests.exceptions.Timeout:
            print(f"[device] Registration timed out - retrying in 5s")

        time.sleep(5)


def poll():
    """
    Sends a poll request to the server.
    Returns the target version if an update is available, or None if not.
    """
    global current_version   # we need to modify the global variable from inside this function

    try:
        response = requests.post(
            f"{SERVER_URL}/api/device/poll",
            json={"device_id": DEVICE_ID, "version": current_version},
            timeout=5
        )

        if response.status_code != 200:
            print(f"[device] Poll failed: {response.status_code}")
            return None

        data = response.json()
        print(f"[device] Polled server - running v{current_version} - "
              f"update available: {data['update_available']}")

        if data["update_available"]:
            return data["target_version"]

    except requests.exceptions.ConnectionError:
        print(f"[device] Could not reach server during poll")
    except requests.exceptions.Timeout:
        print(f"[device] Poll timed out")

    return None


def apply_update(target_version):
    """
    Applies an update by switching to the target version.
    Notifies the server once the update has been applied.
    In a real device this would flash firmware to storage - here we
    just update the in-memory version variable.
    """
    global current_version

    from_version = current_version
    print(f"[device] Applying update: {from_version} -> {target_version}")

    # Simulate the update taking a moment
    time.sleep(2)

    # Update our local version
    current_version = target_version
    print(f"[device] Update applied - now running v{current_version}")

    # Tell the server the update was applied
    try:
        response = requests.post(
            f"{SERVER_URL}/api/device/apply",
            json={
                "device_id": DEVICE_ID,
                "from_version": from_version,
                "to_version": target_version
            },
            timeout=5
        )
        if response.status_code == 200:
            print(f"[device] Server acknowledged update")
        else:
            print(f"[device] Server acknowledgement failed: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print(f"[device] Could not reach server to confirm update")
    except requests.exceptions.Timeout:
        print(f"[device] Server acknowledgement timed out")


def main():
    """
    Main entry point. Registers with the server then enters
    the polling loop indefinitely.
    """
    print(f"[device] Starting up - device ID: {DEVICE_ID}")
    print(f"[device] Initial version: {current_version}")
    print(f"[device] Server URL: {SERVER_URL}")
    print(f"[device] Poll interval: {POLL_INTERVAL}s")

    # Register first - retry until the server is ready
    register()

    # Poll forever
    print(f"[device] Entering polling loop")
    while True:
        target_version = poll()

        if target_version:
            apply_update(target_version)

        time.sleep(POLL_INTERVAL)


# This is the standard Python entry point guard.
# It means this block only runs when the file is executed directly,
# not when it is imported by another module.
if __name__ == "__main__":
    main()