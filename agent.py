"""
AI Action-Taking Triage Agent for PotionLabs Recruitment Pipeline
Evaluates candidate submissions against schema-driven rules, triggers deterministic actions,
and queues transactional outbox events (instant empathetic rejections, advance invitations).
"""

import os
import json
import uuid
import hashlib
from typing import Dict, Any, Tuple
from datetime import datetime

from database import get_connection, log_audit
from models import EvaluationResult, ApplicantCreate

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "evaluation_rules.json")

def load_rules() -> Dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_idempotency_key(applicant_id: str, event_type: str) -> str:
    raw = f"{applicant_id}:{event_type}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

class RecruitmentTriageAgent:
    def __init__(self):
        self.rules = load_rules()

    def evaluate_applicant(self, applicant: ApplicantCreate) -> EvaluationResult:
        """
        Deep signal extraction and scoring based on schema-driven weights.
        Differentiates real action-taking agents & backend depth from generic tutorial chatbot wrappers.
        """
        text = (applicant.resume_text + " " + (applicant.read_first_note or "")).lower()
        rubric = self.rules.get("scoring_rubric", {})
        
        # 1. Tool-Calling & Action-Taking Agents (Weight: 30)
        tool_keywords = rubric.get("tool_calling_and_agents", {}).get("keywords", [])
        tool_hits = [k for k in tool_keywords if k in text]
        chatbot_negatives = rubric.get("tool_calling_and_agents", {}).get("negative_keywords", [])
        has_negative_bot = any(k in text for k in chatbot_negatives)
        
        tool_score = min(30, len(tool_hits) * 5)
        if "function calling" in text or "tool use" in text or "tool orchestration" in text:
            tool_score = max(tool_score, 25)
        if has_negative_bot and tool_score < 15:
            tool_score = max(5, tool_score - 10)

        # 2. Production Python & Backend (Weight: 25)
        py_keywords = rubric.get("production_python_and_backend", {}).get("keywords", [])
        py_hits = [k for k in py_keywords if k in text]
        py_score = min(25, len(py_hits) * 5)
        if "fastapi" in text or "asyncio" in text:
            py_score = max(py_score, 20)

        # 3. SQL & Database Design (Weight: 15)
        sql_keywords = rubric.get("sql_and_database_design", {}).get("keywords", [])
        sql_hits = [k for k in sql_keywords if k in text]
        sql_score = min(15, len(sql_hits) * 3)

        # 4. Background Workers & Queue Patterns (Weight: 15)
        worker_keywords = rubric.get("worker_and_background_patterns", {}).get("keywords", [])
        worker_hits = [k for k in worker_keywords if k in text]
        worker_score = min(15, len(worker_hits) * 4)

        # 5. Real-World Project Depth (Weight: 15)
        project_keywords = rubric.get("real_world_projects_depth", {}).get("keywords", [])
        project_hits = [k for k in project_keywords if k in text]
        generic_negatives = rubric.get("real_world_projects_depth", {}).get("negative_keywords", [])
        has_generic_projects = any(k in text for k in generic_negatives)
        
        project_score = min(15, len(project_hits) * 3)
        if has_generic_projects and len(project_hits) < 2:
            project_score = max(3, project_score - 6)

        overall_score = tool_score + py_score + sql_score + worker_score + project_score
        
        # Hard constraint verification
        hard_constraints = self.rules.get("hard_constraints", {})
        min_threshold = hard_constraints.get("min_overall_score_for_review_deck", 65)
        
        passed_hard_constraints = True
        disqualification_reason = None

        if "python" not in text:
            passed_hard_constraints = False
            disqualification_reason = "No demonstrable Python proficiency"
        elif has_negative_bot and tool_score < 15:
            passed_hard_constraints = False
            disqualification_reason = "Conversational chat wrapper without backend tool execution or autonomous actions"
        elif overall_score < min_threshold:
            passed_hard_constraints = False
            disqualification_reason = f"Composite score ({overall_score}/100) below threshold of {min_threshold} for technical internship track"

        # Generate reasoning summary
        if passed_hard_constraints:
            reasoning = (
                f"Candidate exhibits strong signal across key industrial competencies (Score: {overall_score}/100). "
                f"Tool-calling: {tool_score}/30 ({', '.join(tool_hits[:3]) or 'present'}). "
                f"Backend Python: {py_score}/25. Database/SQL: {sql_score}/15. "
                f"Ready for recruiter review deck."
            )
        else:
            reasoning = f"Automated triage triggered disqualification: {disqualification_reason}. Queued empathetic notification."

        return EvaluationResult(
            overall_score=overall_score,
            tool_calling_score=tool_score,
            backend_python_score=py_score,
            sql_score=sql_score,
            worker_patterns_score=worker_score,
            project_depth_score=project_score,
            passed_hard_constraints=passed_hard_constraints,
            disqualification_reason=disqualification_reason,
            reasoning_summary=reasoning,
            raw_signals={
                "tool_hits": tool_hits,
                "py_hits": py_hits,
                "sql_hits": sql_hits,
                "worker_hits": worker_hits,
                "project_hits": project_hits,
                "has_generic_projects": has_generic_projects
            }
        )

    def process_new_application(self, applicant_data: ApplicantCreate) -> Dict[str, Any]:
        """
        End-to-end pipeline: persist applicant, run AI triage evaluation,
        and trigger instantaneous automated action (outbox event).
        """
        applicant_id = f"app_{uuid.uuid4().hex[:10]}"
        evaluation = self.evaluate_applicant(applicant_data)
        
        initial_status = "pending_review" if evaluation.passed_hard_constraints else "disqualified_auto"
        
        conn = get_connection()
        with conn:
            # 1. Insert applicant
            conn.execute("""
                INSERT INTO applicants (
                    id, job_id, full_name, email, phone, city, 
                    linkedin_portfolio, source_attribution, read_first_note, 
                    resume_text, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                applicant_id, "ai-coding-intern", applicant_data.full_name, applicant_data.email,
                applicant_data.phone, applicant_data.city, applicant_data.linkedin_portfolio,
                applicant_data.source_attribution, applicant_data.read_first_note,
                applicant_data.resume_text, initial_status
            ))

            # 2. Insert evaluation record
            eval_id = f"eval_{uuid.uuid4().hex[:10]}"
            conn.execute("""
                INSERT INTO evaluations (
                    id, applicant_id, overall_score, tool_calling_score, 
                    backend_python_score, sql_score, worker_patterns_score, 
                    project_depth_score, passed_hard_constraints, 
                    disqualification_reason, reasoning_summary, raw_signals_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                eval_id, applicant_id, evaluation.overall_score, evaluation.tool_calling_score,
                evaluation.backend_python_score, evaluation.sql_score, evaluation.worker_patterns_score,
                evaluation.project_depth_score, 1 if evaluation.passed_hard_constraints else 0,
                evaluation.disqualification_reason, evaluation.reasoning_summary,
                json.dumps(evaluation.raw_signals)
            ))

            # 3. Action Trigger: If disqualified, queue INSTANT rejection email event
            if not evaluation.passed_hard_constraints:
                tmpl = self.rules.get("templates", {}).get("instant_rejection_email", {})
                subject = tmpl.get("subject", "Update on your PotionLabs application")
                body = tmpl.get("body", "").format(
                    name=applicant_data.full_name,
                    reason=evaluation.disqualification_reason or "criteria mismatch"
                )
                
                outbox_id = f"evt_{uuid.uuid4().hex[:10]}"
                idempotency_key = generate_idempotency_key(applicant_id, "instant_rejection")
                
                payload = {
                    "applicant_id": applicant_id,
                    "recipient_email": applicant_data.email,
                    "recipient_name": applicant_data.full_name,
                    "subject": subject,
                    "body": body,
                    "type": "instant_disqualification"
                }
                
                conn.execute("""
                    INSERT INTO outbox_events (
                        id, idempotency_key, event_type, recipient_email, 
                        payload_json, status, retry_count
                    ) VALUES (?, ?, ?, ?, ?, 'pending', 0)
                """, (outbox_id, idempotency_key, "email.instant_rejection", applicant_data.email, json.dumps(payload)))
                
                log_audit("applicant", applicant_id, "auto_disqualified", f"Score: {evaluation.overall_score}, Reason: {evaluation.disqualification_reason}", conn=conn)
            else:
                log_audit("applicant", applicant_id, "queued_for_review_deck", f"Score: {evaluation.overall_score}/100", conn=conn)

        conn.close()
        
        return {
            "applicant_id": applicant_id,
            "status": initial_status,
            "evaluation": evaluation.dict()
        }

    def execute_recruiter_action(self, applicant_id: str, action: str, reviewer_name: str, notes: str = None) -> Dict[str, Any]:
        """
        Executes reviewer action from the Swipe Deck:
        - 'accept': triggers stage-1 confirmation + assignment outbox event, moves to 'accepted_stage1'
        - 'reject': moves candidate to 'double_check_review' folder so it is audited before any final disposition
        - 'double_check_promote': promotes a candidate from double-check to 'accepted_stage1'
        """
        conn = get_connection()
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM applicants WHERE id = ?", (applicant_id,))
            applicant = cur.fetchone()
            if not applicant:
                conn.close()
                raise ValueError(f"Applicant {applicant_id} not found")

            prev_status = applicant["status"]
            
            if action == "accept" or action == "double_check_promote":
                new_status = "accepted_stage1"
                
                # Queue advance confirmation email with technical assignment link
                tmpl = self.rules.get("templates", {}).get("advance_confirmation_email", {})
                assignment_link = f"https://potionlabs.ai/challenge/take-home?app_id={applicant_id}"
                subject = tmpl.get("subject", "Your PotionLabs application is moving forward")
                body = tmpl.get("body", "").format(
                    name=applicant["full_name"],
                    assignment_link=assignment_link
                )
                
                outbox_id = f"evt_{uuid.uuid4().hex[:10]}"
                idempotency_key = generate_idempotency_key(applicant_id, "advance_confirmation")
                
                payload = {
                    "applicant_id": applicant_id,
                    "recipient_email": applicant["email"],
                    "recipient_name": applicant["full_name"],
                    "subject": subject,
                    "body": body,
                    "assignment_link": assignment_link,
                    "type": "stage1_advancement"
                }
                
                # Insert outbox event idempotently
                conn.execute("""
                    INSERT OR IGNORE INTO outbox_events (
                        id, idempotency_key, event_type, recipient_email, 
                        payload_json, status, retry_count
                    ) VALUES (?, ?, ?, ?, ?, 'pending', 0)
                """, (outbox_id, idempotency_key, "email.advance_confirmation", applicant["email"], json.dumps(payload)))

            elif action == "reject":
                # Do NOT discard into void — route into double_check_review queue!
                new_status = "double_check_review"
            elif action == "restore":
                new_status = "pending_review"
            else:
                new_status = prev_status

            # Update applicant status
            conn.execute("UPDATE applicants SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, applicant_id))
            
            # Record review action
            action_id = f"act_{uuid.uuid4().hex[:10]}"
            conn.execute("""
                INSERT INTO review_actions (
                    id, applicant_id, reviewer_name, action, 
                    previous_status, new_status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (action_id, applicant_id, reviewer_name, action, prev_status, new_status, notes or ""))

            log_audit("applicant", applicant_id, f"action_{action}", f"Reviewer: {reviewer_name}, Prev: {prev_status}, New: {new_status}", conn=conn)

        conn.close()
        return {
            "applicant_id": applicant_id,
            "previous_status": prev_status,
            "new_status": new_status,
            "action": action
        }
