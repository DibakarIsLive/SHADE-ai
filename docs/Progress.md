# SHADE-ai Progress

## Review snapshot

**Review scope:** backend/API and vendor-neutral vision contracts, standalone local-video worker, experimental CPU RTMO-S provider, temporal/event boundaries, structured event provenance, React dashboard, documentation, and repository quality gates.

**Status:** Phase 5A/5B are implemented; Phase 5C separately demonstrated a bounded RTMO-S control-video observation run and injected-observation persistence through the actual worker/verifier/event-service/MongoDB path. Phase 5D adds a validated, nullable event-provenance contract and wires actual worker runtime metadata into verifier-approved event creation. These are still distinct proofs: RTMO produced no verified decision/event in the control run; the injected MongoDB event was not RTMO evidence. No suitable authorized fall clip has been identified, and no model-backed MongoDB event or fall accuracy is demonstrated. Model/training-data rights remain unresolved beyond local academic evaluation; webcam/RTSP, shared worker status/publication, and responder integrations remain deferred.

**Operating principle:** `OBSERVE → ANALYZE → VERIFY → RESPOND`

## Verified implementation matrix

| Area | Status | Verified behavior |
| --- | --- | --- |
| Django project | Implemented | Split settings, API routing, health, capabilities, and local development configuration exist under `app/`. |
| MongoDB boundary | Implemented | MongoEngine documents persist camera configuration and emergency-event metadata when MongoDB is reachable. |
| Health diagnostics | Implemented | `/api/health/` reports healthy/degraded status, bounded database diagnostics, runtime configuration, monitoring state, and safety flags. |
| Camera API | Implemented | Camera list/create contracts validate supported source types; RTSP and video-file inputs require a source URI. |
| Event API | Implemented | Event list/create contracts validate event fields and optional nested provenance; historical events without provenance serialize with `provenance: null`. |
| Event provenance | Implemented and tested | Nullable embedded provenance records provider, optional model identifier/version/digest, source type, camera ID, and processing timestamp; service and API boundaries validate supplied values. |
| Vision contracts | Implemented | Frame, detection, tracking, pose, observation, decision, source, and pipeline interfaces are vendor-neutral. |
| Temporal fall rule | Implemented | Bounded evidence, upright-to-low transition, sustained low posture, duration, and confidence gates are represented and tested. |
| Development/test sources | Implemented | Deterministic synthetic and iterable sources support pipeline and repeatable tests. |
| Video-file source | Implemented | `VideoFileCameraSource` reads a configured local file sequentially, exposes decoder metadata, stops at EOF without looping, and releases its decoder. The standalone worker currently accepts this source type only. |
| Monitoring control plane | Implemented with boundary | HTTP start/stop changes process-local intent state and creates a local session identifier; it remains separate from and does not launch or report the standalone worker. |
| WebSocket route | Boundary only | A read-oriented monitoring consumer and route exist; live worker event publication is not connected. |
| React dashboard | Implemented | Responsive JSX dashboard loads API snapshots, presents safe fallback data, exposes review/source views, and includes accessible status and action labels. It accepts the additive event response field without displaying internal artifact details. |
| Branding | Implemented | Supplied `public/Logo.png` and `public/Banner.png` are used by the dashboard and are explicitly unignored for version control. |
| Presentation fallback | Implemented | Synthetic data is runtime-relative, visibly labeled, and separated from live camera/model claims. |
| Startup dependency cycle | Implemented | Normal startup follows MongoDB → backend → frontend; the root waits for backend health before launching the web child, while backend and frontend each expose an explicit `--force` diagnostic bypass. |
| Authentication | Planned | Operator authentication and authorization are not implemented. |
| Physical camera capture | Deferred | Webcam and RTSP adapters are not implemented; the first executable source is a local video file. |
| Real vision provider | Experimental | MMPose RTMO-S body7 640×640 ONNX adapter runs on CPU and maps detections/17 keypoints to SHADE types; artifact-backed video smoke passes. This is observation extraction, not fall/activity inference or validated accuracy. |
| Posture / temporal analysis | Implemented, not validated | Geometric posture cues feed the unchanged bounded verifier; representative fall evaluation and detection-performance evidence are absent. |
| Standalone monitoring worker | Implemented, selectable inference | `python manage.py run_monitor --camera-id …` reads configured local video outside HTTP handling. The default `development-null` emits no detections; explicitly selected `rtmo-s` initializes once from local `VISION_MODEL_PATH` and fails closed if unavailable. HTTP intent is not worker health. |
| Notifications | Deferred | No production email/SMS/push delivery workflow is connected. |
| Event review mutations | Deferred | Event creation exists; acknowledge, investigate, resolve, and false-positive UI/API workflows are not complete. |
| Retention scheduler | Planned | Retention policy fields/boundaries may exist, but automated cleanup is not implemented. |
| Event persistence | Injected-observation MongoDB path demonstrated; model-backed DB event not demonstrated | The worker accepts only validated temporally verified decisions and calls `events.services.create_event`, passing runtime provenance. A bounded one-off run verified a deterministic injected sequence through the real service and MongoDB; this is not RTMO evidence. No RTMO-generated verified decision has been saved to MongoDB. |
| Model artifact / rights | Local academic evaluation only | RTMO-S weights/training-data rights remain unresolved. No redistribution or production use; weights stay outside Git and are never silently downloaded. |
| Accuracy/performance claims | Not established | The one local CPU smoke is functional-path/performance sampling only; no representative detection/fall evaluation, calibrated accuracy, or real-time guarantee exists. |

