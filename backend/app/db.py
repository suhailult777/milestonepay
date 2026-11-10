import json
import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, client_name TEXT, client_email TEXT,
  total TEXT, currency TEXT, source_text TEXT, status TEXT, extraction_source TEXT, created REAL);
CREATE TABLE IF NOT EXISTS milestones(id TEXT PRIMARY KEY, project_id TEXT, seq INTEGER, title TEXT,
  amount TEXT, currency TEXT, due_date TEXT, evidence TEXT, status TEXT, invoice_id TEXT,
  request_id TEXT UNIQUE, pay_link TEXT, paid_amount TEXT,
  op_state TEXT NOT NULL DEFAULT 'NONE', op_note TEXT, hold TEXT);
CREATE TABLE IF NOT EXISTS webhook_events(event_id TEXT PRIMARY KEY, event_type TEXT, resource_id TEXT,
  outcome TEXT, received REAL);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, actor TEXT,
  action TEXT, detail TEXT, at REAL);
"""


def connect(path: str) -> sqlite3.Connection:
    c = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


def audit(c: sqlite3.Connection, project_id: str | None, actor: str, action: str, detail: dict) -> None:
    c.execute("INSERT INTO audit(project_id,actor,action,detail,at) VALUES(?,?,?,?,?)",
              (project_id, actor, action, json.dumps(detail, default=str), time.time()))
