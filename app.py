from flask import Flask, render_template, request, redirect, url_for, session, send_file
from datetime import datetime, timedelta
import pandas as pd
import io, os

from utils.file_handler import load_csv, save_csv, append_csv
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATA_FOLDER = 'data'
USER_FILE = os.path.join(DATA_FOLDER, 'users.csv')
ITEM_FILE = os.path.join(DATA_FOLDER, 'items.csv')
ORDER_FILE = os.path.join(DATA_FOLDER, 'orders.csv')

os.makedirs(DATA_FOLDER, exist_ok=True)

default_users = [
    {'user_id': 'admin', 'password': 'admin123', 'role': 'admin'},
    {'user_id': 'gangnam', 'password': '1234', 'role': 'user'},
    {'user_id': 'seochogu', 'password': 'abcd1234', 'role': 'user'},
]

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
                save_csv(ITEM_FILE, items, ['name', 'description', 'stock', 'image'])
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

    start_date = request.args.get('start')
    end_date = request.args.get('end')
    selected_store = request.args.get('store')

    orders = load_csv(ORDER_FILE)
    filtered_orders = orders

    if start_date and end_date:
        try:
            sdt = datetime.strptime(start_date, "%Y-%m-%d")
            edt = datetime.strptime(end_date, "%Y-%m-%d")
            filtered_orders = [
                o for o in filtered_orders
                if 'date' in o and o['date'] and sdt <= datetime.strptime(o['date'], "%Y-%m-%d") <= edt
            ]
        except:
            pass

    if selected_store:
        filtered_orders = [o for o in filtered_orders if o['store'] == selected_store]

    total_quantity = sum(int(o['quantity']) for o in filtered_orders) if filtered_orders else 0
    store_names = sorted(set(o['store'] for o in orders))

    return render_template('admin_orders.html',
                           orders=filtered_orders,
                           start_date=start_date or '',
                           end_date=end_date or '',
                           selected_store=selected_store or '',
                           store_names=store_names,
                           total_quantity=total_quantity)

@app.route('/admin/items')
def manage_items():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    items = load_csv(ITEM_FILE)
    return render_template('admin_items.html', items=items)

@app.route('/admin/users', methods=['GET', 'POST'])
def manage_users():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    users = load_csv(USER_FILE)

    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        role = request.form.get('role')

        if action == 'add':
            users.append({'user_id': user_id, 'password': password, 'role': role})
        elif action == 'delete':
            users = [u for u in users if u['user_id'] != user_id]

        save_csv(USER_FILE, users, ['user_id', 'password', 'role'])
        return redirect(url_for('manage_users'))

    return render_template('manage_users.html', users=users)

@app.route('/admin/dashboard')
def admin_dashboard():
    ...  # 기존 코드 유지

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    start_date = request.args.get('start')
    end_date = request.args.get('end')
    selected_store = request.args.get('store')

    orders = load_csv(ORDER_FILE)
    filtered_orders = orders

    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            filtered_orders = [
                o for o in orders
                if o.get('wish_date') and start_dt <= datetime.strptime(o['wish_date'], "%Y-%m-%d") <= end_dt
            ]
        except:
            pass

    if selected_store:
        filtered_orders = [o for o in filtered_orders if o.get('store') == selected_store]

    total_orders = len(filtered_orders)
    total_quantity = sum(int(o.get('quantity', 0) or 0) for o in filtered_orders)

    store_counts = {}
    item_counts = {}
    for o in filtered_orders:
        store = o.get('store')
        item = o.get('item')
        qty = int(o.get('quantity', 0) or 0)
        store_counts[store] = store_counts.get(store, 0) + qty
        item_counts[item] = item_counts.get(item, 0) + qty

    top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    store_names = list(store_counts.keys())
    store_values = list(store_counts.values())
    item_names = list(item_counts.keys())
    item_values = list(item_counts.values())

    store_list = sorted(set(o.get('store') for o in orders if o.get('store')))
    item_list = sorted(set(o.get('item') for o in orders if o.get('item')))

    return render_template('admin_dashboard.html',
        store_names=store_names,
        store_values=store_values,
        item_names=item_names,
        item_values=item_values,
        start_date=start_date or '',
        end_date=end_date or '',
        selected_store=selected_store or '',
        store_list=store_list,
        item_list=item_list,
        total_orders=total_orders,
        total_quantity=total_quantity,
        top_items=top_items
    )
