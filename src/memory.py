import sqlite3
import os
from datetime import datetime, UTC
DB_PATH = "memory/investigations.db"

def init_db():
    os.makedirs("memory", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS investigations (subject TEXT PRIMARY KEY,confidence REAL,summary TEXT,timestamp TEXT)""")
    conn.commit()
    conn.close()

def get_past_investigation(subject: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT confidence, summary, timestamp FROM investigations WHERE subject = ?",(subject,)).fetchone()
    conn.close()
    if row:
        return {"confidence": row[0], "summary": row[1], "timestamp": row[2]}
    return None

def save_investigation(subject: str, confidence: float, summary: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR REPLACE INTO investigations (subject, confidence, summary, timestamp) VALUES (?, ?, ?, ?)",(subject, confidence, summary, datetime.now(UTC).isoformat()))
    conn.commit()
    conn.close()