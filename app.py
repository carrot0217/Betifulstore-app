from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from datetime import datetime
from db import get_connection

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# -------------------- 사용자 인증 --------------------
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, is_admin FROM users WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['username'] = username
            session['is_admin'] = user[1]
            return redirect(url_for('dashboard'))
        else:
            flash('❌ 로그인 실패: 아이디나 비밀번호를 확인하세요.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -------------------- 대시보드 --------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, description, quantity FROM items")
    items = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('index.html', items=items, username=session.get('username'))

# -------------------- 주문 처리 --------------------
@app.route('/order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    item_id = request.form['item_id']
    quantity = int(request.form['quantity'])

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders (user_id, item_id, quantity)
        VALUES (%s, %s, %s)
    """, (session['user_id'], item_id, quantity))
    conn.commit()
    cur.close()
    conn.close()

    flash('✅ 주문이 완료되었습니다!')
    return redirect(url_for('dashboard'))

# -------------------- 관리자 상품 등록 --------------------
@app.route('/admin/items', methods=['GET', 'POST'])
def manage_items():
    if not session.get('is_admin'):
        return redirect(url_for('dashboard'))

    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        quantity = int(request.form['quantity'])
        cur.execute("""
            INSERT INTO items (name, description, quantity)
            VALUES (%s, %s, %s)
        """, (name, description, quantity))
        conn.commit()
        flash('✅ 상품이 등록되었습니다!')

    cur.execute("SELECT id, name, description, quantity FROM items")
    items = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_items.html', items=items)

if __name__ == '__main__':
    app.run(debug=True)
