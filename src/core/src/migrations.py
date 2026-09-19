
import sqlite3
from pathlib import Path


def init_database(path, schema_sql):
    path=Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn=sqlite3.connect(path)
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()
    return {"status":"INITIALIZED","path":str(path)}


JOBS_SCHEMA="""
CREATE TABLE IF NOT EXISTS jobs(
    job_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    request TEXT NOT NULL,
    status TEXT NOT NULL,
    result_json TEXT,
    error_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

QUEUE_SCHEMA="""
CREATE TABLE IF NOT EXISTS queue_jobs(
    job_id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    available_at REAL NOT NULL DEFAULT 0,
    lease_until REAL,
    worker_id TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

DLQ_SCHEMA="""
CREATE TABLE IF NOT EXISTS dead_letters(
    job_id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    error TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
"""


MEMORY_SCHEMA="""
CREATE TABLE IF NOT EXISTS memory_objects(
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id TEXT NOT NULL,
    version TEXT NOT NULL,
    project_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(object_id, version)
);
"""

AUDIT_SCHEMA="""
CREATE TABLE IF NOT EXISTS run_events(
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    state TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    component TEXT NOT NULL,
    status TEXT NOT NULL,
    details_json TEXT NOT NULL,
    parent_event_id TEXT
);
"""

OPERATOR_SCHEMA="""
CREATE TABLE IF NOT EXISTS operator_actions(
    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operator_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target_id TEXT NOT NULL,
    payload TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def init_all(data_dir):
    data_dir=Path(data_dir)
    results=[]
    results.append(init_database(data_dir/"jobs.sqlite3",JOBS_SCHEMA))
    results.append(init_database(data_dir/"queue.sqlite3",QUEUE_SCHEMA))
    results.append(init_database(data_dir/"dead_letter.sqlite3",DLQ_SCHEMA))
    results.append(init_database(data_dir/"operator.sqlite3",OPERATOR_SCHEMA))
    results.append(init_database(data_dir/"memory.sqlite3",MEMORY_SCHEMA))
    results.append(init_database(data_dir/"audit.sqlite3",AUDIT_SCHEMA))
    return {"status":"INITIALIZED","databases":results}