## Phase 5A — Monitoring worker foundation and video-file pipeline — 30 September 2026

### Completed

- Added a standalone Django `run_monitor` management command that loads one enabled camera configuration from MongoDB and runs outside the HTTP request lifecycle. It validates the camera ID, enabled state, supported source type, and file URI; `--max-frames` bounds development runs.
- Added `VideoFileCameraSource` behind the camera-source contract. It opens a local file, reports dimensions/FPS, yields decoded frames in order, stops at EOF without implicit looping, reports failures, and releases the decoder.
- Added a vendor-neutral `VisionProvider` boundary and an explicitly unavailable `development-null` provider. It traverses the existing pipeline with empty detections, so it generates no observations, verified decisions, or events.
- The worker orchestrates frame processing, checks a cooperative stop event between frames, handles SIGINT/SIGTERM in the command, logs startup/source/processing/failure/shutdown details, records bounded processing counts, and closes the source on normal and exceptional exits.
- Preserved the existing bounded temporal fall verifier. The worker persists only validated, verified decisions from an inference-capable provider through the existing `events.services.create_event` service, with in-run duplicate suppression and truthful persistence-failure handling. The current CLI provider cannot reach this event path.
- Added deterministic source, worker, command, temporal-boundary, and event-persistence tests in `app/tests/test_camera_sources.py`, `app/tests/test_monitoring_worker.py`, and `app/tests/test_run_monitor_command.py`.

### Execution flow and verification

```text
Enabled MongoDB camera configuration
    → local video-file source
    → sequential decoded frames
    → development-null vision provider / existing pipeline
    → existing temporal verifier boundary (no observations from null provider)
    → no event generated or persisted by the current CLI provider
    → graceful shutdown and video decoder release
```

- Focused Phase 5A tests: **21 passed**. Full backend test suite: **39 passed**.
- `make check`, `make test`, `make compile`, `make build`, `make ci`, and `git diff --check` all passed. The Vite production build processed 39 modules. `make ci` also covers checks, tests, compilation, and the frontend build.
- Manually generated a temporary four-frame 32×24 MJPG fixture and stored two camera configurations in an isolated local MongoDB database. `run_monitor` loaded the enabled video-file configuration, opened it at 10 FPS, processed four frames, reached EOF, logged graceful shutdown, and reported `development-null` inference unavailable with no detections or emergency events. The temporary video and isolated database were removed.
- Manually invoked the command on the second configuration pointing to a nonexistent video; it exited with status 1 and the specific `Video file does not exist or is not a regular file` error.
- Decoder-release behavior is additionally covered by source/worker tests. The temporal/event integration tests use deterministic test adapters and a persistence callback; they do not demonstrate real model inference or a model-produced event saved to MongoDB.

