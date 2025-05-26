import psycopg2
from db import fetch_all, fetch_one, execute_query
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from datetime import datetime
import pandas as pd
import io, os

from utils.file_handler import load_csv, save_csv, append_csv
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATA_FOLDER = 'data'
USER_FILE = os.path.join(DATA_FOLDER, 'users.csv')
ITEM_FILE = os.path.join(DATA_FOLDER, 'items.csv')
ORDER_FILE = os.path.join(DATA_FOLDER, 'orders.csv')
os.makedirs(DATA_FOLDER, exist_ok=True)

# 기본 사용자 계정은 파일이 없을 때만 저장
if not os.path.exists(USER_FILE):
    default_users = [
        {'user_id': 'admin', 'password': 'admin123', 'role': 'admin', 'admin_type': '2'},
        {'user_id': 'gangnam', 'password': '1234', 'role': 'user'},
        {'user_id': 'seochogu', 'password': 'abcd1234', 'role': 'user'},
    ]
    save_csv(USER_FILE, default_users, ['user_id', 'password', 'role', 'admin_type'])

if not os.path.exists(ITEM_FILE):
    save_csv(ITEM_FILE, [], ['name', 'description', 'stock', 'image', 'category', 'price', 'manufacturer'])

if not os.path.exists(ORDER_FILE):
    save_csv(ORDER_FILE, [], ['store', 'item', 'quantity', 'wish_date', 'date', 'delivery_date'])

@app.route('/')
def index():
    if 'user_id' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))
    items = load_csv(ITEM_FILE)
    items = [item for item in items if int(item.get('stock', 0)) > 0]
    return render_template('index.html', items=items)

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']

        # PostgreSQL 연결
        conn = psycopg2.connect(
            host="dpg-d0pihfje5dus73ds74gg-a.singapore-postgres.render.com",
            port="5432",
            database="beautifulstore",
            user="carrot0217",
            password="oxfvqRLiEN9thqDC1VuRZ9o4xHeKqLPK"
        )
        cur = conn.cursor()

        # 사용자 조회
        cur.execute(
            "SELECT username, password, is_admin FROM users WHERE username = %s",
            (user_id,)
        )
        result = cur.fetchone()

        cur.close()
        conn.close()

        # 인증 성공 시
        if result and result[1] == password:
            session['user_id'] = result[0]
            session['role'] = 'admin' if result[2] else 'user'
            return redirect(url_for('admin_home' if result[2] else 'user_home'))
        else:
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
                save_csv(ITEM_FILE, items, ['name', 'description', 'stock', 'image', 'category', 'price', 'manufacturer'])
                append_csv(ORDER_FILE, {
                    'store': store,
                    'item': item_name,
                    'quantity': quantity,
                    'wish_date': wish_date,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'delivery_date': ''
                }, ['store', 'item', 'quantity', 'wish_date', 'date', 'delivery_date'])
                return redirect(url_for('index'))
            else:
                return render_template("stock_alert.html", item_name=item_name, stock=current_stock)
    return "❌ 상품을 찾을 수 없습니다."

@app.route('/admin/home')
def admin_home():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    admin_type = session.get('admin_type', '1')
    return render_template('admin_home.html', admin_type=admin_type)

@app.route('/admin/orders')
def admin_orders():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    start_date = request.args.get('start')
    end_date = request.args.get('end')
    selected_store = request.args.get('store')

    orders = load_csv(ORDER_FILE)
    filtered_orders = []

    for o in orders:
        try:
            if start_date and end_date:
                order_date = datetime.strptime(o.get('date', ''), "%Y-%m-%d")
                if not (datetime.strptime(start_date, "%Y-%m-%d") <= order_date <= datetime.strptime(end_date, "%Y-%m-%d")):
                    continue
            if selected_store and o.get('store') != selected_store:
                continue
            filtered_orders.append(o)
        except:
            continue

    total_quantity = sum(int(o.get('quantity') or 0) for o in filtered_orders)
    store_names = sorted(set(o.get('store') for o in orders if o.get('store')))

    return render_template('admin_orders.html',
                           orders=filtered_orders,
                           start_date=start_date or '',
                           end_date=end_date or '',
                           selected_store=selected_store or '',
                           store_names=store_names,
                           total_quantity=total_quantity)

@app.route('/admin/orders/update_delivery', methods=['POST'])
def update_delivery():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    order_idx = int(request.form['order_idx'])
    delivery_date = request.form['delivery_date']

    orders = load_csv(ORDER_FILE)
    if 0 <= order_idx < len(orders):
        orders[order_idx]['delivery_date'] = delivery_date
        save_csv(ORDER_FILE, orders, ['store', 'item', 'quantity', 'wish_date', 'date', 'delivery_date'])
        flash('출고일이 확정되었습니다')
    return redirect(url_for('admin_orders'))

