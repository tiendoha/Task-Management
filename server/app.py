from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import cv2
import numpy as np
import base64

from datetime import datetime, timedelta
import pandas as pd
import io
from werkzeug.security import generate_password_hash, check_password_hash # Keep for compatibility if needed, but security.py has it too.
# Import Models và AI Engine
from models.db_models import db, User, Shift, Attendance, UserRole, AttendanceStatus
from core.ai_engine import AIEngine
from core.security import hash_password, verify_password, generate_token, token_required
from core.shift_manager import ShiftManager

app = Flask(__name__)
# Allow Authorization header for JWT
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True, expose_headers=["Authorization"], allow_headers=["Authorization", "Content-Type"]) 

# Cấu hình Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hrm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Khởi tạo AI Engine
ai_engine = AIEngine()

# --- KHỞI TẠO DỮ LIỆU BAN ĐẦU ---


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

@app.route('/api/employees', methods=['POST'])
@token_required(roles=['admin'])
def create_employee(current_user): # current_user is injected
    # Note: Route changed from /api/register to /api/employees to match RESTful style and plan
    # But strictly speaking, the user plan says: Sửa lại hàm register_face hoặc tạo thêm hàm create_employee.
    # I will replace `register` with `create_employee` at `/api/employees`.
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
    # hashed_pw = generate_password_hash(data.get('password'), method='pbkdf2:sha256') # Old
    hashed_pw = hash_password(data.get('password'))

    # Role Enum
    role_str = data.get('role', 'employee')
    role_enum = UserRole.ADMIN if role_str == 'admin' else UserRole.EMPLOYEE

    # 4. Lưu vào DB
    new_user = User(
        name=data.get('name'), 
        username=data.get('username'), 
        password_hash=hashed_pw,
        email=data.get('email'),
        phone=data.get('phone'),
        dob=data.get('dob'),
        role=role_enum, 
        face_encoding=encodings_to_save,
        shift_id=1
    )
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Thêm nhân viên thành công!", "user": new_user.to_dict()})


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    
    if not user or not user.password_hash:
        return jsonify({"success": False, "message": "Tài khoản không tồn tại hoặc chưa có mật khẩu!"}), 401
    
    if verify_password(user.password_hash, password):
        token = generate_token(user.id, user.role.value)
        return jsonify({
            "success": True,
            "token": token,
            "user": user.to_dict()
        })
    else:
        return jsonify({"success": False, "message": "Sai mật khẩu!"})

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
    # Filter users with face encoding
    valid_users = [u for u in users if u.face_encoding is not None]

    if not valid_users:
        return jsonify({"success": False, "message": "Chưa có dữ liệu khuôn mặt nào!"})

    # Gọi AI Engine xử lý nhận diện
    input_embedding = ai_engine.extract_embedding(img)
    if input_embedding is None:
        return jsonify({"success": False, "message": "Không nhận diện được khuôn mặt!"})

    matched_user, distance = ai_engine.find_match(input_embedding, users)

    if matched_user:
        user = matched_user
        found_id = user.id
        now = datetime.now()

        # 1. Tìm ca làm việc tự động
        matched_shift = ShiftManager.get_matching_shift(now)
        
        # 2. Logic Check-in vs Check-out
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Tìm attendance của user trong ngày hôm nay (dựa vào checkin_time)
        attendance = Attendance.query.filter(
            Attendance.user_id == found_id,
            Attendance.checkin_time >= today_start
        ).first()

        if attendance:
             # --- LOGIC CHẶN SPAM (Cooldown 60s) ---
            if attendance.checkout_time:
                # Nếu đã checkout rồi mà check lại, check time diff from checkout
                last_action_time = attendance.checkout_time
            else:
                 # Nếu chưa checkout, check time diff from checkin
                 last_action_time = attendance.checkin_time
            
            if (now - last_action_time) < timedelta(seconds=60):
                 status_str = "Check-out" if attendance.checkout_time else "Check-in"
                 return jsonify({
                    "success": True, 
                    "name": user.name, 
                    "status": status_str, # Trả về status text
                    "message": "Bạn vừa thao tác rồi (Chờ 60s)!"
                })

            # A. Nếu đã check-in -> Xử lý Check-out
            attendance.checkout_time = now
            db.session.commit()
            
            return jsonify({
                "success": True,
                "type": "CHECK_OUT",
                "name": user.name,
                "status": "Đã về",
                "message": "Check-out thành công!"
            })
        else:
            # B. Nếu chưa check-in -> Tạo Check-in mới
            status = AttendanceStatus.ON_TIME
            shift_id = None
            
            if matched_shift:
                shift_id = matched_shift.id
                status = ShiftManager.calculate_status(now, matched_shift)
            else:
                status = AttendanceStatus.OVERTIME
                
            new_attendance = Attendance(
                user_id=found_id,
                shift_id=shift_id,
                checkin_time=now,
                status=status
            )
            db.session.add(new_attendance)
            db.session.commit()
            
            status_vn = "Đúng giờ" if status == AttendanceStatus.ON_TIME else ("Đi muộn" if status == AttendanceStatus.LATE else "Ngoài giờ")
            shift_name = matched_shift.name if matched_shift else "Tăng ca"

            return jsonify({
                "success": True,
                "type": "CHECK_IN",
                "name": user.name,
                "status": status_vn,
                "message": f"Check-in thành công ({status_vn}) - {shift_name}"
            })

    else:
        return jsonify({"success": False, "message": "Không nhận diện được khuôn mặt!"})