### Deferred and not established

Production detector/pose/activity-model integration and model-backed event persistence; webcam and RTSP; multi-camera operation; shared/observable worker health; wiring HTTP “armed” intent to worker lifecycle; live WebSocket publication; notifications; authentication; and event lifecycle mutations remain incomplete. No browser rendering or production monitoring behavior is claimed. Phase 5 as a whole remains open.

## Phase 5B — RTMO-S CPU observation provider — 3 October 2026

### Model and license scope

- Selected **RTMO-S body7**, the small pose-capable RTMO export from the MMPose 1.2.0 family. The local ONNX export is opset 11, fixed 640×640 input `input`, with `dets` and `keypoints` outputs; the smoke-tested file is 39,617,685 bytes. The model reports person detections and keypoints; it is not a fall or emergency classifier.
- Runtime: pinned `onnxruntime==1.24.3` (MIT; Python metadata requires >=3.10) plus existing `opencv-python-headless`/NumPy. CPU is the supported path; no CUDA dependency. GPU is not enabled by this adapter and an unsupported GPU request fails clearly.
- Preprocessing follows the archived MMPose pipeline: BGR frame, fit to 640×640, pad with 114, and scale 0–1. The model wrapper returns detector boxes/scores and 17 keypoints, which are validated and normalized into SHADE dataclasses. Pixel-identical parity with the exporter was not verified.
- Confidence and keypoint thresholds are explicit settings (`VISION_CONFIDENCE_THRESHOLD`, `VISION_KEYPOINT_THRESHOLD`); model path is configurable via `VISION_MODEL_PATH`, with an ignored repo-local default. The default provider remains `development-null`. RTMO-S initializes once per provider instance; missing weights/runtime, bad signature/configuration, and unsupported device fail closed. Startup does not download weights or silently use the null provider.
- SHADE uses a simple local IoU association because verifier history is keyed by track. IDs are short-lived process-local trajectories, not identity recognition; difficult multi-person crossing/association has not been validated. Pose-to-posture output is geometric and explicitly tagged `pose_heuristic_not_activity_model`; only `standing`, `sitting`, `lying`, or `unknown` are emitted. No learned fall/activity model is present.
- **Rights restriction:** user approval covers local academic evaluation only. Rights for the ONNX weights and mixed training data are unresolved; MMPose's code license does not by itself license those assets. Do not redistribute weights/artifact or use this model in production. SHADE's root license separately excludes commercial and safety-critical use. Model files are ignored by Git.

### Pipeline and tests

```text
local video file → RTMO-S ONNX CPU inference → validated person boxes/17 keypoints
→ SHADE detections/poses → ephemeral IoU trajectory IDs → geometric posture observation
→ existing FallTemporalVerifier → verified-decision event boundary
```

