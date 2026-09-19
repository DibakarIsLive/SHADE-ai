const ago = (minutes) => new Date(Date.now() - minutes * 60_000).toISOString();

export const presentationEvents = [
  {
    event_id: "demo-001",
    event_type: "Fall verification",
    severity: "critical",
    status: "verified",
    camera_id: "synthetic-demo",
    track_id: "person-01",
    confidence: 0.94,
    duration_seconds: 1.8,
    occurred_at: ago(4),
    context: { activity: "lying", zone: "Living room" },
  },
  {
    event_id: "demo-002",
    event_type: "Motionless posture",
    severity: "warning",
    status: "acknowledged",
    camera_id: "synthetic-demo",
    track_id: "person-01",
    confidence: 0.81,
    duration_seconds: 12.4,
    occurred_at: ago(18),
    context: { activity: "motionless", zone: "Living room" },
  },
  {
    event_id: "demo-003",
    event_type: "Monitoring session started",
    severity: "info",
    status: "resolved",
    camera_id: "synthetic-demo",
    track_id: "",
    confidence: 1,
    duration_seconds: 0,
    occurred_at: ago(42),
    context: { activity: "standing", zone: "Entryway" },
  },
];

export const presentationCameras = [
  {
    camera_id: "synthetic-demo",
    name: "Synthetic demo feed",
    source_type: "synthetic",
    location: "Living room",
    status: "ready",
    enabled: true,
  },
];

export const activityMix = [
  { label: "Walking", value: 38, color: "mint" },
  { label: "Standing", value: 29, color: "blue" },
  { label: "Sitting", value: 21, color: "violet" },
  { label: "Other", value: 12, color: "slate" },
];
