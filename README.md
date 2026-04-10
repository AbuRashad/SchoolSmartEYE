# Intelligent School Monitoring System (FastAPI)

Production-oriented FastAPI starter architecture for an intelligent school monitoring platform based on 14 integrated units, including a dedicated Arab Data Governance layer.

## Quick Start

### Backend
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: `http://127.0.0.1:8000/docs`

> **Note:** Copy `.env.example` to `.env` (or leave blank — all settings have defaults).

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Tests
```bash
pytest -q
```

## Project Structure

- `app/main.py` - FastAPI app entrypoint.
- `app/api/v1/` - API routes.
- `app/core/config.py` - Runtime settings.
- `app/core/governance_layer.py` - Arab Data Governance Model implementation.
- `app/units/` - 14 integrated unit placeholders.
- `tests/` - Initial test suite.

## Governance Layer Capabilities

1. Automated data anonymization by blurring detected faces of minors.
2. Strict Time-To-Live (TTL) enforcement for stored video logs.
3. Role-Based Access Control (RBAC) for `Teacher`, `Principal`, and `Ministry` hierarchy.

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: `http://127.0.0.1:8000/docs`

## Run Tests

```bash
pytest -q
```

## Frontend Dashboard

A React + Tailwind operational dashboard is available under `frontend/`.

```bash
cd frontend
npm install
npm run dev
```

The UI includes:

- Sidebar navigation for safety operations modules.
- KPI header with an SSI gauge chart.
- Color-coded live alert feed for coherence ruptures and anomaly alerts.
- SVG floor-plan heatmap with dynamic risk overlays, tooltips, and time slider.
- WebSocket-ready dashboard state hook for real-time backend integration.

## Dashboard API

The frontend dashboard consumes the following backend endpoints:

- `GET /api/v1/dashboard/summary` - School name, SSI, benchmark, and connection state.
- `GET /api/v1/dashboard/alerts` - Live alert feed items for coherence, anomaly, and density streams.
- `GET /api/v1/dashboard/heatmap` - Frontend-ready heatmap cells with `x`, `y`, `time_slot`, `risk_intensity`, `reason`, and `label`.
- `WS /api/v1/dashboard/ws` - Event-driven snapshot stream for dashboard refresh events.

The WebSocket sends an initial snapshot on connect and can return a fresh payload when the client sends `refresh`.
