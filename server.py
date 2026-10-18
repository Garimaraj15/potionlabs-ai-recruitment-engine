"""
FastAPI Server for PotionLabs AI Recruitment Engine
Endpoints for Applicant Portal, Recruiter Swipe Deck, Transparency Folders,
Metrics, and Config-Driven Rule Editing.
"""

import os
import json
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import init_db, get_connection, get_pipeline_metrics, log_audit
from models import ApplicantCreate, ReviewActionRequest
from agent import RecruitmentTriageAgent, load_rules, CONFIG_PATH
from worker import worker_instance

triage_agent = RecruitmentTriageAgent()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure DB and start background worker
    init_db()
    worker_instance.start()
    yield
    # Shutdown
    worker_instance.stop()

app = FastAPI(
    title="PotionLabs AI × Operations Recruitment Engine",
    description="Automated Triage, Swipe Review Deck & Double-Check Transparency Pipeline",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>PotionLabs Recruitment Engine UI Loading...</h1>"

@app.post("/api/apply")
async def apply_applicant(applicant: ApplicantCreate):
    """
    Submits application, runs AI Triage Agent, persists candidate and evaluation,
    and returns immediate automated outcome.
    """
    try:
        res = triage_agent.process_new_application(applicant)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/candidates/deck")
async def get_swipe_deck():
    """
    Returns pending candidates for the Tinder-style swipe review deck,
    enriched with full AI evaluation signals, ordered by overall score.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            a.id, a.full_name, a.email, a.phone, a.city, 
            a.linkedin_portfolio, a.read_first_note, a.resume_text,
            a.status, a.created_at,
            e.overall_score, e.tool_calling_score, e.backend_python_score,
            e.sql_score, e.worker_patterns_score, e.project_depth_score,
            e.reasoning_summary, e.raw_signals_json
        FROM applicants a
        INNER JOIN evaluations e ON a.id = e.applicant_id
        WHERE a.status = 'pending_review'
        ORDER BY e.overall_score DESC, a.created_at ASC
    """)
    rows = cur.fetchall()
    candidates = []
    for r in rows:
        candidates.append({
            "id": r["id"],
            "full_name": r["full_name"],
            "email": r["email"],
            "phone": r["phone"],
            "city": r["city"],
            "linkedin_portfolio": r["linkedin_portfolio"],
            "read_first_note": r["read_first_note"],
            "resume_text": r["resume_text"],
            "status": r["status"],
            "created_at": r["created_at"],
            "evaluation": {
                "overall_score": r["overall_score"],
                "tool_calling_score": r["tool_calling_score"],
                "backend_python_score": r["backend_python_score"],
                "sql_score": r["sql_score"],
                "worker_patterns_score": r["worker_patterns_score"],
                "project_depth_score": r["project_depth_score"],
                "reasoning_summary": r["reasoning_summary"],
                "raw_signals": json.loads(r["raw_signals_json"]) if r["raw_signals_json"] else {}
            }
        })
    conn.close()
    return {"candidates": candidates, "count": len(candidates)}

@app.post("/api/candidates/{candidate_id}/action")
async def perform_review_action(candidate_id: str, req: ReviewActionRequest):
    """
    Recruiter action from the Swipe Deck:
    - accept -> advances to stage 1, dispatches technical assignment email
    - reject -> routes to double_check_review queue (not discarded!)
    - double_check_promote -> secondary reviewer confirms and accepts candidate
    """
    try:
        res = triage_agent.execute_recruiter_action(
            applicant_id=candidate_id,
            action=req.action,
            reviewer_name=req.reviewer_name,
            notes=req.notes
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/candidates/folders")
async def get_candidate_folders():
    """
    Categorized folders for transparency:
    1. 'accepted_stage1': Shortlisted candidates moving to technical assignment
    2. 'double_check': Candidates rejected during first pass, awaiting second reviewer verification
    3. 'disqualified_auto': Candidates failing baseline parameters (with automated transparent rejection status)
    """
    conn = get_connection()
    cur = conn.cursor()
    
    query = """
        SELECT 
            a.id, a.full_name, a.email, a.city, a.linkedin_portfolio, a.read_first_note,
            a.status, a.created_at, a.updated_at,
            e.overall_score, e.disqualification_reason, e.reasoning_summary,
            (SELECT action FROM review_actions WHERE applicant_id = a.id ORDER BY action_timestamp DESC LIMIT 1) as last_action,
            (SELECT notes FROM review_actions WHERE applicant_id = a.id ORDER BY action_timestamp DESC LIMIT 1) as last_action_notes,
            (SELECT status FROM outbox_events WHERE recipient_email = a.email ORDER BY created_at DESC LIMIT 1) as email_delivery_status
        FROM applicants a
        LEFT JOIN evaluations e ON a.id = e.applicant_id
        ORDER BY a.updated_at DESC
    """
    cur.execute(query)
    rows = cur.fetchall()
    
    folders = {
        "accepted": [],
        "double_check": [],
        "disqualified_auto": []
    }
    
    for r in rows:
        item = dict(r)
        if r["status"] == "accepted_stage1":
            folders["accepted"].append(item)
        elif r["status"] == "double_check_review":
            folders["double_check"].append(item)
        elif r["status"] == "disqualified_auto":
            folders["disqualified_auto"].append(item)

    conn.close()
    return folders

@app.get("/api/metrics")
async def get_metrics():
    """Real-time pipeline metrics"""
    return get_pipeline_metrics()

@app.get("/api/outbox/events")
async def get_outbox_events():
    """Live stream of background outbox events and worker activity"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, idempotency_key, event_type, recipient_email, payload_json, 
               status, retry_count, max_retries, last_error, processed_at, created_at
        FROM outbox_events
        ORDER BY created_at DESC
        LIMIT 30
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {
        "events": rows,
        "worker_logs": worker_instance.logs_buffer[-20:]
    }

@app.get("/api/config")
async def get_config():
    """Returns the schema-driven evaluation rules"""
    return load_rules()

@app.post("/api/config")
async def update_config(new_rules: Dict[str, Any]):
    """Updates evaluation rules dynamically without code change"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(new_rules, f, indent=2)
    triage_agent.rules = new_rules
    log_audit("config", "evaluation_rules", "updated_schema", f"Version: {new_rules.get('version')}")
    return {"status": "success", "rules": new_rules}
