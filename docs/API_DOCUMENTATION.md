# HRM FaceID System - API Documentation & Developer Notes

## 1. Authentication & Security
Hệ thống sử dụng **JWT (JSON Web Token)** để xác thực.
- **Header**: `Authorization: Bearer <token>`
- **Token Expiry**: 24 giờ.
- **Roles**:
    - `admin`: Quyền cao nhất (Quản lý nhân viên, Ca làm việc).
    - `employee`: Quyền hạn chế (Chỉ xem thông tin cá nhân - planned feature).

### API: Login
- **Endpoint**: `POST /api/auth/login`
- **Body**: `{ "username": "...", "password": "..." }`
- **Response**: `{ "success": true, "token": "...", "user": {...} }`

---

## 2. Shift Management (Quản lý Ca làm việc)
Logic "Smart Shift" tự động xác định ca dựa trên giờ Check-in.

### Get All Shifts
- **Endpoint**: `GET /api/shifts`
- **Public**: Yes
- **Response**: List các ca làm việc, bao gồm `grace_period_minutes`.

### Create Shift (Admin/Public intended for seeding)
- **Endpoint**: `POST /api/shifts`
- **Body**: `{ "name": "Ca Sáng", "start_time": "08:00:00", "end_time": "12:00:00", "grace_period_minutes": 15 }`

### Update Shift (Admin Only)
- **Endpoint**: `PUT /api/shifts/<id>`
- **Header**: `Authorization: Bearer <admin_token>`
- **Body**: Các trường cần sửa (VD: `{ "grace_period_minutes": 30 }`)

---

## 3. Employee Management (Admin Only)

### Create Employee (Register)
- **Endpoint**: `POST /api/employees`
- **Header**: `Authorization: Bearer <admin_token>`
- **Body**:
  ```json
  {
    "username": "user1",
    "password": "123",
    "name": "Nguyen Van A",
    "role": "employee",
    "image": "data:image/jpeg;base64,..."
  }
  ```
- **Note**: Hệ thống sẽ tự trích xuất vector khuôn mặt từ ảnh.

### Get Employees
- **Endpoint**: `GET /api/employees`
- **Header**: `Authorization: Bearer <admin_token>`
- **Response**: List of users with detailed fields:
  ```json
  [
    {
      "id": 1,
      "name": "User One",
      "username": "user1",
      "role": "employee",
      "email": "user1@example.com",
      "phone": "0123456789",
      "dob": "1990-01-01",
      "shift": "Ca Sáng",
      "shift_id": 1,
      "face_image": true
    }
  ]
  ```

### Get Employee by ID
- **Endpoint**: `GET /api/employees/<id>`
- **Header**: `Authorization: Bearer <admin_token>`
- **Response**: Detailed object for specific user.
  ```json
  {
      "id": 1,
      "name": "User One",
      "username": "user1",
      "role": "employee",
      "email": "...",
      "phone": "...",
      "dob": "...",
      "shift": "Ca Sáng",
      "shift_id": 1,
      "face_image": true
  }
  ```

---

### Update Employee
- **Endpoint**: `PUT /api/employees/<id>`
- **Header**: `Authorization: Bearer <admin_token>`
- **Body**:
  ```json
  {
      "name": "New Name",
      "email": "new@example.com",
      "role": "admin",
      "shift_id": 2,
      "password": "new_password",        // Optional (Requires oldPassword)
      "oldPassword": "current_password", // Required if changing password
      "image": "data:image/jpeg;base64,..." // Optional (Updates FaceID)
  }
  ```
- **Response**: `{ "success": true, "message": "Cập nhật thành công!" }`

---

## 4. Timekeeping (Chấm công)

### Check-in / Check-out
- **Endpoint**: `POST /api/checkin`
- **Body**: `{ "image": "data:image/jpeg;base64,..." }`
- **Logic**:
    1. Nhận diện khuôn mặt -> Lấy `user_id`.
    2. Xác định ca làm việc hiện tại (`ShiftManager`).
    3. Kiểm tra User đã check-in hôm nay chưa?
        - **Chưa**: Tạo record `Check-in`. Tính trạng thái (Đúng giờ / Đi muộn) dựa trên `start_time` + `grace_period`.
        - **Rồi**: Update record đó thành `Check-out` (Nếu time diff > 60s).
- **Response**: Trả về `status` (text tiếng Việt) để hiển thị lên màn hình.

---

## 5. Development Notes & Troubleshooting (Các lỗi đã gặp)

Trong quá trình phát triển tính năng này, tôi đã gặp và xử lý các vấn đề sau:

### 1. AttributeError: 'AIEngine' object has no attribute 'process_image'
- **Nguyên nhân**: Code cũ trong `app.py` gọi hàm `process_image` nhưng `AIEngine` mới (DeepFace update) đã đổi sang method `extract_embedding` và `find_match`.
- **Giải pháp**: Refactor lại hàm `checkin` trong `app.py` để dùng đúng luồng 2 bước: Trích xuất -> Tìm kiếm vector.

### 2. IntegrityError (UNIQUE constraint failed) khi chạy Test
- **Nguyên nhân**: Script tự động tạo Admin (`db.session.add(admin)`) chạy mỗi khi import `app.py`. Khi chạy Unit Test, logic này conflict với việc test setup cũng tạo Admin.
- **Giải pháp**: Di chuyển logic seeding vào trong block `if __name__ == '__main__':` của `app.py` để nó chỉ chạy khi khởi động server thực tế, không chạy khi test import.

### 3. Database Schema Mismatch (OperationalError)
- **Nguyên nhân**: SQLite không hỗ trợ `ALTER TABLE` đầy đủ. Khi thêm cột `date_of_birth` hay `shift_id`, app bị lỗi không tìm thấy cột.
- **Giải pháp**: Yêu cầu xóa file `hrm.db` để SQLAlchemy tạo lại bảng mới từ đầu.

### 4. Dependency Conflicts
- **Vấn đề**: `numpy` 2.0 gây lỗi với `tensorflow`.
- **Giải pháp**: Force `numpy<2` trong `requirements.txt`.