- The temporal rule is unchanged: >=3 observations, >=0.5 seconds, prior upright activity, at least two low-posture items in the latest two, and minimum observation confidence 0.65. These code thresholds are not a claim of demonstrated fall detection.
- Normalization tests cover one/multiple/no person, thresholds, absent keypoints, malformed boxes/outputs, invalid confidences/coordinates, frame validation, preprocessing geometry, and CPU/provider initialization failures. Unit tests do not fetch model weights.
- Opt-in integration test: `app/tests/test_rtmo_smoke.py`; creates a temporary three-frame video from an already-local image and runs the real video decoder → ONNX model → SHADE observation mapping. It does not download weights/media or require an actual fall.
- Real local smoke passed: **1 passed**; 3 decoded frames, 24 observations, 960×640. Latest one-run M2/8-GB CPU timing: initialization 0.173 s, mean pipeline time 0.112 s/frame (~8.961 measured pipeline FPS). The ~39.6-MB model and temporary licensed test image were outside Git. These timings are a single development sample, not a real-time or deployment guarantee.
- Deterministic worker test feeds a known observation sequence through the existing verifier and injected event-persistence callback, checks provenance, and verifies duplicate suppression. This tests the existing event boundary; it is **not** a real model-produced MongoDB event. The smoke sequence yielded person observations only: no fall/temporal transition or event was demonstrated.
- At the Phase 5B checkpoint, repository verification passed `make check`, `make test` (**67 passed, 1 skipped**), `make compile`, `make build` (Vite, 39 modules), `make ci`, and `git diff --check`. Focused RTMO/worker/temporal/pipeline tests at that checkpoint: **48 passed**. Current Phase 5C verification is recorded below.

### Remaining gates

Representative, rights-cleared posture/fall evaluation; any license clearance beyond local academic use; a real model-backed verified event written via actual worker→`create_event`→MongoDB wiring; broad multi-person tracker validation; actual worker process-health integration; webcam/RTSP, WebSocket/dashboard publication, notifications, authentication, and event lifecycle review all remain incomplete. Phase 5 and the complete monitoring product are **not** complete.

## Phase 5C — Bounded worker and persistence-path evidence — 3 October 2026

### A–B. Audit and execution path

Audited the existing RTMO adapter/provider and vendor-neutral types, tracker, worker and `run_monitor` command, temporal verifier, `events.services.create_event`, MongoEngine event/camera documents and configuration, Phase 5A/5B tests, and the Phase 5 plan. No architecture rewrite or verifier-threshold change was made.

```text
enabled MongoDB camera configuration
  → sequential local video decoder
  → RTMO-S body7 ONNX CPU inference
  → normalized SHADE person/keypoint observations
  → ephemeral IoU tracks and geometric posture cues
  → existing temporal verifier (unchanged)
  → only a verified decision may call events.services.create_event
  → MongoEngine EmergencyEvent in MongoDB
```

The RTMO adapter produces person/keypoint estimates; `standing`/`sitting`/`lying`/`unknown` are geometric pose heuristics, not a learned fall classifier. The verifier continues to require multiple observations, sufficient duration, prior upright activity, sustained low-posture evidence, and minimum confidence.

### C–G. Local input and actual RTMO standalone-worker run

No rights-cleared representative fall clip was identified for this run. No fall footage was downloaded or used. The bounded control clip was a temporary three-frame video assembled from repeated copies of an already-local street-scene still (Wikimedia Commons, “People walking on the street in Nairobi, Kenya.jpg,” creator AEira-WMF, CC BY); it contains no staged or observed fall and is **control footage only**, not fall-evaluation evidence.

From `app/`, the standalone command was run with `MONGODB_DATABASE=shade_ai_test`, `VISION_PROVIDER=rtmo-s`, and `VISION_MODEL_PATH=/tmp/shade-rtmo-official-body7.onnx` (local MongoDB connection settings omitted from this record):

```sh
.venv/bin/python manage.py run_monitor --camera-id phase5c-rtmo-20261003T012108-88021 --max-frames 3
```

The enabled video-file camera loaded; the `mmpose-rtmo-s-body7-onnx` provider initialized on CPU and decoded the three-frame local clip. Actual run summary: **3 frames, 24 normalized observations, 8 unique tracks, 0 temporal decisions, 0 verified decisions, 0 persisted events**. EOF/shutdown completed. This proves actual standalone command → real RTMO observations → existing temporal pipeline on a non-fall control input; it does **not** prove a real-model fall or event.

