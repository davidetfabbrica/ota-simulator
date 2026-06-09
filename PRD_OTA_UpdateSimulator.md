# Project PRD: OTA Update Simulator
**Version:** 1.0  
**Author:** DT  
**Status:** Draft  
**Last updated:** June 2026

---

## 1. Purpose

This document defines what we are building, why, and how. It is the single source of truth for the project. If there is ever a question about scope or direction, refer back here first.

The goal is to build a simulated Over-the-Air (OTA) software update system. The system will demonstrate how connected devices — phones, industrial sensors, smart appliances — receive remote software updates from a central server. We are simulating the *mechanism*, not flashing real firmware. The device is a Python process running in a Docker container.

This project is also the practical basis for a blog post documenting an AI-assisted development workflow from scratch.

---

## 2. Background: Why OTA Updates Matter

OTA updates are how the software industry maintains devices in the field without physical access. Android, iOS, Tesla vehicles, Ring doorbells, and industrial PLCs all use variants of this pattern. The core challenge is: how do you reliably update software on a device you cannot touch, ensure the update is valid, and recover safely if something goes wrong?

This project replicates the three fundamental operations of any OTA system:

- **Poll**: the device asks the server "do you have anything newer for me?"
- **Push**: the server tells the device "apply this version now"
- **Rollback**: the device reverts to the previous version if the new one is marked as faulty

---

## 3. Project Objectives

| Objective | Description |
|---|---|
| Learn Docker | Understand containers, images, Dockerfiles, and Docker Compose by building with them |
| Learn Kubernetes | Deploy the finished system to a local Kubernetes cluster using Minikube |
| Build something real | Produce a working OTA system with a live dashboard, not just a tutorial exercise |
| Blog-ready | Document the AI-assisted build process honestly, with technical depth |

---

## 4. Scope

### In scope
- A Python-based Update Server with a REST API
- A Python-based Device Simulator running as a separate process
- A PostgreSQL database for state and history
- A web dashboard served by the Update Server
- Docker containers for all three components
- Docker Compose to wire them together locally
- Kubernetes manifests for Minikube deployment
- A README suitable for GitHub

### Out of scope
- Real firmware or binary files
- Multiple simulated devices (we will build for one, with notes on how to extend)
- Cloud deployment (Minikube runs locally)
- Authentication and security hardening (noted as future work)
- Automated CI/CD pipelines

---

## 5. System Architecture

```
┌─────────────────────────────────────────────────┐
│                  Docker Network                  │
│                                                 │
│  ┌──────────────┐      ┌──────────────────────┐ │
│  │   Device     │      │    Update Server     │ │
│  │  Simulator   │◄────►│    (Flask API +      │ │
│  │  (Python)    │ HTTP │     Dashboard)       │ │
│  └──────────────┘      └──────────┬───────────┘ │
│                                   │             │
│                         ┌─────────▼──────────┐  │
│                         │    PostgreSQL DB    │  │
│                         │  (State + History)  │  │
│                         └────────────────────┘  │
└─────────────────────────────────────────────────┘
         │
         │ Port 5001
         ▼
  Browser Dashboard
  (runs on your Mac)
```

**Three containers, one network:**

- The Device Simulator and Update Server communicate over HTTP within the Docker network
- PostgreSQL is only accessible internally — it is never exposed to the host machine
- The dashboard is served by the Update Server on port 5001, accessible in your browser

---

## 6. Components

### 6.1 Update Server (`server/`)

A Python Flask web application. Responsible for:

- Storing known firmware versions in the database
- Receiving poll requests from the device ("what version should I be on?")
- Accepting push commands from the dashboard
- Serving the web dashboard
- Writing all update events to the database

