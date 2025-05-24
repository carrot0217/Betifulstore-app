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

@app.route('/admin/items/add', methods=['POST'])
def add_item():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    try:
        name = request.form['name']
        description = request.form.get('description', '')
        stock = request.form.get('stock', '0')
        image_file = request.files.get('image')
        image_filename = ''

        if image_file and image_file.filename != '':
            image_filename = secure_filename(image_file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)

            count = 1
            orig_name, ext = os.path.splitext(image_filename)
            while os.path.exists(save_path):
                image_filename = f"{orig_name}_{count}{ext}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                count += 1

            image_file.save(save_path)

        items = load_csv(ITEM_FILE)
        items.append({
            'name': name,
            'description': description,
            'stock': stock,
            'image': image_filename
        })
        save_csv(ITEM_FILE, items, ['name', 'description', 'stock', 'image'])

        return redirect(url_for('manage_items'))

    except Exception as e:
        return f"❌ 등록 중 오류가 발생했습니다: {str(e)}"

@app.route('/admin/items/delete', methods=['POST'])
def delete_item():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    name = request.form['item_name']
    items = load_csv(ITEM_FILE)
    new_items = []
    for item in items:
        if item['name'] == name:
            if item.get('image'):
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], item['image'])
                if os.path.exists(image_path):
                    os.remove(image_path)
            continue
        new_items.append(item)
    save_csv(ITEM_FILE, new_items, ['name', 'description', 'stock', 'image'])
    return redirect(url_for('manage_items'))

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

@app.route('/admin/dashboard/download')
def download_dashboard_data():
    ...  # 기존 코드 유지

@app.route('/admin/orders/download')
def download_orders_excel():
    ...  # 기존 코드 유지

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
