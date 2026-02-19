"""
Simulated email backend for the M3 Agentic AI lab.

Run with:
    uvicorn email_server:app --reload --port 8000

Routes:
    POST   /send
    GET    /emails
    GET    /emails/unread
    GET    /emails/search?q=<query>
    GET    /emails/filter?recipient=&date_from=&date_to=
    GET    /emails/{id}
    PATCH  /emails/{id}/read
    PATCH  /emails/{id}/unread
    DELETE /emails/{id}
    GET    /reset_database
"""

from __future__ import annotations

import copy
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="Simulated Email Service")

# ---------------------------------------------------------------------------
# Seed data — restored on every /reset_database call
# ---------------------------------------------------------------------------
_SEED: List[dict] = [
    {
        "id": 1,
        "sender": "boss@email.com",
        "recipient": "you@email.com",
        "subject": "Q3 Report",
        "body": "Please send me the Q3 report by Friday.",
        "timestamp": "2024-09-01T09:00:00",
        "read": False,
    },
    {
        "id": 2,
        "sender": "alice@work.com",
        "recipient": "you@email.com",
        "subject": "Team Lunch",
        "body": "Are you free for team lunch on Thursday?",
        "timestamp": "2024-09-02T11:30:00",
        "read": False,
    },
    {
        "id": 3,
        "sender": "newsletter@updates.com",
        "recipient": "you@email.com",
        "subject": "Happy Hour",
        "body": "Join us this Friday for Happy Hour at 5 PM!",
        "timestamp": "2024-09-03T08:00:00",
        "read": False,
    },
    {
        "id": 4,
        "sender": "boss@email.com",
        "recipient": "you@email.com",
        "subject": "Follow-up on Project",
        "body": "Just following up on the project status.",
        "timestamp": "2024-09-04T14:00:00",
        "read": True,
    },
    {
        "id": 5,
        "sender": "friend@personal.com",
        "recipient": "you@email.com",
        "subject": "Weekend plans",
        "body": "Hey, are you free this weekend? Let's catch up!",
        "timestamp": "2024-09-05T18:00:00",
        "read": False,
    },
]

_db: List[dict] = copy.deepcopy(_SEED)
_next_id: int = max(e["id"] for e in _SEED) + 1


# ---------------------------------------------------------------------------
# Pydantic schema
# ---------------------------------------------------------------------------
class SendPayload(BaseModel):
    recipient: str
    subject: str
    body: str
    sender: str = "you@email.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _find(email_id: int) -> dict:
    for e in _db:
        if e["id"] == email_id:
            return e
    raise HTTPException(status_code=404, detail=f"Email {email_id} not found")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/reset_database")
def reset_database():
    global _db, _next_id
    _db = copy.deepcopy(_SEED)
    _next_id = max(e["id"] for e in _SEED) + 1
    return {"message": "Database reset to initial state", "email_count": len(_db)}


@app.post("/send", status_code=200)
def send_email(payload: SendPayload):
    global _next_id
    email = {
        "id": _next_id,
        "sender": payload.sender,
        "recipient": payload.recipient,
        "subject": payload.subject,
        "body": payload.body,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        "read": False,
    }
    _db.insert(0, email)
    _next_id += 1
    return email


@app.get("/emails")
def list_emails():
    return sorted(_db, key=lambda e: e["timestamp"], reverse=True)


@app.get("/emails/unread")
def list_unread():
    unread = [e for e in _db if not e["read"]]
    return sorted(unread, key=lambda e: e["timestamp"], reverse=True)


@app.get("/emails/search")
def search_emails(q: str = Query(..., description="Search query")):
    q_lower = q.lower()
    results = [
        e for e in _db
        if q_lower in e["subject"].lower()
        or q_lower in e["body"].lower()
        or q_lower in e["sender"].lower()
    ]
    return sorted(results, key=lambda e: e["timestamp"], reverse=True)


@app.get("/emails/filter")
def filter_emails(
    recipient: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    results = list(_db)
    if recipient:
        results = [e for e in results if e["recipient"].lower() == recipient.lower()]
    if date_from:
        results = [e for e in results if e["timestamp"] >= date_from]
    if date_to:
        results = [e for e in results if e["timestamp"] <= date_to + "T23:59:59"]
    return sorted(results, key=lambda e: e["timestamp"], reverse=True)


@app.get("/emails/{email_id}")
def get_email(email_id: int):
    return _find(email_id)


@app.patch("/emails/{email_id}/read")
def mark_read(email_id: int):
    email = _find(email_id)
    email["read"] = True
    return email


@app.patch("/emails/{email_id}/unread")
def mark_unread(email_id: int):
    email = _find(email_id)
    email["read"] = False
    return email


@app.delete("/emails/{email_id}")
def delete_email(email_id: int):
    global _db
    _find(email_id)  # raises 404 if missing
    _db = [e for e in _db if e["id"] != email_id]
    return {"message": "Email deleted"}
