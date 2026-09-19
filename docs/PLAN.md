# SHADE-ai Project Plan

## Smart Human Activity Detection and Emergency System

> **Planning status:** Architecture, foundation, and first dashboard slice implemented
>
> **Current phase:** Phase 4 — Domain API and local dashboard foundation
>
> **Implementation status:** Backend contracts, MongoEngine documents, vision boundaries, monitoring control plane, and React dashboard are implemented; production camera/model adapters remain intentionally deferred

---

## 1. Document Purpose

This document defines how SHADE-ai will be built from the existing project specification while following the repository conventions demonstrated by PhishGuard and VisionCore.

The plan intentionally separates:

- What the first usable version must do.
- What belongs in later phases.
- What must be measured before making performance claims.
- Which components own computer vision, event processing, persistence, notifications, and user-interface responsibilities.
- How every phase will be tested and accepted.

The first implementation target is a local, single-camera monitoring system that can detect people, track them across frames, estimate posture, identify a potential fall, verify that event using temporal context, save the event, and show it in a React dashboard.

SHADE-ai is a safety-monitoring aid. It must not be presented as a medical diagnosis system, a guaranteed security system, or a replacement for human emergency response.

---

## 2. Project Definition

### 2.1 One-line definition

> SHADE-ai is a Django and React-based computer-vision monitoring platform that detects human activity, analyzes temporal context, verifies potentially dangerous situations, records emergency events, and notifies designated responders.

### 2.2 Core design principle

```text
OBSERVE → ANALYZE → VERIFY → RESPOND
```

The system must not follow this unsafe pattern:

```text
ONE UNCERTAIN PREDICTION → IMMEDIATE ALARM
```

Every emergency decision should combine multiple observations where practical:

- Detection confidence.
- Tracking continuity.
- Body posture.
- Movement and movement speed.
- Previous activity states.
- Duration of the suspicious condition.
- A configurable rule threshold.
- A cooldown or deduplication policy.

### 2.3 First target scenario

The first complete scenario is fall detection:

```text
Webcam
  ↓
OpenCV frame capture
  ↓
Person detection
  ↓
Person tracking
  ↓
Pose and posture analysis
  ↓
Temporal activity history
  ↓
Fall verification
  ↓
Emergency event
  ↓
Dashboard update
  ↓
Optional development-safe email alert
```

---

## 3. Conventions Adopted from Existing Projects

### 3.1 From PhishGuard

SHADE-ai will adopt these proven patterns:

- `app/` for the Django backend and `web/` for the browser application.
- Django settings separated into `base.py`, `development.py`, and `production.py`.
- Django REST Framework for the HTTP API.
- MongoDB through MongoEngine for application history and event documents.
- Environment-based configuration with `.env.example` and ignored local `.env` files.
- Root and service-level `Makefile` commands.
- Focused tests under the API project.
- Explicit health and capability endpoints.
- Best-effort handling of runtime dependencies during intentional diagnostic mode.
- Documentation that distinguishes implemented behavior from future work.
- React with JavaScript and JSX rather than TypeScript or TSX.
- A visible safety and limitation boundary instead of unsupported accuracy claims.

### 3.2 From VisionCore

SHADE-ai will also adopt the useful architectural patterns from VisionCore:

- A dedicated vision/service layer instead of putting model logic inside API views.
- Lazy model loading and a model manager abstraction.
- Clear separation between model artifacts, inference services, API views, and database records.
- Setup, maintenance, and test scripts grouped by responsibility.
- Model metadata and evaluation evidence stored separately from executable code.
- Explicit test and stress-test workflows.
- Runtime logging that explains routing and model decisions.
- A staged roadmap with completion gates.

The frontend will remain **plain JavaScript and JSX**. VisionCore's TypeScript/TSX convention will not be copied into SHADE-ai.

### 3.3 Naming rules

The project will follow `Resources/ProjectNaming.md`:

- Project and general directory names: `kebab-case` where possible.
- General file names: `kebab-case`.
- React component files: `PascalCase.jsx`.
- React component names: `PascalCase`.
- JavaScript variables and functions: `camelCase`.
- Python modules and packages: `snake_case` because that is the Python ecosystem convention.
- True constants only: `UPPER_SNAKE_CASE`.
- Hooks: `useSomething.js`.
- Tests: responsibility-based names such as `fall-verification.test.js` or `test_temporal_engine.py`.
- API paths: resource nouns, with HTTP methods describing the action.
- Git branches: `type/kebab-case`.
- Commits: `type: action-oriented description`.

---

## 4. Technology Decisions

### 4.1 Backend

| Technology               | Role                                                          |
| ------------------------ | ------------------------------------------------------------- |
| Python 3.11+             | Runtime and computer-vision services                          |
| Django 4.2+              | Web framework and application configuration                   |
| Django REST Framework    | JSON API and request validation                               |
| Django Channels          | WebSocket delivery for live dashboard state and events        |
| MongoDB                  | Event, camera, monitoring-session, and alert history          |
| MongoEngine              | MongoDB document layer, consistent with the existing projects |
| OpenCV                   | Camera input, frame processing, overlays, and image utilities |
| NumPy                    | Numerical operations and normalized vision data               |
| YOLO-compatible detector | Person detection and, where suitable, pose inference          |
| Pose-estimation adapter  | Normalized human keypoints and posture signals                |
| Python logging           | Structured runtime and diagnostic logs                        |

The exact detector and pose package versions will be selected during implementation after checking compatibility, model licensing, CPU/GPU behavior, and local performance. The rest of the application must depend on interfaces rather than on a vendor-specific model API.

### 4.2 Frontend

