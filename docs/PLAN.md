# SHADE-ai Project Plan

## Smart Human Activity Detection and Emergency System

> **Planning status:** Phase 5A/5B implemented; Phase 5C verified standalone RTMO control-video observations and an independent injected-observation MongoDB path; Phase 5D implemented validated nullable event provenance; authorized fall evaluation and the model-backed event gate remain open
>
> **Current phase:** Phase 5D event-provenance contract documented; authorized fall evaluation and RTMO-generated verified-event gates remain open
>
> **Implementation status:** Django/DRF contracts, MongoEngine camera/event documents, vendor-neutral vision contracts, local-video worker, bounded temporal verifier, and React dashboard are implemented. The worker defaults to the explicit null provider or can select RTMO-S body7 ONNX for experimental CPU person/keypoint observations. Posture labels are geometric heuristics, not learned fall/activity classifications. Model/training-data rights remain unresolved beyond local academic evaluation; fall accuracy and a model-produced MongoDB event are not demonstrated. Webcam/RTSP, shared worker health, live publication, notifications, authentication, and event lifecycle workflows remain incomplete.

---

## 1. Document Purpose

This document defines how SHADE-ai will be built from the existing project specification while following the repository conventions demonstrated by PhishGuard and VisionCore.

The plan intentionally separates:

- What the first usable version must do.
- What belongs in later phases.
- What must be measured before making performance claims.
- Which components own computer vision, event processing, persistence, notifications, and user-interface responsibilities.
- How every phase will be tested and accepted.

The long-term first usable target is a local, single-camera monitoring system that can detect people, track them across frames, estimate posture, identify a potential fall, verify that event using temporal context, save the event, and show it in a React dashboard. The current repository implements a standalone video-file worker, an experimental RTMO-S CPU observation adapter, and a structured, validated, nullable event-provenance contract. A non-fall control video traversed the actual worker and model into normalized observations, while an independent injected-observation run verified event-service/MongoDB persistence; neither establishes a real-model verified fall or model-backed persisted event. It is not a validated fall detector: representative evaluation and physical camera input have not been demonstrated.

SHADE-ai is a safety-monitoring aid. It must not be presented as a medical diagnosis system, a guaranteed security system, or a replacement for human emergency response.

---

## 2. Project Definition

### 2.1 One-line definition

> SHADE-ai is a Django and React-based computer-vision monitoring platform intended to detect human activity, analyze temporal context, verify potentially dangerous situations, record emergency-event metadata, and eventually notify designated responders. Notification delivery is planned, not implemented in the current foundation slice.

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

The technology table below describes the target architecture. Items marked as planned or experimental are not claims that the corresponding runtime adapter is already connected.

| Technology               | Role / current boundary                                      |
| ------------------------ | ------------------------------------------------------------- |
| Python 3.11+             | Runtime and computer-vision service contracts                 |
| Django 4.2+              | Web framework and application configuration                   |
| Django REST Framework    | Implemented JSON API and request validation                   |
| Django Channels          | WebSocket boundary; live worker delivery remains deferred    |
| MongoDB                  | Planned persistence for camera and event metadata             |
| MongoEngine              | Implemented document boundary for camera/event records       |
| OpenCV                   | Local video-file decoding implemented; webcam/RTSP deferred  |
| NumPy                    | Normalized vision data and RTMO-S preprocessing               |
| ONNX Runtime 1.24.3      | Pinned CPU runtime for experimental RTMO-S inference          |
| MMPose RTMO-S body7      | Experimental person boxes and 17-keypoint observation adapter |
| Python logging           | Implemented runtime and diagnostic logging                    |

The implemented adapter uses an official OpenMMLab MMPose-family RTMO-S body7 640×640 ONNX export (opset 11; fixed input `input`, outputs `dets` and `keypoints`) through SHADE's vendor-neutral contracts. `onnxruntime==1.24.3` is pinned in `app/requirements.txt`; existing `opencv-python-headless` and NumPy are reused. The model emits person detections and keypoints, not fall/activity decisions. Artifact/training-data rights remain unresolved: the authorized scope is local academic evaluation only, with no redistribution or production use. Package/source licensing does not clear the weights or training data.

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
- Normal `make dev` startup blocks before Django launches when the configured MongoDB service is not reachable.
- The API keeps bounded health diagnostics and an explicit `--force` diagnostic bypass, following PhishGuard's operational boundary.
- The supported bypass syntax is `make dev -- --force`; direct backend startup uses `python manage.py runserver --force` from `app/`.
- A local in-memory Channels layer is acceptable for a single-process prototype.
- Redis will be introduced only when multi-process or multi-camera real-time delivery requires it.
- Continuous raw video will not be stored by default.
- Event metadata and optional evidence snapshots will use configurable retention rules.

