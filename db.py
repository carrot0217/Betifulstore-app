# db.py
import psycopg2

def get_connection():
    conn = psycopg2.connect(
        host="dpg-d0pihfje5dus73ds74gg-a.singapore-postgres.render.com",
        port="5432",
        database="beautifulstore",
        user="carrot0217",
        password="oxfvqRLiEN9thqDC1VuRZ9o4xHeKqLPK"
    )
    conn.autocommit = True   # ★ 이 한 줄 추가!!
    return conn
