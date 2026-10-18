"""
Production SQL Database Layer for PotionLabs AI Recruitment Engine
Schema design, connection lifecycle, indices, and complex analytical queries.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "potionlabs_recruitment.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")  # High concurrency WAL mode
    return conn

def init_db():
    conn = get_connection()
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            department TEXT NOT NULL,
            location TEXT NOT NULL,
            stipend TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS applicants (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            city TEXT,
            linkedin_portfolio TEXT,
            source_attribution TEXT,
            read_first_note TEXT,
            resume_text TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN (
                'new', 
                'disqualified_auto', 
                'pending_review', 
                'accepted_stage1', 
                'double_check_review', 
                'rejected_final'
            )),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );

        CREATE TABLE IF NOT EXISTS evaluations (
            id TEXT PRIMARY KEY,
            applicant_id TEXT NOT NULL UNIQUE,
            overall_score INTEGER NOT NULL,
            tool_calling_score INTEGER NOT NULL,
            backend_python_score INTEGER NOT NULL,
            sql_score INTEGER NOT NULL,
            worker_patterns_score INTEGER NOT NULL,
            project_depth_score INTEGER NOT NULL,
            passed_hard_constraints INTEGER NOT NULL,
            disqualification_reason TEXT,
            reasoning_summary TEXT NOT NULL,
            raw_signals_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (applicant_id) REFERENCES applicants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS review_actions (
            id TEXT PRIMARY KEY,
            applicant_id TEXT NOT NULL,
            reviewer_name TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('accept', 'reject', 'double_check_promote', 'restore')),
            previous_status TEXT NOT NULL,
            new_status TEXT NOT NULL,
            notes TEXT,
            action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (applicant_id) REFERENCES applicants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS outbox_events (
            id TEXT PRIMARY KEY,
            idempotency_key TEXT NOT NULL UNIQUE,
            event_type TEXT NOT NULL,
            recipient_email TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'processing', 'sent', 'failed')),
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            last_error TEXT,
            processed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Performance Indices
        CREATE INDEX IF NOT EXISTS idx_applicants_status ON applicants(status);
        CREATE INDEX IF NOT EXISTS idx_applicants_email ON applicants(email);
        CREATE INDEX IF NOT EXISTS idx_evaluations_applicant_id ON evaluations(applicant_id);
        CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox_events(status, retry_count);
        CREATE INDEX IF NOT EXISTS idx_outbox_idempotency ON outbox_events(idempotency_key);
        CREATE INDEX IF NOT EXISTS idx_review_actions_applicant ON review_actions(applicant_id);

        -- Default Job definition
        INSERT OR IGNORE INTO jobs (id, title, department, location, stipend) 
        VALUES ('ai-coding-intern', 'AI & Coding Intern', 'AI & Engineering', 'Park Street, Kolkata', '₹12,000–15,000 per month');
        """)
    conn.close()

def log_audit(entity_type: str, entity_id: str, action: str, details: str = "", conn: Optional[sqlite3.Connection] = None):
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
    conn.execute(
        "INSERT INTO audit_logs (entity_type, entity_id, action, details) VALUES (?, ?, ?, ?)",
        (entity_type, entity_id, action, details)
    )
    if should_close:
        conn.commit()
        conn.close()

def get_pipeline_metrics() -> Dict[str, Any]:
    """Complex SQL query aggregating real-time recruitment pipeline metrics"""
    conn = get_connection()
    with conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                COUNT(*) as total_applicants,
                SUM(CASE WHEN status = 'pending_review' THEN 1 ELSE 0 END) as pending_review,
                SUM(CASE WHEN status = 'accepted_stage1' THEN 1 ELSE 0 END) as accepted_stage1,
                SUM(CASE WHEN status = 'double_check_review' THEN 1 ELSE 0 END) as double_check_review,
                SUM(CASE WHEN status = 'disqualified_auto' THEN 1 ELSE 0 END) as disqualified_auto,
                AVG(CASE WHEN e.overall_score IS NOT NULL THEN e.overall_score ELSE 0 END) as avg_score
            FROM applicants a
            LEFT JOIN evaluations e ON a.id = e.applicant_id
        """)
        row = cur.fetchone()
        
        # Outbox stats
        cur.execute("""
            SELECT 
                COUNT(*) as total_events,
                SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent_events,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_events,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_events
            FROM outbox_events
        """)
        outbox_row = cur.fetchone()
        
    conn.close()
    return {
        "total_applicants": row["total_applicants"] or 0,
        "pending_review": row["pending_review"] or 0,
        "accepted_stage1": row["accepted_stage1"] or 0,
        "double_check_review": row["double_check_review"] or 0,
        "disqualified_auto": row["disqualified_auto"] or 0,
        "avg_score": round(row["avg_score"] or 0, 1),
        "outbox": {
            "total": outbox_row["total_events"] or 0,
            "sent": outbox_row["sent_events"] or 0,
            "pending": outbox_row["pending_events"] or 0,
            "failed": outbox_row["failed_events"] or 0
        }
    }