### 4.4 External notification providers

Email is the first planned outbound notification channel. SMS, push notifications, messaging platforms, and hardware alarms are later adapters. No production notification adapter is connected in the current repository slice.

When notification work begins, development defaults must use one of these safe modes:

- Console email backend.
- Explicit dry-run notification adapter.
- A test recipient configured through environment variables.

Real emergency recipients must never be embedded in source code or used in automated tests.

---

## 5. Scope Boundaries

### 5.1 MVP capabilities

The following is the target MVP contract, not a list of capabilities already connected end to end. The current implementation state is tracked in `Progress.md`.

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

The tree above is a target architecture. Existing files are authoritative for the current slice; a conceptual path such as `models.py`, `run-monitor.py`, or the planned notification modules must not be described as implemented until it exists and is tested.

- Keep long-running vision processing out of request views.
- Keep model loading and inference inside `vision/`.
- Keep database access and event orchestration inside application services.
- Keep serializers responsible for request and response contracts.
- Keep API views thin.
- Keep frontend files grouped by feature instead of creating one unbounded components directory.
- Keep generated media, logs, model weights, local environments, and secrets out of Git.
- Keep model weights outside Git by default. Record artifact source, version, checksum, licensing/rights status, configuration, and evaluation evidence; this RTMO-S artifact is permitted only for local academic evaluation while weight/training-data rights remain unresolved.

---

## 7. Target High-Level Architecture

The following diagram is a target design, not a complete runtime inventory. Phase 5A adds the standalone video-file worker; Phase 5B adds optional RTMO-S body7 ONNX CPU person/pose observations. The worker still defaults to the explicit null provider. Fall evaluation, demonstrated model-backed database persistence, webcam/RTSP, shared worker state, publication, and alerts remain open.

