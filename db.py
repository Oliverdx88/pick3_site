import sqlite3
from contextlib import closing

DB_PATH = "app.db"

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            stripe_customer_id TEXT,
            plan TEXT,               -- free | vip_monthly | vip_yearly
            status TEXT,             -- active | trialing | canceled | incomplete | past_due
            current_period_end INTEGER
        )
        """)

def upsert_user(email, stripe_customer_id=None, plan=None, status=None, current_period_end=None):
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        # upsert by email
        row = conn.execute("SELECT email FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            conn.execute("""
              UPDATE users
                 SET stripe_customer_id = COALESCE(?, stripe_customer_id),
                     plan = COALESCE(?, plan),
                     status = COALESCE(?, status),
                     current_period_end = COALESCE(?, current_period_end)
               WHERE email = ?
            """, (stripe_customer_id, plan, status, current_period_end, email))
        else:
            conn.execute("""
              INSERT INTO users (email, stripe_customer_id, plan, status, current_period_end)
              VALUES (?, ?, ?, ?, ?)
            """, (email, stripe_customer_id, plan, status, current_period_end))

def get_user(email):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        row = conn.execute("""
          SELECT email, stripe_customer_id, plan, status, current_period_end
            FROM users WHERE email = ?
        """, (email,)).fetchone()
        if not row:
            return None
        return {
            "email": row[0],
            "stripe_customer_id": row[1],
            "plan": row[2],
            "status": row[3],
            "current_period_end": row[4],
        }
