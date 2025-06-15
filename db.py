# db.py
import psycopg

def get_connection():
    conn = psycopg.connect(
        host="dpg-d0pihfje5dus73ds74gg-a.singapore-postgres.render.com",
        port=5432,
        dbname="beautifulstore",
        user="carrot0217",
        password="oxfvqRLiEN9thqDC1VuRZ9o4xHeKqLPK"
    )
    return conn
