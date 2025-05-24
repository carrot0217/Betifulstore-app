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

os.makedirs(UPLOAD_FOLDER, exist_ok=True)   # ← 이 위치!


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

    # 🔍 필터 파라미터 받아오기
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    selected_store = request.args.get('store')

    orders = load_csv(ORDER_FILE)
    filtered_orders = orders

    # ✅ 날짜 필터 적용
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

    # ✅ 매장 필터 적용
    if selected_store:
        filtered_orders = [o for o in filtered_orders if o['store'] == selected_store]

    # ✅ 총 수량 계산
    total_quantity = sum(int(o['quantity']) for o in filtered_orders) if filtered_orders else 0

    # ✅ 필터용 매장 목록 추출
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

        # 이미지가 있는 경우에만 저장
        if image_file and image_file.filename != '':
            image_filename = secure_filename(image_file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)

            # 파일명 중복 방지
            count = 1
            orig_name, ext = os.path.splitext(image_filename)
            while os.path.exists(save_path):
                image_filename = f"{orig_name}_{count}{ext}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                count += 1

            image_file.save(save_path)

        # 기존 데이터 불러오고 추가
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
            # 이미지 삭제
            if item.get('image'):
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], item['image'])
                if os.path.exists(image_path):
                    os.remove(image_path)
            continue
        new_items.append(item)
    save_csv(ITEM_FILE, new_items, ['name', 'description', 'stock', 'image'])
    return redirect(url_for('manage_items'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    # --- 기간/매장 필터링 ---
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    selected_store = request.args.get('store')

    orders = load_csv(ORDER_FILE)
    filtered_orders = orders

    # 필터: 기간(날짜)
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            filtered_orders = [o for o in filtered_orders if o.get('wish_date') and start_dt <= datetime.strptime(o['wish_date'], "%Y-%m-%d") <= end_dt]
        except:
            pass

    # 필터: 매장
    if selected_store:
        filtered_orders = [o for o in filtered_orders if o['store'] == selected_store]

    # --- 통계 데이터 생성 ---
    total_orders = len(filtered_orders)
    total_quantity = sum(int(o['quantity']) for o in filtered_orders) if filtered_orders else 0

    # 최근 7일 날짜 및 일별 주문건수
    recent_7_days = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
    daily_counts = {d: 0 for d in recent_7_days}
    for o in filtered_orders:
        date = o.get('wish_date')
        if date in daily_counts:
            daily_counts[date] += 1
    daily_data = [daily_counts[d] for d in recent_7_days]

    # store별/상품별 통계
    store_counts = {}
    item_counts = {}
    for o in filtered_orders:
        store = o['store']
        item = o['item']
        qty = int(o['quantity'])
        store_counts[store] = store_counts.get(store, 0) + qty
        item_counts[item] = item_counts.get(item, 0) + qty

    store_names = list(store_counts.keys())
    store_values = list(store_counts.values())
    item_names = list(item_counts.keys())
    item_values = list(item_counts.values())

    # TOP 주문 상품 (수량 기준)
    top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # 매장/상품 리스트(필터용)
    store_list = sorted(set(o['store'] for o in orders))
    item_list = sorted(set(o['item'] for o in orders))

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
        recent_7_days=recent_7_days,
        daily_data=daily_data,
        top_items=top_items
    )


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

@app.route('/admin/orders/download')
def download_orders_excel():
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

    if not filtered_orders:
        return render_template("no_data.html")

    df = pd.DataFrame(filtered_orders)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='주문내역')
    output.seek(0)

    today_str = datetime.now().strftime('%Y%m%d')
    filename = f"전체주문목록_{today_str}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

