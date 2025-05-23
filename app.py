from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 로그인 사용자 정보 (예시)
users = {
    'admin': 'admin1234',
    'store1': 'pass1'
}

# 상품 목록 저장용 (임시 리스트)
items = []

# ------------------- 라우터 영역 -------------------

# 홈 또는 로그인
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login_user', methods=['POST'])
def login_user():
    user_id = request.form['user_id']
    password = request.form['password']
    if user_id in users and users[user_id] == password:
        session['user'] = user_id
        if user_id == 'admin':
            return redirect(url_for('admin_home'))
        else:
            return redirect(url_for('user_home'))
    return '로그인 실패!'

# 사용자 홈
@app.route('/user/home')
def user_home():
    return render_template('user_home.html')

# 관리자 홈
@app.route('/admin')
def admin_home():
    return render_template('admin_home.html')

# 전체 주문 이력 (예시용)
@app.route('/admin/orders')
def admin_orders():
    return render_template('admin_orders.html')

# 사용자 관리 (예시용)
@app.route('/admin/users')
def manage_users():
    return render_template('manage_users.html')

# 관리자 대시보드 (예시용)
@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

# ------------------- 상품 등록/삭제 기능 -------------------

@app.route('/admin/items')
def manage_items():
    return render_template('admin_items.html', items=items)

@app.route('/admin/items/add', methods=['POST'])
def add_item():
    item_name = request.form.get('item_name')
    if item_name:
        items.append(item_name)
    return redirect(url_for('manage_items'))

# ------------------- 세션 로그아웃 -------------------

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ------------------- 실행 -------------------

if __name__ == '__main__':
    app.run(debug=True)
