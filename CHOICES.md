# CHOICES.md — Engineering Decisions & Trade-offs

## 1. YOLOv8n (nano) over YOLOv8x or YOLOv9

**Decision**: Use the nano variant.

**Reasoning**: The challenge runs on a reviewer's laptop. YOLOv8x gives ~3% better mAP on COCO but requires a GPU and would fail `docker compose up` on most machines. YOLOv8n at 5 FPS on CPU detects 85-90% of persons in retail settings, which is sufficient for counting. The business metric (conversion rate) tolerates ±5% counting error far better than it tolerates a pipeline that doesn't run.

**Trade-off accepted**: We lose some accuracy on partially occluded or very distant persons. Mitigated by tuning the confidence threshold down to 0.45 for recall at the cost of a few false positives.

---

## 2. ByteTrack over DeepSORT or StrongSORT

**Decision**: ByteTrack for multi-object tracking.

**Reasoning**: ByteTrack uses no external ReID model during tracking — it associates detections using IoU alone, plus a "low confidence" bin to recover lost tracks. This makes it faster and removes a GPU dependency. DeepSORT's ReID step adds 15-20ms per frame which would drop us below real-time at 5 FPS on CPU.

**Trade-off accepted**: ByteTrack can swap IDs when people cross paths or are occluded for > 2 seconds. We mitigate this with a track history buffer and appearance re-check on re-association.

---

## 3. Redis Streams over Kafka

**Decision**: Redis Streams as the event backbone.

**Reasoning**: Kafka is the "enterprise" answer but requires ZooKeeper or KRaft, multiple broker nodes, and adds ~500MB to the Docker stack. Redis Streams gives us 95% of what we need: append-only log, consumer groups, replay, fan-out. For a single-store, single-day event volume (~5,000 events/day), Redis is perfectly sized and requires one `redis:7` container.

**Trade-off accepted**: Redis is not as durable as Kafka under catastrophic failure. Mitigated by Redis AOF persistence and SQLite checkpointing.

---

## 4. SQLite over PostgreSQL

**Decision**: SQLite for metric persistence.

**Reasoning**: PostgreSQL is the right choice for multi-store, multi-user production. For this challenge (single store, single day, single reviewer), SQLite running in WAL mode is sufficient, zero-config, and ships inside the container — no extra service. The schema is straightforward enough that migrating to Postgres is a one-line change in the ORM config.

**Trade-off accepted**: No concurrent writes from multiple aggregator instances. Acceptable since we run one aggregator process per store.

---

## 5. 5 FPS Sampling Rate

**Decision**: Sample video at 5 frames per second.

**Reasoning**: Standard retail CCTV captures at 15-25 FPS. Most of that is redundant for counting purposes. At 5 FPS we have a 200ms window per frame — sufficient to detect movement across entry/exit zones. This cuts CPU load by ~70% vs processing every frame.

**Trade-off accepted**: Very fast movements (someone running) might skip a zone detection. In practice, retail shoppers move at walking pace, and entry/exit events are gated by a virtual line crossing algorithm (not single-frame detection) so missed frames don't cause missed events.

---

## 6. Rule-based Anomaly Detection over ML

**Decision**: Rule-based anomaly detection with statistical thresholds.

**Reasoning**: An ML-based anomaly detector (e.g., Isolation Forest, LSTM autoencoder) needs training data — historical "normal" day patterns. We don't have that. Rule-based detection using domain knowledge (>4 orders in 20 min = suspicious, re-entry rate >4% = investigate) is immediately useful and fully explainable. A store manager can understand and act on "5 transactions in 18 minutes" without needing to understand model outputs.

**Trade-off accepted**: Rule-based systems miss novel anomalies not anticipated at design time. The right roadmap is: ship rules first, collect labelled data, train ML model in month 2.

---

## 7. Session-based Funnel (no double-counting)

**Decision**: Funnel is computed per session (unique entry event), not per visit or per camera zone crossing.

**Reasoning**: A customer walking from the entrance to the makeup aisle to the skin aisle generates 3 zone events. Counting each as a funnel step would over-inflate "engagement." Instead, we assign each unique track ID one session. Zone engagement = any DWELL event > 5 min. Product interaction = track centroid within 1m of a product zone. Checkout initiated = track detected in the checkout zone. Purchase = matched against POS data.

**Trade-off accepted**: If POS-CCTV sync fails, the bottom of the funnel falls back to order data only (which we have from the CSV). This is acceptable — the CSV is the ground truth for purchases.

---

## 8. Static Frontend on GitHub Pages

**Decision**: Dashboard is a single `index.html` with embedded Chart.js.

**Reasoning**: The challenge asks for a "working live link." GitHub Pages serves static HTML for free with zero config. In production the dashboard would poll the FastAPI `/metrics` endpoint every 30 seconds. For the demo, metrics are embedded as JSON constants derived from the real sales CSV. This means the live link works for every reviewer without setting up the full Docker stack.

**Trade-off accepted**: Demo data is static, not real-time. The architecture fully supports real-time via the API — the frontend is the only thing simplified for the demo.

---

## 9. Conversion Rate Definition

**Decision**: Conversion = (unique customers who completed a purchase) / (unique visitors, excluding staff and re-entries).

**Formula**: 24 unique orders / 284 unique visitors = **8.5%**

**Why this definition**: Industry standard for physical retail. We exclude re-entries (same person counted once) and staff (tracked but flagged `is_staff: true`). We do not divide by total footfall events (which would double-count re-entries) or by total line items (which confuses units sold with customers served).

---

## 10. Confidence Thresholds

| Parameter | Value | Reason |
|-----------|-------|--------|
| YOLO confidence | 0.45 | Favour recall (miss fewer people) |
| Track confirmation | 3 frames | Reject ghost detections |
| ReID similarity | 0.75 | Balance re-entry detection vs false merges |
| Re-entry cooldown | 5 minutes | Typical errand-then-return pattern |
| Staff colour match | 0.65 | Uniform colours are distinct |
