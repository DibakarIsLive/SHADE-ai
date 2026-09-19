# SHADE-ai

## Smart Human Activity Detection and Emergency System

SHADE-ai is a Django + React computer-vision monitoring platform for detecting human activity, evaluating temporal context, recording potentially dangerous events, and presenting safety information in a focused dashboard.

> SHADE-ai is a safety-monitoring aid. It is not a medical diagnosis system, a guaranteed security system, or a replacement for human emergency response.

## Current implementation

The repository currently contains the first professional foundation slice:

- Django REST Framework backend under `app/`.
- Django project package under `app/config/` with split settings.
- MongoDB/MongoEngine document boundaries for cameras and emergency events.
- Bounded database health diagnostics that keep the API inspectable when MongoDB is offline.
- Vision interfaces for sources, detection, tracking, posture, activity classification, and temporal fall verification.
- A dedicated monitoring worker boundary so camera processing does not run inside HTTP views.
- React + JSX + Vite dashboard under `web/`.
- Three Makefiles for root, backend (`app/`), and UI (`web/`) workflows.
- Tests for API contracts, temporal verification, and the vision pipeline.

The first runtime mode is intentionally explicit: the dashboard can be explored with a safe synthetic presentation state, while real camera/model adapters are introduced behind the vision interfaces.

## Repository layout

```text
SHADE-ai/
├── app/
│   ├── config/                  # Django project and settings package
│   ├── core/                    # Health, capabilities, and API metadata
│   ├── cameras/                 # Camera document and API boundary
│   ├── events/                  # Emergency event document and API boundary
│   ├── monitoring/              # Monitoring control plane and worker boundary
│   ├── vision/                  # Vendor-neutral computer-vision domain services
│   ├── tests/                   # Backend contract and vision tests
│   ├── Makefile
│   └── requirements.txt
├── web/
│   ├── src/                     # React JSX dashboard
│   └── Makefile
├── docs/                        # Architecture and development documentation
├── Makefile
├── PLAN.md
└── SHADE — Project Specification.md
```

## Quick start

### 1. Prepare dependencies

```bash
cd "/Users/dibakar/Local Documents/Code-Local/Git & Github/Repo/SHADE-ai"
make install
```

### 2. Start MongoDB

Use the MongoDB installation appropriate for the local machine. SHADE-ai will still boot without MongoDB so that health and capability endpoints remain inspectable; persistence endpoints report a degraded state until MongoDB is available.

### 3. Run the API and UI

```bash
make dev
```

Or start each service explicitly:

```bash
make app   # http://127.0.0.1:8000
make ui    # http://127.0.0.1:5173
```

### 4. Run quality gates

```bash
make check
make test
make build
```

## API surface

| Endpoint | Purpose |
| --- | --- |
| `GET /api/` | API metadata and service links |
| `GET /api/health/` | API and bounded MongoDB health report |
| `GET /api/capabilities/` | Implemented, experimental, and planned capabilities |
| `GET /api/cameras/` | List configured camera sources |
| `POST /api/cameras/` | Register a camera configuration |
| `GET /api/events/` | List persisted emergency events |
| `POST /api/events/` | Persist a verified event record |
| `GET /api/monitoring/status/` | Read local monitoring control-plane state |
| `POST /api/monitoring/start/` | Arm monitoring for a camera |
| `POST /api/monitoring/stop/` | Stop the local monitoring intent |
| `ws://127.0.0.1:8000/ws/monitoring/` | Live dashboard event channel boundary |

## Safety and privacy boundaries

- Continuous raw video is not persisted by default.
- Evidence storage is opt-in and retention-limited through environment settings.
- Development notifications use a dry-run adapter unless explicitly configured.
- Event verification is temporal and should not alarm on one uncertain frame.
- Model accuracy claims require a documented, representative evaluation set.
- Real-world emergency workflows require human review, deployment testing, and an independently reviewed notification policy.

See `PLAN.md`, `docs/ARCHITECTURE.md`, and `docs/DEVELOPMENT_GUIDE.md` for the implementation contract.
