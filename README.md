# Intelligent School Monitoring System — SchoolSmartEYE

A real-time school safety and monitoring platform built on **15 integrated AI-powered units**, with a FastAPI backend (SQLAlchemy persistence, JWT authentication with roles) and a React + Vite + Tailwind frontend.

## 📜 Trust & Ethics

[![Charter](https://img.shields.io/badge/Charter-v1.0-1f6feb?style=flat-square)](docs/CHARTER.md)
[![Human-in-the-Loop](https://img.shields.io/badge/AI-Human--in--the--Loop-success?style=flat-square)](docs/CHARTER.md)
[![Privacy First](https://img.shields.io/badge/Privacy-First-blue?style=flat-square)](docs/CHARTER.md)

---

## 🚀 Quick Start

### Option 1 — Docker (one command)

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

Sign in with one of the [demo accounts](#-authentication--roles). The SQLite database is stored in the `db_data` Docker volume, so data survives restarts.
Compose reads its settings from your shell / a `.env` file next to `docker-compose.yml`; the defaults run in `APP_ENV=development`. For a real deployment set `APP_ENV=production`, a strong `JWT_SECRET_KEY` and your own `DEMO_*_PASSWORD` values (see [Configuration](#️-configuration)).

### Option 2 — Local Development

#### Backend

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # edit as needed
uvicorn app.main:app --reload
```

API docs: <http://127.0.0.1:8000/docs>. On first start the tables are created in `./schoolsmarteye.db` and the demo data and demo users are inserted (only when the tables are empty).

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
│   ├── main.py                     # FastAPI entrypoint (lifespan: DB init, seeding, cameras, Unit 15 job)
│   ├── core/
│   │   ├── config.py               # Pydantic settings (DB, JWT, CORS, cameras)
│   │   ├── security.py             # Password hashing (bcrypt) + JWT helpers
│   │   ├── governance_layer.py     # Arab Data Governance Model (RBAC, anonymization, TTL)
│   │   └── runtime_settings.py     # Settings editable at runtime from the Control Panel
│   ├── db/                         # SQLAlchemy: engine, get_db dependency, ORM models
│   ├── api/
│   │   ├── deps.py                 # get_current_user, require_roles(...)
│   │   └── v1/
│   │       ├── router.py           # Mounts all endpoint routers
│   │       └── endpoints/          # health, auth, dashboard, ssi, units, analytics, reports,
│   │                               # portal, parent_identity, cameras, students, bracelets, settings, agent
│   ├── units/                      # 15 integrated monitoring units (unit_01 … unit_15)
│   ├── services/                   # Core AI/analytics services + seed_data.py
│   ├── schemas/                    # Pydantic request/response schemas
│   └── models/                     # Domain dataclasses shared across units
├── migrations/                     # Alembic migrations (+ alembic.ini at the repo root)
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # App shell (login gate + pages)
│   │   ├── auth.ts, AuthContext.tsx# Token storage, role helpers, authenticated fetch
│   │   ├── components/             # UI components; components/control/ = Control Panel tabs
│   │   ├── hooks/                  # WebSocket + REST data hooks
│   │   └── types.ts                # TypeScript type definitions
│   ├── vite.config.ts              # Dev proxy to backend :8000
│   ├── Dockerfile                  # Multi-stage build (Node to nginx)
│   └── nginx.conf                  # Reverse proxy for API + WebSocket
├── tests/                          # pytest suite (uses an in-memory SQLite DB per test)
├── scripts/test_control_api.py     # End-to-end smoke test of the Control Panel API
├── Dockerfile                      # Backend container
└── docker-compose.yml              # Full-stack one-command startup (with DB volume)
```

---

## 🗄️ Database

Students, bracelets, attendance records, notifications, users, zones, cameras, incidents, SSI history, drills and agent feedback are stored in a SQL database via **SQLAlchemy 2.x**. Heatmaps and the Unit 15 engagement snapshots are still in-memory demo data.

| Setting | Default | Notes |
|---------|---------|-------|
| `DATABASE_URL` | `sqlite:///./schoolsmarteye.db` | Any SQLAlchemy URL |
| `DB_AUTO_CREATE` | `true` | Create missing tables at startup |

**SQLite** works out of the box (the `*.db` file is git-ignored).
For an **existing database**, run `alembic upgrade head` before starting the updated application. `DB_AUTO_CREATE=true` creates missing tables but does not add new columns to existing tables. Tenant revisions `0003`–`0005` add school ownership fields; revision `0006` adds audited parent-to-student links. Legacy ownership remains nullable and parent links are never inferred. Do not bulk-assign old records or parent identities without verified mappings.

**PostgreSQL** only needs a different URL and a driver:

```bash
pip install "psycopg[binary]"
# .env
DATABASE_URL=postgresql+psycopg://<user>:<password>@localhost:5432/schoolsmarteye
```

**Migrations (Alembic)** — the schema lives in `app/db/models.py`; migrations in `migrations/versions/`:

```bash
alembic upgrade head                                 # apply migrations (set DB_AUTO_CREATE=false when you use this)
alembic revision --autogenerate -m "describe change"  # after editing the models
```

**Demo data** — on startup `seed_data.populate()` inserts 10 students, 5 bracelets, attendance history, notifications and the demo users **only if the tables are empty**; existing data is never overwritten.

---

## 🔐 Authentication & Roles

The API uses **JWT bearer tokens**. Obtain one with the OAuth2 password form:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
     -d "username=principal" -d "password=principal123"
# → {"access_token": "...", "token_type": "bearer", "expires_in": 3600, "user": {...}}
```

Send it as the header `Authorization: Bearer <access_token>`. `GET /api/v1/auth/me` returns the current user. The frontend shows a login screen, stores the token, attaches it to every API call, returns to the login screen on `401`, and hides actions the current role cannot use.

### Roles

School staff roles follow the RBAC hierarchy: **Teacher → Principal → Ministry**. The **Parent** role is separate, has no staff permissions, and can access only students linked through an active, school-verified parent identity record.

| Demo user   | Role      | Demo password   |
|-------------|-----------|-----------------|
| `teacher`   | Teacher   | `teacher123`    |
| `principal` | Principal | `principal123`  |
| `ministry`  | Ministry  | `ministry123`   |
| Parent accounts | Parent | No demo account; provision individually after school identity verification |

> These are **demo credentials only**. Override them with `DEMO_TEACHER_PASSWORD`, `DEMO_PRINCIPAL_PASSWORD` and `DEMO_MINISTRY_PASSWORD` (or `SEED_DEMO_USERS=false`). With `APP_ENV=production` the demo users are *not* created while the published default passwords are in use.

| Access level | Endpoints |
|--------------|-----------|
| Public       | `/health`, `/auth/login`, `/units` (static unit metadata only) |
| Teacher+     | School-scoped student/profile/history, zones, bracelet reads, camera list/snapshot/stream, agent and attendance-risk reads |
| Principal+   | School-scoped student and bracelet CRUD, bracelet ping, camera register/delete/start/stop |
| Ministry     | `/reports/*` (school-scoped on-demand previews; not persisted/downloadable) |
| Parent       | `/parent/students*` (only through active verified parent/student/school links) |

**Tenant-isolation status:** Student, bracelet, camera, incident, drill, SSI-history, dashboard REST, analytics, report-preview, and parent-summary reads/writes use authenticated school or verified parent/student scope. Dashboard WebSocket, live SSI, unit health/alerts, and process-global runtime settings remain unavailable until their underlying streams, caches, and settings are tenant-partitioned. Dashboard, analytics, and report previews identify seeded demo data as synthetic, not live telemetry. Ministry report previews are generated on demand and are not persisted/downloadable. Static `/units` metadata remains available.

### Security-related settings

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | `change-me-in-production` | **Must** be overridden in production (≥ 32 chars). The app refuses to start otherwise. Generate with `openssl rand -hex 32`. |
| `JWT_ALGORITHM` | `HS256` | Signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime |
| `CORS_ORIGINS` | `http://127.0.0.1:5173,http://localhost:5173` | Comma-separated browser origins allowed by CORS |

---

## 🎓 Student Profile

**Control Panel → Students** lists students with search, grade / section / status filters, and an *Add Student* drawer (principal+). Click a student name or the eye icon to open the profile modal with the tabs **Overview · Attendance · Bracelet · Notifications · Engagement (Unit 15) · Edit** (Edit and activate / delete are principal+).

The modal is backed by `GET /api/v1/students/{student_id}/profile`. It returns school-scoped student, bracelet, attendance, and recipient-validated notification information. Incident-derived safety fields are scoped through school-owned zones.

---

## 📡 API Endpoints

All paths are under `/api/v1`. See the [roles table](#-authentication--roles) for who can call what.

### Health & Auth

| Method | Endpoint       | Description                         |
|--------|----------------|-------------------------------------|
| GET    | `/health`      | Service health check                |
| POST   | `/auth/login`  | OAuth2 password login → JWT         |
| GET    | `/auth/me`     | Current user and role               |

### Dashboard

| Method    | Endpoint              | Description                                    |
|-----------|-----------------------|------------------------------------------------|
| GET       | `/dashboard/summary`  | School-scoped REST summary; demo data clearly labelled |
| GET       | `/dashboard/alerts`   | School-scoped persisted incident alerts |
| GET       | `/dashboard/heatmap`  | School-scoped incident-derived heatmap (not video analytics) |
| GET       | `/dashboard/live`     | School-scoped REST snapshot; not a live camera stream |
| WebSocket | `/dashboard/ws`       | Refused until the stream manager is partitioned by school |



### School Safety Index, Units, Analytics

| Method | Endpoint                | Description                                  |
|--------|-------------------------|----------------------------------------------|
| GET    | `/ssi/live`             | Temporarily unavailable (503) until live signals are school-scoped |
| GET    | `/ssi/history`          | School-scoped historical trend and anomaly summary |
| GET    | `/units`                | Metadata for the system units                |
| GET    | `/units/capture/health` | Temporarily unavailable (503) pending per-school stream health |
| GET    | `/units/alerts/summary` | Temporarily unavailable (503) pending per-school alert queues |
| GET    | `/analytics/overview`   | School-scoped aggregates with demo/unknown provenance labels |

### Reports (Ministry) and Parent Portal

| Method | Endpoint           | Description                             |
|--------|--------------------|-----------------------------------------|
| GET    | `/reports/list`    | School-scoped on-demand preview cards; not persisted |
| GET    | `/reports/stats`   | School-scoped preview statistics; not downloadable artifacts |
| GET    | `/portal/student`  | Legacy portal status; does not grant parent access |

### Parent Identity & Portal (backend API)

| Method | Endpoint | Min. role | Description |
|---|---|---|---|
| POST | `/parent/links` | Principal+ | Verify and create a parent-to-student link within the principal's school |
| DELETE | `/parent/links/{link_id}` | Principal+ | Revoke a link with verifier and timestamp audit |
| GET | `/parent/students` | Parent (exact role) | List only students with active verified links |
| GET | `/parent/students/{student_id}/summary` | Parent (exact role) | Last 7 days of attendance and current-recipient notifications |

Parent accounts are not demo-seeded. A principal must verify the adult against authoritative school records and provision the parent login separately. Parent endpoints do not expose live location, camera frames, or internal safety signals. The React app routes parent-role accounts into a dedicated portal shell connected to these endpoints; parent accounts still require separate provisioning.

### Students, Zones & Bracelets (Control Panel)

| Method | Endpoint                                  | Min. role | Description                                |
|--------|-------------------------------------------|-----------|--------------------------------------------|
| GET    | `/students`                               | Teacher   | List students                              |
| POST   | `/students`                               | Principal | Create a student                           |
| PATCH  | `/students/{student_id}`                  | Principal | Update a student                           |
| DELETE | `/students/{student_id}`                  | Principal | Delete (cascades to bracelet + attendance) |
| GET    | `/students/{student_id}/profile`          | Teacher   | Aggregated student profile                 |
| GET    | `/students/{student_id}/behavioral-history` | Teacher | Unit 15 engagement snapshots               |
| GET    | `/zones`                                  | Teacher   | School zones                               |
| GET    | `/bracelets`                              | Teacher   | List bracelets                             |
| POST   | `/bracelets`                              | Principal | Assign a bracelet to a student             |
| PATCH  | `/bracelets/{bracelet_id}`                | Principal | Update a bracelet                          |
| DELETE | `/bracelets/{bracelet_id}`                | Principal | Remove a bracelet                          |
| POST   | `/bracelets/{bracelet_id}/ping`           | Principal | Gateway heartbeat (zone, battery)          |

### Runtime Settings

| Method | Endpoint     | Min. role | Description                                     |
|--------|--------------|-----------|-------------------------------------------------|
| GET    | `/settings`  | Teacher   | Camera FPS / quality, SSI benchmark, TTL, etc.  |
| PATCH  | `/settings`  | Principal | Change settings live (no restart)               |

### Unit 15 — Pedagogical Agent

| Method | Endpoint                 | Description                                          |
|--------|--------------------------|------------------------------------------------------|
| GET    | `/agent/insights`        | Session engagement, disengagement flags, A/V mismatches |
| POST   | `/agent/feedback`        | Teacher confirmation / correction of a prediction    |
| GET    | `/agent/feedback/metrics`| Self-evaluation metrics                              |
| GET    | `/agent/baselines`       | Daily per-student engagement baselines               |
| GET    | `/agent/recommendations/{student_id}` | Actions informed by history and prior feedback |
| GET    | `/risk/attendance[/{student_id}]` | Teacher+: attendance early-warning risk scores |
| GET    | `/ssi/history`           | Stored SSI history with trend and anomaly days       |

Camera endpoints are listed in [Connecting Real School Cameras](#-connecting-real-school-cameras).

---

## 🧩 15 Integrated Units

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
| 15 | Pedagogical Behavioral Intelligence Agent | Pose-based engagement scoring, Egyptian-Arabic audio context, per-student behavioral memory (nightly baseline harvesting) and a teacher-feedback self-evaluation loop |

---

## 📹 Connecting Real School Cameras

SchoolSmartEYE can ingest live frames from real cameras via RTSP, HTTP MJPEG,
USB webcams, or local video files. All frames pass through the **Arab Data
Governance Layer (Unit 14)** for automatic face anonymization before being
shown or stored.

### 1. Create a `cameras.json` file at the project root

`cameras.json` may contain RTSP credentials, so it is git-ignored. Without it the app starts in demo mode.

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
| GET    | `/api/v1/cameras`                                 | List cameras linked to zones in the authenticated school (teacher+) |
| POST   | `/api/v1/cameras`                                 | Register camera against a school-owned zone (principal+) |
| DELETE | `/api/v1/cameras/{camera_id}`                     | Unregister a camera owned by the authenticated school (principal+) |
| POST   | `/api/v1/cameras/{camera_id}/start`               | Start an owned camera worker (principal+) |
| POST   | `/api/v1/cameras/{camera_id}/stop`                | Stop an owned camera worker (principal+) |
| GET    | `/api/v1/cameras/{camera_id}/snapshot.jpg`        | One-shot JPEG after school membership check (teacher+) |
| GET    | `/api/v1/cameras/{camera_id}/stream.mjpg`         | School-checked MJPEG stream (teacher+) |

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
APP_ENV=development              # "production" enforces a real JWT secret
API_V1_STR=/api/v1
VIDEO_LOG_DIR=./video_logs
VIDEO_TTL_HOURS=72

DATABASE_URL=sqlite:///./schoolsmarteye.db
DB_AUTO_CREATE=true

JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

SEED_DEMO_USERS=true
DEMO_TEACHER_PASSWORD=teacher123
DEMO_PRINCIPAL_PASSWORD=principal123
DEMO_MINISTRY_PASSWORD=ministry123

CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

Camera-related variables are described in the cameras section above.

---

## 🧪 Running Tests

```bash
# All tests (each test gets a fresh in-memory SQLite database — see tests/conftest.py)
pytest -q

# With verbose output
pytest -v tests/

# End-to-end smoke test of the Control Panel API (uses a temporary database)
python scripts/test_control_api.py

# Frontend type-check + production build
cd frontend && npm run build
```

Tests cover: database seeding and persistence, JWT authentication and the role matrix, student CRUD and the profile endpoint, bracelets, verified parent identity and portal authorization, full Alembic migration upgrade, governance layer, health, dashboard, SSI, drill simulation, school-scoped report previews, risk heatmap, school safety index, spatial behavioral memory, attendance-safety integration, collective behavioral coherence, crowd density forecasting and the Unit 15 pedagogical agent.
