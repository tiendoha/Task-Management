from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
# Critical Fix 1: Add missing imports from werkzeug.security and datetime
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pandas as pd
import io
import cv2
import numpy as np
import base64

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

# ==========================================
# 1. API AUTH & EMPLOYEE MANAGEMENT
# ==========================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    
    # Check if user exists and password is correct
    if not user or not user.password_hash:
        return jsonify({"success": False, "message": "Tài khoản không tồn tại hoặc chưa cài đặt mật khẩu!"}), 401
    
    # verify_password wrapper or check_password_hash directly?
    # Using imported verify_password from core.security which wraps check_password_hash likely.
    # But let's use the standard check_password_hash for clarity if verify_password is ambiguous.
    # Actually core.security.verify_password uses check_password_hash as seen in file view.
    if verify_password(user.password_hash, password):
        token = generate_token(user.id, user.role.value)
        return jsonify({
            "success": True,
            "token": token,
            "user": user.to_dict()
        })
    else:
        return jsonify({"success": False, "message": "Sai mật khẩu!"}), 401

@app.route('/api/employees', methods=['POST'])
@token_required(roles=['admin'])
def create_employee(current_user):
    data = request.json
    
    # Validate required username
    if User.query.filter_by(username=data.get('username')).first():
        return jsonify({"success": False, "message": "Tên đăng nhập đã tồn tại!"}), 400

    encodings_to_save = None
    
    # Handle Face Image
    if data.get('image'):
        # Critical Fix 2: Use AIEngine.base64_to_image
        img = AIEngine.base64_to_image(data.get('image'))
        if img is not None:
             embedding = AIEngine.extract_embedding(img)
             if embedding is not None:
                 encodings_to_save = embedding
             else:
                 return jsonify({"success": False, "message": "Ảnh không rõ mặt, vui lòng chụp lại!"}), 400
    
    # Hash password
    # Prompt asked to use hash_password (which calls generate_password_hash)
    # or direclty generate_password_hash?
    # "Hash password using hash_password." -> from core.security
    hashed_pw = hash_password(data.get('password'))

    # Role Enum
    role_str = data.get('role', 'employee')
    try:
        role_enum = UserRole(role_str)
    except ValueError:
        role_enum = UserRole.EMPLOYEE

    new_user = User(
        name=data.get('name'), 
        username=data.get('username'), 
        password_hash=hashed_pw,
        email=data.get('email'),
        phone=data.get('phone'),
        dob=data.get('dob'),
        role=role_enum, 
        face_encoding=encodings_to_save,
        shift_id=int(data.get('shift_id')) if data.get('shift_id') else None
    )
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Thêm nhân viên thành công!", "user": new_user.to_dict()})

@app.route('/api/employees/<int:id>', methods=['PUT'])
@token_required(roles=['admin'])
def update_employee(current_user, id):
    user = User.query.get(id)
    if not user:
        return jsonify({"success": False, "message": "Nhân viên không tồn tại"}), 404
    
    data = request.json
    
    # Update Basic Fields
    user.name = data.get('name', user.name)
    user.email = data.get('email', user.email)
    user.phone = data.get('phone', user.phone)
    user.dob = data.get('dob', user.dob)
    
    if data.get('role'):
        try:
            user.role = UserRole(data.get('role'))
        except ValueError:
            pass
            
    if data.get('shift_id'):
        user.shift_id = int(data.get('shift_id'))

    # Password Change Logic
    if data.get('password'):
        old_password = data.get('oldPassword')
        # Critical Check using check_password_hash
        if not old_password or not user.password_hash or not check_password_hash(user.password_hash, old_password):
            return jsonify({"message": "Mật khẩu cũ không đúng"}), 400
        
        # Update using generate_password_hash
        user.password_hash = generate_password_hash(data.get('password'))

    # FaceID Update Logic
    if data.get('image'):
        # Critical Fix 2: Use AIEngine.base64_to_image
        img = AIEngine.base64_to_image(data.get('image'))
        if img is not None:
            embedding = AIEngine.extract_embedding(img)
            if embedding is not None:
                user.face_encoding = embedding
            else:
                return jsonify({"message": "Ảnh không rõ mặt, vui lòng chụp lại"}), 400
        else:
             return jsonify({"message": "Lỗi dữ liệu ảnh"}), 400

    db.session.commit()
    return jsonify({"success": True, "message": "Cập nhật thành công!"})

