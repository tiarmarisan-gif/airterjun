from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import mysql.connector
from flask_cors import CORS
import json

app = Flask(__name__)
app.secret_key = 'KULIKAP_SECRET_KEY' # Wajib ada untuk session
CORS(app)

db_config = {
    'host': 'gateway01.ap-southeast-1.prod.aws.tidbcloud.com',
    'user': '4HQPxRC6isGsCW2.root',
    'password': 'j592Fvmiu82my3qc',
    'database': 'etravel',
    'port': 4000,
    'ssl_verify_cert': False, 
    'use_pure': True    
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# --- ROUTES ---

@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM packages WHERE status='active' ORDER BY featured DESC")
    packages = cursor.fetchall()
    
    for pkg in packages:
        if pkg['features'] and isinstance(pkg['features'], str):
            pkg['features'] = json.loads(pkg['features'])
            
    cursor.close()
    conn.close()
    
    # Kirim data session ke template
    return render_template('index.html', packages=packages, user=session.get('user'))

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Simple login (disarankan pakai hashing untuk produksi)
    cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", 
                   (data['username'], data['password']))
    user = cursor.fetchone()
    
    if user:
        session['user'] = user # Simpan data user di session
        return jsonify({"status": "success", "role": user['role']})
    else:
        return jsonify({"status": "error", "message": "Login Gagal"}), 401

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/admin')
def admin_dashboard():
    # Proteksi: Hanya admin yang bisa masuk
    if not session.get('user') or session['user']['role'] != 'admin':
        return "Akses Ditolak", 403
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Ambil data reservasi join dengan nama user
    cursor.execute("""
        SELECT r.*, u.full_name, u.phone 
        FROM reservations r 
        JOIN users u ON r.customer_id = u.id 
        ORDER BY r.created_at DESC
    """)
    reservations = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('admin.html', reservations=reservations)

@app.route('/api/reservations', methods=['POST'])
def create_reservation():
    if not session.get('user'):
        return jsonify({"status": "error", "message": "Silahkan login"}), 401
    
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Gunakan nama kolom sesuai screenshot database Anda
        res_sql = """
            INSERT INTO reservations 
            (booking_code, customer_id, origin_city, total_participants, 
             addons_total, total_price, payment_status, notes, 
             package_name, trip_date) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Pastikan urutan data %s di bawah ini sama dengan urutan kolom di atas
        res_values = (
            data['booking_code'], 
            session['user']['id'], 
            data['kota'], 
            data['jumlah_peserta'], 
            data['addons'], 
            data['total_pembayaran'], 
            'pending', 
            data['catatan'],
            data['paket'],        # Masuk ke package_name
            data['tanggal_trip']  # Masuk ke trip_date
        )
        
        cursor.execute(res_sql, res_values)
        conn.commit()
        
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"DATABASE ERROR: {e}") # Cek pesan ini di terminal IDX jika masih gagal
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Cek apakah username sudah ada
        cursor.execute("SELECT id FROM users WHERE username = %s", (data['username'],))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Username sudah terdaftar"}), 400

        # Simpan user baru
        sql = """
            INSERT INTO users (username, password, full_name, email, phone, role) 
            VALUES (%s, %s, %s, %s, %s, 'customer')
        """
        cursor.execute(sql, (
            data['username'], 
            data['password'], 
            data['full_name'], 
            data['email'], 
            data['phone']
        ))
        conn.commit()
        return jsonify({"status": "success", "message": "Akun berhasil dibuat! Silahkan login."})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/reservations/update/<int:res_id>', methods=['POST'])
def update_status(res_id):
    if not session.get('user') or session['user']['role'] != 'admin':
        return jsonify({"status": "error", "message": "Akses ditolak"}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Ubah status menjadi 'lunas' (sesuai enum di database Anda)
        cursor.execute("UPDATE reservations SET payment_status = 'lunas' WHERE id = %s", (res_id,))
        conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/reservations/delete/<int:res_id>', methods=['POST'])
def delete_reservation(res_id):
    if not session.get('user') or session['user']['role'] != 'admin':
        return jsonify({"status": "error", "message": "Akses ditolak"}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM reservations WHERE id = %s", (res_id,))
        conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
        
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)