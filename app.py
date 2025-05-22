from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

inventory = []
orders = []

# 사용자 계정
users = {
    "gangnam": "1234",
    "seochogu": "abcd1234",
    "hongdae": "pppp5555"
}

# 사용자용 메인 페이지
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

    return render_template('index.html', inventory=filtered_inventory,
                           keyword=keyword, sort_by=sort_by)

# 사용자 로그인/로그아웃
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

# 관리자 로그인/로그아웃
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

# 관리자 상품 등록 페이지
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

# 상품 삭제
@app.route('/delete/<int:index>', methods=['POST'])
def delete(index):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    if 0 <= index < len(inventory):
        del inventory[index]
    return redirect(url_for('admin'))

# 상품 수정
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

# 주문 처리
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

# 사용자 주문 이력 보기
@app.route('/orders')
def view_orders():
    if 'user_id' not in session:
        return redirect(url_for('login_user'))
    user_orders = [o for o in orders if o['store'] == session['user_id']]
    return render_template('orders.html', orders=user_orders)

# 관리자 전체 주문 이력
@app.route('/admin/orders', methods=['GET', 'POST'])
def admin_orders():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    selected_store = request.form.get('store')
    filtered_orders = orders
    if selected_store:
        filtered_orders = [o for o in orders if o['store'] == selected_store]
    store_names = sorted(set(o['store'] for o in orders))

    return render_template('admin_orders.html',
                           orders=filtered_orders,
                           store_names=store_names,
                           selected_store=selected_store)

# 관리자 통계 대시보드
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    start_date = request.args.get('start')
    end_date = request.args.get('end')
    selected_store = request.args.get('store')
    selected_item = request.args.get('item')

    filtered_orders = orders
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            filtered_orders = [
                o for o in filtered_orders
                if 'wish_date' in o and start_dt <= datetime.strptime(o['wish_date'], "%Y-%m-%d") <= end_dt
            ]
        except:
            pass

    if selected_store:
        filtered_orders = [o for o in filtered_orders if o['store'] == selected_store]
    if selected_item:
        filtered_orders = [o for o in filtered_orders if o['item'] == selected_item]

    total_orders = len(filtered_orders)
    total_quantity = sum(o['quantity'] for o in filtered_orders)

    store_counts = {}
    item_counts = {}
    daily_counts = {}

    for o in filtered_orders:
        store = o['store']
        item = o['item']
        qty = o['quantity']
        date = o.get('wish_date', '')
        store_counts[store] = store_counts.get(store, 0) + 1
        item_counts[item] = item_counts.get(item, 0) + qty
        if date:
            daily_counts[date] = daily_counts.get(date, 0) + 1

    recent_7_days = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
    daily_data = [daily_counts.get(day, 0) for day in recent_7_days]
    top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    store_list = sorted(set(o['store'] for o in orders))
    item_list = sorted(set(o['item'] for o in orders))

    return render_template('admin_dashboard.html',
                           total_orders=total_orders,
                           total_quantity=total_quantity,
                           store_counts=store_counts,
                           item_counts=item_counts,
                           recent_7_days=recent_7_days,
                           daily_data=daily_data,
                           top_items=top_items,
                           start_date=start_date or '',
                           end_date=end_date or '',
                           selected_store=selected_store or '',
                           selected_item=selected_item or '',
                           store_list=store_list,
                           item_list=item_list)

# /wakeup 중간 안내 페이지
@app.route('/wakeup')
def wakeup():
    return render_template('wakeup.html')

# 사용자 관리
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

# 서버 실행
if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=10000)