@app.route('/api/employees/<int:id>', methods=['DELETE'])
@token_required(roles=['admin'])
def delete_employee(current_user, id):
    user = User.query.get(id)
    if not user:
        return jsonify({"success": False, "message": "Nhân viên không tồn tại"}), 404
        
    # Cascade Delete
    Attendance.query.filter_by(user_id=id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({"success": True, "message": "Đã xóa nhân viên"})

@app.route('/api/employees', methods=['GET'])
@token_required(roles=['admin'])
def get_employees(current_user):
    users = User.query.all()
    # User.to_dict() automatically handles face_image boolean logic now
    return jsonify([u.to_dict() for u in users])

@app.route('/api/employees/<int:id>', methods=['GET'])
@token_required(roles=['admin'])
def get_employee_by_id(current_user, id):
    user = User.query.get(id)
    if not user:
        return jsonify({"success": False, "message": "Nhân viên không tồn tại"}), 404
    return jsonify(user.to_dict())

# ==========================================
# 2. API ATTENDANCE (CORE AI)
# ==========================================

@app.route('/api/checkin', methods=['POST'])
def checkin():
    data = request.json
    # Critical Fix 2: Use AIEngine.base64_to_image
    img = AIEngine.base64_to_image(data.get('image'))
    
    if img is None:
        return jsonify({"success": False, "message": "Lỗi ảnh đầu vào!"}), 400

    users = User.query.all()
    valid_users = [u for u in users if u.face_encoding is not None]

    if not valid_users:
        return jsonify({"success": False, "message": "Chưa có dữ liệu khuôn mặt nào trong hệ thống!"}), 400

    # Extract & Match
    input_embedding = AIEngine.extract_embedding(img)
    if input_embedding is None:
        return jsonify({"success": False, "message": "Không nhận diện được khuôn mặt!"}), 400

    matched_user, distance = AIEngine.find_match(input_embedding, users)

    if matched_user:
        user = matched_user
        now = datetime.now()
        
        # Critical Fix 3: Use ShiftManager.get_matching_shift(now)
        matched_shift = ShiftManager.get_matching_shift(now)
        
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check existing attendance
        attendance = Attendance.query.filter(
            Attendance.user_id == user.id,
            Attendance.checkin_time >= today_start
        ).first()

        if attendance:
             # SPAM PREVENTION
            last_action_time = attendance.checkout_time if attendance.checkout_time else attendance.checkin_time
            if (now - last_action_time) < timedelta(seconds=60):
                 status_str = "Check-out" if attendance.checkout_time else "Check-in"
                 return jsonify({
                    "success": True, 
                    "name": user.name, 
                    "status": status_str,
                    "message": "Bạn vừa thao tác rồi (Chờ 60s)!"
                })

            # Handle Check-out
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
            # Handle Check-in
            status = AttendanceStatus.ON_TIME
            shift_id = None
            
            if matched_shift:
                shift_id = matched_shift.id
                status = ShiftManager.calculate_status(now, matched_shift)
            else:
                status = AttendanceStatus.OVERTIME
                
            new_attendance = Attendance(
                user_id=user.id,
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
        return jsonify({"success": False, "message": "Không nhận diện được khuôn mặt!"}), 400

# ==========================================
# 3. API BÁO CÁO & SHIFT
# ==========================================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    total_users = User.query.count()
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    logs_today = Attendance.query.filter(Attendance.checkin_time >= today_start).all()
    
    present_count = len(set([l.user_id for l in logs_today]))
    late_count = len([l for l in logs_today if l.status == AttendanceStatus.LATE])
    
    return jsonify({
        "total_employees": total_users,
        "present_today": present_count,
        "late_today": late_count,
        "absent": total_users - present_count
    })

@app.route('/api/logs', methods=['GET'])
def get_logs():
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
@token_required(roles=['admin'])
def create_shift(current_user): # Added decorator logic
    data = request.json
    name = data.get('name')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    grace = data.get('grace_period_minutes', 15)
    
    if not name or not start_time or not end_time:
         return jsonify({"success": False, "message": "Thiếu thông tin bắt buộc"}), 400

    new_shift = Shift(name=name, start_time=start_time, end_time=end_time, grace_period_minutes=grace)
    db.session.add(new_shift)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Tạo ca làm việc thành công"})

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
    return jsonify({"success": True, "message": "Cập nhật thành công"})

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
    with app.app_context():
        db.create_all()
        
        # Create Default Shift
        if Shift.query.count() == 0:
            s1 = Shift(name="Ca Sáng", start_time="08:00:00", end_time="12:00:00")
            s2 = Shift(name="Ca Chiều", start_time="13:00:00", end_time="17:00:00")
            db.session.add_all([s1, s2])
            db.session.commit()

        # Create Default Admin
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
            print(">>> Init Admin: admin | Admin@123")

    app.run(debug=True, port=5000)