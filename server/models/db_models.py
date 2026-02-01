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

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "role": self.role.value,
            "email": self.email,
            "phone": self.phone,
            "dob": self.dob,
            "shift": self.shift.name if self.shift else "-"
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