The opt-in RTMO smoke remains a separate observation-only proof: **1 passed**, 3 frames/24 observations at 960×640; initialization **0.173 s**, average pipeline processing **0.112 s/frame** (about **8.961 measured FPS**) on the recorded M2/8-GB CPU sample. These are development measurements from the smoke test, not a benchmark or real-time claim. The bounded CLI run did not produce a separately recorded initialization/FPS timing.

### H–J. Independent injected-observation → MongoDB demonstration

Separately from RTMO, a deterministic standing → falling → lying → lying observation sequence was sent through the actual `MonitoringWorker` and unchanged verifier, with the real `events.services.create_event` service connected to the isolated local `shade_ai_test` MongoDB. The baseline event count was zero. The worker processed **4 frames / 4 observations / 1 track**, reached **2 verified decisions** for that track, and its in-run duplicate suppression persisted **1 event**. Querying MongoDB confirmed the raw event document (`fall`, `critical`, `verified`, confidence **0.9**, duration **0.9 s**, frame count **3**); thus the service→MongoDB boundary was verified independently of model inference. This is an injected-observation test, **not** a model-backed event.

The deterministic worker tests also check repeat suppression/re-arming after upright activity, persistence failures, and no-event/low-confidence sequences. The smoke/control run persisted no event. After verification, the temporary RTMO-run camera and the inserted event plus camera from the injected demonstration were removed; the temporary control MP4 was removed. Final isolated database counts were **0 cameras / 0 emergency events**.

### K–Q. Verification and limitations

- At the Phase 5C checkpoint, repository gates all passed: `make check`; `make test` (**68 passed, 1 skipped**); `make compile`; `make build` (Vite, 39 modules); `make ci`; and `git diff --check`. The separate artifact-backed smoke passed as noted above.
- No authorized representative fall clip was available/identified. The RTMO→verified fall→MongoDB chain therefore remains **not demonstrated**; model-generated event provenance, fall accuracy, calibration, and representative dataset evaluation are not claimed.
- Automated tests are deterministic and do not download model weights. They cover source/worker shutdown, verifier gates, duplicate suppression, event-boundary behavior, provider normalization, and invalid/non-event sequences. The actual MongoDB exercise was a bounded manual integration demonstration, not an automated test that requires MongoDB.
- Browser visual/API-proxy verification was unavailable in this run; no local-browser rendering or console result is claimed.
- Remaining limits: local-academic-only RTMO artifact use while weight/training-data rights remain unresolved; geometric posture heuristics; one non-fall control clip; no live worker state or HTTP supervision; no webcam/RTSP, WebSocket, notifications, authentication, production deployment, or accuracy evidence. Phase 5 and the monitoring system remain incomplete.

## Phase 5D — Event provenance contract and authorized evaluation preparation — 3 October 2026

### A–F. Provenance audit and implementation

- Added a typed nullable `EventProvenance` embedded document on `EmergencyEvent`, alongside—not in place of—the existing event `context`. Its fields are `provider`, nullable `model_identifier`, nullable `model_version`, nullable `artifact_sha256`, `source_type`, `camera_id`, and timezone-aware `processed_at`.
- Added centralized event-service validation and typed construction. Provider and camera identity must be non-empty; source type must be supported; provenance camera ID must match the event's camera ID; processing time must be timezone-aware; optional model identity/version must be non-empty when supplied; and artifact SHA-256 must be exactly 64 hexadecimal characters (normalized lowercase). Unknown fields are rejected, and artifact digest is never treated as a model version.
- Provenance remains optional. Legacy callers and historical records may have no provenance and serialize additively as `provenance: null`; no historical model/source claims are inferred. Existing event fields remain unchanged. API nested validation and response tests cover the additive shape and invalid/unknown/mismatched inputs. The frontend does not require the new key and does not expose internal artifact details.
- The worker supplies provenance only on an actual verifier-approved event, from the active runtime provider/model, configured camera and source, and an aware UTC processing time. Provider/model fields are not hardcoded in the event service. Missing model version/digest remain `null`; no local model path is stored.
- RTMO-S identifies the configured model as `rtmo-s-body7`; no independent model-version metadata is available, so `model_version` stays `null`. After successful CPU session initialization, the adapter calculates SHA-256 once in 1 MiB chunks and retains it for that provider run. It does not hash on each frame or persist the artifact path. Tests mock the artifact/hash boundary, so normal tests do not need model weights.
- Deterministic coverage includes service-level provenance validation/construction, nullable legacy compatibility, API nested serialization/rejection, worker provenance and event gating, provider metadata forwarding, digest call count, and duplicate suppression/re-arm. No temporal thresholds or verifier principles were changed.

