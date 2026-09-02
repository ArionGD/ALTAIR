import os
import sqlite3
import json
import uuid
from datetime import datetime
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "research_sessions.db")

def load_env():
    env_file = os.path.join(BASE_DIR, ".env")
    env_vars = {}
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()
    return env_vars

ENV = load_env()
SUPABASE_URL = ENV.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = ENV.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY", "")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            table_data TEXT,
            chart_data TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

def create_session(title: str = "Quantitative Research Session") -> dict:
    session_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    
    # 1. SQLite Local
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (session_id, title, now, now)
    )
    conn.commit()
    conn.close()
    
    # 2. Supabase Sync (if configured)
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            url = f"{SUPABASE_URL}/rest/v1/sessions"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
            data = json.dumps({"id": session_id, "title": title, "created_at": now, "updated_at": now}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers)
            urllib.request.urlopen(req, timeout=4)
        except Exception as e:
            print(f"Supabase session sync notice: {e}")

    return {"id": session_id, "title": title, "created_at": now, "updated_at": now}

def list_sessions() -> list:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT s.id, s.title, s.created_at, s.updated_at,
               COUNT(m.id) as message_count,
               (SELECT content FROM messages WHERE session_id = s.id ORDER BY created_at DESC LIMIT 1) as last_message
        FROM sessions s
        LEFT JOIN messages m ON s.id = m.session_id
        GROUP BY s.id
        ORDER BY s.updated_at DESC
    ''')
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_session_messages(session_id: str) -> list:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, session_id, role, content, table_data, chart_data, created_at FROM messages WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,)
    )
    rows = []
    for r in c.fetchall():
        d = dict(r)
        if d.get("table_data"):
            try:
                d["table_data"] = json.loads(d["table_data"])
            except Exception:
                pass
        if d.get("chart_data"):
            try:
                d["chart_data"] = json.loads(d["chart_data"])
            except Exception:
                pass
        rows.append(d)
    conn.close()
    return rows

def add_message(session_id: str, role: str, content: str, table_data=None, chart_data=None) -> dict:
    msg_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    table_json = json.dumps(table_data) if table_data else None
    chart_json = json.dumps(chart_data) if chart_data else None
    
    # 1. Save in SQLite
    conn = get_db_connection()
    c = conn.cursor()
    
    # Ensure session exists
    c.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
    if not c.fetchone():
        # Auto-create session if missing
        first_title = content[:30] + ("..." if len(content) > 30 else "")
        c.execute("INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                  (session_id, first_title, now, now))
    else:
        c.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        
    c.execute(
        "INSERT INTO messages (id, session_id, role, content, table_data, chart_data, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (msg_id, session_id, role, content, table_json, chart_json, now)
    )
    conn.commit()
    conn.close()
    
    # 2. Supabase Sync (if configured)
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            url = f"{SUPABASE_URL}/rest/v1/messages"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
            payload = {
                "id": msg_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "table_data": table_json,
                "chart_data": chart_json,
                "created_at": now
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
            urllib.request.urlopen(req, timeout=4)
        except Exception as e:
            print(f"Supabase message sync notice: {e}")

    return {
        "id": msg_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "table_data": table_data,
        "chart_data": chart_data,
        "created_at": now
    }

def delete_session(session_id: str) -> bool:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

    if SUPABASE_URL and SUPABASE_KEY:
        try:
            url = f"{SUPABASE_URL}/rest/v1/sessions?id=eq.{session_id}"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
            req = urllib.request.Request(url, headers=headers, method="DELETE")
            urllib.request.urlopen(req, timeout=4)
        except Exception as e:
            print(f"Supabase delete notice: {e}")

    return True

# Initialize database on import
init_db()