| Technology                                    | Role                                                          |
| --------------------------------------------- | ------------------------------------------------------------- |
| React                                         | Dashboard and monitoring interface                            |
| Vite                                          | Development server and production build                       |
| JavaScript                                    | Frontend application language                                 |
| JSX                                           | React component markup                                        |
| React Router                                  | Page navigation when multiple pages are introduced            |
| Fetch API                                     | HTTP communication                                            |
| WebSocket API                                 | Real-time monitoring updates                                  |
| CSS or a deliberately selected styling system | Layout, state colors, responsive dashboard, and accessibility |

No TypeScript, TSX, or generated type layer will be introduced unless the project direction is explicitly changed later.

### 4.3 Development and deployment data stores

- MongoDB is the primary application data store, matching the existing projects.
- A local MongoDB instance is the normal development dependency.
- The API will use a bounded startup check and an explicit diagnostic bypass, following PhishGuard's operational boundary.
- A local in-memory Channels layer is acceptable for a single-process prototype.
- Redis will be introduced only when multi-process or multi-camera real-time delivery requires it.
- Continuous raw video will not be stored by default.
- Event metadata and optional evidence snapshots will use configurable retention rules.

### 4.4 External notification providers

Email is the first outbound notification channel. SMS, push notifications, messaging platforms, and hardware alarms are later adapters.

Development defaults must use one of these safe modes:

- Console email backend.
- Explicit dry-run notification adapter.
- A test recipient configured through environment variables.

Real emergency recipients must never be embedded in source code or used in automated tests.

---

## 5. Scope Boundaries

### 5.1 MVP capabilities

The minimum complete version will provide:

- One local webcam source.
- A camera configuration record.
- Start and stop monitoring from a controlled local workflow.
- Person detection in sampled frames.
- Stable track identifiers during a monitoring session.
- Basic pose/posture signals.
- Configurable activity categories:
  - `standing`
  - `walking`
  - `sitting`
  - `running`
  - `lying`
  - `falling`
  - `motionless`
- A bounded temporal history per tracked person.
- Fall verification using a sequence of observations instead of one frame.
- Emergency event creation with confidence, severity, reason, camera, timestamp, and status.
- MongoDB persistence for cameras, activity summaries, emergency events, and alerts.
- A REST API for dashboard data and event history.
- A real-time dashboard update path using WebSockets.
- A visible live monitoring view or annotated preview appropriate for the local MVP.
- Dashboard notifications for newly confirmed events.
- Development-safe email notification support after the event pipeline is stable.
- Acknowledge, investigate, resolve, and false-positive event states.
- Focused backend tests, frontend build verification, and synthetic temporal tests.

### 5.2 Deliberately deferred capabilities

These are not part of the first coding phase:

- Multiple physical cameras.
- Cloud camera ingestion.
- Production-scale distributed video processing.
- Medical diagnosis or health conclusions.
- Face recognition or identity recognition.
- Emotion recognition.
- Continuous cloud video upload.
- Guaranteed detection of every fall or dangerous event.
- Automatic contact with emergency services.
- SMS or push notifications before email and dashboard behavior are verified.
- Fighting recognition before the fall pipeline and temporal engine are stable.
- Restricted-area rules before camera regions can be configured and tested.
- Mobile applications.
- Hardware sirens and IoT integration.
- Production deployment claims.

---

## 6. Proposed Repository Structure

The specification uses `backend/` and `frontend/` as conceptual names. SHADE-ai will use the preferred project-level names `app/` and `web/`.

```text
SHADE-ai/
│
├── app/
│   ├── config/
│   │   ├── settings/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   └── production.py
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   │
│   ├── cameras/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── tests/
│   │
│   ├── activities/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── tests/
│   │
│   ├── emergencies/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── tests/
│   │
│   ├── notifications/
│   │   ├── adapters/
│   │   │   ├── base.py
│   │   │   ├── console.py
│   │   │   └── email.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── tests/
│   │
│   ├── monitoring/
│   │   ├── consumers.py
│   │   ├── routing.py
│   │   ├── services.py
│   │   ├── management/
│   │   │   └── commands/
│   │   │       └── run-monitor.py
│   │   └── tests/
│   │
│   ├── vision/
│   │   ├── camera/
│   │   │   ├── camera_source.py
│   │   │   ├── frame_processor.py
│   │   │   └── video_stream.py
│   │   ├── detection/
│   │   │   ├── detector.py
│   │   │   └── person_detector.py
│   │   ├── tracking/
│   │   │   ├── person_tracker.py
│   │   │   └── track_state.py
│   │   ├── pose/
│   │   │   ├── pose_estimator.py
│   │   │   └── posture_analyzer.py
│   │   ├── activity/
│   │   │   ├── activity_classifier.py
│   │   │   └── activity_rules.py
│   │   ├── temporal/
│   │   │   ├── history_buffer.py
│   │   │   └── temporal_analyzer.py
│   │   ├── event_engine/
│   │   │   ├── emergency_verifier.py
│   │   │   └── event_state.py
│   │   ├── model_manager.py
│   │   ├── services.py
│   │   ├── types.py
│   │   └── tests/
│   │
│   ├── ml_models/
│   │   ├── README.md
│   │   └── .gitkeep
│   │
│   ├── tests/
│   │   ├── integration/
│   │   └── test_settings.py
│   │
│   ├── logs/
│   ├── media/
│   ├── manage.py
│   ├── requirements/
│   │   ├── base.txt
│   │   ├── development.txt
│   │   └── production.txt
│   ├── .env.example
│   └── Makefile
│
├── web/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   └── ui/
│   │   ├── features/
│   │   │   ├── cameras/
│   │   │   ├── dashboard/
│   │   │   ├── emergencies/
│   │   │   └── monitoring/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── utils/
│   │   ├── App.jsx
│   │   ├── global.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── Makefile
│
├── docs/
│   ├── architecture.md
│   ├── api-reference.md
│   ├── development-guide.md
│   ├── model-evaluation.md
│   ├── privacy-and-safety.md
│   ├── testing-guide.md
│   └── roadmap.md
│
├── scripts/
│   ├── setup/
│   ├── test/
│   └── maintenance/
│
├── tests/
│   ├── integration/
│   └── e2e/
│
├── .gitignore
├── LICENSE
├── Makefile
├── PLAN.md
└── README.md
```

