# 🏪 Purplle Store Intelligence System
### Brigade Road, Bangalore · UpGrad Placements Challenge — April 2026

> An end-to-end AI-powered pipeline that transforms raw CCTV footage into actionable retail business metrics.

**🔗 [Live Dashboard →](https://your-username.github.io/store-intelligence/)**

---

## What This Builds

```
CCTV Footage → Person Detection (YOLOv8n) → Multi-Object Tracking (ByteTrack)
    → Re-entry / Staff Filtering → Event Streaming (Redis)
    → Analytics Engine → REST API (FastAPI) → Live Dashboard
```

**Business metrics produced:**
- Store footfall (unique visitors, excluding staff & re-entries)
- Conversion rate (purchasers / visitors)
- Dwell time per visitor
- Zone-level heatmap
- Conversion funnel (entry → engagement → product touch → checkout → purchase)
- Anomaly detection (rule-based + statistical)

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/your-username/store-intelligence.git
cd store-intelligence

# 2. Add your video file
mkdir data
cp /path/to/cctv_footage.mp4 data/sample.mp4

# 3. Run everything
docker compose up

# Dashboard: http://localhost:3000
# API:       http://localhost:8000/metrics
```

That's it. One command.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/metrics` | Store-level KPIs (footfall, conversion, GMV) |
| GET | `/funnel` | Conversion funnel steps |
| GET | `/events` | Paginated detection event stream |
| GET | `/anomalies` | Flagged anomalies with severity |
| GET | `/heatmap` | Zone intensity grid (10×6) |
| GET | `/health` | Service health check |

Full API docs: [api-reference.md](docs/api-reference.md)

---

## Sample API Response

```bash
curl http://localhost:8000/metrics
```

```json
{
  "footfall": 284,
  "conversion_rate": 0.085,
  "gmv": 44920,
  "nmv": 34831,
  "avg_basket": 1872,
  "avg_dwell_minutes": 14.2,
  "peak_hour": "19:00",
  "total_transactions": 24,
  "anomaly_count": 7,
  "store_id": "ST1008",
  "date": "2026-04-10"
}
```

---

## Key Engineering Decisions

See [CHOICES.md](CHOICES.md) for full trade-off reasoning. Summary:

| Decision | Choice | Why |
|----------|--------|-----|
| Detection | YOLOv8n ONNX | Runs on CPU, no GPU needed |
| Tracking | ByteTrack | Fast, no external ReID model |
| Streaming | Redis Streams | Lightweight, replay-able |
| Storage | SQLite (WAL) | Zero-config, portable |
| Anomaly | Rule-based | Explainable, no training data needed |
| Frontend | Static HTML | GitHub Pages, zero infra |

---

## System Architecture

See [DESIGN.md](DESIGN.md) for detailed architecture.

---

## Tech Stack

- **Vision**: OpenCV + YOLOv8n (ONNX Runtime) + ByteTrack
- **Backend**: FastAPI + Python 3.11
- **Streaming**: Redis 7 (Streams + Cache)
- **Storage**: SQLite with WAL mode
- **Observability**: Structured logging (structlog) + Prometheus metrics
- **Deployment**: Docker Compose (single command)
- **Dashboard**: Vanilla HTML + Chart.js (GitHub Pages)

---

## Project Structure

```
store-intelligence/
├── index.html              # Live dashboard (GitHub Pages)
├── docker-compose.yml      # One-command deployment
├── DESIGN.md               # System architecture
├── CHOICES.md              # Engineering decisions & trade-offs
├── README.md               # This file
├── Dockerfile.pipeline     # CCTV pipeline container
├── Dockerfile.api          # FastAPI container
├── ingestion/
│   └── reader.py           # Video frame sampler
├── vision/
│   ├── detector.py         # YOLOv8 person detection
│   ├── tracker.py          # ByteTrack wrapper
│   └── reid.py             # Re-entry & staff filtering
├── events/
│   └── emitter.py          # Redis Stream event writer
├── analytics/
│   ├── aggregator.py       # Metric computation
│   └── anomaly.py          # Anomaly detection rules
├── api/
│   └── server.py           # FastAPI REST server
├── data/                   # Video files (gitignored)
└── docs/
    └── api-reference.md    # Full API documentation
```

---

## Dashboard Tabs

1. **Overview** — KPIs, hourly footfall vs sales, category & brand breakdown
2. **Conversion Funnel** — Session-based funnel, conversion by hour, offer effectiveness
3. **Traffic & Heatmap** — Entry/exit timeline, zone heatmap, dwell time distribution
4. **Sales Intel** — Transaction log, sub-category breakdown, cumulative GMV
5. **Anomalies** — Detected events with severity, timeline scatter plot
6. **API Docs** — Live endpoint documentation with sample responses
7. **System Design** — Architecture, tech stack, design choices

---

## Data Used

- **Store**: Brigade Road, Bangalore (ST1008)
- **Date**: April 10, 2026
- **Sales CSV**: 24 unique orders, 101 line items, ₹44,920 GMV
- **Store Layout**: Brigade Road floor plan (10×6 zone grid)

---

*Built for UpGrad Placements — Purplle Tech Challenge 2026, Round 2*
