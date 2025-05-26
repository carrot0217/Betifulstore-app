# db.py
import psycopg2

DB_CONFIG = {
    'host': 'dpg-d0pihfje5dus73ds74gg-a.singapore-postgres.render.com',
    'port': 5432,
    'database': 'beautifulstore',
    'user': 'carrot0217',
    'password': 'oxfvqRLiEN9thqDC1VuRZ9o4xHeKqLPK'
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def fetch_all(query, params=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    result = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return [dict(zip(colnames, row)) for row in result]

def fetch_one(query, params=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    row = cur.fetchone()
    colnames = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return dict(zip(colnames, row)) if row else None

def execute_query(query, params=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    conn.commit()
    cur.close()
    conn.close()