### 6.1 Structure rules

- Keep long-running vision processing out of request views.
- Keep model loading and inference inside `vision/`.
- Keep database access and event orchestration inside application services.
- Keep serializers responsible for request and response contracts.
- Keep API views thin.
- Keep frontend files grouped by feature instead of creating one unbounded components directory.
- Keep generated media, logs, model weights, local environments, and secrets out of Git.
- Treat `app/ml_models/` as an artifact boundary. Every committed model artifact must have provenance, license information, version metadata, and evaluation evidence.

---

## 7. High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│ React + Vite + JavaScript/JSX (`web/`)                              │
│ Dashboard · live monitor · camera settings · event history          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP JSON + WebSocket events
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Django + Django REST Framework (`app/`)                            │
│ serializers · views · URLs · health · camera/event APIs            │
└───────────────┬───────────────────────┬─────────────────────────────┘
                │                       │
                ▼                       ▼
┌──────────────────────────┐  ┌──────────────────────────────────────┐
│ MongoDB + MongoEngine    │  │ Monitoring worker                     │
│ cameras · activities     │  │ camera source · OpenCV · vision       │
│ emergencies · alerts     │  │ temporal engine · event publisher     │
└──────────────────────────┘  └───────────────┬──────────────────────┘
                                               │
                                               ▼
                                  ┌────────────────────────┐
                                  │ Vision pipeline         │
                                  │ detect → track → pose  │
                                  │ → classify → verify    │
                                  └────────────┬───────────┘
                                               │
                                               ▼
                                  ┌────────────────────────┐
                                  │ Alert adapters          │
                                  │ dashboard · console    │
                                  │ email · future SMS     │
                                  └────────────────────────┘
```

### 7.1 Processing ownership

| Responsibility                                            | Owning module                                   |
| --------------------------------------------------------- | ----------------------------------------------- |
| Open webcam, RTSP source, or video file                   | `vision.camera`                                 |
| Resize, sample, and timestamp frames                      | `vision.camera.frame_processor`                 |
| Detect people                                             | `vision.detection`                              |
| Maintain person IDs                                       | `vision.tracking`                               |
| Generate keypoints                                        | `vision.pose`                                   |
| Convert keypoints and movement into activity observations | `vision.activity`                               |
| Maintain short per-person histories                       | `vision.temporal`                               |
| Decide whether a danger is verified                       | `vision.event_engine`                           |
| Persist domain events                                     | `activities`, `emergencies`, and their services |
| Publish live state                                        | `monitoring` and Channels consumers             |
| Send notifications                                        | `notifications`                                 |
| Serve JSON contracts                                      | Django REST Framework views and serializers     |
| Render dashboard                                          | React feature components                        |

### 7.2 Worker boundary

The camera loop must not run inside a normal HTTP request.

The local development workflow will use a dedicated Django management command, conceptually:

```bash
python manage.py run_monitor --camera-id <camera-id>
```

The worker will:

1. Open the configured source.
2. Read frames at a controlled rate.
3. Run the vision pipeline on selected frames.
4. Maintain in-memory track and temporal state.
5. Persist event transitions and summaries rather than every frame.
6. Publish live state and confirmed events.
7. Shut down cleanly when requested.

A later multi-camera deployment can move this worker into a separate process or service without changing the detector, activity, or emergency interfaces.

---

## 8. Vision Pipeline Design

### 8.1 Camera source abstraction

Create a source interface that can support:

- Local webcam.
- Video file for repeatable testing.
- RTSP/IP camera in a later phase.

Each source should expose frames with:

```python
{
    "frame": frame,
    "timestamp": timestamp,
    "frame_index": frame_index,
    "source_id": source_id,
}
```

The first source will be a local webcam. The video-file source is important for deterministic regression tests and should be added early, even if it is not exposed as a public feature.

### 8.2 Frame processing

The frame processor will own:

- Resolution normalization.
- Frame sampling and target FPS.
- Basic color and shape conversion.
- Timestamp assignment.
- Optional privacy masking before preview publication.
- Graceful handling of dropped or unreadable frames.

The processor must not silently create unbounded memory usage or write continuous video files.

### 8.3 Person detection

The detector adapter will return a normalized structure rather than exposing raw vendor output to the rest of the application:

```json
{
  "class_name": "person",
  "confidence": 0.94,
  "bounding_box": {
    "left": 120,
    "top": 80,
    "right": 340,
    "bottom": 520
  }
}
```

The first version will ignore non-person detections. The detector threshold, input size, and frame interval will be configurable.

The model manager will:

- Load the detector lazily.
- Cache it for the monitoring process.
- Expose model metadata and readiness status.
- Fail with a useful diagnostic when a model artifact is missing.
- Keep model paths and thresholds outside API views.

### 8.4 Person tracking

Tracking is required because an emergency decision depends on a sequence belonging to the same person.

The tracker will:

- Assign a temporary `track_id`.
- Match detections across adjacent frames.
- Preserve short-term state through brief missed detections.
- Expire tracks after a configurable absence period.
- Record only bounded in-memory state.

The tracker must not be treated as identity recognition. A `track_id` identifies a temporary trajectory during one monitoring session, not a real person.

### 8.5 Pose and posture

The pose adapter will normalize keypoints into a stable internal representation:

```json
{
  "keypoints": {
    "nose": { "x": 0.5, "y": 0.12, "confidence": 0.91 },
    "left_shoulder": { "x": 0.42, "y": 0.29, "confidence": 0.88 },
    "right_shoulder": { "x": 0.58, "y": 0.3, "confidence": 0.9 },
    "left_hip": { "x": 0.44, "y": 0.62, "confidence": 0.84 },
    "right_hip": { "x": 0.57, "y": 0.63, "confidence": 0.86 }
  },
  "posture": "upright",
  "quality": 0.87
}
```

The rest of the system will not depend directly on a particular keypoint library. The adapter boundary makes it possible to compare a YOLO pose model and a MediaPipe-based implementation without rewriting the temporal engine.

### 8.6 Activity recognition

The first activity recognizer will be a transparent feature-and-rule baseline. It will use:

- Bounding-box aspect ratio.
- Center-point movement.
- Estimated vertical velocity.
- Body orientation.
- Shoulder-to-hip geometry.
- Keypoint confidence.
- Recent activity history.
- Time spent in a posture.

It will produce an observation such as:

```json
{
  "track_id": 17,
  "activity": "falling",
  "confidence": 0.86,
  "posture": "horizontal",
  "movement_speed": 1.42,
  "timestamp": "2026-09-18T12:00:00Z"
}
```

This rule-based baseline is intentional. It will make the first system inspectable and testable before a learned temporal activity model is considered.

### 8.7 Temporal analysis

Maintain a bounded history per `track_id` using a time-based buffer or deque.

Example:

```python
activity_history = [
    "standing",
    "walking",
    "falling",
    "lying",
    "motionless",
]
```

The temporal analyzer will calculate:

- Previous activities.
- Activity transition order.
- Time spent in each state.
- Recent movement magnitude.
- Missing-observation gaps.
- Whether the history is long and reliable enough for a decision.

No emergency decision should be made from a history containing only one uncertain observation.

### 8.8 Emergency verification

Initial fall verification will use a configurable rule similar to:

```text
IF
  a person was upright or moving
  AND a rapid downward posture transition is observed
  AND horizontal posture is sustained
  AND movement remains low for the configured duration
  AND the combined confidence is above the configured threshold
  AND no active cooldown exists