# ==========================================
# 3. API QUẢN LÝ NHÂN VIÊN
# ==========================================

@app.route('/api/employees', methods=['GET'])
@token_required(roles=['admin'])
def get_employees(current_user):
    users = User.query.all()
    return jsonify([{
        "id": u.id, 
        "name": u.name, 
        "username": u.username,
        "role": u.role.value, 
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
    # Using checkin_time instead of timestamp
    logs_today = Attendance.query.filter(Attendance.checkin_time >= today_start).all()
    
    present_count = len(set([l.user_id for l in logs_today]))
    # Status is now Enum, convert to value for comparison or compare with Enum member
    # DB stores Enum name or value? SQLAlchemyEnum stores name by default 
    # But usually we compare with Enum
    late_count = len([l for l in logs_today if l.status == AttendanceStatus.LATE])
    
    return jsonify({
        "total_employees": total_users,
        "present_today": present_count,
        "late_today": late_count,
        "absent": total_users - present_count
    })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    # Lấy 20 log mới nhất
    logs = Attendance.query.order_by(Attendance.checkin_time.desc()).limit(20).all()
    results = [{
        "name": l.user.name, 
        "time": l.checkin_time.strftime("%H:%M:%S %d/%m") if l.checkin_time else "", 
        "checkout": l.checkout_time.strftime("%H:%M:%S %d/%m") if l.checkout_time else "-",
        "status": l.status.value if hasattr(l.status, 'value') else str(l.status)
    } for l in logs]
    return jsonify(results)

@app.route('/api/shifts', methods=['GET'])
def get_shifts():
    shifts = Shift.query.all()
    return jsonify([{
        "id": s.id, 
        "name": s.name, 
        "start_time": s.start_time, 
        "end_time": s.end_time,
        "grace_period_minutes": s.grace_period_minutes
    } for s in shifts])

@app.route('/api/shifts', methods=['POST'])
def create_shift():
    data = request.json
    name = data.get('name')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    grace = data.get('grace_period_minutes', 15)
    
    if not name or not start_time or not end_time:
         return jsonify({"success": False, "message": "Thiếu thông tin bắt buộc (name, start_time, end_time)"}), 400

    new_shift = Shift(name=name, start_time=start_time, end_time=end_time, grace_period_minutes=grace)
    db.session.add(new_shift)
    db.session.commit()
    
    return jsonify({
        "success": True, 
        "message": "Tạo ca thành công", 
        "shift": {
            "id": new_shift.id,
            "name": new_shift.name
        }
    })

@app.route('/api/shifts/<int:id>', methods=['PUT'])
@token_required(roles=['admin'])
def update_shift(current_user, id):
    shift = Shift.query.get(id)
    if not shift:
        return jsonify({"success": False, "message": "Ca làm việc không tồn tại"}), 404
    
    data = request.json
    shift.name = data.get('name', shift.name)
    shift.start_time = data.get('start_time', shift.start_time)
    shift.end_time = data.get('end_time', shift.end_time)
    shift.grace_period_minutes = data.get('grace_period_minutes', shift.grace_period_minutes)
    
    db.session.commit()
    return jsonify({"success": True, "message": "Cập nhật ca thành công"})

# API để tạo nhanh Ca làm việc (Seeding)
@app.route('/api/seed/shifts', methods=['POST'])
def seed_shifts():
    if Shift.query.count() > 0:
        return jsonify({"msg": "Shifts already exist"}), 400
        
    s1 = Shift(name="Ca Sáng", start_time="08:00:00", end_time="12:00:00", grace_period_minutes=15)
    s2 = Shift(name="Ca Chiều", start_time="13:00:00", end_time="17:00:00", grace_period_minutes=15)
    
    db.session.add_all([s1, s2])
    db.session.commit()
    return jsonify({"msg": "Shifts created!"})

@app.route('/api/export_excel', methods=['GET'])
def export_excel():
    logs = Attendance.query.all()
    data = []
    for l in logs:
        data.append({
            "Mã NV": l.user.id,
            "Họ Tên": l.user.name,
            "Email": l.user.email,
            "Check-in": l.checkin_time.strftime("%Y-%m-%d %H:%M:%S") if l.checkin_time else "",
            "Check-out": l.checkout_time.strftime("%Y-%m-%d %H:%M:%S") if l.checkout_time else "",
            "Trạng Thái": l.status.value if hasattr(l.status, 'value') else str(l.status)
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
    # --- KHỞI TẠO DỮ LIỆU BAN ĐẦU ---
    with app.app_context():
        db.create_all()
        
        # 1. Tạo Ca làm việc mặc định (Nếu chưa có)
        pass
        
        # 2. Tạo tài khoản Admin mặc định (admin / Admin@123)
        if not User.query.filter_by(username='admin').first():
            hashed_pw = hash_password('Admin@123')
            admin = User(
                name="Administrator", 
                username="admin", 
                password_hash=hashed_pw, 
                role=UserRole.ADMIN, 
                shift_id=1,
                email="admin@hrm.system",
                phone="0000000000"
            )
            db.session.add(admin)
            db.session.commit()
            print(">>> Đã khởi tạo Admin mặc định: admin | Pass: Admin@123")

    # Chạy server
    app.run(debug=True, port=5000)