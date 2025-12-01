import datetime
import os
import io
import numpy as np
from PIL import Image

# IMPORTS
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array

# CONFIG
app = Flask(__name__)
app.config['SECRET_KEY'] = 'rahasia_super_aman_banget'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kasir.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ==========================================
# 1. MODEL DATABASE
# ==========================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(20), default='user') # 'admin' atau 'user'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, default=0) 
    ai_index = db.Column(db.Integer, unique=True, nullable=False) 

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.now)
    items_str = db.Column(db.Text, nullable=False)
    total_price = db.Column(db.Integer, nullable=False)
    cash_in = db.Column(db.Integer, default=0)
    change = db.Column(db.Integer, default=0)
    payment_method = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='PAID') # 'PAID' atau 'PENDING'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==========================================
# 2. INIT DATABASE
# ==========================================
def init_db():
    with app.app_context():
        db.create_all()
        
        # Buat Akun Default
        if User.query.count() == 0:
            print("⚙️ Membuat Akun Default...")
            # Admin
            admin = User(username='admin', password=generate_password_hash('admin', method='pbkdf2:sha256'), role='admin')
            db.session.add(admin)
            # Kasir (User Biasa)
            user = User(username='kasir', password=generate_password_hash('kasir', method='pbkdf2:sha256'), role='user')
            db.session.add(user)
            db.session.commit()
            print("✅ User 'admin' & 'kasir' BERHASIL DIBUAT!")

        # Buat Produk Default
        if Product.query.count() == 0:
            print("⚙️ Mengisi Stok Awal...")
            initial_products = [
                Product(name="Biore", price=25000, stock=50, ai_index=0),
                Product(name="Indomie", price=3500, stock=100, ai_index=1),
                Product(name="Teh Botol", price=5000, stock=48, ai_index=2),
                Product(name="Zinc", price=18000, stock=20, ai_index=3)
            ]
            db.session.bulk_save_objects(initial_products)
            db.session.commit()

init_db()

# LOAD AI
try:
    model = load_model('best_checkout_model.h5')
    print("✅ AI Model Loaded!")
except:
    print("❌ Warning: Model AI tidak ditemukan.")

# ==========================================
# 3. ROUTES (HALAMAN)
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            # LOGIKA REDIRECT: Admin -> Antrian, User -> Kasir
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('cashier_dashboard'))
        else:
            return render_template('login.html', error="Login Gagal!")
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- HALAMAN USER (KASIR MANDIRI) ---
@app.route('/')
@login_required
def cashier_dashboard():
    return render_template('kasir_laptop.html', user=current_user)

# --- HALAMAN ADMIN (ANTRIAN PEMBAYARAN) ---
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin': return redirect(url_for('cashier_dashboard'))
    
    # Ambil transaksi yang PENDING
    pending_trans = Transaction.query.filter_by(status='PENDING').order_by(Transaction.timestamp.desc()).all()
    return render_template('admin_dashboard.html', pending_trans=pending_trans)

# --- HALAMAN ADMIN LAINNYA ---
@app.route('/inventory')
@login_required
def inventory_page():
    if current_user.role != 'admin': return redirect(url_for('cashier_dashboard'))
    products = Product.query.order_by(Product.ai_index).all()
    return render_template('inventory.html', products=products)

@app.route('/history')
@login_required
def history_page():
    if current_user.role != 'admin': return redirect(url_for('cashier_dashboard'))
    data = Transaction.query.order_by(Transaction.timestamp.desc()).all()
    total_omzet = sum(t.total_price for t in data if t.status == 'PAID') # Hitung yg lunas saja
    count = len(data)
    return render_template('history.html', transactions=data, omzet=total_omzet, count=count)

@app.route('/scan')
def scanner_mobile():
    return render_template('scanner_hp.html')

# ==========================================
# 4. API (LOGIC CHECKOUT & AI)
# ==========================================

