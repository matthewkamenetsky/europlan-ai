import os
import sqlite3
import json
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/europlan.db")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def insert_trip(name: str, cities: list[str], trip_length: int, interests: list[str]) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO trips (name, cities, trip_length, interests, itinerary, conversation) VALUES (?, ?, ?, ?, NULL, NULL)",
            (name, json.dumps(cities), trip_length, json.dumps(interests)),
        )
        conn.commit()
        return cursor.lastrowid

def save_itinerary(trip_id: int, itinerary: str):
    with get_db() as conn:
        conn.execute("UPDATE trips SET itinerary = ? WHERE id = ?", (itinerary, trip_id))
        conn.commit()

def update_itinerary(trip_id: int, itinerary: str) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE trips SET itinerary = ? WHERE id = ?", (itinerary, trip_id))
        conn.commit()
        return cursor.rowcount > 0

def fetch_conversation(trip_id: int) -> list[dict]:
    """Returns conversation history as a list of {role, content} dicts. Empty list if none."""
    with get_db() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT conversation FROM trips WHERE id = ?", (trip_id,))
        row = cursor.fetchone()
        if row is None or row["conversation"] is None:
            return []
        return json.loads(row["conversation"])

def update_conversation(trip_id: int, messages: list[dict]) -> bool:
    """Overwrites the full conversation history for a trip."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE trips SET conversation = ? WHERE id = ?",
            (json.dumps(messages), trip_id),
        )
        conn.commit()
        return cursor.rowcount > 0

def fetch_all_trips() -> list[dict]:
    with get_db() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, cities, trip_length, interests, created_at
            FROM trips ORDER BY created_at DESC
        """)
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "cities": json.loads(row["cities"]),
                "trip_length": row["trip_length"],
                "interests": json.loads(row["interests"]),
                "created_at": row["created_at"],
            }
            for row in cursor.fetchall()
        ]

def fetch_trip(trip_id: int) -> dict | None:
    with get_db() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trips WHERE id = ?", (trip_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "cities": json.loads(row["cities"]),
            "trip_length": row["trip_length"],
            "interests": json.loads(row["interests"]),
            "itinerary": row["itinerary"],
            "conversation": json.loads(row["conversation"]) if row["conversation"] else [],
            "created_at": row["created_at"],
        }

def delete_trip(trip_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
        conn.commit()
        return cursor.rowcount > 0