@app.route('/admin/orders/download')
def download_orders_excel():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    start_date = request.args.get('start')
    end_date = request.args.get('end')
    selected_store = request.args.get('store')

    orders = load_csv(ORDER_FILE)
    filtered_orders = []

    for o in orders:
        try:
            if start_date and end_date:
                order_date = datetime.strptime(o.get('date', ''), "%Y-%m-%d")
                if not (datetime.strptime(start_date, "%Y-%m-%d") <= order_date <= datetime.strptime(end_date, "%Y-%m-%d")):
                    continue
            if selected_store and o.get('store') != selected_store:
                continue
            filtered_orders.append(o)
        except:
            continue

    if not filtered_orders:
        return "❗ 다운로드할 주문 내역이 없습니다.", 400

    df = pd.DataFrame(filtered_orders)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='주문내역')
    output.seek(0)

    filename = f"주문내역_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output,
                     download_name=filename,
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/admin/items')
def manage_items():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    items = fetch_all("SELECT * FROM inventory ORDER BY id DESC")
    return render_template('admin_items.html', items=items)


@app.route('/admin/items/add', methods=['POST'])
def add_item():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    name = request.form.get('name')
    description = request.form.get('description', '')
    stock = int(request.form.get('stock', '0'))
    category_select = request.form.get('category_select', '')
    custom_category = request.form.get('category', '')
    final_category = custom_category if custom_category else category_select
    price = int(request.form.get('price', '0'))
    manufacturer = request.form.get('manufacturer', '')
    image_file = request.files.get('image')
    image_filename = ''

    if image_file and image_file.filename:
        image_filename = secure_filename(image_file.filename)
        upload_folder = 'static/uploads'
        os.makedirs(upload_folder, exist_ok=True)
        save_path = os.path.join(upload_folder, image_filename)
        base, ext = os.path.splitext(image_filename)
        count = 1
        while os.path.exists(save_path):
            image_filename = f"{base}_{count}{ext}"
            save_path = os.path.join(upload_folder, image_filename)
            count += 1
        image_file.save(save_path)

    execute_query("""
        INSERT INTO inventory (name, description, stock, image, category, price, manufacturer)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (name, description, stock, image_filename, final_category, price, manufacturer))

    return redirect(url_for('manage_items'))


    items = load_csv(ITEM_FILE)
    items.append({
        'name': name,
        'description': description,
        'stock': stock,
        'image': image_filename,
        'category': final_category,
        'price': price,
        'manufacturer': manufacturer
    })
    save_csv(ITEM_FILE, items, ['name', 'description', 'stock', 'image', 'category', 'price', 'manufacturer'])

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
            new_user = {
                'user_id': user_id,
                'password': password,
                'role': role,
                'admin_type': '1'
            }
            users.append(new_user)

        elif action == 'delete':
            users = [u for u in users if u['user_id'] != user_id]

        save_csv(USER_FILE, users, ['user_id', 'password', 'role', 'admin_type'])
        return redirect(url_for('manage_users'))

    return render_template('manage_users.html', users=users)

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
            sdt = datetime.strptime(start_date, "%Y-%m-%d")
            edt = datetime.strptime(end_date, "%Y-%m-%d")
            filtered_orders = [
                o for o in filtered_orders
                if 'wish_date' in o and o['wish_date'] and sdt <= datetime.strptime(o['wish_date'], "%Y-%m-%d") <= edt
            ]
        except:
            pass

    if selected_store:
        filtered_orders = [o for o in filtered_orders if o.get('store') == selected_store]

    store_counts = {}
    item_counts = {}
    for o in filtered_orders:
        store = o.get('store')
        item = o.get('item')
        qty = int(o.get('quantity', 0) or 0)
        if store: store_counts[store] = store_counts.get(store, 0) + qty
        if item: item_counts[item] = item_counts.get(item, 0) + qty

    total_orders = len(filtered_orders)
    total_quantity = sum(int(o.get('quantity', 0) or 0) for o in filtered_orders)
    top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return render_template("admin_dashboard.html",
                           store_names=list(store_counts.keys()),
                           store_values=list(store_counts.values()),
                           item_names=list(item_counts.keys()),
                           item_values=list(item_counts.values()),
                           top_items=top_items,
                           total_orders=total_orders,
                           total_quantity=total_quantity,
                           start_date=start_date or '',
                           end_date=end_date or '',
                           selected_store=selected_store or '',
                           store_list=sorted(set(o.get('store') for o in orders if o.get('store'))))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
