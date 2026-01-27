import jwt
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import request, jsonify, current_app
from models.db_models import User

# Cấu hình Secret Key (Nên để trong .env, nhưng demo để đây tạm)
SECRET_KEY = "SGU_CAPSTONE_SECRET_KEY_2024" 

def hash_password(password):
    return generate_password_hash(password)

def verify_password(password_hash, password):
    return check_password_hash(password_hash, password)

def generate_token(user_id, role):
    """Tạo JWT Token có hạn 24h"""
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def token_required(roles=None):
    """
    Decorator để bảo vệ API.
    - roles: List các role được phép truy cập (VD: ['admin']). Nếu None thì ai login cũng được.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = None
            
            # 1. Lấy token từ Header: "Authorization: Bearer <token>"
            if "Authorization" in request.headers:
                auth_header = request.headers["Authorization"]
                if auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
            
            if not token:
                return jsonify({"message": "Token is missing!"}), 401
            
            try:
                # 2. Giải mã Token
                data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                current_user = User.query.get(data["sub"])
                user_role = data["role"]
                
                if not current_user:
                    return jsonify({"message": "User not found!"}), 401
                
                # 3. Check quyền (Authorization)
                # roles is passed to the outer decorator.
                # If roles is provided, check if user_role in keys
                if roles:
                    # user_role is stored as string "admin" or "employee" in token
                    if user_role not in roles:
                        return jsonify({"message": "Permission denied!"}), 403
                
            except jwt.ExpiredSignatureError:
                return jsonify({"message": "Token expired!"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"message": "Invalid token!"}), 401
                
            # Truyền user vào hàm xử lý
            return f(current_user, *args, **kwargs)
        
        return decorated
    return decorator
