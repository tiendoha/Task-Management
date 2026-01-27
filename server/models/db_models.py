from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

import enum
from sqlalchemy import Enum as SQLAlchemyEnum

# Định nghĩa Role
class UserRole(enum.Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"

class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    users = db.relationship('User', backref='shift', lazy=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # 1. Thông tin đăng nhập
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=True) # Đổi tên thành password cho khớp code cũ hoặc sửa code cũ? User request dùng password_hash. Let's stick to user request but check app.py compatibility.
    # WAIT: The user request asks for `password_hash` column but in step 4.2 uses `password_hash` in `User` model but `app.py` usually uses `password`.
    # Code cũ trong app.py dùng `password`. Plan user gửi: `password_hash = db.Column...`
    # Tôi sẽ dùng `password` theo code cũ để đỡ phải sửa nhiều chỗ khác, hoặc tôi sẽ sửa hết thành `password_hash` theo đúng chuẩn.
    # User Request code mẫu: `password_hash = db.Column...`. OK I will use `password` to be consistent with existing checks or I should rename it. 
    # Let's verify: Code cũ `user.password`. User request new model `password_hash`.
    # I will follow the User Request to use `password_hash` and strict to the plan. I will refactor app.py to use `password_hash` later.
    password_hash = db.Column(db.String(255), nullable=True)

    # 2. Role
    role = db.Column(SQLAlchemyEnum(UserRole), default=UserRole.EMPLOYEE, nullable=False)

    # 3. Thông tin cá nhân
    name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    face_encoding = db.Column(db.PickleType, nullable=True) 
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=True)
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
    timestamp = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(50))