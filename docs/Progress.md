# SHADE-ai Progress

## Review snapshot

**Review scope:** backend/API foundation, vision contracts, monitoring control plane, React dashboard, supplied branding, documentation, and repository quality gates.

**Status:** foundation slice implemented; production camera/model and responder integrations remain deferred.

**Operating principle:** `OBSERVE → ANALYZE → VERIFY → RESPOND`

## Verified implementation matrix

| Area | Status | Verified behavior |
| --- | --- | --- |
| Django project | Implemented | Split settings, API routing, health, capabilities, and local development configuration exist under `app/`. |
| MongoDB boundary | Implemented | MongoEngine documents persist camera configuration and emergency-event metadata when MongoDB is reachable. |
| Health diagnostics | Implemented | `/api/health/` reports healthy/degraded status, bounded database diagnostics, runtime configuration, monitoring state, and safety flags. |
| Camera API | Implemented | Camera list/create contracts validate supported source types; RTSP and video-file inputs require a source URI. |
| Event API | Implemented | Event list/create contracts validate severity, lifecycle status, camera ID, confidence, duration, frame count, and context. |
| Vision contracts | Implemented | Frame, detection, tracking, pose, observation, decision, source, and pipeline interfaces are vendor-neutral. |
| Temporal fall rule | Implemented | Bounded evidence, upright-to-low transition, sustained low posture, duration, and confidence gates are represented and tested. |
| Synthetic vision source | Implemented | Deterministic synthetic and iterable sources support development and repeatable tests. |
| Monitoring control plane | Implemented with boundary | Start/stop changes process-local intent state and creates a local session identifier; it does not launch a camera worker. |
| WebSocket route | Boundary only | A read-oriented monitoring consumer and route exist; live worker event publication is not connected. |
| React dashboard | Implemented | Responsive JSX dashboard loads API snapshots, presents safe fallback data, exposes review/source views, and includes accessible status and action labels. |
| Branding | Implemented | Supplied `public/Logo.png` and `public/Banner.png` are used by the dashboard and are explicitly unignored for version control. |
| Presentation fallback | Implemented | Synthetic data is runtime-relative, visibly labeled, and separated from live camera/model claims. |
| Authentication | Planned | Operator authentication and authorization are not implemented. |
| Physical camera capture | Deferred/experimental | No webcam or RTSP adapter is connected; current source implementations are synthetic/iterable. |
| Detector and pose models | Deferred/experimental | Vendor-neutral interfaces exist, but validated production model artifacts and adapters are not connected. |
| Worker loop | Deferred | The management-worker architecture is planned; current HTTP monitoring state is process-local only. |
| Notifications | Deferred | No production email/SMS/push delivery workflow is connected. |
| Event review mutations | Deferred | Event creation exists; acknowledge, investigate, resolve, and false-positive UI/API workflows are not complete. |
| Retention scheduler | Planned | Retention policy fields/boundaries may exist, but automated cleanup is not implemented. |
| Accuracy claims | Not established | No representative evaluation result should be inferred from dashboard event scores or synthetic data. |

## Verified dashboard boundaries

The UI is an operator-facing presentation and control surface, not a finished surveillance product:

- API responses are preferred when available.
- Synthetic presentation records are used when the API cannot be reached and are labeled in the UI.
- A reachable API does not automatically mean MongoDB persistence is healthy; health and persistence status are shown separately.
- Camera cards describe configured sources and monitoring intent. They do not render a physical feed in the current slice.
- Event confidence is a returned decision score, not accuracy, recall, precision, or a safety guarantee.
- The activity mix is derived from currently displayed event context and is a distribution view, not model evaluation.
- The interface keeps human review and local-only safety language visible.

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
```

For focused checks:

```bash
make test-vision
make test-api
make -C app check
make -C web build
```

## Next delivery gates

1. Implement a real, tested camera-source adapter without changing the vendor-neutral contracts.
2. Add detector and pose adapters with provenance, licensing, resource, and evaluation documentation.
3. Run a dedicated worker outside HTTP request handling and persist only deliberate event/activity transitions.
4. Connect live worker state to authenticated dashboard sessions and WebSocket publication.
5. Add human-reviewed event lifecycle mutations, notification dry runs, retention controls, and deployment tests.
6. Publish evaluation results before presenting detection performance as a project claim.