### G. Authorized evaluation material

No suitable authorized fall clip was identified in the repository or in the previously searched `/Users/dibakar/Documents/Code-Local` tree. Those searches do not establish absence elsewhere. No random footage was downloaded and no fall sequence was manufactured. The earlier Nairobi street-scene still/three-frame clip is non-fall control material only. Weight/training-data rights also remain unresolved beyond local academic evaluation.

### H–I. Model evaluation and MongoDB evidence

No Phase 5D real-model fall evaluation was performed because suitable authorized fall material was not identified. The Phase 5C RTMO control run remains the only real-worker model evidence: 3 frames, 24 observations, 8 tracks, 0 temporal decisions, 0 verified decisions, and 0 persisted events. The separate Phase 5C injected-observation event persisted through the actual service and isolated MongoDB, but it is not RTMO evidence. No model-backed MongoDB event or event-provenance document has been demonstrated.

### J–L. Verification, limitations, and next task

- Phase 5D focused provenance coverage passed: **66 passed**.
- Full repository verification from the repository root passed: `make check`, `make test` (**83 passed, 1 skipped**), `make compile`, `make build` (Vite, 39 modules), `make ci` (including its check/test/compile/build gates), and `git diff --check`. The test suite emitted two existing MongoEngine `datetime.utcnow()` deprecation warnings.
- Explicitly proven: real RTMO observations through the bounded worker on a non-fall control; separately, injected verifier-approved observations through the actual event service to MongoDB; deterministic provenance contract and validation tests. Not proven: an authorized fall sequence, an RTMO-generated verified fall, RTMO-backed MongoDB persistence, model accuracy, or calibration.
- Remaining limitations: provider weights/training-data rights, lack of authorized representative fall data, geometric posture heuristics rather than learned fall recognition, limited tracker evaluation, no webcam/RTSP, shared worker health, WebSocket publication, notifications, authentication, production deployment, or accuracy evidence.
- **Recommended next task:** obtain and document a suitably licensed/authorized, representative fall-evaluation video and its permitted local academic use; then run a bounded `run_monitor` evaluation with the currently unchanged provider/verifier. Record the outcomes even if no decision verifies. Do not calibrate on a single clip or claim a model-backed event unless the actual inference→verifier→service→MongoDB chain occurs.

## Verified dashboard boundaries

The UI is an operator-facing presentation and control surface, not a finished surveillance product:

- API responses are preferred when available.
- Synthetic presentation records are used when the API cannot be reached and are labeled in the UI.
- A reachable API does not automatically mean MongoDB persistence is healthy; health and persistence status are shown separately.
- Camera cards describe configured sources and monitoring intent. They do not render a physical feed in the current slice.
- Event confidence is a returned decision score, not accuracy, recall, precision, or a safety guarantee.
- The activity mix is derived from currently displayed event context and is a distribution view, not model evaluation.
- The interface keeps human review and local-only safety language visible.

## Frontend integrity, integration, and responsive audit — 30 September 2026

