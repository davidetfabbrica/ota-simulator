# ota-simulator
Uses Docker and Kubernetes to simulate a device OTA update through containerisation

# OTA Update Simulator

A simulated Over-the-Air (OTA) software update system built with Python, Docker, and Kubernetes. Built as a learning project to demonstrate containerisation, container orchestration, and AI-assisted development.

## What it does

Three containers work together to simulate how connected devices receive remote software updates:

- **Update Server** — a Flask API that manages firmware versions, receives poll requests from the device, and serves a web dashboard
- **Device Simulator** — a Python process that mimics a connected device, polling the server every 10 seconds and applying updates when instructed
- **PostgreSQL** — stores device state, firmware versions, and a full event log

The system supports three operations found in real production OTA systems:

- **Poll** — the device asks the server whether a newer version is available
- **Push** — an operator pushes a specific firmware version to the device from the dashboard
- **Rollback** — the device reverts to its previous version if the new one is problematic

## Architecture

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
│                         └────────────────────┘  │
└─────────────────────────────────────────────────┘
│
│ Port 5001
▼
Browser Dashboard

## Running with Docker Compose

Requirements: Docker Desktop or Colima

```bash
git clone https://github.com/davidetfabbrica/ota-simulator.git
cd ota-simulator
cp .env.example .env
docker compose up --build
```

Open your browser at `http://localhost:5001`

To stop:
```bash
docker compose down
```

## Running with Kubernetes (Minikube)

Requirements: Minikube, kubectl

```bash
minikube start --driver=docker
eval $(minikube docker-env)
docker build -t ota-server:latest ./server
docker build -t ota-device:latest ./device
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/init-configmap.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/server-deployment.yaml
kubectl apply -f k8s/device-deployment.yaml
kubectl get pods -w
```

Access the dashboard:
```bash
minikube service ota-server
```

## Project structure
ota-simulator/
├── docker-compose.yml
├── init.sql                  # database schema and seed data
├── .env.example              # environment variable template
├── server/                   # update server
│   ├── Dockerfile
│   ├── app.py
│   ├── db.py
│   ├── requirements.txt
│   ├── routes/
│   │   ├── device.py
│   │   ├── firmware.py
│   │   └── history.py
│   └── templates/
│       └── dashboard.html
├── device/                   # device simulator
│   ├── Dockerfile
│   ├── device.py
│   └── requirements.txt
└── k8s/                      # kubernetes manifests
├── configmap.yaml
├── init-configmap.yaml
├── postgres-deployment.yaml
├── server-deployment.yaml
└── device-deployment.yaml

## Built with AI assistance

This project was designed, debugged, and built in approximately one hour using Claude as a technical collaborator. The process involved:

- Scoping the project from a vague initial prompt to a full PRD
- Resolving real environment failures (macOS version incompatibility, architecture mismatches, shell configuration conflicts) without derailing the session
- Explaining architectural decisions as they were made rather than just generating code
- Annotating all code for a developer returning to Python after a gap

The most accurate description of AI-assisted development at this level is not a code generator but a technical collaborator that holds full project context and adapts when reality doesn't match the plan.

## What would come next

- Tests for the server API endpoints
- A second simulated device to demonstrate multi-device management
- Kubernetes horizontal pod autoscaling on the server
- Proper Kubernetes Secrets rather than plain environment variables for credentials
- A CI/CD pipeline using GitHub Actions