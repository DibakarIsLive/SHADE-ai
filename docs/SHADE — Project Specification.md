# SHADE

## Smart Human Activity Detection and Emergency System

> **Project Specification — v1.0**

---

## 1. Project Overview

**SHADE (Smart Human Activity Detection and Emergency System)** is an AI-powered monitoring system designed to detect human activities from a live camera feed, identify potentially dangerous or abnormal situations, and automatically trigger an emergency response when required.

The system combines **computer vision, human activity recognition, real-time event processing, and emergency notifications** into a single platform.

The primary goal is not simply to detect whether a person exists in a video.

The goal is to understand:

> **"What is the person doing, and does that activity require attention?"**

For example:

```text
Camera
   ↓
Human Detection
   ↓
Activity / Pose Analysis
   ↓
Activity Classification
   ↓
Is the activity dangerous?
   ↓
 ┌───────────────┐
 │               │
 NO              YES
 │               │
 ↓               ↓
Continue       Verify Event
Monitoring        ↓
              Emergency?
                  ↓
              Send Alert
```

---

# 2. Problem Statement

Traditional CCTV systems primarily act as passive recording systems.

A human operator must continuously watch the footage to identify situations such as:

- A person falling
- A person remaining motionless
- Physical confrontation
- A person entering a restricted area
- Potential accidents
- Other predefined emergency situations

Continuous human monitoring is expensive, tiring, and prone to missed events.

SHADE aims to automate this monitoring process by using AI to continuously analyze camera footage and identify activities that may require human intervention.

---

# 3. Core Objective

SHADE should be capable of:

1. Detecting people in video footage.
2. Tracking detected people across consecutive frames.
3. Analyzing their movement and body posture.
4. Identifying predefined human activities.
5. Distinguishing normal activities from potentially dangerous activities.
6. Verifying dangerous events using multiple frames rather than relying on a single frame.
7. Creating an emergency event when a dangerous situation is confirmed.
8. Recording the event.
9. Notifying a designated person/system.
10. Providing a dashboard for monitoring detected events.

---

# 4. Core Concept

The fundamental concept of SHADE is:

```text
DETECT
   ↓
TRACK
   ↓
UNDERSTAND
   ↓
VERIFY
   ↓
RESPOND
```

### Detect

Find humans in the camera frame.

### Track

Maintain the identity/location of each detected person across frames.

### Understand

Analyze movement, position, posture, and activity.

### Verify

Determine whether the detected activity is actually an emergency.

### Respond

Generate an alert and record the incident.

---

# 5. Example Scenario — Fall Detection

Suppose a person is walking.

```text
Frame 1
Person standing
       ↓
Frame 2
Person moving
       ↓
Frame 3
Person losing vertical posture
       ↓
Frame 4
Person becomes horizontal
       ↓
Frame 5
Person remains on ground
       ↓
Frame 6
Person remains motionless
```

SHADE should not immediately trigger an emergency simply because the person became horizontal.

Instead, it can use a sequence of observations:

```text
Vertical posture
      ↓
Rapid posture change
      ↓
Horizontal posture
      ↓
No significant movement
      ↓
FALL CONFIRMED
      ↓
Emergency Event
```

This reduces false alarms.

---

# 6. Initial Activity Categories

The first version of SHADE can focus on a small number of activities.

### Normal Activities

```text
WALKING
STANDING
SITTING
RUNNING
```

### Potentially Dangerous Activities

```text
FALLING
LYING MOTIONLESS
FIGHTING / PHYSICAL ALTERCATION
```

### Security-Related Events

```text
RESTRICTED AREA ENTRY
UNAUTHORIZED PRESENCE
```

The exact activity list should remain configurable.

The system should be designed so that additional activities can be added later without rebuilding the entire application.

---

# 7. System Architecture

A high-level architecture could look like this:

```text
                    ┌─────────────────┐
                    │     CAMERA      │
                    │ Webcam / CCTV   │
                    └────────┬────────┘
                             │
                             ↓
                    ┌─────────────────┐
                    │ VIDEO PROCESSOR │
                    │     OpenCV      │
                    └────────┬────────┘
                             │
                             ↓
                    ┌─────────────────┐
                    │ HUMAN DETECTOR  │
                    │      YOLO       │
                    └────────┬────────┘
                             │
                             ↓
                    ┌─────────────────┐
                    │ PERSON TRACKER  │
                    │ Tracking System │
                    └────────┬────────┘
                             │
                             ↓
                    ┌─────────────────┐
                    │ POSE / ACTIVITY │
                    │    ANALYSIS     │
                    └────────┬────────┘
                             │
                             ↓
                    ┌─────────────────┐
                    │ EVENT ENGINE    │
                    │ Normal / Danger │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    ↓                 ↓
              NORMAL EVENT        EMERGENCY
                    │                 │
                    ↓                 ↓
                Logging          Verification
                                      │
                                      ↓
                                ┌─────────────┐
                                │ ALERT ENGINE│
                                └──────┬──────┘
                                       │
                         ┌─────────────┼─────────────┐
                         ↓             ↓             ↓
                       Email          SMS        Dashboard
                                       │
                                       ↓
                                  Event Database
```

