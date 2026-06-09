-- This file runs automatically when the PostgreSQL container starts for the first time.
-- It creates the three tables our application needs.

-- Stores available firmware versions that can be pushed to devices
CREATE TABLE IF NOT EXISTS firmware_versions (
    id          SERIAL PRIMARY KEY,       -- auto-incrementing unique ID
    version     TEXT NOT NULL UNIQUE,     -- e.g. "1.0.0", "1.1.0"
    label       TEXT,                     -- human-readable description e.g. "Stability fix"
    created_at  TIMESTAMP DEFAULT NOW()   -- when this version was added
);

-- Stores the current state of each device
CREATE TABLE IF NOT EXISTS device_state (
    id               SERIAL PRIMARY KEY,
    device_id        TEXT NOT NULL UNIQUE,  -- identifier for the device e.g. "device-001"
    current_version  TEXT,                  -- the version it is currently running
    previous_version TEXT,                  -- the version before the last update (used for rollback)
    last_seen        TIMESTAMP              -- when it last polled the server
);

-- Stores a log of every update event that has occurred
CREATE TABLE IF NOT EXISTS update_events (
    id           SERIAL PRIMARY KEY,
    device_id    TEXT,
    event_type   TEXT,       -- one of: 'register', 'poll', 'push', 'apply', 'rollback', 'error'
    from_version TEXT,       -- version before the event (can be null for first registration)
    to_version   TEXT,       -- version after the event (can be null for a poll with no update)
    created_at   TIMESTAMP DEFAULT NOW()
);

-- Seed the database with some initial firmware versions so we have something to work with
INSERT INTO firmware_versions (version, label) VALUES
    ('1.0.0', 'Initial release'),
    ('1.1.0', 'Bug fixes'),
    ('1.2.0', 'Performance improvements')
ON CONFLICT (version) DO NOTHING;  -- if these already exist, do nothing (safe to re-run)
