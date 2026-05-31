# DESIGN.md — Purplle Store Intelligence System

## System Overview

An end-to-end pipeline that ingests raw CCTV footage, detects and tracks persons, emits structured events, computes business metrics (footfall, conversion, dwell time, anomalies), and serves them via a REST API with a live dashboard.

```
CCTV Feeds → Frame Sampler → YOLO Detector → ByteTracker → Event Engine
                                                               ↓
                                                        Redis Streams
                                                               ↓
                                                      Analytics Aggregator
                                                               ↓
                                                   SQLite (persistence)
                                                               ↓
                                                    FastAPI REST Server
                                                               ↓
                                                     Static HTML Dashboard
```

---

## Components

### 1. Video Ingestion (`ingestion/reader.py`)
- Reads from RTSP streams or local MP4 files via `cv2.VideoCapture`
- Samples at **5 FPS** (configurable) to balance CPU load vs temporal resolution
- Supports multi-camera setup via thread-per-camera workers
- Frame buffer: `queue.Queue(maxsize=30)` per camera to handle downstream slowness

### 2. Person Detection (`vision/detector.py`)
- **Model**: YOLOv8n (nano variant) exported to ONNX
- Class filter: `person` only (class 0)
- Confidence threshold: 0.45
- NMS IoU threshold: 0.5
- Runs on CPU via ONNX Runtime — no GPU dependency

### 3. Multi-Object Tracking (`vision/tracker.py`)
- **Algorithm**: ByteTrack (BYTE association)
- Maintains stable track IDs across frames even during brief occlusion
- Track lifecycle: `tentative → confirmed → lost → deleted`
- Track ID is the unique visitor identifier within a camera session

### 4. Re-entry & Staff Logic (`vision/reid.py`)
- **Re-entry**: Track ID expiry + appearance embedding (MobileNetV2 crops) + 5-minute cooldown window. If a person re-enters within 5 min with >0.75 cosine similarity, they are counted as a re-entry, not a new visitor.
- **Staff exclusion**: Staff wear branded uniforms. A lightweight colour histogram check on the upper-body region + zone-based heuristics (staff lounge zone) excludes their movement from visitor counts.
- **Group entry**: Persons entering in a cluster (spatial proximity < 80px, within 2 seconds) are flagged as a group via `group_id`.

### 5. Event Engine (`events/emitter.py`)
Event schema:
```json
{
  "event_id": "evt_20260410_165536_0042",
  "track_id": 42,
  "event_type": "ENTRY | EXIT | REENTRY | DWELL",
  "timestamp": "2026-04-10T16:55:36Z",
  "zone": "ENTRANCE_LEFT",
  "confidence": 0.93,
  "is_staff": false,
  "group_id": null,
  "camera_id": "CAM_01"
}
```
Events are written to **Redis Streams** (`XADD store:events *`), providing replay, fan-out, and persistence.

### 6. Analytics Aggregator (`analytics/aggregator.py`)
Consumes the Redis stream (`XREAD`) and maintains in-memory counters:
- Footfall (unique track IDs per day, excluding staff, deduplicating re-entries)
- Conversion rate = unique purchasing visitors / total footfall
- Dwell time = EXIT timestamp − ENTRY timestamp per track
- Zone heatmap = count of DWELL events per zone cell
- Hourly bucketing for temporal analysis

Persists aggregated metrics to **SQLite** every 60 seconds for durability.

### 7. Anomaly Detection (`analytics/anomaly.py`)
Rule-based + statistical:
| Rule | Threshold | Severity |
|------|-----------|----------|
| Rapid transactions | >4 orders in 20 min | HIGH |
| Re-entry rate | >4% of footfall | HIGH |
| Staff-zone overlap | Staff in customer zones during peak | MEDIUM |
| Zero revenue window | 0 transactions during >30 footfall hour | MEDIUM |
| Late-hour spike | Traffic >1.5σ above hourly mean | LOW |

### 8. REST API (`api/server.py`)
Built with **FastAPI**. Endpoints:
- `GET /metrics` — Store-level KPIs
- `GET /funnel` — Conversion funnel steps (session-based)
- `GET /events?limit=50&page=1` — Paginated event stream
- `GET /anomalies` — Detected anomalies
- `GET /heatmap` — Zone intensity grid

Response caching: 30-second TTL via `fastapi-cache2` with Redis backend.

### 9. Dashboard (`index.html`)
- Single-file static HTML — deploys to GitHub Pages, Netlify, or any CDN
- Chart.js for all visualizations
- 7 tabs: Overview, Funnel, Traffic, Sales, Anomalies, API Docs, System Design
- In production, fetches live data from the FastAPI server; demo uses embedded JSON

---

## Deployment

```bash
docker compose up   # starts all services: redis, pipeline, api, dashboard
```

Services:
- `redis:7` — event stream + cache
- `pipeline` — video ingestion + detection + tracking + event emission
- `api` — FastAPI server on port 8000
- `dashboard` — Nginx serving `index.html` on port 3000

Health checks, restart policies, and volume mounts for video files are all configured in `docker-compose.yml`.

---

## Data Flow Guarantees

- Events are immutable once written to Redis Streams
- Aggregator uses consumer groups — no event processed twice
- SQLite WAL mode for concurrent read/write
- API is stateless — horizontally scalable behind a load balancer