---

# 8. Major System Components

## 8.1 Camera Input Module

Responsible for obtaining video frames.

Possible sources:

```text
Webcam
CCTV camera
IP camera
Recorded video
```

For development, a normal laptop webcam should be sufficient.

---

## 8.2 Video Processing Module

Responsible for:

- Reading frames
- Resizing frames
- Frame-rate management
- Image preprocessing
- Passing frames to AI models

Likely technology:

```text
OpenCV
NumPy
```

---

## 8.3 Human Detection Module

The first AI layer identifies humans inside the frame.

Example:

```text
                 CAMERA FRAME

       ┌─────────────────────────────┐
       │                             │
       │       ┌───────┐             │
       │       │Person │             │
       │       └───────┘             │
       │                             │
       │              ┌───────┐      │
       │              │Person │      │
       │              └───────┘      │
       │                             │
       └─────────────────────────────┘
```

A YOLO-based detector can provide:

```text
Bounding Box
Confidence
Class
```

Example:

```python
{
    "class": "person",
    "confidence": 0.94,
    "bbox": [...]
}
```

---

# 9. Person Tracking

Detection alone is not enough.

SHADE needs to know whether:

```text
Person A
at Frame 1
```

is the same person as:

```text
Person A
at Frame 2
```

Tracking allows the system to maintain something like:

```text
Person ID: 17

Frame 101 → standing
Frame 102 → walking
Frame 103 → walking
Frame 104 → falling
Frame 105 → lying
```

This becomes extremely useful for activity recognition.

---

# 10. Pose / Human Activity Analysis

Human activity cannot always be determined reliably from a bounding box alone.

For example:

```text
Standing
     ↓
 ┌───────┐
 │   O   │
 │   │   │
 │  / \  │
 └───────┘
```

versus:

```text
Lying
     ↓
 ┌────────────┐
 │ O────────  │
 └────────────┘
```

Therefore SHADE can use human pose information such as:

```text
Head
Shoulders
Elbows
Wrists
Hips
Knees
Ankles
```

A pose-estimation system can provide these keypoints.

Example:

```text
Person
   ↓
Pose Model
   ↓
Keypoints
   ↓
Posture Analysis
   ↓
Activity
```

Possible technology:

```text
MediaPipe
YOLO Pose
Other pose-estimation models
```

---

# 11. Activity Recognition Engine

This is one of the most important components.

It takes information such as:

```text
Person location
Body keypoints
Movement
Velocity
Posture
Previous frames
Duration
```

and determines the current activity.

Example:

```text
Input:

Posture = horizontal
Movement = very low
Duration = 8 seconds

        ↓

Activity Engine

        ↓

LYING / POSSIBLE FALL
```

---

# 12. Temporal Analysis

SHADE should analyze **multiple frames**, not just individual frames.

This is critical.

A single frame might show:

```text
Person lying down
```

But that could mean:

```text
Someone intentionally lying down
```

or:

```text
Someone has fallen
```

The difference can be determined by looking at what happened before it.

For example:

```text
Standing
   ↓
Walking
   ↓
Rapid downward movement
   ↓
Horizontal posture
   ↓
No movement
```

is much more suspicious than:

```text
Walking
   ↓
Walking
   ↓
Person slowly sits
   ↓
Sitting
```

Therefore SHADE should maintain a short history of activity states.

Example:

```python
activity_history = [
    "walking",
    "walking",
    "falling",
    "lying",
    "motionless"
]
```

---

# 13. Emergency Verification

The system should avoid triggering an emergency from one uncertain prediction.

Instead:

```text
Potential Danger
       ↓
Confidence Check
       ↓
Duration Check
       ↓
Previous Activity Check
       ↓
Emergency Confirmation
```

Example rule:

```text
IF

fall probability > threshold

AND

horizontal posture detected

AND

little/no movement for N seconds

THEN

create emergency event
```

The actual thresholds should be configurable.

---

# 14. Emergency Event

Once an emergency is confirmed, SHADE creates an event.

Example:

