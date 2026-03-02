from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime, timedelta
import pandas as pd
import io
import cv2
import numpy as np
import base64

# Import Models và AI Engine
from models.db_models import db, User, Shift, Attendance, UserRole, AttendanceStatus, LeaveRequest, LeaveType, LeaveStatus
from sqlalchemy import func 
from core.ai_engine import AIEngine
from core.security import hash_password, verify_password, generate_token, token_required
from core.shift_manager import ShiftManager
from core.leave_manager import LeaveManager
from utils.mail_service import init_mail

app = Flask(__name__)
init_mail(app)
# Allow Authorization header for JWT
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True, expose_headers=["Authorization"], allow_headers=["Authorization", "Content-Type"])

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({"success": False, "message": f"Server crash: Vui lòng liên hệ Admin ({str(e)})"}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    # Pass through HTTP errors
    if hasattr(e, 'code'):
        return jsonify({"success": False, "message": str(e)}), e.code
    # Treat non-HTTP errors as 500
    return jsonify({"success": False, "message": f"Lỗi nội bộ: {str(e)}"}), 500

# Cấu hình Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hrm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Khởi tạo AI Engine
ai_engine = AIEngine()

# ==========================================
# 4. API LEAVE MANAGEMENT
# ==========================================

@app.route('/api/leaves', methods=['POST'])
@token_required()
def create_leave_request(current_user):
    data = request.json
    try:
        leave_type = LeaveType(data.get('leave_type'))
    except ValueError:
        return jsonify({"success": False, "message": "Loại nghỉ phép không hợp lệ"}), 400
        
    start_str = data.get('start_date')
    end_str = data.get('end_date')
    reason = data.get('reason')
    
    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"success": False, "message": "Định dạng ngày không hợp lệ (YYYY-MM-DD)"}), 400
        
    if start_date > end_date:
        return jsonify({"success": False, "message": "Ngày bắt đầu phải trước ngày kết thúc"}), 400
        
    new_request = LeaveRequest(
        user_id=current_user.id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status=LeaveStatus.PENDING
    )
    
    db.session.add(new_request)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Đã gửi yêu cầu nghỉ phép"})

@app.route('/api/leaves', methods=['GET'])
@token_required()
def get_leave_requests(current_user):
    scope = request.args.get("scope", "me")
    
    if scope == "all" and current_user.role == UserRole.ADMIN:
        requests = LeaveRequest.query.order_by(LeaveRequest.created_at.desc()).all()
    else:
        # Fallback to "me" scope or if the user is not an Admin trying to access "all"
        requests = LeaveRequest.query.filter_by(user_id=current_user.id).order_by(LeaveRequest.created_at.desc()).all()
        
    results = []
    for r in requests:
        user_name = r.user.name if r.user else "Unknown User"
        
        results.append({
            "id": r.id,
            "user_id": r.user_id,
            "user_name": user_name,
            "leave_type": r.leave_type.value,
            "start_date": r.start_date.strftime("%Y-%m-%d"),
            "end_date": r.end_date.strftime("%Y-%m-%d"),
            "reason": r.reason,
            "status": r.status.value,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M")
        })

    return jsonify(results)

@app.route('/api/leaves/<int:id>', methods=['PUT'])
@token_required(roles=['admin'])
def update_leave_request(current_user, id):
    data = request.json
    status_str = data.get('status')
    comment = data.get('comment')
    
    req = LeaveRequest.query.get(id)
    if not req:
        return jsonify({"success": False, "message": "Không tìm thấy yêu cầu"}), 404
        
    if status_str == "APPROVED":
        # Critical Logic via LeaveManager
        success, msg = LeaveManager.approve_leave_request(id, current_user.id)
        if success:
            if comment:
                req.admin_comment = comment
                db.session.commit()
            return jsonify({"success": True, "message": msg})
        else:
            return jsonify({"success": False, "message": msg}), 400
            
    elif status_str == "REJECTED":
        req.status = LeaveStatus.REJECTED
        req.admin_comment = comment
        db.session.commit()
        return jsonify({"success": True, "message": "Đã từ chối yêu cầu"})
        
    else:
        return jsonify({"success": False, "message": "Trạng thái không hợp lệ"}), 400


# ==========================================
# 1. API AUTH: ĐĂNG KÝ & ĐĂNG NHẬP
# ==========================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"success": False, "message": "Vui lòng nhập đầy đủ thông tin"}), 400
        
    user = User.query.filter_by(username=username).first()
    
    # Check if user exists and password is correct (Consolidated error for security)
    if not user or not user.password_hash or not verify_password(user.password_hash, password):
        return jsonify({"success": False, "message": "Tên đăng nhập hoặc mật khẩu không đúng"}), 401

    # Check if user is active
    if not user.is_active:
        return jsonify({"success": False, "message": "Tài khoản của bạn đang bị khóa. Vui lòng liên hệ Admin."}), 403

    token = generate_token(user.id, user.role.value)
    return jsonify({
        "success": True,
        "token": token,
        "user": user.to_dict()
    })