THEN
  create one fall emergency event
```

The verifier will return both the decision and its reasons:

```json
{
  "confirmed": true,
  "emergency_type": "fall",
  "severity": "critical",
  "confidence": 0.91,
  "reasons": [
    "upright-to-horizontal transition detected",
    "rapid downward movement observed",
    "low movement sustained for 7 seconds"
  ]
}
```

### 8.9 Event deduplication and cooldown

The event engine must prevent one continuing fall from creating one database record and one email per frame.

Required safeguards:

- One active emergency per camera, person track, and event type during a cooldown window.
- Idempotent event creation where practical.
- A clear transition from potential danger to confirmed danger.
- A clear resolution or expiration path.
- Logging when a duplicate event is suppressed.

---

## 9. Domain Data Design

The exact document implementation will be finalized during Phase 4, but the initial domain model is:

### 9.1 Camera

```text
camera_id
name
location
source_type
source_uri_or_index
status
enabled
configuration
created_at
updated_at
```

`source_uri_or_index` must be handled carefully. Credentials embedded in RTSP URLs must not be returned in API responses or logs.

### 9.2 Monitoring session

```text
session_id
camera_id
started_at
ended_at
status
configuration_snapshot
frames_processed
frames_dropped
people_seen
```

A session separates one temporary set of track IDs from another.

### 9.3 Activity event

```text
activity_event_id
camera_id
session_id
track_id
activity
confidence
severity
started_at
ended_at
duration_seconds
summary
```

The system will not store a database row for every analyzed frame. Activity events represent meaningful transitions or bounded summaries.

### 9.4 Emergency event

```text
emergency_event_id
activity_event_id
camera_id
session_id
track_id
emergency_type
confidence
severity
reasons
evidence_snapshot_path
status
detected_at
acknowledged_at
resolved_at
resolution_note
```

Initial statuses:

```text
unresolved
acknowledged
resolved
false_positive
```

### 9.5 Alert

```text
alert_id
emergency_event_id
channel
recipient_reference
status
sent_at
failure_reason
provider_message_id
created_at
```

Recipients and provider details must be redacted from normal logs. The alert record should make retries and failures visible without exposing secrets.

### 9.6 Configuration and activity rules

Thresholds should be versioned or captured in the monitoring session so that a later investigation can determine which rules produced an event.

Examples:

```text
person_detection_threshold
pose_confidence_threshold
fall_confidence_threshold
motionless_duration_seconds
track_expiry_seconds
event_cooldown_seconds
evidence_capture_enabled
evidence_retention_days
```

---

## 10. Backend API Plan

The API will use resource-oriented paths and keep views thin.

### 10.1 System endpoints

```text
GET /                         API root and service metadata
GET /api/health/              API, database, worker, and model status
GET /api/capabilities/       Implemented and deferred capabilities
```

### 10.2 Camera endpoints

```text
GET    /api/cameras/                  List cameras
POST   /api/cameras/                  Create a camera configuration
GET    /api/cameras/{camera_id}/      Retrieve one camera
PATCH  /api/cameras/{camera_id}/      Update camera configuration
DELETE /api/cameras/{camera_id}/      Remove a camera configuration
GET    /api/cameras/{camera_id}/status/   Current worker/source status
GET    /api/cameras/{camera_id}/stream/   Local preview stream boundary
POST   /api/cameras/{camera_id}/sessions/ Create a monitoring session
```

The session creation endpoint represents starting a monitoring session without placing a verb such as `start-camera` in the resource path.

### 10.3 Activity endpoints

```text
GET /api/activity-events/                         Filterable activity history
GET /api/activity-events/{activity_event_id}/     Activity event detail
```

Filters will be added for camera, activity, severity, time range, and session after the basic contract is stable.

### 10.4 Emergency endpoints

```text
GET   /api/emergency-events/                         List emergency events
GET   /api/emergency-events/{emergency_event_id}/     Emergency detail
PATCH /api/emergency-events/{emergency_event_id}/     Acknowledge, resolve, or mark false positive
GET   /api/emergency-events/{emergency_event_id}/alerts/ Alert delivery history
```

### 10.5 Dashboard endpoint

```text
GET /api/dashboard/summary/     Current counts, active cameras, and recent events
```

This endpoint is a read model for the dashboard and must not contain model inference logic.

### 10.6 WebSocket channels

```text
/ws/dashboard/
/ws/cameras/{camera_id}/
```

Initial message types:

```text
monitoring_status
frame_metadata
activity_update
emergency_created
emergency_updated
alert_updated
worker_error
```

The browser must be able to reconnect and request a fresh REST snapshot after reconnecting. WebSockets are an update channel, not the only source of truth.

---

## 11. React Dashboard Plan

### 11.1 Initial pages

```text
pages/
├── Home.jsx
├── Monitoring.jsx
├── Cameras.jsx
├── Emergencies.jsx
└── Settings.jsx
```

The first implementation may begin with `Home.jsx` and `Monitoring.jsx` only, but the boundaries should not require a rewrite when event history and camera management are added.

### 11.2 Feature areas

```text
features/
├── cameras/
│   ├── CameraCard.jsx
│   ├── CameraForm.jsx
│   └── camera-api.js
├── dashboard/
│   ├── ActivitySummary.jsx
│   ├── EmergencyBanner.jsx
│   ├── PeopleCountCard.jsx
│   └── dashboard-api.js
├── emergencies/
│   ├── EmergencyDetails.jsx
│   ├── EmergencyTable.jsx
│   └── emergency-api.js
└── monitoring/
    ├── ActivityTimeline.jsx
    ├── LiveCameraPanel.jsx
    ├── MonitoringControls.jsx
    └── monitoring-api.js