```text
Emergency Event
────────────────────────────

Event ID:       EVT-000124
Type:           FALL
Person ID:      17
Confidence:     94%
Camera:         Camera-01
Time:           18:42:17
Location:       Room A

Status:         UNRESOLVED
```

The event should be stored in the database.

---

# 15. Alert System

After an emergency event is created, the alert engine can notify designated recipients.

Possible channels:

```text
Email
SMS
Push Notification
Dashboard Alert
Local Alarm
```

For example:

```text
🚨 SHADE EMERGENCY

Possible fall detected.

Camera: Camera-01
Location: Room A
Time: 18:42

Please check immediately.
```

The first version can start with **dashboard + email**.

Other notification channels can be added later.

---

# 16. Dashboard

A web dashboard can provide real-time monitoring.

Possible dashboard sections:

```text
┌──────────────────────────────────────────┐
│                  SHADE                   │
├──────────────────────────────────────────┤
│                                          │
│  LIVE CAMERA                             │
│  ┌──────────────────────────────┐        │
│  │                              │        │
│  │       LIVE VIDEO FEED        │        │
│  │                              │        │
│  └──────────────────────────────┘        │
│                                          │
│  Current Activity: WALKING               │
│  People Detected: 3                      │
│                                          │
├──────────────────────────────────────────┤
│ RECENT EVENTS                            │
│                                          │
│ 🚨 Fall       Camera 01     18:42        │
│ ⚠ Restricted Camera 02     18:31         │
│ ✓ Walking    Camera 01     18:25         │
│                                          │
└──────────────────────────────────────────┘
```

---

# 17. Database

The database can store:

### Users

```text
id
name
email
role
password_hash
```

### Cameras

```text
id
name
location
source
status
```

### Activity Events

```text
id
camera_id
person_id
activity
confidence
timestamp
duration
```

### Emergency Events

```text
id
activity_event_id
emergency_type
confidence
timestamp
status
resolved_at
```

### Alerts

```text
id
emergency_event_id
channel
recipient
sent_at
status
```

---

# 18. Suggested Technology Stack

## AI / Computer Vision

```text
Python
OpenCV
YOLO
Pose Estimation
NumPy
PyTorch
```

## Backend

One possible implementation:

```text
Django
Django REST Framework
```

Alternatively:

```text
FastAPI
```

## Database

Development:

```text
SQLite
```

Production:

```text
PostgreSQL
```

## Frontend

Possible options:

```text
React
```

or a simpler:

```text
HTML
CSS
JavaScript
```

## Real-Time Communication

For live events:

```text
WebSockets
```

Django Channels could be used if Django is selected.

---

# 19. Recommended Project Structure

A possible architecture:

```text
shade/
│
├── backend/
│   ├── manage.py
│   │
│   ├── users/
│   ├── cameras/
│   ├── activities/
│   ├── emergencies/
│   ├── notifications/
│   └── dashboard/
│
├── ai/
│   ├── detection/
│   ├── tracking/
│   ├── pose/
│   ├── activity/
│   └── models/
│
├── video/
│   ├── camera.py
│   ├── processor.py
│   └── stream.py
│
├── config/
│   ├── settings/
│   └── constants.py
│
├── tests/
│
├── requirements.txt
│
└── README.md
```

The exact structure can change once implementation begins.

---

# 20. Processing Pipeline

The complete pipeline should look approximately like:

```text
Camera
  │
  ↓
Frame Capture
  │
  ↓
Preprocessing
  │
  ↓
Person Detection
  │
  ↓
Person Tracking
  │
  ↓
Pose Estimation
  │
  ↓
Activity Recognition
  │
  ↓
Temporal Analysis
  │
  ↓
Emergency Verification
  │
  ├──────────────→ Normal → Log
  │
  ↓
Emergency
  │
  ↓
Create Event
  │
  ├──────────────→ Database
  │
  ├──────────────→ Dashboard
  │
  └──────────────→ Notification
```

---

# 21. False Positive Prevention

A serious emergency system must consider false alarms.

For example:

```text
Person intentionally lies down
```

should not necessarily become:

```text
🚨 MEDICAL EMERGENCY
```

Therefore SHADE should consider multiple signals:

```text
Posture
+
Movement
+
Movement speed
+
Previous activity
+
Duration
+
Model confidence
```

This is much better than:

```text
IF person is horizontal:
    EMERGENCY
```

💀

---

# 22. Event Severity

A useful extension is to assign event severity.

```text
INFO
│
├── Normal activity
│
WARNING
│
├── Suspicious activity
│
HIGH
│
├── Potential emergency
│
CRITICAL
│
└── Confirmed emergency
```

This allows the dashboard and notification system to behave differently depending on the severity.

