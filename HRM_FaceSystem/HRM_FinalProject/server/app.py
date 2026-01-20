from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import cv2
import numpy as np
import base64
import face_recognition
from datetime import datetime, timedelta
import pandas as pd
import io

# --- THÊM IMPORT MÃ HÓA ---
from werkzeug.security import generate_password_hash, check_password_hash

from models.db_models import db, User, Shift, Attendance
from core.ai_engine import AIEngine

app = Flask(__name__)
CORS(app) 

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hrm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

ai_engine = AIEngine()

with app.app_context():
    db.create_all()
    # Tạo ca mặc định nếu chưa có
    if not Shift.query.first():
        db.session.add(Shift(name="Ca Sáng", start_time="08:00", end_time="17:00"))
        db.session.commit()

# Hàm xử lý ảnh
def base64_to_image(base64_string):
    encoded_data = base64_string.split(',')[1]
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

# ==========================================
# 1. ĐĂNG KÝ (CÓ HASH PASS)
# ==========================================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    # ... (code check username cũ giữ nguyên) ...
    
    # Lấy thêm thông tin
    email = data.get('email')
    phone = data.get('phone')

    # ... (code xử lý ảnh giữ nguyên) ...

    new_user = User(
        name=data.get('name'), 
        username=data.get('username'), 
        password=generate_password_hash(data.get('password'), method='pbkdf2:sha256'),
        email=email, # Lưu email
        phone=phone, # Lưu sdt
        role="user", 
        face_encoding=encodings[0], 
        shift_id=1
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"success": True, "message": "Đăng ký thành công!"})
# ==========================================
# 2. ĐĂNG NHẬP (CHECK HASH)
# ==========================================
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # Tìm user theo username trước
    user = User.query.filter_by(username=username).first()
    
    # Nếu user tồn tại VÀ mật khẩu khớp (sau khi giải mã)
    if user and check_password_hash(user.password, password):
        return jsonify({
            "success": True, 
            "user": {"id": user.id, "name": user.name, "role": user.role}
        })
    else:
        return jsonify({"success": False, "message": "Sai tài khoản hoặc mật khẩu!"})

# ==========================================
# 3. CHECKIN (ĐIỂM DANH) - GIỮ NGUYÊN
# ==========================================
@app.route('/api/checkin', methods=['POST'])
def checkin():
    data = request.json
    image_b64 = data.get('image')
    img = base64_to_image(image_b64)

    users = User.query.all()
    known_encodings = [u.face_encoding for u in users if u.face_encoding is not None]
    known_ids = [u.id for u in users if u.face_encoding is not None]

    if not known_ids:
        return jsonify({"success": False, "message": "Chưa có dữ liệu!"})

    found_id, is_real, msg = ai_engine.process_image(img, known_encodings, known_ids)

    if found_id:
        if not is_real:
             return jsonify({"success": False, "message": "⚠️ Cảnh báo giả mạo!"})

        user = User.query.get(found_id)
        now = datetime.now()

        # Cooldown 60s
        last_log = Attendance.query.filter_by(user_id=found_id).order_by(Attendance.timestamp.desc()).first()
        if last_log and (now - last_log.timestamp) < timedelta(seconds=60):
            return jsonify({"success": True, "name": user.name, "status": last_log.status, "message": "Đã điểm danh rồi!"})

        shift_start = datetime.strptime(user.shift.start_time, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
        status = "Đi muộn" if now > shift_start else "Đúng giờ"
        
        new_log = Attendance(user_id=found_id, status=status)
        db.session.add(new_log)
        db.session.commit()
        
        return jsonify({"success": True, "name": user.name, "status": status, "message": "Thành công!"})
    else:
        return jsonify({"success": False, "message": "Đang tìm khuôn mặt..."})

# ==========================================
# 4. CÁC API QUẢN LÝ KHÁC (GIỮ NGUYÊN)
# ==========================================
@app.route('/api/stats', methods=['GET'])
def get_stats():
    total = User.query.count()
    today = datetime.now().replace(hour=0, minute=0, second=0)
    logs = Attendance.query.filter(Attendance.timestamp >= today).all()
    present = len(set([l.user_id for l in logs]))
    late = len([l for l in logs if l.status == 'Đi muộn'])
    return jsonify({"total_employees": total, "present_today": present, "late_today": late, "absent": total - present})

@app.route('/api/employees', methods=['GET'])
def get_employees():
    users = User.query.all()
    return jsonify([{
        "id": u.id, 
        "name": u.name, 
        "role": u.role, 
        "email": u.email, # Mới
        "phone": u.phone, # Mới
        "shift": u.shift.name if u.shift else "-"
    } for u in users])

@app.route('/api/employees/<int:id>', methods=['PUT'])
def update_employee(id):
    user = User.query.get(id)
    if not user:
        return jsonify({"success": False, "message": "Không tìm thấy user"})
    
    data = request.json
    user.name = data.get('name', user.name)
    user.email = data.get('email', user.email)
    user.phone = data.get('phone', user.phone)
    user.role = data.get('role', user.role)
    
    db.session.commit()
    return jsonify({"success": True, "message": "Cập nhật thành công!"})

@app.route('/api/employees/<int:id>', methods=['DELETE'])
def delete_employee(id):
    user = User.query.get(id)
    if user:
        Attendance.query.filter_by(user_id=id).delete()
        db.session.delete(user)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/api/shifts', methods=['GET', 'POST'])
def manage_shifts():
    if request.method == 'GET':
        shifts = Shift.query.all()
        return jsonify([{"id": s.id, "name": s.name, "start": s.start_time, "end": s.end_time} for s in shifts])
    if request.method == 'POST':
        data = request.json
        shift = Shift.query.get(1)
        if shift:
            shift.start_time = data.get('start_time')
            shift.end_time = data.get('end_time')
            db.session.commit()
        return jsonify({"success": True})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    logs = Attendance.query.order_by(Attendance.timestamp.desc()).limit(20).all()
    return jsonify([{"name": l.user.name, "time": l.timestamp.strftime("%H:%M:%S %d/%m"), "status": l.status} for l in logs])

@app.route('/api/export_excel', methods=['GET'])
def export_excel():
    logs = Attendance.query.all()
    data = [{"ID": l.user.id, "Tên": l.user.name, "Thời Gian": l.timestamp, "Trạng Thái": l.status} for l in logs]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='LogChamCong.xlsx')

if __name__ == '__main__':
    app.run(debug=True, port=5000)