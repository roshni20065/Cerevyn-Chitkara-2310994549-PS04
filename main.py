"""Cerevyn PS04: explainable support-ticket automation API."""
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

APP_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("DB_PATH", str(APP_DIR.parent / "tickets.db"))

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create the local database tables when the API starts."""
    init_db()
    yield


app = FastAPI(
    title="Cerevyn PS04 - Support Ticket Automation",
    description="Classifies fictional support tickets and drafts replies for human review. No messages are sent.",
    version="1.0.1",
    lifespan=lifespan,
)

Category = Literal["Billing", "Technical", "Access", "General"]

class TicketIn(BaseModel):
    ticket_id: str = Field(min_length=3, max_length=40, examples=["T-1001"])
    message: str = Field(min_length=8, max_length=3000, examples=["I was charged twice for my monthly invoice."])

    @field_validator("ticket_id")
    @classmethod
    def clean_ticket_id(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,40}", value):
            raise ValueError("ticket_id may contain only letters, numbers, underscores and hyphens")
        return value

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 8:
            raise ValueError("message must contain at least 8 non-space characters")
        return value

class ApprovalIn(BaseModel):
    reviewer: str = Field(min_length=2, max_length=80, examples=["support-supervisor"])
    note: str = Field(default="Approved after human review", max_length=500)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            message TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            assigned_team TEXT NOT NULL,
            summary TEXT NOT NULL,
            draft_response TEXT NOT NULL,
            confidence REAL NOT NULL,
            needs_review INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            approved_by TEXT,
            approval_note TEXT,
            approved_at TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT NOT NULL,
            action TEXT NOT NULL,
            actor TEXT NOT NULL,
            note TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")


CATEGORY_RULES = {
    "Billing": ["bill", "billing", "invoice", "charged", "charge", "refund", "payment", "subscription", "receipt", "tax", "overcharged", "overcharge"],
    "Technical": ["error", "bug", "crash", "slow", "failed", "failure", "broken", "not working", "timeout", "server", "api", "sync", "synchronization", "upload", "download", "screen freezes", "exception"],
    "Access": ["login", "log in", "password", "sign in", "signin", "locked", "lockout", "permission", "access", "two-factor", "2fa", "account disabled", "reset password", "authentication"],
    "General": ["question", "how do i", "information", "hours", "documentation", "feature request", "feedback", "suggestion", "hello", "thank you", "general", "plan details"],
}
TEAM_BY_CATEGORY = {"Billing": "Finance Support", "Technical": "Technical Support", "Access": "Identity & Access Support", "General": "Customer Support"}
URGENT_TERMS = ["urgent", "critical", "production down", "all users", "security breach", "data leak", "cannot work", "business stopped"]
HIGH_TERMS = ["blocked", "deadline", "multiple users", "cannot access", "unable to login", "unable to log in", "failed payment", "charged twice", "data loss"]


def classify_message(message: str) -> dict:
    """Simple transparent keyword scoring; confidence is a heuristic, not a probability."""
    text = re.sub(r"\s+", " ", message.lower()).strip()
    scores = {}
    for category, terms in CATEGORY_RULES.items():
        scores[category] = sum(1 for term in terms if term in text)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_category, best_score = ranked[0]
    second_score = ranked[1][1]
    if best_score == 0:
        category, confidence, needs_review = "General", 0.30, True
    else:
        # A tie between categories is deliberately routed for human review.
        tied = sum(1 for _, score in ranked if score == best_score) > 1
        confidence = min(0.95, 0.55 + 0.12 * best_score + (0.12 if best_score > second_score else 0))
        needs_review = tied or best_score == second_score or confidence < 0.70
        category = best_category
    if any(term in text for term in URGENT_TERMS):
        priority = "Urgent"
    elif any(term in text for term in HIGH_TERMS):
        priority = "High"
    elif any(term in text for term in ["when possible", "minor", "question", "suggestion", "feature request"]):
        priority = "Low"
    else:
        priority = "Medium"
    return {"category": category, "priority": priority, "assigned_team": TEAM_BY_CATEGORY[category],
            "confidence": round(confidence, 2), "needs_review": needs_review, "scores": scores}


def make_summary(message: str) -> str:
    words = message.split()
    summary = " ".join(words[:22])
    return summary + ("…" if len(words) > 22 else "")


def make_draft(category: str, priority: str, summary: str) -> str:
    return (f"Hello, thank you for contacting support. We have recorded your {category.lower()} issue "
            f"with {priority.lower()} priority: ‘{summary}’. Our {TEAM_BY_CATEGORY[category]} team will review it. "
            "If more details are needed, a team member will contact you. This is a draft for human review; "
            "it has not been sent.")


def ticket_dict(row: sqlite3.Row) -> dict:
    result = dict(row)
    result["needs_review"] = bool(result["needs_review"])
    return result

@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "service": "cerevyn-ps04"}

@app.post("/tickets", status_code=status.HTTP_201_CREATED, tags=["tickets"])
def create_ticket(ticket: TicketIn) -> dict:
    init_db()
    prediction = classify_message(ticket.message)
    summary = make_summary(ticket.message)
    draft = make_draft(prediction["category"], prediction["priority"], summary)
    ticket_status = "needs_review" if prediction["needs_review"] else "pending_approval"
    created_at = utc_now()
    try:
        with connect() as conn:
            conn.execute("""INSERT INTO tickets
                (ticket_id,message,category,priority,assigned_team,summary,draft_response,confidence,needs_review,status,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (ticket.ticket_id, ticket.message, prediction["category"], prediction["priority"],
                 prediction["assigned_team"], summary, draft, prediction["confidence"],
                 int(prediction["needs_review"]), ticket_status, created_at))
            conn.execute("INSERT INTO audit_log(ticket_id,action,actor,note,created_at) VALUES(?,?,?,?,?)",
                         (ticket.ticket_id, "created", "system", "Ticket classified and draft prepared", created_at))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"Ticket ID '{ticket.ticket_id}' already exists")
    return {"ticket_id": ticket.ticket_id, "category": prediction["category"], "priority": prediction["priority"],
            "assigned_team": prediction["assigned_team"], "summary": summary, "draft_response": draft,
            "confidence": prediction["confidence"], "needs_review": prediction["needs_review"],
            "status": ticket_status, "message_sent": False, "classification_scores": prediction["scores"]}

