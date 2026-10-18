# PotionLabs AI × Operations Recruitment Engine

> **Live Production-Grade Architecture for Automated Triage, Swipe Review Deck & Double-Check Transparency Pipeline**

Built specifically for **PotionLabs (JD Jones & Co.)** to solve the high-volume candidate screening bottleneck and eliminate candidate ghosting/limbo.

---

## 🌟 Key Architecture & Capabilities

### 1. Schema-Driven Evaluation Engine (`config/evaluation_rules.json`)
* **Config-over-code design:** Evaluation weights, hard constraints, and scoring thresholds are externalized in JSON schemas.
* Recruiter can modify screening rules without redeploying code.
* Automatically distinguishes **real tool-calling / action-taking agents** and backend engineering from shallow ChatGPT wrappers or tutorial clones.

### 2. Zero-Delay AI Triage & Empathetic Rejection
* Incoming applicants who fail baseline requirements receive **instant, respectful, transparent feedback** within seconds.
* Eliminates candidate anxiety and multi-week waiting periods.
* Dispatches through a transactional outbox queue with verified delivery logs.

### 3. Recruiter Tinder-Style Swipe Deck (`static/index.html`)
* Candidates clearing baseline constraints enter the daily recruiter review deck.
* **1-Click / Keyboard Shortcut Controls:**
  * **[← Left Key] REJECT:** Routes applicant to the **Double-Check Queue** for secondary review (never discarded blindly).
  * **[Right Key →] ACCEPT:** Advances applicant to **Stage 1**, automatically generating and dispatching their technical take-home challenge link.

### 4. Dual-Pass Transparency & Governance
* **Accepted / Advancing:** Real-time visibility into shortlisted candidates with timestamped challenge delivery status.
* **Double-Check Queue:** Holds profiles rejected on first pass so a second reviewer or engineering lead can audit false-negatives and promote deserving candidates with 1 click.
* **Instant Disqualified:** Complete audit log explaining the exact rubric discrepancy.

### 5. Industrial Background Worker Pattern (`worker.py`)
* **Polling Loops & Queues:** Dedicated background worker thread continuously polls `outbox_events`.
* **Idempotency Enforcement:** SHA-256 hashed keys (`applicant_id:event_type`) guarantee that transactional emails are never sent twice.
* **Retries & Backoff:** Exponential retry policy with dead-letter queue semantics for transient gateway errors.

### 6. Relational SQL Database (`database.py`)
* Fully normalized SQLite database with foreign keys, WAL mode for concurrency, and performance indices (`idx_applicants_status`, `idx_outbox_idempotency`).
* Complex analytical aggregation queries powering real-time pipeline funnel metrics.

---

## 🚀 Quick Start

### 1. Launch the Server
Double-click `start_server.bat` or run:
```bash
cd "C:\Users\Garima\OneDrive\Desktop\potionlabs_ai\recruitment_engine"
python run.py
```

### 2. Open in Browser
Visit: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 📁 System Structure
```
recruitment_engine/
├── config/
│   └── evaluation_rules.json     # Schema-driven criteria and email templates
├── static/
│   └── index.html                # PotionLabs-styled interactive UI (Deck, Form, Folders, Ops)
├── agent.py                      # AI Action-Taking Triage Agent
├── database.py                   # Normalized SQL schemas, indices & analytics queries
├── models.py                     # Pydantic data schemas & request validation
├── worker.py                     # Background worker, polling loop, retries & idempotency
├── server.py                     # FastAPI application endpoints
├── seed_data.py                  # Benchmark applicant seeding script
├── run.py                        # Single launcher script
└── start_server.bat              # 1-click Windows launcher
```