@app.route('/api/profile', methods=['PUT'])
@token_required()
def update_profile(current_user):
    data = request.json
    
    # Basic info update logic
    current_user.name = data.get('name', current_user.name)
    current_user.email = data.get('email', current_user.email)
    current_user.phone = data.get('phone', current_user.phone)
    current_user.dob = data.get('dob', current_user.dob)
    
    # Password update logic
    if data.get('password'):
        old_password = data.get('oldPassword')
        if not old_password or not current_user.password_hash or not verify_password(current_user.password_hash, old_password):
            return jsonify({"success": False, "message": "Mật khẩu cũ không đúng"}), 400
        
        current_user.password_hash = hash_password(data.get('password'))

    db.session.commit()
    return jsonify({"success": True, "message": "Cập nhật thông tin thành công!", "user": current_user.to_dict()}), 200

@app.route('/api/employees', methods=['POST'])
@token_required(roles=['admin'])
def create_employee(current_user):
    data = request.json
    
    # 1. Validate trùng username
    if User.query.filter_by(username=data.get('username')).first():
        return jsonify({"success": False, "message": "Tên đăng nhập đã tồn tại!"}), 400

    encodings_to_save = None
    
    # 2. Xử lý ảnh (nếu có)
    if data.get('image'):
        img = AIEngine.base64_to_image(data.get('image'))
        if img is not None:
             embedding, msg = AIEngine.get_embedding(img)
             if embedding is not None:
                 encodings_to_save = embedding
             else:
                 return jsonify({"success": False, "message": f"Lỗi ảnh: {msg}"}), 400
    
    # 3. Mã hóa mật khẩu
    # hashed_pw = generate_password_hash(data.get('password'), method='pbkdf2:sha256') # Old
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
    
    if 'is_active' in data:
        user.is_active = bool(data.get('is_active'))
    
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
        # Critical Check using verify_password
        if not old_password or not user.password_hash or not verify_password(user.password_hash, old_password):
            return jsonify({"success": False, "message": "Mật khẩu cũ không đúng"}), 400
        
        # Update using hash_password
        user.password_hash = hash_password(data.get('password'))

    # FaceID Update Logic
    if data.get('image'):
        # Critical Fix 2: Use AIEngine.base64_to_image
        img = AIEngine.base64_to_image(data.get('image'))
        if img is not None:
            embedding, msg = AIEngine.get_embedding(img)
            if embedding is not None:
                user.face_encoding = embedding
            else:
                return jsonify({"message": f"Ảnh lỗi: {msg}"}), 400
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
# 2. API CHẤM CÔNG (CORE AI)
# ==========================================

@app.route('/api/checkin', methods=['POST'])
def checkin():
    data = request.json
    img = AIEngine.base64_to_image(data.get('image'))
    
    if img is None:
        return jsonify({"success": False, "message": "Lỗi ảnh đầu vào!"}), 400

    users = User.query.all()
    valid_users = [u for u in users if u.face_encoding is not None]

    if not valid_users:
        return jsonify({"success": False, "message": "Chưa có dữ liệu khuôn mặt nào trong hệ thống!"}), 400

    # Extract & Match (Anti-Spoofing handled inside AIEngine)
    input_embedding, msg = AIEngine.get_embedding(img)
    if input_embedding is None:
        return jsonify({"success": False, "message": f"Không nhận diện được khuôn mặt: {msg}"}), 400

    matched_user, distance = AIEngine.find_match(input_embedding, users)

    if matched_user:
        user = matched_user
        now = datetime.now()
        
        # 1. Tìm ca làm việc tự động
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
# 2.1. API ĐĂNG KÝ KHUÔN MẶT (3 GÓC)
# ==========================================
@app.route('/api/face-setup/analyze', methods=['POST'])
@token_required(roles=['admin'])
def analyze_face_pose(current_user):
    data = request.json
    image_b64 = data.get('image')
    step = data.get('current_step', 'center')  # center, left, right

    if not image_b64:
        return jsonify({"success": False, "message": "Thieu anh"}), 400

    img = AIEngine.base64_to_image(image_b64)
    if img is None:
        return jsonify({"success": False, "message": "Anh loi"}), 400

    # check goc mat
    from core.ai_engine import FaceQualityEngine
    pose, msg = FaceQualityEngine.check_pose(img)
    print(f"[face-setup] step {step} - detected {pose} ({msg})")

    # check step co khop ko
    if step == 'center' and pose != 'center':
        return jsonify({"success": False, "message": f"Nhin thang di! ({msg})"}), 400
    if step == 'left' and pose != 'left':
        return jsonify({"success": False, "message": f"Quay trai di! ({msg})"}), 400
    if step == 'right' and pose != 'right':
        return jsonify({"success": False, "message": f"Quay phai di! ({msg})"}), 400

    try:
        # lay embedding (Anti-spoofing is now inside get_embedding)
        embedding, msg = AIEngine.get_embedding(img)
        if not embedding:
            return jsonify({"success": False, "message": f"Lỗi: {msg}"}), 400

        return jsonify({
            "success": True,
            "embedding": embedding,
            "message": "OK",
            "pose": pose
        })

    except Exception as e:
        print(f"[ERROR analyze] {str(e)}")
        return jsonify({"success": False, "message": "Loi xu ly"}), 500


