import os
import time
from datetime import datetime, timezone

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI not found in .env")

client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=8000)


def _with_retry(fn, retries=3, delay=2):
    for attempt in range(retries):
        try:
            return fn()
        except (ConnectionFailure, ServerSelectionTimeoutError):
            if attempt == retries - 1:
                raise
            time.sleep(delay)
db = client["u4h_fundraising"]

roster_col = db["roster"]
recommendations_col = db["recommendations"]
feedback_col = db["feedback"]


def test_connection() -> str:
    _with_retry(lambda: client.admin.command("ping"))
    return "MongoDB connection successful"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# insert + update functions for roster, recommendations, and feedback, as well as retrieval functions.
def upsert_person(person: dict) -> str:
    name = person.get("name", "").strip()
    if not name:
        return "skipped"
    result = roster_col.update_one(
        {"name": {"$regex": f"^{name}$", "$options": "i"}},
        {"$set": {**person, "updated_at": _now_iso()}},
        upsert=True,
    )
    return "inserted" if result.upserted_id else "updated"

def seed_roster_if_empty(people: list[dict]) -> int:
    if not people:
        return 0
    count = 0
    for person in people:
        status = upsert_person(person)
        if status == "inserted":
            count += 1
    return count

def reseed_roster(people: list[dict]) -> int:
    roster_col.delete_many({})
    if not people:
        return 0
    roster_col.insert_many(people)
    return len(people)


def get_roster() -> list[dict]:
    return _with_retry(lambda: list(roster_col.find({}, {"_id": 0})))


def find_person_by_name(name: str) -> dict | None:
    return roster_col.find_one(
        {"name": {"$regex": f"^{name}$", "$options": "i"}},
        {"_id": 0},
    )


def update_person_in_roster(existing_name: str, updates: dict) -> int:
    if not existing_name.strip() or not updates:
        return 0
    payload = {**updates, "updated_at": _now_iso()}
    result = roster_col.update_one(
        {"name": {"$regex": f"^{existing_name}$", "$options": "i"}},
        {"$set": payload},
    )
    return result.modified_count

def save_recommendation(rec: dict) -> str:
    doc = {**rec, "created_at": _now_iso()}
    result = recommendations_col.insert_one(doc)
    return str(result.inserted_id)


def get_recommendations(limit: int = 50) -> list[dict]:
    return list(recommendations_col.find().sort("_id", -1).limit(limit))


def get_recommendation_by_id(rec_id: str):
    try:
        return recommendations_col.find_one({"_id": ObjectId(rec_id)})
    except Exception:
        return None


def save_feedback(rec_id: str, person_name: str, outcome: str, note: str = "") -> str:
    entry = {
        "recommendation_id": rec_id,
        "person_name": person_name,
        "outcome": outcome,
        "note": note,
        "created_at": _now_iso(),
    }
    result = feedback_col.insert_one(entry)
    return str(result.inserted_id)


def get_feedback(limit: int = 50) -> list[dict]:
    return list(feedback_col.find({}, {"_id": 0}).sort("_id", -1).limit(limit))


def get_feedback_for_person(name: str) -> list[dict]:
    target = (name or "").strip()
    if not target:
        return []
    return list(
        feedback_col.find(
            {"person_name": {"$regex": f"^{target}$", "$options": "i"}},
            {"_id": 0},
        ).sort("_id", -1)
    )


def get_outcome_history(limit: int = 100) -> list[dict]:
    rows = _with_retry(
        lambda: list(feedback_col.find({}, {"_id": 0}).sort("_id", -1).limit(limit))
    )
    return [
        {
            "person_name": fb.get("person_name"),
            "outcome": fb.get("outcome"),
            "note": fb.get("note", ""),
        }
        for fb in rows
    ]