---

# 23. Privacy Considerations

Because SHADE processes human video, privacy should be considered from the beginning.

Possible measures:

- Process video locally where practical.
- Avoid unnecessary long-term video storage.
- Store event metadata rather than entire recordings when possible.
- Restrict dashboard access.
- Authenticate users.
- Encrypt sensitive communication.
- Provide configurable retention periods.

---

# 24. MVP — Minimum Viable Product

Do **not** try to build everything simultaneously.

The first working version should be:

```text
Webcam
   ↓
OpenCV
   ↓
YOLO
   ↓
Person Detection
   ↓
Pose Estimation
   ↓
Basic Fall Detection
   ↓
Emergency Event
   ↓
Dashboard Alert
```

If this works reliably, expand it.

---

# 25. Phase-Based Development

## Phase 1 — Computer Vision Foundation

Build:

```text
Camera Input
+
OpenCV
+
YOLO Person Detection
```

Goal:

> Detect people in real time.

---

## Phase 2 — Tracking

Add:

```text
Person IDs
+
Movement Tracking
```

Goal:

> Know which detected person is which across frames.

---

## Phase 3 — Pose

Add:

```text
Pose Estimation
+
Keypoints
```

Goal:

> Understand body posture.

---

## Phase 4 — Activity Recognition

Implement:

```text
Standing
Walking
Sitting
Running
Lying
Falling
```

Goal:

> Convert raw visual information into activities.

---

## Phase 5 — Emergency Engine

Implement:

```text
Activity
+
Temporal Analysis
+
Rules
=
Emergency Decision
```

Goal:

> Detect genuine emergency situations.

---

## Phase 6 — Backend

Build:

```text
Django
+
Database
+
REST API
```

Goal:

> Store and expose system events.

---

## Phase 7 — Dashboard

Build:

```text
Live Feed
+
Current Activities
+
Emergency Alerts
+
Event History
```

Goal:

> Give humans a central monitoring interface.

---

## Phase 8 — Notifications

Add:

```text
Email
SMS
Push
```

Goal:

> Notify someone even when they aren't watching the dashboard.

---

# 26. Future Extensions

SHADE could eventually support:

### Advanced Activity Recognition

```text
Fighting
Running
Climbing
Crawling
Waving
Aggressive movement
```

### Multi-Camera Monitoring

```text
Camera 1
Camera 2
Camera 3
Camera 4
       ↓
Central SHADE Server
```

### IoT Integration

```text
SHADE
  ↓
ESP32
  ↓
Siren / Buzzer
```

### Smart Emergency Response

The system could eventually determine:

```text
WHAT happened?
WHERE did it happen?
WHEN did it happen?
HOW severe is it?
WHO should be notified?
```

---

# 27. Example End-to-End Scenario

Imagine SHADE is installed in a laboratory.

A person is walking normally.

```text
Activity = WALKING
```

No alert is generated.

The person suddenly falls.

```text
Activity sequence:

WALKING
   ↓
FALLING
   ↓
LYING
   ↓
MOTIONLESS
```

SHADE detects the transition.

It calculates:

```text
Fall confidence = 93%
Duration motionless = 7 seconds
Previous activity = Walking
```

The emergency engine confirms the event.

```text
🚨 EMERGENCY DETECTED
```

The system then:

```text
1. Saves the event
2. Captures relevant evidence if configured
3. Updates the dashboard
4. Sends an alert
5. Marks the event as unresolved
```

A human operator checks the dashboard.

```text
Event → Investigated
```

After the situation is handled:

```text
Status → RESOLVED
```

---

# 28. Core Design Principle

SHADE should **not** be designed as simply:

> "AI sees something → immediately send an alarm."

Instead:

> **Observe → Analyze → Verify → Respond**

This principle should guide the entire project.

---

# 29. Final Vision

The long-term vision of SHADE is to create an intelligent monitoring platform that can transform ordinary cameras into **context-aware safety systems**.

Instead of merely recording what happened, SHADE attempts to recognize:

```text
WHAT is happening?
        +
IS it unusual?
        +
IS it dangerous?
        +
DOES someone need to respond?
```

The final system should therefore combine:

```text
Computer Vision
       +
Artificial Intelligence
       +
Activity Recognition
       +
Real-Time Processing
       +
Backend Engineering
       +
Database
       +
Emergency Notification
       +
Human Monitoring
```

into one integrated system.

---

## 30. One-Line Definition

> **SHADE is an AI-powered real-time surveillance and emergency-response system that detects human activities, analyzes potentially dangerous situations, verifies emergencies using temporal context, and alerts designated responders.**
