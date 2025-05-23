from flask import Flask, render_template, request, redirect, url_for, session, send_file
from datetime import datetime, timedelta
import pandas as pd
import io, os

from utils.file_handler import load_csv, save_csv, append_csv

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATA_FOLDER = 'data'
USER_FILE = os.path.join(DATA_FOLDER, 'users.csv')
ITEM_FILE = os.path.join(DATA_FOLDER, 'items.csv')
ORDER_FILE = os.path.join(DATA_FOLDER, 'orders.csv')

# Ensure data folder exists
os.makedirs(DATA_FOLDER, exist_ok=True)

# 기본 관리자 계정
default_users = [
    {'user_id': 'admin', 'password': 'admin123', 'role': 'admin'},
    {'user_id': 'gangnam', 'password': '1234', 'role': 'user'},
    {'user_id': 'seochogu', 'password': 'abcd1234', 'role': 'user'},
]

# 초기 데이터 세팅
if not os.path.exists(USER_FILE):
    save_csv(USER_FILE, default_users, ['user_id', 'password', 'role'])

@app.route('/')
def index():
    if 'user_id' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))
    items = load_csv(ITEM_FILE)
    return render_template('index.html', items=items)

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        users = load_csv(USER_FILE)
        for user in users:
            if user['user_id'] == user_id and user['password'] == password:
                session['user_id'] = user_id
                session['role'] = user['role']
                return redirect(url_for('admin_home' if user['role'] == 'admin' else 'user_home'))
        message = '❌ 로그인 실패: ID 또는 비밀번호 확인'
    return render_template('login.html', message=message)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/user/home')
def user_home():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    return render_template('user_home.html')

@app.route('/orders')
def view_orders():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    orders = load_csv(ORDER_FILE)
    user_orders = [o for o in orders if o['store'] == session['user_id']]
    return render_template('orders.html', orders=user_orders)

@app.route('/order', methods=['POST'])
def place_order():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    item_name = request.form['item_name']
    quantity = int(request.form['quantity'])
    wish_date = request.form['wish_date']
    store = session['user_id']

    items = load_csv(ITEM_FILE)
    for item in items:
        if item['name'] == item_name:
            current_stock = int(item['stock'])
            if current_stock >= quantity:
                item['stock'] = str(current_stock - quantity)
                save_csv(ITEM_FILE, items, ['name', 'description', 'stock'])
                append_csv(ORDER_FILE, {
                    'store': store,
                    'item': item_name,
                    'quantity': quantity,
                    'wish_date': wish_date,
                    'date': datetime.now().strftime('%Y-%m-%d')
                }, ['store', 'item', 'quantity', 'wish_date', 'date'])
                return redirect(url_for('index'))
            else:
                return f"❗ 재고 부족: 현재 {current_stock}개 남아 있습니다."
    return "❌ 상품을 찾을 수 없습니다."

@app.route('/admin/home')
def admin_home():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    return render_template('admin_home.html')

@app.route('/admin/orders')
def admin_orders():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    orders = load_csv(ORDER_FILE)
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/items')
def manage_items():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    items = load_csv(ITEM_FILE)
    return render_template('admin_items.html', items=items)

@app.route('/admin/items/add', methods=['POST'])
def add_item():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    item = {
        'name': request.form['name'],
        'description': request.form['description'],
        'stock': request.form['stock']
    }
    items = load_csv(ITEM_FILE)
    items.append(item)
    save_csv(ITEM_FILE, items, ['name', 'description', 'stock'])
    return redirect(url_for('manage_items'))

@app.route('/admin/items/delete', methods=['POST'])
def delete_item():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    name = request.form['item_name']
    items = load_csv(ITEM_FILE)
    items = [item for item in items if item['name'] != name]
    save_csv(ITEM_FILE, items, ['name', 'description', 'stock'])
    return redirect(url_for('manage_items'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    orders = load_csv(ORDER_FILE)
    total_quantity = sum(int(o['quantity']) for o in orders)
    item_counts = {}
    for o in orders:
        item_counts[o['item']] = item_counts.get(o['item'], 0) + int(o['quantity'])
    top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    return render_template('admin_dashboard.html',
                           total_orders=len(orders),
                           total_quantity=total_quantity,
                           top_items=top_items)

@app.route('/admin/dashboard/download')
def download_dashboard_data():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    orders = load_csv(ORDER_FILE)
    if not orders:
        return render_template('no_data.html')
    df = pd.DataFrame(orders)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='주문통계')
    output.seek(0)
    today_str = datetime.now().strftime('%Y%m%d')
    filename = f"주문통계_{today_str}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

