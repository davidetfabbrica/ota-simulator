# db.py - handles all database connections and queries for the Update Server
# Every other module imports from here rather than connecting directly to the database.

import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection():
    """
    Opens and returns a new database connection using credentials
    from environment variables. Never hardcodes credentials.
    RealDictCursor means rows come back as dictionaries (column_name: value)
    rather than plain tuples, which makes the code much more readable.
    """
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=RealDictCursor
    )


def get_device_state(device_id):
    """
    Returns the current state of a device as a dictionary,
    or None if the device has not registered yet.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM device_state WHERE device_id = %s",
                (device_id,)   # always use parameterised queries - never string formatting
            )
            return cur.fetchone()


def upsert_device_state(device_id, current_version, previous_version=None):
    """
    Creates a device record if it doesn't exist, or updates it if it does.
    'Upsert' = insert or update. The ON CONFLICT clause handles this cleanly in PostgreSQL.
    Also updates last_seen to the current time on every call.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO device_state (device_id, current_version, previous_version, last_seen)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (device_id) DO UPDATE SET
                    current_version  = EXCLUDED.current_version,
                    previous_version = EXCLUDED.previous_version,
                    last_seen        = NOW()
            """, (device_id, current_version, previous_version))
        conn.commit()   # write the change to the database


def log_event(device_id, event_type, from_version=None, to_version=None):
    """
    Writes a record to the update_events table.
    Called every time something significant happens: poll, push, apply, rollback, error.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO update_events (device_id, event_type, from_version, to_version)
                VALUES (%s, %s, %s, %s)
            """, (device_id, event_type, from_version, to_version))
        conn.commit()


def get_all_firmware():
    """
    Returns all firmware versions ordered by creation date, newest first.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM firmware_versions ORDER BY created_at DESC"
            )
            return cur.fetchall()


def add_firmware(version, label):
    """
    Adds a new firmware version to the database.
    Returns the newly created row, or None if the version already exists.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO firmware_versions (version, label)
                VALUES (%s, %s)
                ON CONFLICT (version) DO NOTHING
                RETURNING *
            """, (version, label))
            result = cur.fetchone()
        conn.commit()
        return result


def get_event_history(limit=50):
    """
    Returns the most recent update events, newest first.
    Limits to 50 rows by default to keep the dashboard responsive.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM update_events
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            return cur.fetchall()


def get_pending_update(device_id):
    """
    Checks whether there is a pending push command for this device.
    Returns the target version string if there is one, or None if not.
    We store pending pushes in a simple table rather than a message queue
    to keep things straightforward for this project.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT to_version FROM update_events
                WHERE device_id = %s
                AND event_type = 'push'
                AND from_version IS NULL
                ORDER BY created_at DESC
                LIMIT 1
            """, (device_id,))
            row = cur.fetchone()
            return row["to_version"] if row else None


def set_pending_update(device_id, to_version):
    """
    Records a push command for a device by writing an event with event_type 'push'
    and from_version NULL. The device picks this up on its next poll.
    When the device applies it, it will write its own 'apply' event.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO update_events (device_id, event_type, from_version, to_version)
                VALUES (%s, 'push', NULL, %s)
            """, (device_id, to_version))
        conn.commit()