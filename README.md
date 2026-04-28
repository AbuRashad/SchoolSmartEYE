# Intelligent School Monitoring System — SchoolSmartEYE

A production-ready, real-time school safety and monitoring platform built on **14 integrated AI-powered units**, with a FastAPI backend and React + Tailwind frontend.

---

## 🚀 Quick Start

### Option 1 — Docker (recommended, one command)

```bash
git clone https://github.com/AbuRashad/SchoolSmartEYE.git
cd SchoolSmartEYE
docker-compose up --build
```

| Service   | URL                               |
|-----------|-----------------------------------|
| Frontend  | <http://localhost:3000>           |
| Backend   | <http://localhost:8000>           |
| API Docs  | <http://localhost:8000/docs>      |

### Option 2 — Local Development

#### Backend

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # edit as needed
uvicorn app.main:app --reload
```

API docs: <http://127.0.0.1:8000/docs>

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: <http://127.0.0.1:5173>

> The Vite dev server proxies all `/api/*` calls to the FastAPI backend on port 8000.

### Tests

```bash
pytest -q
```

---

## 🏗️ Architecture

```
SchoolSmartEYE/
├── app/
│   ├── main.py                     # FastAPI entrypoint (with seed data lifespan)
│   ├── core/
│   │   ├── config.py               # Pydantic settings
│   │   └── governance_layer.py     # Arab Data Governance Model (RBAC, anonymization, TTL)
│   ├── api/v1/
│   │   ├── router.py               # Mounts all 7 endpoint routers
│   │   └── endpoints/              # health, dashboard, ssi, units, analytics, reports, portal
│   ├── units/                      # 14 integrated monitoring units
│   │   ├── unit_01/  ...  unit_14/ # Each: module.py with service class
│   ├── services/                   # Core AI/analytics services
│   ├── schemas/                    # Pydantic request/response schemas
│   ├── models/                     # Domain models shared across units
│   └── services/seed_data.py       # In-memory demo data (populated on startup)
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # Main dashboard app
│   │   ├── components/             # UI components (KPI gauge, heatmap, alerts, etc.)
│   │   ├── hooks/                  # WebSocket + REST data hooks
│   │   └── types.ts                # TypeScript type definitions
│   ├── vite.config.ts              # Dev proxy to backend :8000
│   ├── Dockerfile                  # Multi-stage build (Node to nginx)
│   └── nginx.conf                  # Reverse proxy for API + WebSocket
├── tests/                          # 41+ unit & integration tests
├── Dockerfile                      # Backend container
└── docker-compose.yml              # Full-stack one-command startup
```

---

## 📡 API Endpoints

### Health

| Method | Endpoint           | Description          |
|--------|--------------------|----------------------|
| GET    | `/api/v1/health`   | Service health check |

### Dashboard

| Method    | Endpoint                     | Description                                    |
|-----------|------------------------------|------------------------------------------------|
| GET       | `/api/v1/dashboard/summary`  | School name, SSI score, benchmark             |
| GET       | `/api/v1/dashboard/alerts`   | Live alert feed (coherence, anomaly, density) |
| GET       | `/api/v1/dashboard/heatmap`  | Risk heatmap cells with zone labels           |
| GET       | `/api/v1/dashboard/live`     | Full snapshot (REST polling fallback)         |
| WebSocket | `/api/v1/dashboard/ws`       | Real-time dashboard stream                    |

**WebSocket messages:** send `refresh`, `subscribe`, `ping` to receive snapshot JSON; send `close` to disconnect.

### School Safety Index (SSI)

| Method | Endpoint              | Description                                       |
|--------|-----------------------|---------------------------------------------------|
| GET    | `/api/v1/ssi/live`    | Real-time SSI computed from sensor inputs        |
| GET    | `/api/v1/ssi/history` | 30-day SSI trend with improvement analysis       |

### Units

| Method | Endpoint                       | Description                             |
|--------|--------------------------------|-----------------------------------------|
| GET    | `/api/v1/units`                | Metadata for all 14 system units       |
| GET    | `/api/v1/units/capture/health` | Unit 01 camera stream health           |
| GET    | `/api/v1/units/alerts/summary` | Unit 09 alert queue summary            |

### Analytics

| Method | Endpoint                     | Description                             |
|--------|------------------------------|-----------------------------------------|
| GET    | `/api/v1/analytics/overview` | KPI metrics (attendance, cameras, etc.) |

### Reports

| Method | Endpoint                | Description                             |
|--------|-------------------------|-----------------------------------------|
| GET    | `/api/v1/reports/list`  | List all generated reports             |
| GET    | `/api/v1/reports/stats` | Incident statistics and zone risk data |

### Parent Portal

| Method | Endpoint                  | Description                             |
|--------|---------------------------|-----------------------------------------|
| GET    | `/api/v1/portal/student`  | Student attendance and safety status   |

---

## 🧩 14 Integrated Units

| # | Unit Name | Description |
|---|-----------|-------------|
| 01 | Video Capture Unit | Manages live camera streams across all school zones |
| 02 | Scene Understanding Unit | Crowd density, movement direction, congestion zones |
| 03 | Path Tracking Unit | Learns typical movement paths, flags deviations |
| 04 | Hazard Detection Unit | Detects falls, stampedes, fights, loitering |
| 05 | Spatial Behavioral Memory | Tracks zone-level behavioral baselines |
| 06 | Collective Behavioral Coherence | Measures group synchrony vs. fragmentation |
| 07 | Predictive Density Unit | Forecasts crowd density with safety thresholds |
| 08 | Attendance & Safety Integration | Links attendance records with safety detections |
| 09 | Alert & Response Unit | Issues prioritized safety alerts |
| 10 | Smart Monitoring Dashboard | Real-time KPI aggregation and heatmaps |
| 11 | Multi-Level Periodic Reports | Operational, analytical, supervisory, ministerial |
| 12 | Smart Parent Portal | Privacy-governed parent access to child status |
| 13 | Institutional Self-Assessment | End-of-semester safety assessment reports |
| 14 | Arab Data Governance Layer | RBAC, face anonymization, video TTL enforcement |

---

## 📹 Connecting Real School Cameras

SchoolSmartEYE can ingest live frames from real cameras via RTSP, HTTP MJPEG,
USB webcams, or local video files. All frames pass through the **Arab Data
Governance Layer (Unit 14)** for automatic face anonymization before being
shown or stored.

### 1. Create a `cameras.json` file at the project root

A template is provided in `cameras.example.json`. Copy it and edit:

```bash
cp cameras.example.json cameras.json
```

Each entry supports four source types:

| Type            | `source_url` example                                                      |
|-----------------|---------------------------------------------------------------------------|
| RTSP (IP cam)   | `rtsp://admin:PASSWORD@192.168.1.50:554/Streaming/Channels/101`           |
| HTTP MJPEG      | `http://192.168.1.60/mjpg/video.mjpg`                                     |
| USB webcam      | `"0"` (camera index as string)                                            |
| Local file      | `./samples/playground.mp4` (loops via auto-reconnect)                     |

```json
[
  {
    "camera_id": "cam-gate",
    "zone_id": "zone-main-gate",
    "label": "Main Gate — Entry",
    "source_url": "rtsp://admin:YOUR_PASSWORD@192.168.1.50:554/Streaming/Channels/101",
    "anonymize_faces": true
  }
]
```

### 2. Restart the backend

```bash
uvicorn app.main:app --reload
```

You should see:

```
INFO  Live camera ingestion active: 1 camera(s)
```

### 3. Open the **Live Cameras** tab in the dashboard

Navigate to <http://127.0.0.1:5173> and click **Live Cameras** in the sidebar.
Each registered camera appears as an MJPEG tile updated in real time.

### Runtime endpoints

| Method | Endpoint                                          | Description                             |
|--------|---------------------------------------------------|-----------------------------------------|
| GET    | `/api/v1/cameras`                                 | List registered live cameras + status   |
| POST   | `/api/v1/cameras`                                 | Register a new camera at runtime        |
| DELETE | `/api/v1/cameras/{camera_id}`                     | Unregister & stop a camera              |
| POST   | `/api/v1/cameras/{camera_id}/start`               | Restart a stopped worker                |
| POST   | `/api/v1/cameras/{camera_id}/stop`                | Stop a worker (keep registration)       |
| GET    | `/api/v1/cameras/{camera_id}/snapshot.jpg`        | One-shot latest JPEG                    |
| GET    | `/api/v1/cameras/{camera_id}/stream.mjpg`         | Live MJPEG multipart stream             |

### Tuning (in `.env`)

```env
CAMERA_SOURCES_FILE=./cameras.json
CAMERA_RECONNECT_SECONDS=5.0
CAMERA_JPEG_QUALITY=70           # 1-100; lower = less bandwidth
CAMERA_MAX_FPS=15                # cap CPU/network use per camera
CAMERA_ANONYMIZE_FACES=true      # global default for new cameras
CAMERA_OPEN_TIMEOUT_SECONDS=10
```

### Troubleshooting

- **Camera shows "offline"** → Check the URL with VLC first. RTSP credentials
  often need URL-encoding (`@` → `%40`).
- **No tile appears at all** → Backend logs say `"No live cameras configured"`
  → check that `cameras.json` exists at the project root and is valid JSON.
- **High latency** → Lower `CAMERA_MAX_FPS` and `CAMERA_JPEG_QUALITY`.

---

## 🔒 Arab Data Governance Model

The governance layer (`app/core/governance_layer.py`) enforces:

1. **Automated anonymization** — OpenCV-based face blurring for minors in all video streams
2. **Video TTL enforcement** — Strict 72-hour default retention policy with configurable TTL
3. **RBAC hierarchy** — Teacher → Principal → Ministry access levels with scope isolation

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and adjust as needed:

```env
APP_NAME=Intelligent School Monitoring System
APP_ENV=development
API_V1_STR=/api/v1
VIDEO_LOG_DIR=./video_logs
VIDEO_TTL_HOURS=72
```

---

## 🧪 Running Tests

```bash
# All tests
pytest -q

# With verbose output
pytest -v tests/
```

Tests cover: governance layer, health, dashboard, SSI, drill simulation, ministry reports, parent portal, report generator, risk heatmap, school safety index, spatial behavioral memory, attendance-safety integration, collective behavioral coherence, and crowd density forecasting.
