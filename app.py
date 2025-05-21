from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
from collections import Counter
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

inventory = []
orders = []

users = {
    "gangnam": "1234",
    "seochogu": "abcd1234",
    "hongdae": "pppp5555"
}

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))

    keyword = request.args.get('keyword', '')
    sort_by = request.args.get('sort', '')

    filtered_inventory = [item for item in inventory if keyword.lower() in item['name'].lower()]

    if sort_by == 'name':
        filtered_inventory.sort(key=lambda x: x['name'])
    elif sort_by == 'stock':
        filtered_inventory.sort(key=lambda x: x['stock'], reverse=True)

    return render_template('index.html', inventory=filtered_inventory, keyword=keyword, sort_by=sort_by)

@app.route('/login_user', methods=['GET', 'POST'])
def login_user():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        if user_id in users and users[user_id] == password:
            session['user_id'] = user_id
            return redirect(url_for('index'))
        else:
            return "로그인 실패: 잘못된 ID 또는 비밀번호입니다."
    return render_template('login_user.html')

@app.route('/logout_user')
def logout_user():
    session.pop('user_id', None)
    return redirect(url_for('login_user'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        stock = int(request.form['stock'])
        image = request.files['image']
        filename = secure_filename(image.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(image_path)

        for item in inventory:
            if item['name'] == name:
                return "이미 동일한 상품명이 등록되어 있습니다."

        inventory.append({
            'name': name,
            'description': description,
            'stock': stock,
            'image': image_path
        })
        return redirect(url_for('admin'))
    return render_template('admin.html', inventory=inventory)

@app.route('/delete/<int:index>', methods=['POST'])
def delete(index):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    if 0 <= index < len(inventory):
        del inventory[index]
    return redirect(url_for('admin'))

@app.route('/edit/<int:index>', methods=['GET', 'POST'])
def edit(index):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        inventory[index]['name'] = request.form['name']
        inventory[index]['description'] = request.form['description']
        inventory[index]['stock'] = int(request.form['stock'])
        return redirect(url_for('admin'))
    item = inventory[index]
    return render_template('edit.html', item=item, index=index)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        if password == 'admin123':
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return "비밀번호가 틀렸습니다."
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

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
    else:
        return f"현 재고는 {item['stock']}개 입니다."
    return redirect(url_for('index'))

@app.route('/orders')
def view_orders():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))
    user_orders = [o for o in orders if o['store'] == session['user_id']]
    return render_template('orders.html', orders=user_orders)

@app.route('/admin/orders', methods=['GET', 'POST'])
def admin_orders():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    selected_store = request.form.get('store')
    filtered_orders = orders
    if selected_store:
        filtered_orders = [o for o in orders if o['store'] == selected_store]
    store_names = sorted(set(o['store'] for o in orders))

    return render_template('admin_orders.html', orders=filtered_orders, store_names=store_names, selected_store=selected_store)

@app.route('/admin/users', methods=['GET', 'POST'])
def manage_users():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    message = ''
    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id')
        password = request.form.get('password')

        if action == 'add':
            if user_id in users:
                message = f"⚠ 이미 존재하는 사용자 ID입니다: {user_id}"
            else:
                users[user_id] = password
                message = f"✅ 사용자 추가 완료: {user_id}"
        elif action == 'delete':
            if user_id in users:
                del users[user_id]
                message = f"🗑 사용자 삭제 완료: {user_id}"
            else:
                message = f"❌ 해당 ID는 존재하지 않습니다."

    return render_template('manage_users.html', users=users, message=message)

@app.route('/admin/dashboard')
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    total_orders = len(orders)
    total_quantity = sum(o['quantity'] for o in orders)

    store_counter = Counter(o['store'] for o in orders)
    item_counter = Counter(o['item'] for o in orders)

    recent_days = [datetime.now().date() - timedelta(days=i) for i in range(6, -1, -1)]
    daily_counter = Counter(o['date'] for o in orders if 'date' in o)
    date_labels = [d.strftime('%Y-%m-%d') for d in recent_days]
    daily_counts = [daily_counter.get(d, 0) for d in recent_days]

    top_items = item_counter.most_common(5)
    top_item_labels = [i[0] for i in top_items]
    top_item_counts = [i[1] for i in top_items]

    return render_template('admin_dashboard.html',
                           total_orders=total_orders,
                           total_quantity=total_quantity,
                           store_labels=list(store_counter.keys()),
                           store_counts=list(store_counter.values()),
                           item_labels=list(item_counter.keys()),
                           item_counts=list(item_counter.values()),
                           date_labels=date_labels,
                           daily_counts=daily_counts,
                           top_item_labels=top_item_labels,
                           top_item_counts=top_item_counts)

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=10000)
