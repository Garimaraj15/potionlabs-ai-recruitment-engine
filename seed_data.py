"""
Seed script to initialize and populate the PotionLabs Recruitment Engine database
with diverse test candidates demonstrating all pipeline tracks.
"""

from database import init_db, get_connection
from agent import RecruitmentTriageAgent
from models import ApplicantCreate

def seed():
    init_db()
    agent = RecruitmentTriageAgent()
    
    # Check if applicants already seeded
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM applicants")
    count = cur.fetchone()[0]
    conn.close()
    
    if count > 0:
        print(f"Database already has {count} applicants. Skipping seed.")
        return

    print("Seeding database with benchmark candidates...")

    candidates = [
        # 1. Star Candidate: Garima Raj (Matches PotionLabs AI x Operations JD perfectly)
        ApplicantCreate(
            full_name="Garima Raj",
            email="Garimaraj536@gmail.com",
            phone="+91 7870505606",
            city="Kolkata",
            linkedin_portfolio="https://linkedin.com/in/garimaraj",
            source_attribution="PotionLabs Careers Portal",
            read_first_note="Built this production-ready AI x Operations Recruitment Engine to solve PotionLabs' candidate volume bottleneck using tool-calling agents & background workers.",
            resume_text="""
            Garima Raj | Kolkata, West Bengal | Heritage Institute of Technology (B.Tech CSE Data Science, 2027)
            AI & Agent Systems Engineer | Backend & LLM Systems
            Professional Summary: Backend & AI Systems Engineer specializing in LLM Agent Workflows, API Systems, and Tool-Augmented AI Platforms.
            Hands-on experience architecting autonomous agents with FastAPI, Google Gemini, and OpenAI APIs, utilizing structured function calling,
            multi-step tool orchestration, and automated evaluation/regression testing. 250+ LeetCode DSA solved. Winner HackHeritage 3.0.
            
            Technical Projects:
            1. StockSikh – Autonomous Market Analysis & Trading Agent:
            Architected Vidya AI, an autonomous financial mentor agent utilizing structured tool calling to interface dynamically with Yahoo Finance APIs
            for live indicator computations. Designed strict JSON Schema output validation and prompt fallback routines to eliminate hallucinations.
            Engineered high-throughput asynchronous backend endpoints in FastAPI, reducing latency under high concurrency.
            
            2. RetailSphere – Intelligent Retail Operations & Queuing Platform:
            Designed and deployed a full-stack retail management platform with dynamic token generation and wait-time prediction algorithms,
            cutting customer wait times by 30%. Designed modular REST APIs connecting React frontend to relational MySQL database.
            
            3. Her Voice (Women Safety SOS) – Real-Time Emergency Response Platform:
            Built a conversational triage agent using OpenAI APIs to classify incident severity and route distress tickets to nearest contacts.
            Authored automated Selenium regression test suite ensuring zero runtime failure during crisis scenarios.
            
            4. Walmart USA – Advanced Software Engineering (Forage):
            Built a high-performance Python/Pandas ETL pipeline for retail inventory and shipment records, cleaning CSV datasets before loading into SQLite.
            Designed UML class diagrams and optimized data structures for retail supply chain and inventory management workflows.
            
            Technical Skills:
            Agentic AI & LLMs: Function Calling / Tool Use, Structured Outputs (Pydantic / JSON Schema), Google Gemini API, OpenAI API, Prompt Engineering.
            Backend & System Design: Python (FastAPI, Flask, Asyncio), REST API Design, Microservices, Asynchronous Request Handling.
            Databases & Data Pipelines: MySQL, PostgreSQL, MongoDB, SQLite, Query Optimization, ETL Data Pipelines, Pandas, NumPy.
            Background Workers: Queue polling, idempotent processing, retries, worker threads.
            """
        ),

        # 2. Strong Backend Candidate: Shashi Ranjan
        ApplicantCreate(
            full_name="Shashi Ranjan",
            email="shashi.ranjan@example.com",
            phone="+91 9831001122",
            city="Kolkata",
            linkedin_portfolio="https://github.com/shashi-swe",
            source_attribution="LinkedIn",
            read_first_note="Full stack SWE with production FastAPI, Celery background queues, and PostgreSQL indexing experience.",
            resume_text="""
            Shashi Ranjan | Full Stack Software Engineer | Kolkata
            Strong Python backend developer with hands-on experience building REST APIs and microservices in FastAPI, Flask, and Docker.
            Engineered autonomous workflow triggers and tool use pipelines interfacing with OpenAI and third-party ERP APIs.
            Experience with background worker patterns, Redis queues, Celery worker loops, polling, retries, and idempotent webhook handlers.
            Proficient in SQL schema design, PostgreSQL, MySQL query optimization, indexing, and complex CTE joins.
            Winner in regional hackathon; built high-throughput production data pipelines.
            """
        ),

        # 3. Disqualified Candidate: Chatbot Only Wrapper (No backend depth / no tool calling)
        ApplicantCreate(
            full_name="Rohan Gupta",
            email="rohan.gupta.wrapper@example.com",
            phone="+91 9123456789",
            city="Bengaluru",
            linkedin_portfolio="https://github.com/rohan-chat",
            source_attribution="Twitter",
            read_first_note="Looking for internship. Made an AI chatbot.",
            resume_text="""
            Rohan Gupta | Fresher
            Projects:
            ChatGPT Wrapper Bot: Built a simple prompt chatbot using Streamlit and OpenAI API chat completion.
            Basic UI chat where user sends question and gets LLM answer.
            No backend framework used. No database experience. No tool calling.
            """
        ),

        # 4. Borderline Review Candidate: Priya Sharma
        ApplicantCreate(
            full_name="Priya Sharma",
            email="priya.sharma.data@example.com",
            phone="+91 9748003344",
            city="Kolkata",
            linkedin_portfolio="https://linkedin.com/in/priyasharma",
            source_attribution="College Placement Cell",
            read_first_note="Strong in SQL query optimization, data pipelines, and Python scripting.",
            resume_text="""
            Priya Sharma | Data Engineering & Analytics
            Skilled in Python, SQL, PostgreSQL, database schema design, and ETL pipelines.
            Built automated data ingestion scripts for warehouse loading.
            Familiar with background cron jobs and queue polling basics.
            Looking to transition into industrial AI agent workflows.
            """
        ),

        # 5. Disqualified Candidate: Generic Tutorial Clone
        ApplicantCreate(
            full_name="Aman Verma",
            email="aman.verma.tutorial@example.com",
            phone="+91 8899001122",
            city="Delhi",
            linkedin_portfolio="https://github.com/aman-tutorials",
            source_attribution="Google Search",
            read_first_note="Beginner coder looking for first internship opportunity.",
            resume_text="""
            Aman Verma | Student
            Completed online course.
            Projects:
            - Todo App in JavaScript
            - Simple Calculator
            - Tutorial clone of Netflix landing page with HTML CSS
            - Titanic dataset exploratory analysis in Jupyter notebook
            """
        )
    ]

    for c in candidates:
        res = agent.process_new_application(c)
        print(f"Processed: {c.full_name} -> Status: {res['status']} | Score: {res['evaluation']['overall_score']}/100")

    print("\nSeed completed successfully!")

if __name__ == "__main__":
    seed()
