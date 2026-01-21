from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import cv2
import numpy as np
import base64

from datetime import datetime, timedelta
import pandas as pd
import io
from werkzeug.security import generate_password_hash, check_password_hash

# Import Models và AI Engine
from models.db_models import db, User, Shift, Attendance
from core.ai_engine import AIEngine

app = Flask(__name__)
CORS(app) 

# Cấu hình Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hrm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Khởi tạo AI Engine
ai_engine = AIEngine()

# --- KHỞI TẠO DỮ LIỆU BAN ĐẦU ---
with app.app_context():
    db.create_all()
    
    # 1. Tạo Ca làm việc mặc định
    if not Shift.query.first():
        db.session.add(Shift(name="Ca Sáng", start_time="08:00", end_time="17:00"))
        db.session.commit()
    
    # 2. Tạo tài khoản Admin mặc định (admin / Admin@123)
    # Lưu ý: Admin này sẽ không dùng để chấm công (không có ảnh mặt)
    if not User.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('Admin@123', method='pbkdf2:sha256')
        admin = User(
            name="Administrator", 
            username="admin", 
            password=hashed_pw, 
            role="admin", 
            shift_id=1,
            email="admin@hrm.system",
            phone="0000000000"
        )
        db.session.add(admin)
        db.session.commit()
        print(">>> Đã khởi tạo Admin mặc định: admin | Pass: Admin@123")

# Hàm hỗ trợ: Chuyển Base64 thành ảnh OpenCV
def base64_to_image(base64_string):
    if not base64_string: return None
    try:
        encoded_data = base64_string.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except:
        return None

# ==========================================
# 1. API AUTH: ĐĂNG KÝ & ĐĂNG NHẬP
# ==========================================

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    
    # 1. Validate trùng username
    if User.query.filter_by(username=data.get('username')).first():
        return jsonify({"success": False, "message": "Tên đăng nhập đã tồn tại!"})

    encodings_to_save = None
    
    # 2. Xử lý ảnh (nếu có)
    if data.get('image'):
        img = base64_to_image(data.get('image'))
        if img is not None:
            # DeepFace accepts BGR (OpenCV format) directly via ai_engine
            embedding = AIEngine.extract_embedding(img)
            if embedding is not None:
                encodings_to_save = embedding
            else:
                return jsonify({"success": False, "message": "Không tìm thấy khuôn mặt trong ảnh!"})
    
    # 3. Mã hóa mật khẩu
    hashed_pw = generate_password_hash(data.get('password'), method='pbkdf2:sha256')

    # 4. Lưu vào DB
    new_user = User(
        name=data.get('name'), 
        username=data.get('username'), 
        password=hashed_pw,
        email=data.get('email'),
        phone=data.get('phone'),
        dob=data.get('dob'),
        role=data.get('role', 'user'), 
        face_encoding=encodings_to_save,
        shift_id=1
    )
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Thêm nhân viên thành công!"})


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password, password):
        return jsonify({
            "success": True, 
            "user": {
                "id": user.id, 
                "name": user.name, 
                "role": user.role
            }
        })
    else:
        return jsonify({"success": False, "message": "Sai tài khoản hoặc mật khẩu!"})

# ==========================================
# 2. API CHẤM CÔNG (CORE AI)
# ==========================================

@app.route('/api/checkin', methods=['POST'])
def checkin():
    data = request.json
    img = base64_to_image(data.get('image'))
    
    if img is None:
        return jsonify({"success": False, "message": "Lỗi ảnh đầu vào!"})

    # Lấy danh sách vector khuôn mặt đã lưu
    users = User.query.all()
    known_encodings = [u.face_encoding for u in users if u.face_encoding is not None]
    known_ids = [u.id for u in users if u.face_encoding is not None]

    if not known_ids:
        return jsonify({"success": False, "message": "Chưa có dữ liệu khuôn mặt nào!"})

    # Gọi AI Engine xử lý nhận diện
    input_embedding = ai_engine.extract_embedding(img)
    if input_embedding is None:
        return jsonify({"success": False, "message": "Không nhận diện được khuôn mặt!"})

    matched_user, distance = ai_engine.find_match(input_embedding, users)

    if matched_user:
        user = matched_user
        found_id = user.id

        # TODO: Implement liveness check (chống giả mạo) sau.
        # Hiện tại bỏ qua bước kiểm tra is_real vì AIEngine chưa hỗ trợ.
        now = datetime.now()

        # --- LOGIC CHẶN SPAM (Cooldown 60s) ---
        last_log = Attendance.query.filter_by(user_id=found_id).order_by(Attendance.timestamp.desc()).first()
        if last_log and (now - last_log.timestamp) < timedelta(seconds=60):
            # Vẫn trả về success để Frontend dừng quét, nhưng không lưu DB
            return jsonify({
                "success": True, 
                "name": user.name, 
                "status": last_log.status, 
                "message": "Bạn vừa chấm công rồi (Chờ 60s)!"
            })

        # --- LOGIC TÍNH ĐI MUỘN ---
        # Lấy giờ bắt đầu ca (ví dụ 08:00) ghép với ngày hiện tại
        shift_start = datetime.strptime(user.shift.start_time, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        status = "Đi muộn" if now > shift_start else "Đúng giờ"
        
        # Lưu Log
        new_log = Attendance(user_id=found_id, status=status)
        db.session.add(new_log)
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "name": user.name, 
            "status": status, 
            "message": "Điểm danh thành công!"
        })
    else:
        return jsonify({"success": False, "message": "Không nhận diện được khuôn mặt!"})

