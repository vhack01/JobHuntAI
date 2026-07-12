import sqlite3
import os
import json
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    import psycopg2
    from psycopg2.extras import RealDictCursor

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jobs.db")

def get_db_connection():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def get_cursor(conn):
    if DATABASE_URL:
        return conn.cursor(cursor_factory=RealDictCursor)
    else:
        return conn.cursor()

def execute_sql(cursor, query, params=()):
    if DATABASE_URL:
        # Translate SQLite ? placeholders to Postgres %s
        query = query.replace("?", "%s")
    cursor.execute(query, params)

def init_db():
    conn = get_db_connection()
    cursor = get_cursor(conn)
    
    default_tech_keywords = [
        "Java", "Spring Boot", "Spring", "Hibernate", "JPA", "Hibernate/JPA",
        "React", "ReactJS", "Redux", "TypeScript", "JavaScript", "HTML5", "CSS3",
        "LangChain", "LangGraph", "Python", "FastAPI", "REST API", "Microservices",
        "MySQL", "PostgreSQL", "Redis", "Apache Kafka", "Kafka", "Apache Spark", "Spark",
        "AWS", "Docker", "Kubernetes", "Terraform", "GitLab CI/CD", "Git", "Datadog", "Grafana", "K6"
    ]
    
    # Insert default configurations if not exist
    default_configs = {
        "search_keywords": json.dumps(["Java Spring Boot Kafka", "LangGraph AI Agent", "FastAPI Python Backend", "Software Engineer Java AWS"]),
        "search_locations": json.dumps(["Hyderabad", "India", "Remote"]),
        "schedule_morning": "09:00",
        "schedule_evening": "18:00",
        "last_run": "Never",
        "next_run": "Pending Scheduler",
        "filter_max_experience": "2",
        "filter_show_unspecified_exp": "true",
        "target_companies": json.dumps([]),
        "tech_keywords": json.dumps(default_tech_keywords)
    }

    if DATABASE_URL:
        # Create jobs table in Postgres
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id SERIAL PRIMARY KEY,
            job_id VARCHAR(255) UNIQUE,
            title TEXT,
            company TEXT,
            location TEXT,
            description TEXT,
            experience TEXT,
            tech_stack TEXT,
            salary TEXT,
            apply_url TEXT,
            source TEXT,
            date_posted TEXT,
            date_found TEXT,
            status TEXT DEFAULT 'New',
            notes TEXT DEFAULT '',
            is_targeted INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            portal_type TEXT DEFAULT 'Portal'
        )
        """)
        
        # Alter Postgres jobs table to add columns if they don't exist
        try:
            cursor.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_active INTEGER DEFAULT 1")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS portal_type TEXT DEFAULT 'Portal'")
        except Exception:
            pass
        
        # Create config table in Postgres
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key VARCHAR(255) PRIMARY KEY,
            value TEXT
        )
        """)
        
        for key, val in default_configs.items():
            cursor.execute("INSERT INTO config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING", (key, val))
            
    else:
        # Create jobs table in SQLite
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE,
            title TEXT,
            company TEXT,
            location TEXT,
            description TEXT,
            experience TEXT,
            tech_stack TEXT,
            salary TEXT,
            apply_url TEXT,
            source TEXT,
            date_posted TEXT,
            date_found TEXT,
            status TEXT DEFAULT 'New',
            notes TEXT DEFAULT '',
            is_targeted INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            portal_type TEXT DEFAULT 'Portal'
        )
        """)
        
        # Try to add columns for targeted matching and status tracking in SQLite
        try:
            cursor.execute("ALTER TABLE jobs ADD COLUMN is_targeted INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE jobs ADD COLUMN is_active INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE jobs ADD COLUMN portal_type TEXT DEFAULT 'Portal'")
        except sqlite3.OperationalError:
            pass
            
        # Create config table in SQLite
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)
        
        for key, val in default_configs.items():
            cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", (key, val))
            
    conn.commit()
    conn.close()

def get_jobs(status=None, search=None, portal_type=None, active_only=False):
    conn = get_db_connection()
    cursor = get_cursor(conn)
    
    query = "SELECT * FROM jobs"
    params = []
    conditions = []
    
    if status:
        conditions.append("status = ?")
        params.append(status)
        
    if portal_type:
        conditions.append("portal_type = ?")
        params.append(portal_type)
        
    if active_only:
        conditions.append("is_active = 1")
        
    if search:
        conditions.append("(title LIKE ? OR company LIKE ? OR tech_stack LIKE ? OR description LIKE ?)")
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param, search_param])
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += " ORDER BY date_found DESC"
    
    execute_sql(cursor, query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def add_job(job_data):
    """
    Inserts a job into the DB. 
    If the job already exists (unique job_id), update its details,
    but PRESERVE its status and notes.
    Also mark is_active = 1 as it was re-scraped, and set portal_type.
    """
    conn = get_db_connection()
    cursor = get_cursor(conn)
    
    now_str = datetime.now().isoformat()
    
    # Check if job exists
    execute_sql(cursor, "SELECT status, notes FROM jobs WHERE job_id = ?", (job_data["job_id"],))
    existing = cursor.fetchone()
    
    is_targeted_val = job_data.get("is_targeted", 0)
    ptype = job_data.get("portal_type", "Portal")
    
    if existing:
        # Update existing job, keeping status and notes, but updating is_targeted, is_active, portal_type
        if DATABASE_URL:
            cursor.execute("""
            UPDATE jobs 
            SET title = %s, company = %s, location = %s, description = %s, 
                experience = %s, tech_stack = %s, salary = %s, apply_url = %s, 
                source = %s, date_posted = %s, is_targeted = GREATEST(COALESCE(is_targeted, 0), %s),
                is_active = 1, portal_type = %s
            WHERE job_id = %s
            """, (
                job_data.get("title"),
                job_data.get("company"),
                job_data.get("location"),
                job_data.get("description"),
                job_data.get("experience", "Not specified"),
                job_data.get("tech_stack", ""),
                job_data.get("salary", "Not specified"),
                job_data.get("apply_url"),
                job_data.get("source"),
                job_data.get("date_posted"),
                is_targeted_val,
                ptype,
                job_data["job_id"]
            ))
        else:
            cursor.execute("""
            UPDATE jobs 
            SET title = ?, company = ?, location = ?, description = ?, 
                experience = ?, tech_stack = ?, salary = ?, apply_url = ?, 
                source = ?, date_posted = ?, is_targeted = MAX(COALESCE(is_targeted, 0), ?),
                is_active = 1, portal_type = ?
            WHERE job_id = ?
            """, (
                job_data.get("title"),
                job_data.get("company"),
                job_data.get("location"),
                job_data.get("description"),
                job_data.get("experience", "Not specified"),
                job_data.get("tech_stack", ""),
                job_data.get("salary", "Not specified"),
                job_data.get("apply_url"),
                job_data.get("source"),
                job_data.get("date_posted"),
                is_targeted_val,
                ptype,
                job_data["job_id"]
            ))
        conn.commit()
        conn.close()
        return False # Not a new job
    else:
        # Insert new job
        query = """
        INSERT INTO jobs (
            job_id, title, company, location, description, 
            experience, tech_stack, salary, apply_url, source, 
            date_posted, date_found, status, notes, is_targeted, is_active, portal_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'New', '', ?, 1, ?)
        """
        execute_sql(cursor, query, (
            job_data["job_id"],
            job_data.get("title"),
            job_data.get("company"),
            job_data.get("location"),
            job_data.get("description"),
            job_data.get("experience", "Not specified"),
            job_data.get("tech_stack", ""),
            job_data.get("salary", "Not specified"),
            job_data.get("apply_url"),
            job_data.get("source"),
            job_data.get("date_posted"),
            now_str,
            is_targeted_val,
            ptype
        ))
        conn.commit()
        conn.close()
        return True # New job added

def update_job_status(job_id, status):
    conn = get_db_connection()
    cursor = get_cursor(conn)
    execute_sql(cursor, "UPDATE jobs SET status = ? WHERE job_id = ?", (status, job_id))
    conn.commit()
    conn.close()

def update_job_notes(job_id, notes):
    conn = get_db_connection()
    cursor = get_cursor(conn)
    execute_sql(cursor, "UPDATE jobs SET notes = ? WHERE job_id = ?", (notes, job_id))
    conn.commit()
    conn.close()

def set_job_active_status(job_id, is_active):
    conn = get_db_connection()
    cursor = get_cursor(conn)
    execute_sql(cursor, "UPDATE jobs SET is_active = ? WHERE job_id = ?", (is_active, job_id))
    conn.commit()
    conn.close()

def get_config(key, default=None):
    conn = get_db_connection()
    cursor = get_cursor(conn)
    execute_sql(cursor, "SELECT value FROM config WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row["value"]
    return default

def set_config(key, value):
    conn = get_db_connection()
    cursor = get_cursor(conn)
    if DATABASE_URL:
        cursor.execute("INSERT INTO config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (key, value))
    else:
        cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_all_config():
    conn = get_db_connection()
    cursor = get_cursor(conn)
    execute_sql(cursor, "SELECT key, value FROM config")
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}