# --- PROSES CHECKOUT (HYBRID) ---
@app.route('/checkout', methods=['POST'])
def process_checkout():
    data = request.json
    
    # Logic Status: QRIS = Lunas, TUNAI = Pending (Tunggu Admin)
    initial_status = 'PAID' if data['method'] == 'QRIS' else 'PENDING'

    new_trans = Transaction(
        items_str=data['items'],
        total_price=data['total'],
        cash_in=data['cash_in'],
        change=data['change'],
        payment_method=data['method'],
        status=initial_status
    )
    db.session.add(new_trans)
    
    # Jika QRIS, potong stok langsung
    if initial_status == 'PAID':
        if data['items']:
            item_names = data['items'].split(", ")
            for name in item_names:
                prod = Product.query.filter_by(name=name).first()
                if prod and prod.stock > 0: prod.stock -= 1
    
    db.session.commit()

    # Jika Pending (Tunai), Beritahu Admin via SocketIO
    if initial_status == 'PENDING':
        socketio.emit('incoming_payment', {
            'id': new_trans.id,
            'items': new_trans.items_str,
            'total': new_trans.total_price,
            'method': new_trans.payment_method
        })
    
    return jsonify({"status": "success", "id": new_trans.id, "trx_status": initial_status})

# --- KONFIRMASI ADMIN (TERIMA DUIT) ---
# --- UPDATE DI APP.PY ---

@app.route('/confirm_payment', methods=['POST'])
@login_required
def confirm_payment():
    req = request.json
    t_id = req['id']
    trans = Transaction.query.get(t_id)
    
    if trans and trans.status == 'PENDING':
        trans.status = 'PAID'
        
        # Simpan Data Uang dari Admin (JIKA ADA)
        # Jika confirm QRIS, cash_in = total. Jika Tunai, sesuai input admin.
        if 'cash_in' in req:
            trans.cash_in = req['cash_in']
            trans.change = req['change']
        
        # Potong Stok
        item_names = trans.items_str.split(", ")
        for name in item_names:
            prod = Product.query.filter_by(name=name).first()
            if prod and prod.stock > 0: prod.stock -= 1
            
        db.session.commit()
        return jsonify({"status": "success"})
        
    return jsonify({"status": "fail"})

# --- UPDATE/DELETE/PREDICT LAINNYA ---

@app.route('/update_stock', methods=['POST'])
def update_stock():
    p_id = request.form.get('id')
    prod = Product.query.get(p_id)
    if prod:
        prod.stock = int(request.form.get('stock'))
        prod.price = int(request.form.get('price'))
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"})

@app.route('/update_transaction', methods=['POST'])
def update_transaction():
    trans = Transaction.query.get(request.form.get('id'))
    if trans:
        trans.payment_method = request.form.get('payment_method')
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})

@app.route('/delete_transaction/<int:id>', methods=['POST'])
def delete_transaction(id):
    trans = Transaction.query.get(id)
    if trans:
        db.session.delete(trans)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"})

@app.route('/predict', methods=['POST'])
def predict():
    if "image" not in request.files: return jsonify({"status": "fail"})
    file = request.files["image"].read()
    image = Image.open(io.BytesIO(file)).convert("RGB").resize((150, 150))
    image = img_to_array(image) / 255.0
    image = np.expand_dims(image, axis=0)
    prediction = model.predict(image)
    class_idx = int(np.argmax(prediction)) # INT FIXED
    confidence = float(np.max(prediction))
    
    print(f"DEBUG: Index {class_idx}, Conf {confidence}") # Debugging

    if confidence < 0.50: return jsonify({"status": "fail"})
    product_db = Product.query.filter_by(ai_index=class_idx).first()
    if product_db:
        if product_db.stock <= 0: return jsonify({"status": "fail", "message": "Stok Habis!"})
        data = {"status": "success", "product": product_db.name, "price": product_db.price}
        socketio.emit('new_order', data)
        return jsonify(data)
    return jsonify({"status": "fail"})

if __name__ == "__main__":
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)