# ==========================================
# 3. API QUẢN LÝ NHÂN VIÊN
# ==========================================

@app.route('/api/employees', methods=['GET'])
def get_employees():
    users = User.query.all()
    return jsonify([{
        "id": u.id, 
        "name": u.name, 
        "username": u.username,
        "role": u.role, 
        "email": u.email, 
        "phone": u.phone, 
        "dob": u.dob,
        "shift": u.shift.name if u.shift else "-"
    } for u in users])

@app.route('/api/employees/<int:id>', methods=['PUT'])
def update_employee(id):
    user = User.query.get(id)
    if not user: return jsonify({"success": False, "message": "Nhân viên không tồn tại"})
    
    data = request.json
    
    # Cập nhật thông tin cơ bản
    user.name = data.get('name', user.name)
    user.email = data.get('email', user.email)
    user.phone = data.get('phone', user.phone)
    user.dob = data.get('dob', user.dob)
    user.role = data.get('role', user.role)
    
    # Cập nhật mật khẩu (Nếu có nhập mới)
    if data.get('password') and data.get('password').strip():
        user.password = generate_password_hash(data.get('password'), method='pbkdf2:sha256')

    # Cập nhật FaceID (Nếu có chụp lại ảnh)
    if data.get('image'):
        img = base64_to_image(data.get('image'))
        if img is not None:
            embedding = AIEngine.extract_embedding(img)
            if embedding is not None:
                user.face_encoding = embedding
            else:
                return jsonify({"success": False, "message": "Ảnh mới không rõ mặt, vui lòng chụp lại!"})

    db.session.commit()
    return jsonify({"success": True, "message": "Cập nhật thành công!"})

@app.route('/api/employees/<int:id>', methods=['DELETE'])
def delete_employee(id):
    user = User.query.get(id)
    if user:
        # Xóa hết lịch sử chấm công của người này trước
        Attendance.query.filter_by(user_id=id).delete()
        db.session.delete(user)
        db.session.commit()
        return jsonify({"success": True, "message": "Đã xóa nhân viên!"})
    return jsonify({"success": False, "message": "Không tìm thấy nhân viên!"})

# ==========================================
# 4. API BÁO CÁO & TIỆN ÍCH
# ==========================================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    total_users = User.query.count()
    
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    logs_today = Attendance.query.filter(Attendance.timestamp >= today_start).all()
    
    present_count = len(set([l.user_id for l in logs_today]))
    late_count = len([l for l in logs_today if l.status == 'Đi muộn'])
    
    return jsonify({
        "total_employees": total_users,
        "present_today": present_count,
        "late_today": late_count,
        "absent": total_users - present_count
    })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    # Lấy 20 log mới nhất
    logs = Attendance.query.order_by(Attendance.timestamp.desc()).limit(20).all()
    results = [{
        "name": l.user.name, 
        "time": l.timestamp.strftime("%H:%M:%S %d/%m"), 
        "status": l.status
    } for l in logs]
    return jsonify(results)

@app.route('/api/shifts', methods=['GET', 'POST'])
def manage_shifts():
    if request.method == 'GET':
        shifts = Shift.query.all()
        return jsonify([{"id": s.id, "name": s.name, "start": s.start_time, "end": s.end_time} for s in shifts])
    
    if request.method == 'POST':
        data = request.json
        shift = Shift.query.get(1) # Demo: Chỉ sửa ca đầu tiên
        if shift:
            shift.start_time = data.get('start_time')
            shift.end_time = data.get('end_time')
            db.session.commit()
            return jsonify({"success": True})
        return jsonify({"success": False})

@app.route('/api/export_excel', methods=['GET'])
def export_excel():
    logs = Attendance.query.all()
    data = []
    for l in logs:
        data.append({
            "Mã NV": l.user.id,
            "Họ Tên": l.user.name,
            "Email": l.user.email,
            "Thời Gian": l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "Trạng Thái": l.status
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Log Chấm Công')
    
    output.seek(0)
    return send_file(
        output, 
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True, 
        download_name='BaoCaoChamCong.xlsx'
    )

if __name__ == '__main__':
    # Chạy server
    app.run(debug=True, port=5000)