@app.get("/tickets", tags=["tickets"])
def list_tickets() -> dict:
    init_db()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM tickets ORDER BY created_at DESC").fetchall()
    return {"count": len(rows), "tickets": [ticket_dict(row) for row in rows]}

@app.get("/tickets/{ticket_id}", tags=["tickets"])
def get_ticket(ticket_id: str) -> dict:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket_dict(row)

@app.post("/tickets/{ticket_id}/approve", tags=["review"])
def approve_ticket(ticket_id: str, approval: ApprovalIn) -> dict:
    init_db()
    now = utc_now()
    with connect() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if row["status"] == "draft_ready":
            raise HTTPException(status_code=409, detail="Ticket draft has already been approved")
        conn.execute("UPDATE tickets SET status='draft_ready', approved_by=?, approval_note=?, approved_at=? WHERE ticket_id=?",
                     (approval.reviewer.strip(), approval.note.strip(), now, ticket_id))
        conn.execute("INSERT INTO audit_log(ticket_id,action,actor,note,created_at) VALUES(?,?,?,?,?)",
                     (ticket_id, "approved", approval.reviewer.strip(), approval.note.strip(), now))
        updated = conn.execute("SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
    return {"ticket": ticket_dict(updated), "message_sent": False, "audit_recorded": True}

@app.get("/tickets/{ticket_id}/audit", tags=["review"])
def ticket_audit(ticket_id: str) -> dict:
    init_db()
    with connect() as conn:
        exists = conn.execute("SELECT 1 FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Ticket not found")
        rows = conn.execute("SELECT action,actor,note,created_at FROM audit_log WHERE ticket_id=? ORDER BY id", (ticket_id,)).fetchall()
    return {"ticket_id": ticket_id, "events": [dict(row) for row in rows]}

@app.get("/evaluation", tags=["evaluation"])
def evaluation() -> dict:
    """Evaluate the frozen 10-ticket holdout set from sample_data/tickets.json."""
    data_path = APP_DIR.parent / "sample_data" / "tickets.json"
    if not data_path.exists():
        raise HTTPException(status_code=500, detail="Evaluation dataset is missing")
    records = json.loads(data_path.read_text(encoding="utf-8"))
    holdout = [item for item in records if item["split"] == "test"]
    correct = 0
    results = []
    for item in holdout:
        prediction = classify_message(item["message"])
        matched = prediction["category"] == item["category"]
        correct += int(matched)
        results.append({"ticket_id": item["ticket_id"], "expected": item["category"],
                        "predicted": prediction["category"], "correct": matched})
    return {"method": "keyword scoring baseline", "test_count": len(holdout),
            "correct": correct, "accuracy": round(correct / len(holdout), 4) if holdout else 0,
            "note": "This is a small synthetic holdout set, not a claim of production performance.", "results": results}
