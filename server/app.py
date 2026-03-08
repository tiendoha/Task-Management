from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime, timedelta, date
import pandas as pd
import io
import cv2
import numpy as np
import base64

# Import Models và AI Engine
from models.db_models import db, User, Shift, Attendance, UserRole, AttendanceStatus, LeaveRequest, LeaveType, LeaveStatus, Payroll
from sqlalchemy import func
from core.ai_engine import AIEngine
from core.security import hash_password, verify_password, generate_token, token_required
from core.shift_manager import ShiftManager
from core.leave_manager import LeaveManager
from core.salary_manager import SalaryManager
from utils.mail_service import init_mail
from apscheduler.schedulers.background import BackgroundScheduler

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
        # Safe boolean parsing
        new_active_status = bool(str(data.get('is_active')).lower() == 'true')
        
        # Self-lockout prevention
        if id == current_user.id and not new_active_status:
            return jsonify({"success": False, "message": "Không thể tự khóa tài khoản của chính mình!"}), 400
            
        user.is_active = new_active_status
        
    
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
        
        # Lấy thông tin ca làm việc (hiện tại hoặc sắp tới) dành cho Check-in
        matched_shift = ShiftManager.get_matching_shift(now)
        today = now.date()
        
        # 1. Tìm record của hôm nay
        attendance = Attendance.query.filter_by(
            user_id=user.id,
            work_date=today
        ).first()
        
        # 2. Khôi phục ca đêm từ hôm qua nếu chưa checkout
        if not attendance:
            yesterday = today - timedelta(days=1)
            att_yesterday = Attendance.query.filter_by(
                user_id=user.id,
                work_date=yesterday
            ).first()
            
            if att_yesterday and not att_yesterday.checkout_time and att_yesterday.shift_id:
                shift_past = Shift.query.get(att_yesterday.shift_id)
                if shift_past:
                    start_time_obj = datetime.strptime(shift_past.start_time, "%H:%M:%S").time()
                    end_time_obj = datetime.strptime(shift_past.end_time, "%H:%M:%S").time()
                    # Xác nhận là Ca Đêm VÀ đang check-out vào ban ngày (trước giờ start ca)
                    if end_time_obj <= start_time_obj and now.time() < start_time_obj:
                        attendance = att_yesterday
                        today = yesterday # Nhúng work_date về hôm qua để ghi Checkout


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
            
            # Check-out strict evaluation rules
            if attendance.shift_id:
                try:
                    shift = Shift.query.get(attendance.shift_id)
                    end_time_obj = datetime.strptime(shift.end_time, "%H:%M:%S").time()
                    start_time_obj = datetime.strptime(shift.start_time, "%H:%M:%S").time()
                    
                    # Logic ca đêm
                    end_dt = datetime.combine(today, end_time_obj)
                    if end_time_obj <= start_time_obj:
                        end_dt += timedelta(days=1)
                    
                    if now < end_dt:
                        attendance.early_leave_minutes = int((end_dt - now).total_seconds() // 60)
                        attendance.overtime_minutes = 0
                    elif now > end_dt + timedelta(minutes=10):
                        attendance.overtime_minutes = int((now - end_dt).total_seconds() // 60)
                        attendance.early_leave_minutes = 0
                    else:
                        attendance.early_leave_minutes = 0
                        attendance.overtime_minutes = 0
                except Exception as e:
                    print(f"Error evaluating checkout status: {e}")
            
            db.session.commit()
            
            return jsonify({
                "success": True,
                "type": "CHECK_OUT",
                "name": user.name,
                "status": "Đã về",
                "message": f"Check-out thành công lúc {now.strftime('%H:%M:%S')}!"
            })
        else:
            # Handle Check-in
            shift_id = None
            late_minutes = 0
            
            if matched_shift:
                shift_id = matched_shift.id
                start_time_obj = datetime.strptime(matched_shift.start_time, "%H:%M:%S").time()
                start_dt = datetime.combine(today, start_time_obj)
                
                # Tính Late Minutes (Bỏ qua grace period cũ vì requirement chỉ định "Grace period" là lấy từ object, nhưng logic cũ HR bỏ. 
                # Dựa theo yêu cầu "Calculate late_minutes using grace_period_minutes":
                grace = matched_shift.grace_period_minutes if hasattr(matched_shift, 'grace_period_minutes') else 0
                allowed_time = start_dt + timedelta(minutes=grace)
                
                if now > allowed_time:
                    late_minutes = int((now - start_dt).total_seconds() // 60)
                
            new_attendance = Attendance(
                user_id=user.id,
                shift_id=shift_id,
                work_date=today,
                checkin_time=now,
                status=AttendanceStatus.PRESENT,
                late_minutes=late_minutes
            )
            db.session.add(new_attendance)
            db.session.commit()
            
            shift_name = matched_shift.name if matched_shift else "Tăng ca"

            return jsonify({
                "success": True,
                "type": "CHECK_IN",
                "name": user.name,
                "status": "Có mặt",
                "message": f"Check-in thành công ({'Muộn ' + str(late_minutes) + 'p' if late_minutes > 0 else 'Đúng giờ'}) - {shift_name}"
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
    date_str = request.args.get('date')
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = datetime.now().date()
    else:
        target_date = datetime.now().date()

    logs = Attendance.query.filter(Attendance.work_date == target_date).order_by(Attendance.checkin_time.desc().nullslast()).all()
    results = [{
        "name": l.user.name, 
        "time": l.checkin_time.strftime("%H:%M:%S %d/%m") if l.checkin_time else "-", 
        "checkout": l.checkout_time.strftime("%H:%M:%S %d/%m") if l.checkout_time else "-",
        "status": l.status.value if hasattr(l.status, 'value') else str(l.status),
        "late_minutes": l.late_minutes,
        "early_leave_minutes": l.early_leave_minutes,
        "overtime_minutes": l.overtime_minutes
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
def create_shift(current_user):
    data = request.json
    name = data.get('name')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    grace = data.get('grace_period_minutes', 15)
    
    if not name or not start_time or not end_time:
         return jsonify({"success": False, "message": "Thiếu thông tin bắt buộc"}), 400

    if Shift.query.filter_by(name=name).first():
         return jsonify({"success": False, "message": "Tên ca làm việc đã bị trùng!"}), 400

    try:
        start_obj = datetime.strptime(start_time[:5], "%H:%M")
        end_obj = datetime.strptime(end_time[:5], "%H:%M")
        if end_obj <= start_obj:
            end_obj += timedelta(days=1)
            
        duration = end_obj - start_obj
        if duration <= timedelta(minutes=15):
             return jsonify({"success": False, "message": "Khoảng thời gian ca làm việc (Shift) phải dài hơn 15 phút!"}), 400
    except ValueError:
        return jsonify({"success": False, "message": "Định dạng thời gian Start/End không hợp lệ"}), 400

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
    new_name = data.get('name', shift.name)
    start_time = data.get('start_time', shift.start_time)
    end_time = data.get('end_time', shift.end_time)
    
    duplicate = Shift.query.filter(Shift.name == new_name, Shift.id != id).first()
    if duplicate:
        return jsonify({"success": False, "message": "Tên ca làm việc đã bị trùng!"}), 400

    try:
        start_obj = datetime.strptime(start_time[:5], "%H:%M")
        end_obj = datetime.strptime(end_time[:5], "%H:%M")
        if end_obj <= start_obj:
            end_obj += timedelta(days=1)
            
        duration = end_obj - start_obj
        if duration <= timedelta(minutes=15):
             return jsonify({"success": False, "message": "Khoảng thời gian ca làm việc (Shift) phải dài hơn 15 phút!"}), 400
    except ValueError:
        return jsonify({"success": False, "message": "Định dạng thời gian Start/End không hợp lệ"}), 400

    shift.name = new_name
    shift.start_time = start_time
    shift.end_time = end_time
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

# ==========================================
# 6. PAYROLL MANAGEMENT APIs
# ==========================================

@app.route('/api/payroll/calculate', methods=['POST'])
@token_required(roles=['admin'])
def calculate_payroll(current_user):
    data = request.json
    month = data.get('month')
    year = data.get('year')
    
    if not month or not year:
        return jsonify({"success": False, "message": "Vui lòng cung cấp tháng và năm."}), 400
        
    try:
        month = int(month)
        year = int(year)
    except ValueError:
        return jsonify({"success": False, "message": "Tháng và năm không hợp lệ."}), 400
        
    result = SalaryManager.calculate_monthly_payroll(month, year)
    if result.get("success"):
        return jsonify(result), 200
    else:
        return jsonify(result), 500

@app.route('/api/payroll', methods=['GET'])
@token_required()
def get_payroll(current_user):
    month_str = request.args.get('month')
    year_str = request.args.get('year')
    
    query = Payroll.query
    
    # Nhân viên chỉ lấy bảng lương của chính mình
    if current_user.role != UserRole.ADMIN:
        query = query.filter_by(user_id=current_user.id)
        
    if month_str:
        try:
            query = query.filter_by(month=int(month_str))
        except ValueError:
            pass
            
    if year_str:
        try:
            query = query.filter_by(year=int(year_str))
        except ValueError:
            pass
            
    # Xếp tháng mới gần đây lên đầu
    payrolls = query.order_by(Payroll.year.desc(), Payroll.month.desc()).all()
    
    results = []
    for p in payrolls:
        results.append({
            "id": p.id,
            "user_id": p.user_id,
            "name": p.user.name if p.user else "Unknown",
            "month": p.month,
            "year": p.year,
            "base_salary": p.base_salary,
            "total_working_days": p.total_working_days,
            "total_late_minutes": p.total_late_minutes,
            "total_early_minutes": p.total_early_minutes,
            "total_overtime_minutes": p.total_overtime_minutes,
            "deductions": round(p.deductions, 2),
            "overtime_bonus": round(p.overtime_bonus, 2),
            "net_salary": round(p.net_salary, 2),
            "is_paid": p.is_paid
        })
        
    return jsonify(results)

def backfill_attendance():
    print(f"[{datetime.now()}] Bắt đầu chạy Backfill...")
    active_users = User.query.filter_by(is_active=True).all()
    today_date = date.today()
    for emp in active_users:
        if emp.role.value == 'admin':
            continue
        
        current_date = emp.join_date
        if not current_date:
            continue
            
        while current_date <= (today_date - timedelta(days=1)):
            leave = LeaveRequest.query.filter(
                LeaveRequest.user_id == emp.id,
                LeaveRequest.status == LeaveStatus.APPROVED,
                LeaveRequest.start_date <= datetime.combine(current_date, datetime.max.time()),
                LeaveRequest.end_date >= datetime.combine(current_date, datetime.min.time())
            ).first()
            
            target_status = AttendanceStatus.ON_LEAVE if leave else AttendanceStatus.ABSENT
            
            att = Attendance.query.filter(Attendance.user_id == emp.id, Attendance.work_date == current_date).first()
            if att:
                if not att.status:
                    att.status = target_status
            else:
                new_att = Attendance(
                    user_id=emp.id,
                    work_date=current_date,
                    checkin_time=None,
                    checkout_time=None,
                    status=target_status
                )
                db.session.add(new_att)
                
            current_date += timedelta(days=1)
            
    db.session.commit()
    print(f"[{datetime.now()}] Hoàn tất Backfill!")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        backfill_attendance()
        # Tạo sẵn tài khoản config ban đầu nếu chưa có admin
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            from core.security import hash_password
            from models.db_models import UserRole
            admin = User(
                username='admin',
                password_hash=hash_password('admin'),  # Default pass
                name='Admin User',
                role=UserRole.ADMIN
            )
            db.session.add(admin)
            db.session.commit()
            print("Đã tạo user Admin mặc định!")

        # Import AI engine and warm up models once on startup
        from core.ai_engine import AIEngine
        AIEngine.warm_up_models()
        
    # --- APSCHEDULER: DAILY ATTENDANCE FINALIZATION ---
    def finalize_daily_attendance():
        with app.app_context():
            print(f"[{datetime.now()}] Bắt đầu chạy Cron Job: Chốt công cuối ngày...")
            today = datetime.now().date()
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            active_users = User.query.filter_by(is_active=True).all()
            for user in active_users:
                # Bỏ qua Admin
                if user.role.value == 'admin': continue
                
                # Cẩn thận: Có xin nghỉ không?
                leave = LeaveRequest.query.filter(
                    LeaveRequest.user_id == user.id,
                    LeaveRequest.status == LeaveStatus.APPROVED,
                    LeaveRequest.start_date <= datetime.now(),
                    LeaveRequest.end_date >= today_start
                ).first()
                
                # Có chấm công không?
                att = Attendance.query.filter_by(user_id=user.id, work_date=today).first()
                
                if not att:
                    # Tạo record hiện trạng
                    new_att = Attendance(
                        user_id=user.id,
                        work_date=today,
                        status=AttendanceStatus.ON_LEAVE if leave else AttendanceStatus.ABSENT,
                    )
                    db.session.add(new_att)
                elif att.checkin_time and not att.checkout_time:
                    # Auto-checkout for forgotten checkouts
                    if att.shift_id:
                        shift = Shift.query.get(att.shift_id)
                        if shift:
                            start_time_obj = datetime.strptime(shift.start_time, "%H:%M:%S").time()
                            end_time_obj = datetime.strptime(shift.end_time, "%H:%M:%S").time()
                            
                            checkout_dt = datetime.combine(today, end_time_obj)
                            if end_time_obj <= start_time_obj:
                                checkout_dt += timedelta(days=1)
                            
                            att.checkout_time = checkout_dt
                    else:
                        att.checkout_time = att.checkin_time + timedelta(hours=8)
                        
                    att.early_leave_minutes = 0
                    att.overtime_minutes = 0
                    
            db.session.commit()
            print(f"[{datetime.now()}] Hoàn tất Cron Job Chốt Công!")

    scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
    scheduler.add_job(func=finalize_daily_attendance, trigger="cron", hour=23, minute=59)
    scheduler.start()

    app.run(debug=True, use_reloader=False, port=5000)