```

### 11.3 Frontend behavior

The dashboard will provide:

- Live camera or annotated preview.
- Current monitoring status.
- Number of people currently tracked.
- Current activity by track.
- Clear normal, warning, high, and critical visual states.
- A high-visibility emergency banner.
- Recent emergency history.
- Event detail and evidence metadata where configured.
- Acknowledge and resolve controls.
- Connection and worker-health indicators.
- A visible statement that the system is an assistive monitoring tool.

### 11.4 Frontend state boundaries

- Fetch initial state through service modules.
- Keep API calls out of presentational components.
- Use custom hooks for camera state, dashboard state, emergency history, and WebSocket connection state.
- Show stale-data and disconnected states explicitly.
- Never make a red visual state imply that an emergency is confirmed unless the backend sends a confirmed emergency event.

---

## 12. Privacy, Safety, and Security Requirements

These requirements are part of the architecture, not a final cleanup task.

### 12.1 Privacy

- Process frames locally wherever practical.
- Do not persist continuous raw video by default.
- Store event metadata instead of full recordings whenever possible.
- Make evidence snapshots opt-in and retention-controlled.
- Provide a cleanup command for expired evidence.
- Avoid face recognition and identity inference.
- Do not include raw frames in normal application logs.
- Document which data is retained and for how long.

### 12.2 Security

- Keep secrets in environment variables.
- Never expose camera credentials in serialized responses.
- Restrict CORS to configured development or production origins.
- Add authentication before exposing the dashboard beyond a trusted local machine.
- Add authorization before allowing event resolution or camera configuration changes.
- Validate uploaded or configured sources.
- Avoid arbitrary filesystem paths supplied directly by API clients.
- Limit event and history query sizes.
- Add rate limits to externally reachable endpoints.
- Use secure transport in deployment environments.

### 12.3 Emergency-safety boundary

- Dashboard alerts are not proof that an emergency exists.
- Email delivery is not proof that a recipient saw or acted on an alert.
- The system must expose confidence, reasons, timestamp, camera, and status.
- Every notification must be traceable to one emergency event.
- Development mode must not send real alerts accidentally.
- The project documentation must not claim guaranteed recall, precision, or response time without measured evidence.

---

## 13. Development Phases

## Phase 0 — Planning and repository foundation

### Objective

Create a reproducible project foundation and establish the contracts required for the monitoring pipeline.

### Work

- Keep `PLAN.md` as the implementation reference.
- Completed: root, `app/`, and `web/` scaffolding with three Makefiles.
- Completed: split Django settings, environment loading, logging, and degraded health checks.
- Completed: MongoEngine camera/event documents and API contract tests.
- Completed: vendor-neutral vision contracts, temporal fall verification, and worker boundary.
- Completed: React/JSX dashboard with presentation fallback and monitoring controls.
- Create the `app/`, `web/`, `docs/`, `scripts/`, and test boundaries when coding begins.
- Add root and service Makefiles.
- Add `.gitignore` rules for environments, logs, media, evidence, model weights, caches, and secrets.
- Add Django settings split and `.env.example`.
- Add baseline README sections only when implementation begins.
- Add a health endpoint and capability boundary before feature work expands.

### Completion gate

- [x] Python and Node prerequisites are documented.
- [x] The Django project starts with the intended settings module.
- [x] The React/Vite project builds.
- [x] No generated files or secrets are committed.
- [x] `make check`, `make test`, and `make build` have defined behavior.

---

## Phase 1 — Camera and OpenCV foundation

### Objective

Read a local webcam and a repeatable video file without the API or database owning the frame loop.

### Work

- Implement camera source interfaces.
- Add local webcam capture.
- Add video-file capture for tests.
- Add frame sampling, timestamps, and safe shutdown.
- Add a basic annotated preview or local diagnostic output.
- Record frame-processing metrics in memory and logs.

### Completion gate

- Webcam capture starts and stops cleanly.
- Video-file processing is deterministic enough for repeatable tests.
- Unavailable cameras produce a useful error.
- Processing does not create unbounded memory or disk usage.
- No emergency event is created yet.

---

## Phase 2 — Detection, tracking, and pose adapters

### Objective

Turn frames into stable, normalized person observations.

### Work

- Add lazy detector loading.
- Add person-only detection filtering.
- Add tracker integration.
- Add normalized keypoint and posture adapters.
- Add model readiness and model metadata reporting.
- Add mock detector, tracker, and pose implementations for tests.
- Add model artifact documentation and license review notes.

### Completion gate

- A frame produces a normalized detection contract.
- Consecutive detections can retain a temporary track ID.
- Keypoint data is normalized independently of the model vendor.
- Missing models fail clearly rather than crashing the Django API silently.
- Unit tests run without a camera or downloaded model.

---

## Phase 3 — Activity and temporal analysis

### Objective

Convert person observations into explainable activities and short histories.

### Work

- Implement posture features.
- Implement movement and velocity features.
- Implement the initial activity rules.
- Add per-track bounded histories.
- Add activity transition handling.
- Add motionless-duration measurement.
- Add synthetic sequences for standing, walking, sitting, lying, and falling.

### Completion gate

- Activity observations include activity, confidence, timestamp, and track ID.
- Histories expire correctly when tracks disappear.
- One frame alone cannot confirm an emergency.
- Synthetic sequences produce predictable rule outcomes.
- Ambiguous or low-quality observations remain non-confirmed.

---

## Phase 4 — Django domain model and REST API

### Objective

Persist cameras, sessions, activity events, emergency events, and alerts through a documented API.

### Work

- Configure MongoDB and MongoEngine.
- Add bounded MongoDB startup diagnostics.
- Add explicit `--force` diagnostic behavior where required.
- Implement domain documents and indexes.
- Implement serializers and resource endpoints.
- Add health and capabilities responses.
- Add event filtering and pagination after the base contract works.
- Keep views thin and service logic testable without live MongoDB.

### Completion gate

- API root and health endpoints work.
- Camera configuration can be created and read.
- Activity and emergency event contracts are documented.
- Valid events can be persisted when MongoDB is available.
- Persistence failures are visible and do not corrupt the in-memory decision path.
- Normal startup and diagnostic startup behavior are documented.

---

## Phase 5 — Monitoring worker and event integration

### Objective

Connect the vision pipeline to the domain services without putting the camera loop in HTTP requests.

### Work

- Implement the monitoring management command.
- Create monitoring sessions.
- Connect detection, tracking, pose, activity, temporal, and verification services.
- Persist activity transitions and confirmed emergencies.
- Add duplicate suppression and cooldowns.
- Publish worker status and event updates.
- Add graceful stop and restart behavior.

### Completion gate

- A local webcam session can run through the complete pipeline.
- A synthetic or authorized recorded fall sequence can create one emergency event.
- One continuing event does not create repeated records per frame.
- Worker crashes produce a visible status instead of a permanently healthy dashboard.
- The API remains responsive while monitoring runs.

---

## Phase 6 — Real-time dashboard

### Objective

Give an operator a clear interface for live monitoring and emergency review.

### Work

- Add dashboard pages and feature components.
- Add REST data services.
- Add Channels consumers and WebSocket routing.
- Add reconnect and stale-data handling.
- Add live activity summaries.
- Add emergency banner, event list, and event detail views.
- Add the first local camera preview path.
- Add responsive layout and accessible status indicators.

### Completion gate

- Dashboard loads from the API.
- Current activity updates without a manual refresh.
- Confirmed emergency events appear promptly and visibly.
- Reconnecting the browser restores a current REST snapshot.
- Disconnected worker, disconnected API, and disconnected WebSocket states are distinguishable.
- `npm run build` succeeds.

---

## Phase 7 — Alert engine and event workflow

### Objective

Make confirmed events actionable without creating unsafe or noisy notification behavior.

### Work

- Implement dashboard alert records.
- Implement console/dry-run notifications.
- Implement email adapter.
- Add notification status and failure recording.
- Add idempotent delivery keys or equivalent duplicate protection.
- Add acknowledge, resolve, and false-positive workflows.
- Add configurable recipient references and development safeguards.

### Completion gate

- A confirmed event can produce one dashboard alert.
- A dry-run email can be inspected without contacting a real recipient.
- Email failures are recorded without deleting the emergency event.
- Acknowledgement and resolution are visible in the dashboard and API.
- Duplicate notification attempts are controlled.

---

## Phase 8 — Evaluation, hardening, and documentation

### Objective

Measure the system honestly and make its limitations understandable.

### Work

- Build an authorized, labeled test-clip set.
- Test normal activities and fall-like activities separately.
- Measure false positives and false negatives by scenario.
- Measure end-to-end processing latency and resource usage.
- Tune thresholds using a documented validation set.
- Add model metadata and evaluation reports.
- Add privacy and retention cleanup tests.
- Add API and dashboard screenshots only after behavior is stable.
- Update README and documentation to match the implementation.

### Completion gate

- Every published metric has a dataset, date, command, and evaluation definition.
- Thresholds are documented and reproducible.
- Known failure modes are listed.
- No documentation describes future features as implemented.
- `make ci` and the manual monitoring smoke test pass.

---

## Phase 9 — Future extensions

Potential later work, only after the earlier gates pass:

- Multi-camera monitoring.
- RTSP/IP camera support.
- Redis-backed multi-process Channels deployment.
- Fighting and aggressive-motion analysis.
- Restricted-area polygons and configurable zones.
- SMS and push adapters.
- Event evidence clips with strict retention controls.
- Authentication, roles, and audit history.
- Hardware siren or ESP32 integration.
- Cloud deployment and operational monitoring.
- A learned temporal activity model evaluated against a labeled dataset.

Each extension requires its own implementation, tests, documentation, and acceptance criteria.

---

## 14. Verification Strategy

### 14.1 Backend unit tests

Tests should cover:

- Camera source lifecycle.
- Frame sampling and timestamp behavior.
- Detection normalization.
- Track matching and expiration.
- Keypoint normalization.
- Posture calculations.
- Activity rules.
- Temporal sequence handling.
- Fall verification.
- Confidence and severity boundaries.
- Cooldown and duplicate suppression.
- Event serialization.
- Notification adapter behavior.
- Configuration validation.

### 14.2 Backend integration tests

Tests should cover:

- API root and health endpoints.
- Camera CRUD contract.
- Activity event responses.
- Emergency event status transitions.
- Dashboard summary response.
- MongoDB persistence with controlled test data.
- WebSocket message shapes.
- Worker status publication.

### 14.3 Vision regression tests

Do not require a physical camera in CI. Use:

- Synthetic detections.
- Synthetic keypoints.
- Short authorized video files.
- Stored expected activity transitions.
- Mock model outputs.

A separate model smoke-test command may run real inference locally when the required model artifact is installed.

### 14.4 Frontend verification

Initial checks:

```bash
npm run build
```

Manual checks:

- Dashboard loading state.
- API unavailable state.
- Worker unavailable state.
- WebSocket reconnect state.
- Normal activity display.
- Emergency banner display.
- Event acknowledgement and resolution.
- Empty history.
- Long event reason text without clipping.
- Natural page scrolling on small screens.

Later checks may add JavaScript component tests and browser end-to-end tests.

### 14.5 Full verification workflow

The root project should eventually provide:

```bash
make doctor
make check
make test
make build
make ci
```

Before a milestone is considered complete:

```bash
python3 -m compileall -q app
npm run build --prefix web
git diff --check
```

The exact commands will be finalized with the first implementation scaffold.

---

## 15. Development Commands to Provide

The command surface should resemble the existing projects while using the `app/` backend directory:

```text
make install             Install backend and web dependencies
make setup-env           Create local environment files from templates
make doctor              Inspect Python, Node, MongoDB, and model prerequisites
make dev                 Start backend and web development services
make app                  Start the backend without opening the browser
make web-only            Start the web client and open the frontend URL
make monitor             Start a local monitoring worker
make check               Run Django/system checks
make test                Run backend tests
make build               Build the React application
make health              Call the API health endpoint
make ci                  Run checks, tests, and frontend build
make clean-cache         Remove safe generated caches
```

The frontend development command may open the browser automatically, as in PhishGuard. Starting the API or monitoring worker must not unexpectedly open a browser window.

---

## 16. Environment Configuration Plan

The initial `.env.example` should document values similar to:

```text
DJANGO_ENV=development
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

