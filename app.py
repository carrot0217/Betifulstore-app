from flask import Flask, render_template, request, redirect, url_for, session, send_file
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import io
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

inventory = []
orders = []

# ✅ 사용자 및 관리자 계정 구성
users = {
    "gangnam": {"password": "1234", "role": "user"},
    "seochogu": {"password": "abcd1234", "role": "user"},
    "hongdae": {"password": "pppp5555", "role": "user"},
    "admin": {"password": "admin1234", "role": "admin"}  # 관리자 계정
}

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))
    
    keyword = request.args.get('keyword', '')
    sort_by = request.args.get('sort', '')
    success = request.args.get('success')

    filtered_inventory = [item for item in inventory if keyword.lower() in item['name'].lower()]
    if sort_by == 'name':
        filtered_inventory.sort(key=lambda x: x['name'])
    elif sort_by == 'stock':
        filtered_inventory.sort(key=lambda x: x['stock'], reverse=True)
    
    return render_template('index.html', inventory=filtered_inventory,
                           keyword=keyword, sort_by=sort_by, success=success)

@app.route('/login_user', methods=['GET', 'POST'])
def login_user():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        user = users.get(user_id)
        if user and user['password'] == password:
            session['user_id'] = user_id
            session['role'] = user['role']
            if user['role'] == 'admin':
                return redirect(url_for('admin_home'))
            else:
                return redirect(url_for('user_home'))
        else:
            return "로그인 실패: 잘못된 ID 또는 비밀번호입니다."
    return render_template('login_user.html')

@app.route('/user/home')
def user_home():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))
    return render_template('user_home.html')

@app.route('/logout_user')
def logout_user():
    session.pop('user_id', None)
    session.pop('role', None)
    return redirect(url_for('login_user'))

@app.route('/order', methods=['POST'])
def order():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    item_index = int(request.form['item_index'])
    quantity = int(request.form['quantity'])
    store = session['user_id']
    wish_date = request.form['wish_date']
    item = inventory[item_index]

    if item['stock'] >= quantity:
        item['stock'] -= quantity
        orders.append({
            'store': store,
            'item': item['name'],
            'quantity': quantity,
            'wish_date': wish_date,
            'date': datetime.now().date()
        })
        return redirect(url_for('index', success=1))
    else:
        return f"현 재고는 {item['stock']}개 입니다."

@app.route('/orders')
def view_orders():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))
    user_orders = [o for o in orders if o['store'] == session['user_id']]
    return render_template('orders.html', orders=user_orders)

# ✅ 관리자 홈 라우트
@app.route('/admin/home')
def admin_home():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login_user'))
    return render_template('admin_home.html')

# 실행
if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=10000)

