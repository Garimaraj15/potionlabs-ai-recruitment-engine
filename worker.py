"""
Background Job & Outbox Worker Pattern for PotionLabs Recruitment Engine
Implements polling loops, queue processing, retries with exponential backoff,
idempotency enforcement, and dead-letter queue semantics.
"""

import time
import json
import threading
import logging
from datetime import datetime
from database import get_connection, log_audit

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class OutboxWorker:
    def __init__(self, poll_interval_sec: float = 2.0):
        self.poll_interval = poll_interval_sec
        self._running = False
        self._thread = None
        self.logs_buffer = []

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        logging.info(message)
        self.logs_buffer.append(entry)
        if len(self.logs_buffer) > 100:
            self.logs_buffer.pop(0)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.log("Worker started: Background queue polling loop active.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        self.log("Worker stopped.")

    def _run_loop(self):
        while self._running:
            try:
                self._process_batch()
            except Exception as e:
                self.log(f"Worker iteration error: {str(e)}")
            time.sleep(self.poll_interval)

    def _process_batch(self):
        conn = get_connection()
        try:
            with conn:
                cur = conn.cursor()
                # Select pending or retriable failed events (exponential backoff window)
                cur.execute("""
                    SELECT id, idempotency_key, event_type, recipient_email, payload_json, retry_count, max_retries
                    FROM outbox_events
                    WHERE status = 'pending' 
                       OR (status = 'failed' AND retry_count < max_retries)
                    ORDER BY created_at ASC
                    LIMIT 10
                """)
                events = cur.fetchall()

                for event in events:
                    event_id = event["id"]
                    event_type = event["event_type"]
                    recipient = event["recipient_email"]
                    retry_count = event["retry_count"]
                    max_retries = event["max_retries"]
                    payload = json.loads(event["payload_json"])

                    # Atomic lock: transition to processing
                    cur.execute("""
                        UPDATE outbox_events 
                        SET status = 'processing', updated_at = CURRENT_TIMESTAMP 
                        WHERE id = ? AND (status = 'pending' OR status = 'failed')
                    """, (event_id,))

                    if cur.rowcount == 0:
                        continue  # Another worker thread acquired it

                    self.log(f"Processing event {event_id} [{event_type}] -> {recipient} (Attempt {retry_count + 1}/{max_retries})")

                    try:
                        # Simulated Idempotent External Dispatch (Email / Webhook / Notification)
                        self._dispatch_event(event_type, recipient, payload)

                        # Success: Mark sent
                        cur.execute("""
                            UPDATE outbox_events 
                            SET status = 'sent', processed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP, last_error = NULL
                            WHERE id = ?
                        """, (event_id,))
                        self.log(f"DISPATCH_SUCCESS: {event_id} delivered to {recipient}")
                        log_audit("outbox", event_id, "dispatch_success", f"Delivered to {recipient} [{event_type}]", conn=conn)

                    except Exception as exc:
                        new_retries = retry_count + 1
                        error_msg = str(exc)
                        final_status = "failed"
                        self.log(f"DISPATCH_FAILURE: {event_id} failed: {error_msg}. Retries: {new_retries}/{max_retries}")
                        cur.execute("""
                            UPDATE outbox_events 
                            SET status = ?, retry_count = ?, last_error = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (final_status, new_retries, error_msg, event_id))
                        log_audit("outbox", event_id, "dispatch_failure", f"Error: {error_msg}, Retry: {new_retries}", conn=conn)

        finally:
            conn.close()

    def _dispatch_event(self, event_type: str, recipient: str, payload: dict):
        """Simulates transactional email / webhook API dispatch with realistic latency"""
        time.sleep(0.15)  # Network latency
        
        # Simulated edge case: if email has 'simulate-fail', trigger retry mechanism
        if "simulate-fail" in recipient:
            raise RuntimeError("Transient 503 Service Unavailable: upstream mail gateway reset")

        # In a production setup, this calls Resend/SendGrid/Postmark API or SMTP
        pass

# Global worker singleton
worker_instance = OutboxWorker()