@app.route('/api/face-setup/finish', methods=['POST'])
@token_required(roles=['admin'])
def finish_face_setup(current_user):
    data = request.json
    user_id = data.get('user_id')
    embeddings = data.get('embeddings')  # list of lists

    if not user_id or not embeddings:
        return jsonify({"success": False, "message": "Thieu du lieu"}), 400

    if len(embeddings) == 0:
        return jsonify({"success": False, "message": "Vector trong"}), 400

    from core.ai_engine import FaceQualityEngine
    avg_emb = FaceQualityEngine.avg_embedding(embeddings)

    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User khong ton tai"}), 404

    user.face_encoding = avg_emb
    db.session.commit()

    return jsonify({"success": True, "message": "Dang ky khuon mat xong (3 goc)"})

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

@app.route('/api/stats/top-late', methods=['GET'])
@token_required(roles=['admin'])
def get_top_late_stats(current_user):
    today = datetime.now()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    results = db.session.query(
        Attendance.user_id, 
        func.count(Attendance.id)
    ).filter(
        Attendance.checkin_time >= start_of_month,
        Attendance.status == AttendanceStatus.LATE
    ).group_by(
        Attendance.user_id
    ).order_by(
        func.count(Attendance.id).desc()
    ).limit(5).all()
    
    data = []
    for user_id, count in results:
        user = User.query.get(user_id)
        if user:
            data.append({
                "name": user.name,
                "count": count,
                "avatar": True if user.face_encoding is not None else False
            })
            
    return jsonify(data)

@app.route('/api/stats/chart', methods=['GET'])
@token_required(roles=['admin'])
def get_chart_stats(current_user):
    today = datetime.now()
    dates = [(today - timedelta(days=i)).date() for i in range(6, -1, -1)]
    
    # Initialize data structure
    stats_map = {d: {'late': 0, 'ontime': 0} for d in dates}
    
    start_date = dates[0]
    end_date = dates[-1] + timedelta(days=1) # Ensure we cover the full last day
    
    logs = Attendance.query.filter(
        Attendance.checkin_time >= start_date,
        Attendance.checkin_time < end_date
    ).all()
    
    for log in logs:
        log_date = log.checkin_time.date()
        if log_date in stats_map:
            if log.status == AttendanceStatus.LATE:
                stats_map[log_date]['late'] += 1
            elif log.status == AttendanceStatus.ON_TIME:
                stats_map[log_date]['ontime'] += 1
    
    # Format for output
    labels = [d.strftime("%d/%m") for d in dates]
    data_late = [stats_map[d]['late'] for d in dates]
    data_ontime = [stats_map[d]['ontime'] for d in dates]
    
    return jsonify({
        "labels": labels,
        "data_late": data_late,
        "data_ontime": data_ontime
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

# ==========================================
# 5. PASSWORD MANAGEMENT APIs
# ==========================================

from utils.password_utils import generate_random_password
from utils.mail_service import send_reset_email

@app.route('/api/reset-password-request', methods=['POST'])
def reset_password_request():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    
    if not username or not email:
        return jsonify({"success": False, "message": "Vui lòng cung cấp Username và Email"}), 400
        
    user = User.query.filter_by(username=username, email=email).first()
    if not user:
        return jsonify({"success": False, "message": "Thông tin không khớp. Không thể yêu cầu cấp lại mật khẩu."}), 404
        
    user.change_password_request = True
    db.session.commit()
    return jsonify({"success": True, "message": "Yêu cầu cấp lại mật khẩu đã được gửi đến Admin"})

@app.route('/api/reset-password/<int:user_id>', methods=['PUT'])
@token_required(roles=['admin'])
def reset_password(current_user, user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "Người dùng không tồn tại"}), 404
        
    new_pwd = generate_random_password(10)
    user.password_hash = hash_password(new_pwd)
    user.must_change_password = True
    user.change_password_request = False
    db.session.commit()
    
    send_reset_email(user.email, new_pwd)
    
    return jsonify({"success": True, "message": "Đã reset mật khẩu thành công. Email đã được gửi đến nhân viên."})

@app.route('/api/change-password', methods=['PUT'])
@token_required()
def force_change_password(current_user):
    # Critical security check
    if not current_user.must_change_password:
        return jsonify({"success": False, "message": "Bạn không có yêu cầu bắt buộc đổi mật khẩu lúc này."}), 403
        
    data = request.json
    new_password = data.get('new_password')
    
    if not new_password or len(new_password) < 6:
        return jsonify({"success": False, "message": "Mật khẩu mới phải có ít nhất 6 ký tự."}), 400
        
    current_user.password_hash = hash_password(new_password)
    current_user.must_change_password = False
    db.session.commit()
    
    return jsonify({"success": True, "message": "Đã đổi mật khẩu thành công. Vui lòng đăng nhập lại."})

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

    # Warm-up AI Models before starting server
    from core.ai_engine import AIEngine
    AIEngine.warm_up_models()

    app.run(debug=True, port=5000)