```text
┌─────────────────────────────────────────────────────────────────────┐
│ React + Vite + JavaScript/JSX (`web/`)                              │
│ Dashboard · live monitor · camera settings · event history          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP JSON + WebSocket events
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Django + Django REST Framework (`app/`)                             │
│ serializers · views · URLs · health · camera/event APIs             │
└───────────────┬───────────────────────┬─────────────────────────────┘
                │                       │
                ▼                       ▼
┌──────────────────────────┐  ┌──────────────────────────────────────┐
│ MongoDB + MongoEngine    │  │ Monitoring worker                    │
│ cameras · activities     │  │ camera source · OpenCV · vision      │
│ emergencies · alerts     │  │ temporal engine · event publisher    │
└──────────────────────────┘  └───────────────┬──────────────────────┘
                                               │
                                               ▼
                                  ┌────────────────────────┐
                                  │ Vision pipeline        │
                                  │ detect → track → pose  │
                                  │ → classify → verify    │
                                  └────────────┬───────────┘
                                               │
                                               ▼
                                  ┌────────────────────────┐
                                  │ Alert adapters         │
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

The camera loop must not run inside a normal HTTP request. `POST /api/monitoring/start/` continues to record process-local `armed` intent and a local session identifier; it does not launch or report the standalone worker.

Phase 5A adds this standalone Django management command; Phase 5B adds optional `rtmo-s` provider selection; Phase 5D passes actual runtime provenance for verified events. It loads an enabled `video_file` camera configuration from MongoDB, reads the configured local video sequentially, and runs the vendor-neutral pipeline. `development-null` remains the default and emits no observations. Explicit `rtmo-s` selection requires a locally provisioned ONNX artifact at `VISION_MODEL_PATH`; the worker initializes the provider before opening the video and fails clearly on missing or invalid dependencies/weights/configuration, without downloading or silently falling back. The optional positive `--max-frames` argument bounds a development run.

```bash
python manage.py run_monitor --camera-id <camera-id>
```

The Phase 5A–5D worker currently:

1. Load one enabled video-file configuration from MongoDB; reject missing, disabled, unsupported, or invalid sources.
2. Open the file through `VideoFileCameraSource`, expose decoder metadata, read frames in order, and stop at EOF without looping.
3. Pass every acquired frame through the existing vendor-neutral `VisionPipeline`.
4. Default to the clearly named `development-null` provider, or explicitly initialize one RTMO-S ONNX CPU session per provider instance. RTMO-S outputs are validated and normalized to person detections, confidence, 17 keypoints, frame/time, and model/provider provenance; SHADE-specific geometric posture cues are explicitly tagged `pose_heuristic_not_activity_model`.
5. Use short-lived local IoU track IDs for the verifier's per-track history; these are not identities and their difficult multi-person association is unvalidated. Pass the resulting observations through the unchanged bounded `FallTemporalVerifier`; the model adapter contains no temporal fall/emergency logic.
6. Persist only valid temporally verified decisions through `events.services.create_event`, with in-run duplicate suppression and optional validated structured provenance supplied by the runtime caller. Historical/legacy records may retain null provenance. Deterministic tests exercise this boundary through an injected persistence callback, and a separate bounded Phase 5C manual run verified an injected sequence through the real event service and isolated MongoDB. This remains distinct from real RTMO inference; no RTMO-produced MongoDB event has been demonstrated.
7. Log lifecycle and failures, honor cooperative SIGINT/SIGTERM shutdown between frames, and release the source on normal or exceptional exits.

**Not yet established or implemented:** representative fall/activity accuracy, cleared artifact/training-data rights beyond local academic evaluation, a model-backed database event, crossing-person tracking robustness, webcam or RTSP sources, shared worker-state/crash reporting, HTTP API supervision, WebSocket publication, notifications, multi-camera orchestration, or event-review mutations. The separately verified injected-observation MongoDB path is not a model-backed event. The event document now supports nullable structured runtime provenance; however, no RTMO-generated event or persisted model provenance has been demonstrated. Historical records without provenance remain valid and serialize it as `null`.

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

Phase 5A implements the local video-file source first for reproducible development and test runs. Webcam and RTSP sources remain deferred.

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

The RTMO-S detector adapter returns a normalized structure rather than exposing ONNX Runtime or model-specific output objects to the rest of the application:

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

The provider configuration/adapter will:

- Initialize the ONNX CPU session once per provider instance, before the worker opens the video source.
- Require the configured local model artifact; never download weights at worker startup or fall back silently to the null provider.
- Read `VISION_MODEL_PATH`, `VISION_DEVICE`, `VISION_CONFIDENCE_THRESHOLD`, and `VISION_KEYPOINT_THRESHOLD`; CPU is supported, GPU selection fails clearly for this implementation.
- Validate model inputs/outputs, frame dimensions, boxes, confidence, and keypoint structures before normalization.
- Keep model-specific output parsing in `vision/rtmo.py` and expose only SHADE's vendor-neutral observations.

### 8.4 Person tracking

Per-track history is required by the existing temporal verifier. Phase 5B uses a small greedy camera-local IoU association layer instead of a vendor-specific learned tracker.

- Assign short-lived, process-local trajectory IDs; never represent them as person identity.
- Match boxes between frames and age out a track after configured missed frames; keep state bounded and in memory.
- Do not claim robust identity continuity: difficult crossing-person association is not evaluated, and IDs can switch.

### 8.5 Pose and posture

The RTMO-S adapter normalizes its 17 keypoints into the existing stable internal representation:

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

The rest of the system depends only on SHADE keypoint/observation types; ONNX and model-specific arrays remain inside the adapter. Preprocessing follows the archived MMPose BGR, 640×640 fit/pad-114, 0–1 scale pipeline. Pixel-for-pixel parity with the source exporter has not been verified.

### 8.6 Activity recognition

The current RTMO-S adapter has only a lightweight geometric posture heuristic based on box aspect ratio, keypoint visibility, shoulder/hip geometry, and orientation. It emits `standing`, `sitting`, `lying`, or `unknown`, marked `pose_heuristic_not_activity_model`; it does not infer a fall or emergency. The following richer motion/activity baseline is a future design, not an implemented or evaluated classifier.

A future activity stage may use:

- Bounding-box aspect ratio.
- Center-point movement.
- Estimated vertical velocity.
- Body orientation.
- Shoulder-to-hip geometry.
- Keypoint confidence.
- Recent activity history.
- Time spent in a posture.

It might produce an observation such as:

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

This is a future, illustrative activity observation only. The current geometric heuristic is not calibrated, has not been evaluated on representative activity/fall data, and is not evidence of fall-detection performance.

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
- [x] Root `make dev` launches separate macOS Terminal service windows.
- [x] The frontend child opens the browser automatically; the backend child stays browser-free.
- [x] Root `make stop` stops both configured development service ports.
- [x] Normal `make dev` requires reachable MongoDB before launching services.
- [x] Normal startup follows MongoDB → backend → frontend; the root waits for the backend health endpoint before launching the web child.
- [x] `make dev -- --force` provides the explicit diagnostic bypass and propagates it to both service children.
- [x] Normal frontend startup requires a reachable backend health endpoint.
- [x] `make ui -- --force` and `make -C web dev -- --force` bypass only the frontend backend-reachability gate.
- [x] `make ci` and `git diff --check` pass.

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

Persist camera configuration and emergency-event metadata through a documented API while keeping degraded behavior explicit.

### Current delivery status

The foundation slice for this phase is implemented. MongoEngine documents and service boundaries exist for cameras and emergency events; the API exposes list/create contracts, bounded health diagnostics, capabilities, and process-local monitoring status. Activity summaries, monitoring sessions, alert records, pagination/filtering, and full event lifecycle mutations remain planned.

### Work

- Configure MongoDB and MongoEngine.
- Add bounded MongoDB startup diagnostics.
- Require MongoDB for normal backend and root development startup.
- Add explicit `make dev -- --force` and `python manage.py runserver --force` diagnostic behavior, including autoreloader-safe flag propagation.
- Require the backend health endpoint for normal frontend startup; provide `make ui -- --force` and `make -C web dev -- --force` as frontend-only diagnostic bypasses.
- Start the backend before the frontend and wait for `/api/health/` in root orchestration.
- Implement domain documents and indexes.
- Implement serializers and resource endpoints.
- Add health and capabilities responses.
- Add event filtering and pagination after the base contract works.
- Keep views thin and service logic testable without live MongoDB.

### Completion gate

- [x] API root, health, and capability endpoints work.
- [x] Camera configuration can be validated and persisted when MongoDB is available.
- [x] Emergency-event metadata can be validated and persisted when MongoDB is available.
- [x] Persistence failures are visible through degraded responses and do not corrupt process-local monitoring intent.
- [x] Normal startup and diagnostic startup behavior are documented.
- [x] Frontend startup fails clearly when the backend is unreachable unless `--force` is explicit.
- [x] Root orchestration waits for backend readiness before launching the frontend.
- [ ] Activity summaries, sessions, alerts, filtering, pagination, and complete event lifecycle mutations are implemented.

---

## Phase 5 — Monitoring worker and event integration

### Objective

Connect the existing vision contracts to a real worker and domain services without putting the camera loop in HTTP requests.

### Current delivery status

**Phase 5A/5B are implemented; Phase 5C has distinct, bounded control-path evidence; Phase 5D adds structured event provenance; Phase 5 overall is not complete.** `run_monitor` processed a temporary three-frame non-fall control clip with RTMO-S on CPU, producing 24 normalized observations and no verified decision or event. Separately, deterministic injected observations traversed the actual worker and unchanged verifier into `events.services.create_event` and were verified in isolated MongoDB; this does **not** show that RTMO produced the event. Phase 5D tests the optional provenance contract and its worker handoff, but an actual RTMO-produced persisted event has not been demonstrated. No suitable authorized fall clip was identified; representative fall accuracy therefore remains unproven. Model/training-data rights remain unresolved beyond local academic evaluation. Browser rendering, webcam/RTSP, shared worker health, WebSocket publication, and operator event workflows remain deferred.

### Work

- [x] Add the standalone management command, local video-file source, frame orchestration, EOF handling, cooperative shutdown, and resource cleanup.
- [x] Keep process-local HTTP monitoring intent separate from actual worker execution.
- [x] Preserve the vendor-neutral detector/tracker/pose/activity/temporal pipeline and expose a clearly unavailable null provider rather than fabricating inference.
- [x] Add a bounded verified-event persistence boundary for future inference-capable providers; test it with deterministic adapters.
- [x] Integrate RTMO-S body7 ONNX CPU person/keypoint observations behind vendor-neutral contracts; local artifact-backed smoke executes.
- [x] Add explicit provider/model/device/threshold configuration and fail-closed local artifact handling.
- [x] Normalize detector boxes/confidence/keypoints/frame provenance and short-lived trajectory IDs; activity cues remain geometric heuristics.
- [x] Add an optional validated structured event-provenance contract, worker metadata handoff, additive API serialization, and nullable legacy-event behavior; cover the contract with deterministic tests.
- [ ] Identify authorized representative fall-evaluation material and resolve model-weight/training-data rights beyond local academic evaluation; do not redistribute or use in production meanwhile.
- [ ] Evaluate posture/fall behavior on representative, authorized data.
- [ ] Add webcam and, later, RTSP capture.
- [ ] Expose shared worker status, restart/failure visibility, and (if selected) API process supervision.
- [ ] Publish actual worker state/events and add operator event lifecycle workflow.

### Completion gate

- [x] A deterministic configured video-file can be opened by the standalone process and frames read until EOF; invalid/missing files fail explicitly.
- [x] The actual bounded `run_monitor` command initialized RTMO-S on CPU and processed a temporary non-fall control video through the unchanged pipeline (3 frames, 24 observations, 8 tracks, 0 temporal decisions, 0 verified events, 0 persisted events). This is model-observation evidence only; no suitable authorized fall clip was identified.
- [x] The independent deterministic injected-observation demonstration traversed the real worker/verifier/event-service/MongoDB path; one queried event was subsequently removed with its temporary camera record. It proves the persistence path, not an RTMO-generated decision or event.
- [x] The null-provider worker creates no detections or emergency events; separate deterministic worker tests exercise injected observations and persistence-boundary behavior.
- [x] Real video frames traverse RTMO-S CPU inference and produce normalized SHADE person/keypoint observations in the opt-in smoke test; the actual bounded `run_monitor` command also processed a three-frame non-fall control clip (**24 observations, 8 tracks, 0 decisions, 0 events**).
- [ ] Representative fall/activity evaluation validates observation cues and temporal decision behavior.
- [ ] Demonstrate an RTMO-generated verified decision persisted through actual `events.services.create_event` and MongoDB wiring, with the runtime provenance document queried afterward. The injected-observation MongoDB demonstration does not satisfy this gate.
- [ ] A webcam source can run through the complete model-backed pipeline.
- [ ] Duplicate persistence, visible worker failures, and worker/API supervision have deployment-appropriate status and tests.
- [ ] Live worker state and events reach authorized dashboard sessions.

---

## Phase 6 — Real-time dashboard

### Objective

Give an operator a clear interface for API snapshots, local monitoring intent, and human event review while preserving a visible boundary around live monitoring.

### Current delivery status

The first dashboard foundation is implemented. The React/JSX UI supports overview, event-review, and source views; API snapshots; synthetic presentation fallback; health/persistence messaging; accessible status and action controls; supplied branding; and responsive layout. Live camera preview, live worker updates, reconnect behavior, and production event publication remain deferred.

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

### Current delivery status

Not complete. No notification adapter, dashboard alert document, or acknowledge/resolve/false-positive workflow is connected in the current repository. Event records remain metadata contracts and human review remains external to the API.

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

### Current delivery status

Documentation and safety boundaries have been refreshed for the foundation slice. Representative camera/model evaluation, performance measurement, retention testing, and a complete monitoring smoke test remain future gates.

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

The root project provides the following verification commands:

```bash
make doctor
make check
make test
make build
make ci
make stop
```

Before a milestone is considered complete:

```bash
python3 -m compileall -q app
npm run build --prefix web
git diff --check
```

The root and service Makefiles are now the executable command contract. Use `make -n`, `make -n dev`, and `make -n stop` to inspect recipes without launching services.

---

## 15. Development Commands to Provide

The command surface is implemented across the root, `app/`, and `web/` Makefiles:

```text
make install             Install backend and web dependencies
make setup-env           Create app/.env from the template
make dev                 Start the full development cockpit (MongoDB → backend → frontend)
make dev -- --force      Start diagnostic mode without MongoDB/backend readiness gates
make dev-single          Run both services in one terminal, in dependency order
make app                 Start only the Django backend (MongoDB required)
make app -- --force      Start only the backend in diagnostic mode
make ui                  Start only the React frontend (backend required)
make ui -- --force       Start only the frontend in diagnostic mode
make check               Run Django system checks
make test                Run the complete backend suite
make test-vision         Run temporal and pipeline tests
make test-api            Run HTTP contract tests
make compile             Compile-check Python files
make build               Build the React application
make check-health        Verify MongoDB readiness before normal startup
make health              Call the API health endpoint
make status              Show MongoDB, backend, and frontend status
make open                Open the frontend manually
make logs                Tail backend logs
make stop                Stop both configured development service ports
make restart             Stop, install, and relaunch the cockpit
make clean-cache         Remove safe generated caches
make clean               Remove local dependency environments and output
make ci                  Run checks, tests, compilation, and the frontend build
```

On macOS, root `make dev` first performs a bounded MongoDB reachability check, opens the backend in a separate Terminal window, waits for `/api/health/`, and then opens the frontend in its own Terminal window. The frontend child opens the browser; the backend child stays browser-free. `make -C app dev` remains browser-free and enforces the MongoDB requirement, while `make -C web dev` checks backend reachability before opening the browser. For intentional diagnostics, `make dev -- --force` bypasses both service readiness gates and propagates `--force` to both children; standalone `make app -- --force`, `python manage.py runserver --force`, and `make ui -- --force` remain available. Frontend `--force` bypasses only the backend reachability check and does not make API requests available. On non-macOS systems, the root command falls back to one-terminal mode while preserving the same dependency order. The root `make stop` command is scoped to `API_PORT` and `WEB_PORT` so it does not use broad process-name matching.

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

The custom `LICENSE` preserves Dibakar Is Live attribution and defines the permitted academic, learning, research, and evaluation boundary. It does not relicense dependencies, datasets, model weights, fonts, icons, or external services; each third-party artifact remains subject to its own terms. The Phase 5B RTMO-S artifact/training-data rights are unresolved: use is restricted to local academic evaluation; redistribution and production use are prohibited.

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

Keep the locally smoke-tested RTMO-S body7 ONNX artifact (approximately 39.6 MB) outside Git; `.gitignore` excludes ONNX/model-artifact paths. Its recorded source is the OpenMMLab MMPose RTMO-S body7 640×640 ONNX export (MMPose 1.2.0 family, opset 11); weight and mixed training-data rights remain unresolved. The only approved scope here is local academic evaluation—not redistribution or production use. Provision weights locally and set `VISION_MODEL_PATH`; worker startup must not download them. Loading/inference alone does not establish accuracy.

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

The complete MVP is not yet reached. The following checklist deliberately distinguishes the implemented foundation from the remaining end-to-end gates:

- [ ] A local webcam can be configured and opened.
- [x] A video-file source is available for repeatable tests.
- [x] Person detections and short-lived track IDs are produced by the experimental adapter (tracking robustness not established).
- [x] Pose/keypoints normalize to SHADE observation types; posture output remains an unevaluated heuristic.
- [ ] Basic activities are validated on representative data without claiming model certainty.
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

For the remaining implementation, work in this order. Completed foundation items are retained as historical sequencing, not as pending work:

1. Create the root and service scaffolding using `app/` and `web/`.
2. Add Python settings, environment loading, logging, and health checks.
3. Add dependency files and Makefile commands.
4. Add the camera-source abstraction and video-file test source.
5. Add detector, tracker, and pose interfaces with mock implementations.
6. Add the RTMO-S CPU observation adapter behind existing interfaces (implemented; local academic evaluation only).
7. Validate posture and temporal behavior on rights-cleared representative data.
8. Demonstrate verified event persistence with real worker/service/MongoDB wiring without bypassing existing gates.
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
- [x] Implement the process-local monitoring control boundary.
- [x] Implement the standalone local-video worker and `run_monitor` command with explicit null or optional RTMO-S CPU provider selection.
- [x] Implement the initial REST API.
- [x] Implement the read-oriented WebSocket boundary.
- [x] Implement the React dashboard.
- [ ] Implement safe notification adapters.
- [ ] Resolve artifact/training-data rights and complete representative evaluation; webcam/RTSP and production monitoring adapters remain deferred.

---

## 23. Final Direction

SHADE-ai will be built as a reliable, inspectable event-processing system rather than as a single model call hidden inside a Django endpoint. The current foundation makes those boundaries testable without overstating live-camera, model, notification, or emergency-response behavior. `Progress.md` is the concise verified status companion to this plan.

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