**Key API endpoints:**

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/device/status` | Returns current device version and online status |
| GET | `/api/firmware` | Returns list of all available firmware versions |
| POST | `/api/firmware` | Adds a new firmware version |
| POST | `/api/device/push` | Pushes a specific version to the device |
| POST | `/api/device/rollback` | Triggers rollback to previous version |
| GET | `/api/history` | Returns the full update event log |
| GET | `/` | Serves the dashboard HTML page |

### 6.2 Device Simulator (`device/`)

A Python application that mimics a connected device. Responsible for:

- Registering itself with the server on startup
- Polling the server every 10 seconds for a pending update
- Applying updates when instructed (updating its stored version number)
- Keeping a record of its previous version so rollback is possible
- Reporting its current version on every poll

### 6.3 Database (PostgreSQL)

Three tables:

**`firmware_versions`**
```
id          SERIAL PRIMARY KEY
version     TEXT NOT NULL UNIQUE
label       TEXT
created_at  TIMESTAMP
```

**`device_state`**
```
id              SERIAL PRIMARY KEY
device_id       TEXT NOT NULL
current_version TEXT
previous_version TEXT
last_seen       TIMESTAMP
```

**`update_events`**
```
id          SERIAL PRIMARY KEY
device_id   TEXT
event_type  TEXT   -- 'poll', 'push', 'apply', 'rollback', 'error'
from_version TEXT
to_version   TEXT
created_at   TIMESTAMP
```

### 6.4 Dashboard (served by Update Server)

A single HTML page with vanilla JavaScript. No frameworks, no build step.

Displays:
- Device ID, current version, and last-seen timestamp
- Online/offline indicator (based on last poll time)
- List of available firmware versions with a "Push" button against each
- A "Rollback" button (disabled if no previous version exists)
- A live event log table, auto-refreshing every 5 seconds

---

## 7. Technology Choices

| Component | Technology | Why | Free? |
|---|---|---|---|
| Server language | Python 3 | Readable, widely used, good library support | Yes |
| Web framework | Flask | Lightweight, minimal setup, good for learning | Yes |
| Database | PostgreSQL | Industry standard relational DB, good Docker image available | Yes |
| DB interface | psycopg2 | Standard PostgreSQL adapter for Python | Yes |
| Frontend | Vanilla HTML/JS | No build step, easy to read and modify | Yes |
| Containerisation | Docker + Docker Compose | Industry standard, free for personal use | Yes |
| Local Kubernetes | Minikube | Runs a real Kubernetes cluster on your Mac | Yes |
| Package management | pip + requirements.txt | Standard Python dependency management | Yes |

**Why Flask over Django?**  
Django is a full web framework with many conventions and a steep learning curve. Flask is minimal — you only add what you need. For a learning project with a small API, Flask lets you see exactly what is happening without magic in the background.

**Why PostgreSQL over SQLite?**  
SQLite is fine for single-process applications, but it does not handle multiple containers reading and writing simultaneously. PostgreSQL runs as its own process (its own container), which is the realistic production pattern.

**Why vanilla JS over React?**  
React requires a build step, node modules, and understanding of components. Vanilla JS runs directly in the browser. For a dashboard that just needs to fetch and display data, it is the right tool.

---

## 8. Security Notes (Awareness, Not Implementation)

This project does not implement production security — that is out of scope. However, you should be aware of what a real system would require:

| Risk | Real-world mitigation |
|---|---|
| Any device can call the API | Device authentication (API keys, mutual TLS) |
| Firmware not verified before applying | Cryptographic signature verification on update packages |
| Database credentials in environment variables | Secrets management (Kubernetes Secrets, HashiCorp Vault) |
| No HTTPS | TLS termination at a load balancer or ingress controller |
| Dashboard open to anyone | Authentication layer (OAuth, session tokens) |

We will use environment variables for database credentials (the standard approach at this scale) and keep credentials out of the codebase entirely.

---

## 9. Resilience Notes

Real OTA systems must be resilient. Again, awareness only at this scale:

| Failure scenario | Real-world approach |
|---|---|
| Device loses connection mid-update | Atomic update with checksum verification before applying |
| Server crashes during push | Idempotent operations — replaying the same command is safe |
| Bad firmware bricks the device | Watchdog timer forces rollback if device stops reporting |
| Database goes down | Server returns last-known state from cache |

Our rollback mechanism is the primary resilience feature we will implement.

---

## 10. Folder Structure

```
ota-simulator/
├── docker-compose.yml          # Wires all containers together
├── .env.example                # Template for environment variables (safe to commit)
├── .env                        # Actual credentials (never committed)
├── .gitignore
├── README.md
│
├── server/                     # Update Server
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                  # Flask application entry point
│   ├── db.py                   # Database connection and queries
│   ├── routes/
│   │   ├── firmware.py         # Firmware version endpoints
│   │   ├── device.py           # Device status and control endpoints
│   │   └── history.py          # Event log endpoint
│   └── templates/
│       └── dashboard.html      # The web dashboard
│
├── device/                     # Device Simulator
│   ├── Dockerfile
│   ├── requirements.txt
│   └── device.py               # Main device loop
│
└── k8s/                        # Kubernetes manifests (Phase 6)
    ├── postgres-deployment.yaml
    ├── server-deployment.yaml
    ├── device-deployment.yaml
    └── configmap.yaml
```

---

## 11. Build Phases

| Phase | Name | Content | When |
|---|---|---|---|
| 1 | Docker Fundamentals | Concepts, terminology, first commands | Saturday morning |
| 2 | Database Layer | Schema design, PostgreSQL in Docker | Saturday morning |
| 3 | Update Server | Flask API, all endpoints, database queries | Saturday afternoon |
| 4 | Device Simulator | Polling loop, apply, rollback logic | Saturday afternoon/evening |
| 5 | Docker Compose | Wire all containers, test full flow | Sunday morning |
| 6 | Dashboard | HTML page, live polling, push/rollback controls | Sunday morning |
| 7 | Kubernetes (Minikube) | Manifests, deploy, understand the difference | Sunday afternoon |
| 8 | README + Blog scaffold | Document what was built and how | Sunday evening |

---

## 12. Definition of Done

The project is complete when:

- [ ] All three containers start with a single `docker compose up` command
- [ ] The device polls the server and the event appears in the dashboard log
- [ ] A firmware push from the dashboard causes the device to update its version
- [ ] A rollback from the dashboard causes the device to revert to its previous version
- [ ] The same system deploys to Minikube with `kubectl apply`
- [ ] The README explains what the project does, how to run it, and what you learned
- [ ] No credentials appear anywhere in the codebase

---

## 13. What Success Looks Like for the Blog

The blog post should be honest about:

- What Docker and Kubernetes actually are, in plain terms
- Why we chose each component and what the alternatives were
- Where things went wrong during the build and how they were fixed
- What AI-assisted development actually looks like in practice (not a magic wand)
- What you would add next if you kept building

It should not claim more than was built, and it should not pretend the process was smooth if it was not.

---

*End of PRD v1.0*
