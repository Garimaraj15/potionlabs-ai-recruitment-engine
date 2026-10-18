"""
Single launcher for PotionLabs AI Recruitment Engine
Seeds benchmark candidates and starts FastAPI with Background Worker on localhost.
"""

import os
import sys
import uvicorn
from seed_data import seed
from database import init_db

def main():
    print("=" * 60)
    print("  PotionLabs AI x Operations Recruitment Engine")
    print("  Automated Triage, Swipe Review Deck & Double-Check Queue")
    print("=" * 60)
    
    # 1. Initialize DB and seed
    init_db()
    seed()
    
    # 2. Run server
    from server import app
    port = 8000
    print(f"\n[OK] System Online! Open browser at: http://127.0.0.1:{port}\n")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

if __name__ == "__main__":
    main()