MONGODB_URI=mongodb://127.0.0.1:27017
MONGODB_DATABASE=shade_ai
MONGODB_SERVER_SELECTION_TIMEOUT_MS=2000
MONGODB_CONNECT_TIMEOUT_MS=2000

VITE_API_BASE_URL=http://127.0.0.1:8000/api

VISION_MODEL_PATH=app/ml_models/person/model.pt
VISION_DEVICE=cpu
VISION_FRAME_RATE=8
PERSON_DETECTION_THRESHOLD=0.50
POSE_CONFIDENCE_THRESHOLD=0.50
FALL_CONFIDENCE_THRESHOLD=0.75
MOTIONLESS_DURATION_SECONDS=7
EVENT_COOLDOWN_SECONDS=60

EVIDENCE_CAPTURE_ENABLED=False
EVIDENCE_RETENTION_DAYS=7

NOTIFICATION_MODE=console
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
SHADE_ALERT_RECIPIENT=
```

Secrets must remain blank or development-safe in the template. The actual local `.env` must be ignored by Git.

---

## 17. Observability and Failure Handling

Every major subsystem should expose useful diagnostics:

- Camera source status.
- Last frame timestamp.
- Frames processed and dropped.
- Detector model readiness.
- Pose model readiness.
- Active monitoring session.
- Number of active tracks.
- Last activity update.
- Last confirmed event.
- Notification success and failure.
- MongoDB reachability.
- WebSocket and worker connection state.

Errors should be categorized rather than swallowed:

```text
configuration_error
camera_error
model_error
inference_error
tracking_error
persistence_error
notification_error
websocket_error
```

A persistence or notification failure must not rewrite the original emergency decision. It should be recorded and surfaced separately.

---

## 18. Model and Artifact Policy

Before adding a model file to the repository:

1. Record the model name and version.
2. Record its source and license.
3. Record expected input shape and preprocessing.
4. Record output labels and label order.
5. Record model size and runtime requirements.
6. Record the evaluation dataset and command.
7. Store metadata beside the artifact.
8. Add a model smoke test.
9. Confirm that the model can be removed or replaced through the model manager without changing API contracts.

Large model weights should normally remain outside Git or use the repository's chosen artifact-storage approach. The plan must not assume a model is accurate merely because it loads successfully.

---

## 19. Risk Register

| Risk                      | Effect                             | Mitigation                                                           |
| ------------------------- | ---------------------------------- | -------------------------------------------------------------------- |
| False fall detection      | Alert fatigue and loss of trust    | Temporal verification, cooldowns, labeled evaluation clips           |
| Missed fall               | Unsafe lack of response            | Measure recall by scenario; expose limitations; retain human review  |
| Camera disconnect         | Monitoring silently stops          | Worker health state, reconnect policy, dashboard warning             |
| Model overconfidence      | Incorrect activity state           | Threshold calibration and confidence-quality checks                  |
| Multiple people crossing  | Track identity switches            | Tracker tests, uncertainty states, conservative event verification   |
| Slow CPU inference        | Stale dashboard and missed frames  | Frame sampling, metrics, configurable resolution, hardware profiling |
| MongoDB unavailable       | Event persistence failure          | Startup diagnostics, clear health status, bounded retries            |
| Duplicate alerts          | Notification fatigue               | Event identity, cooldown, idempotent delivery                        |
| Sensitive video retention | Privacy exposure                   | Local processing, opt-in evidence, retention cleanup                 |
| Leaked camera credentials | Unauthorized camera access         | Environment variables, redacted logs, response sanitization          |
| Model license mismatch    | Distribution or deployment problem | License review before artifact adoption                              |
| Browser disconnection     | Operator misses live updates       | REST snapshot on reconnect and visible connection state              |

---

## 20. Definition of Done for the First Complete MVP

The MVP is complete only when all of the following are true:

- [ ] A local webcam can be configured and opened.
- [ ] A video-file source is available for repeatable tests.
- [ ] People are detected and assigned temporary track IDs.
- [ ] Pose/posture observations are normalized.
- [ ] Basic activities are shown without claiming model certainty.
- [x] A fall-like temporal sequence can be verified from multiple observations.
- [ ] A confirmed event is persisted with reasons and timestamps.
- [ ] Duplicate events and duplicate alerts are controlled.
- [x] The dashboard displays monitoring status and recent event records.
- [x] The dashboard clearly distinguishes potential activity from confirmed emergency.
- [ ] The event can be acknowledged, resolved, or marked false positive.
- [ ] Development notification mode is safe and inspectable.
- [x] MongoDB health and monitoring control-plane status are visible.
- [x] Backend tests run without a physical camera.
- [x] Frontend production build succeeds.
- [x] Privacy, retention, and safety boundaries are documented.
- [x] No unsupported performance or emergency-response guarantee is stated.

---

## 21. Immediate Coding Sequence

When implementation begins, work in this order:

1. Create the root and service scaffolding using `app/` and `web/`.
2. Add Python settings, environment loading, logging, and health checks.
3. Add dependency files and Makefile commands.
4. Add the camera-source abstraction and video-file test source.
5. Add detector, tracker, and pose interfaces with mock implementations.
6. Add the first real model adapter only after the interfaces and tests exist.
7. Add normalized activity observations and temporal history.
8. Implement fall verification with synthetic sequence tests.
9. Add MongoEngine domain documents and REST contracts.
10. Add the monitoring management command.
11. Add Channels event publication.
12. Build the React dashboard around stable API and WebSocket contracts.
13. Add dashboard event workflow.
14. Add dry-run and email notification adapters.
15. Run the full verification workflow and update documentation.

The first coding phase should establish the boundaries and test contracts before adding large model files or complex UI behavior.

---

## 22. Current Status Checklist

### Planning

- [x] Read the SHADE-ai project specification.
- [x] Read the project naming guide.
- [x] Study the PhishGuard repository structure and documentation style.
- [x] Study the VisionCore repository structure and documentation style.
- [x] Decide to use `app/` and `web/` for SHADE-ai.
- [x] Decide to use JavaScript and JSX rather than TypeScript and TSX.
- [x] Define a staged MVP-first implementation strategy.
- [x] Define testing, privacy, model, and notification boundaries.

### Implementation

- [x] Create the project scaffold.
- [x] Configure Django and environment settings.
- [x] Configure MongoDB and health checks.
- [x] Implement the camera source contract and deterministic synthetic/iterable sources.
- [x] Implement vendor-neutral detection, tracking, and pose contracts.
- [x] Implement activity and temporal analysis.
- [x] Implement emergency event persistence documents and service boundary.
- [x] Implement the monitoring worker boundary.
- [x] Implement the initial REST API.
- [x] Implement the read-only WebSocket update path.
- [x] Implement the React dashboard.
- [ ] Implement safe notification adapters.
- [ ] Add production camera/model adapters and complete evaluation gates.

---

## 23. Final Direction

SHADE-ai will be built as a reliable, inspectable event-processing system rather than as a single model call hidden inside a Django endpoint.

The architecture will preserve the separation:

```text
Camera input
    ↓
Computer vision adapters
    ↓
Normalized observations
    ↓
Temporal reasoning
    ↓
Emergency verification
    ↓
Persistent event
    ↓
Real-time dashboard
    ↓
Controlled notification
```

This order gives the project a stable foundation for future activity categories, multiple cameras, stronger models, and hardware integration without sacrificing explainability, testability, privacy, or the established Django + React JSX project style.
