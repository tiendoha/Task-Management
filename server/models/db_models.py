from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

import enum
from sqlalchemy import Enum as SQLAlchemyEnum

# Định nghĩa Role
class UserRole(enum.Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"

# 1. Định nghĩa Enum trạng thái chấm công
class AttendanceStatus(enum.Enum):
    ON_TIME = "on_time"       # Đúng giờ
    LATE = "late"             # Đi muộn
    EARLY_LEAVE = "early"     # Về sớm
    OVERTIME = "overtime"     # Ngoài giờ (Không thuộc ca nào)
    ON_LEAVE = "on_leave"     # Nghỉ phép

class LeaveStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class LeaveType(enum.Enum):
    SICK_LEAVE = "sick_leave"
    ANNUAL_LEAVE = "annual_leave"
    PERSONAL_LEAVE = "personal_leave"

class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.String(8), nullable=False) # HH:MM:SS
    end_time = db.Column(db.String(8), nullable=False)   # HH:MM:SS
    grace_period_minutes = db.Column(db.Integer, default=15)
    # Relationship defined in User via backref

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # 1. Thông tin đăng nhập
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=True) # Để tương thích code cũ
    password_hash = db.Column(db.String(255), nullable=True)

    # 2. Role
    role = db.Column(SQLAlchemyEnum(UserRole), default=UserRole.EMPLOYEE, nullable=False)

    # 3. Thông tin cá nhân
    name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    face_encoding = db.Column(db.PickleType, nullable=True) 
    
    # Foreign Key & Relationship
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=True)
    shift = db.relationship('Shift', backref='users')
    
    attendances = db.relationship('Attendance', backref='user', lazy=True)
    leaves = db.relationship('LeaveRequest', backref='user', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "role": self.role.value,
            "email": self.email,
            "phone": self.phone,
            "dob": self.dob,
            "shift_id": self.shift_id,
            "shift_name": self.shift.name if self.shift else "-",
            "face_image": True if self.face_encoding is not None else False
        }

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # 2. Link với Shift để biết hôm đó làm ca nào
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=True)
    
    checkin_time = db.Column(db.DateTime, nullable=True)
    checkout_time = db.Column(db.DateTime, nullable=True)
    
    # 3. Lưu trạng thái
    status = db.Column(SQLAlchemyEnum(AttendanceStatus), default=AttendanceStatus.ON_TIME)
    
    # Relationships
    shift = db.relationship('Shift', backref='attendances')

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    leave_type = db.Column(SQLAlchemyEnum(LeaveType), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    status = db.Column(SQLAlchemyEnum(LeaveStatus), default=LeaveStatus.PENDING)
    admin_comment = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)