- Audited the React entry point, JSX views/components, shared API service, Vite API/WebSocket proxy, global styles, Django route/view/serializer contracts, and existing API tests.
- Confirmed the frontend read paths (`/api/`, health, capabilities, cameras, events, and monitoring status) and the camera-create / monitoring start-stop requests match the implemented API. Camera/event list responses carry `{items, count, persistence}`; unavailable persistence is distinguished from an empty saved-record set.
- API requests validate the supported response shapes, surface readable HTTP/API failures, deduplicate concurrent reads, invalidate affected pending reads after successful mutations, and guard dashboard state against stale loads. Camera configuration success is described as registration, not camera connectivity.
- Dashboard states distinguish API reachability from reported database health and process-local monitoring control state. `armed` is not described as a running worker; live updates are marked inactive. No React WebSocket client, polling loop, event lifecycle mutation control, or live worker publication is present.
- Synthetic camera/event fallbacks are called out as demo data; unavailable metrics do not masquerade as zero. Synthetic camera sources cannot be armed. Event states retain backend terminology, detected events are labelled potential/unverified, severity does not confirm an emergency, and event scores are not described as model accuracy.
- Camera cards remain feed placeholders. Camera creation options/fields match the Django serializer, including the URI requirement for RTSP and video-file sources. Event records use a locally scrollable wide-table wrapper rather than widening the whole page.
- Reviewed page width, grid/flex shrink behavior, responsive breakpoints, small-screen sidebar sizing, long-text wrapping, and focus styling. Mobile navigation includes an accessible menu relationship, focus return, Escape handling, and a focus boundary. Main views are in-memory navigation selections; there are no URL routes or per-view deep links.
- Source-level responsive/accessibility inspection is not a substitute for browser testing. The browser integration could not connect to a focused tab; visual behavior at the specified viewport widths, browser console, and Network panel therefore remain unverified.
- On 30 September 2026, the frontend integrity audit passed `make check`, `make test` (18 passed at that checkpoint), `make compile`, `make build` (Vite, 39 modules), `make -C web check-api` (API reachable at that checkpoint), `make ci`, and `git diff --check`. The updated Phase 5A suite subsequently passed the complete `make check`, `make test` (39 passed), `make compile`, `make build` (Vite, 39 modules), `make ci`, and `git diff --check` gates. These verify backend checks/tests, compilation, and frontend production build, not interactive React runtime behavior.
- Modified dashboard files: `web/src/App.jsx`, `web/src/services/api.js`, `web/src/styles.css`, `web/src/components/ActivityMix.jsx`, `web/src/components/CameraGrid.jsx`, `web/src/components/EventTable.jsx`, `web/src/components/Sidebar.jsx`, and `web/src/components/Topbar.jsx`.

## Repository and asset review

- Official branding is supplied at `public/Logo.png` and `public/Banner.png`.
- The Vite configuration serves the repository-level `public/` directory.
- Generated media, raw captures, model artifacts, dependencies, caches, and logs remain ignored by default.
- The supplied PNG exceptions are intentionally narrow so only the official assets are trackable.
- Personal-name references are absent from product UI and branding; legally required license attribution remains in `LICENSE` and the plan's license note.
- The README contains no machine-specific absolute path and points only to files present in the repository.

## Verification commands

From the repository root:

```bash
make check
make test
make compile
make build
make ci
git diff --check
```

For focused checks:

```bash
make test-vision
make test-api
make -C app check
make -C web build
make -C web check-api
make -C web dev -- --force   # diagnostic UI startup without a reachable backend
```

## Next delivery gates

1. Keep RTMO-S use restricted to local academic evaluation until weight/training-data rights are resolved; validate posture and the temporal rule on representative, authorized clips.
2. Demonstrate one model-backed temporally verified event persisted via real worker/service/MongoDB wiring without weakening gates.
3. Add webcam and later RTSP adapters behind the existing camera-source contract.
4. Establish truthful shared worker lifecycle/health state and decide how (or whether) HTTP monitoring intent supervises worker processes.
5. Publish live worker state/events through authenticated sessions and WebSocket delivery; add human-reviewed event workflow and notifications later.
6. Publish no model/fall performance claims until representative evaluation and artifact rights are cleared.
7. Keep normal local startup ordered as MongoDB → backend → frontend; use service-level `--force` only for explicit diagnostics.
