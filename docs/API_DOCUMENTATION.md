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
- **Response (Thành công)**: Trả về `status` (text tiếng Việt) để hiển thị lên màn hình.
- **Response (Thất bại - Face Anti-Spoofing)**: Nếu đưa ảnh màn hình điện thoại hoặc ảnh in mờ, AI sẽ từ chối và cảnh báo.
  ```json
  {
    "success": false, 
    "message": "Không nhận diện được khuôn mặt: Spoofing detected: Phát hiện hình ảnh giả mạo!"
  }
  ```

---

## 5. Face Registration (Đăng ký khuôn mặt 3 góc)

Công năng này dành riêng cho luồng tạo/đăng ký khuôn mặt mới, yêu cầu quét đủ 3 góc (Chính diện, Trái, Phải) để đảm bảo dữ liệu nhận diện chính xác.
Dành cho FE: Lưu ý luồng gọi API gồm 2 bước: gọi `analyze` 3 lần (cho 3 góc), sau đó gom kết quả gọi `finish`.

### API 1: Phân tích góc mặt (Analyze)
- **Endpoint**: `POST /api/face-setup/analyze`
- **Header**: `Authorization: Bearer <admin_token>`
- **Mô tả**: Gửi ảnh chụp quét khuôn mặt theo góc yêu cầu. Hệ thống sẽ kiểm tra góc mặt, chống giả mạo và trả về Vector đặc trưng (Embedding).
- **Body**:
  ```json
  {
    "image": "data:image/jpeg;base64,...",
    "current_step": "center" // Các bước hợp lệ: "center", "left", "right"
  }
  ```
- **Response (Thành công - Đúng góc mặt)**: FE cần lưu mảng `embedding` trả về lại vào State/Cache để dành cho bước Finish.
  ```json
  {
    "success": true, 
    "embedding": [-0.0123, 0.445, ...], 
    "message": "OK", 
    "pose": "center"
  }
  ```
- **Response (Thất bại - Quay sai góc hoặc lỗi hình ảnh)**: FE hiển thị `message` để hướng dẫn người dùng điều chỉnh tư thế. 
  Đặc biệt, nếu ảnh giả mạo sẽ trả về lỗi từ Anti-Spoofing:
  ```json
  {
    "success": false, 
    "message": "Lỗi: Spoofing detected: Phát hiện hình ảnh giả mạo!"
  }
  ```

### API 2: Hoàn tất lưu dữ liệu (Finish)
- **Endpoint**: `POST /api/face-setup/finish`
- **Header**: `Authorization: Bearer <admin_token>`
- **Mô tả**: Gọi một lần DUY NHẤT sau khi đã đi qua đủ 3 góc ở API Analyze.
- **Body**: Gửi `user_id` nhân viên cần cập nhật khuôn mặt, cùng với mảng các `embedding` đã thu được ở bước Analyze.
  ```json
  {
    "user_id": 1,
    "embeddings": [
      [-0.01, 0.44, ...], // Vector từ ảnh Center
      [0.02, -0.12, ...], // Vector từ ảnh Left
      [-0.03, 0.05, ...]  // Vector từ ảnh Right
    ]
  }
  ```
- **Response**: Hệ thống tự nối các vector lại lấy trung bình (Average Pooling) và lưu vào database.
  ```json
  {
    "success": true, 
    "message": "Hoàn tất đăng ký khuôn mặt (3 góc)!"
  }
  ```

---

## 6. Development Notes & Troubleshooting (Các lỗi đã gặp)

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

---

## 7. Advanced AI Features (Tính năng AI Nâng cao)

### 1. Model Warm-up (Khởi chạy trước Model)
- **Vấn đề**: Theo mặc định, `DeepFace` chỉ load model Face Recognition (ArcFace) và Anti-Spoofing (Fasnet) vào RAM khi API Check-in/Analyze được request gọi lần đầu tiên. Điều này khiến User đầu tiên sử dụng hệ thống mất từ 5 - 10 giây chờ loading.
- **Giải pháp**: Hệ thống backend đã tích hợp function `AIEngine.warm_up_models()`. Hàm này sẽ tự động generate một frame ảnh giả màu đen để "đánh lừa" pipeline DeepFace, bắt model tải trước 100% dung lượng vào Memory Core.
- **Lợi ích**: Khi server chạy hoàn tất (có log `[INFO] Warm-up hoàn tất!`), tốc độ response cho mọi User từ request đầu tiên trở đi sẽ nhanh tức thời và chỉ còn tốn thời gian xử lý ảnh.

### 2. Liveness Detection / Face Anti-Spoofing (Chống giả mạo mặt)
- **Cơ chế**: AI tích hợp Fasnet. Khi quét ảnh từ API `/api/checkin` hoặc `/api/face-setup/analyze`, thuật toán tiến hành bóc tách khuôn mặt và đánh giá tính thực (`is_real`).
- **Xử lý góc nghiêng WebCam**: Để tránh việc camera thấp dìm góc mặt bị Anti-Spoofing dập nhầm (báo là ảnh giả), hệ thống tự động chèn option `align=True` vào lõi phân tích `get_embedding`. Thuật toán sẽ xoay trục ngang 2 mắt cân bằng trước khi scan mức liveness.
- **Quy trình hoạt động**: Dân văn phòng/Nhân sự không thể cầm điện thoại chiếu vào màn hình, hoặc cầm ảnh thẻ giơ lên máy chấm công. AI phát hiện và ném văng token, reject API với thông báo: `Spoofing detected: Phát hiện hình ảnh giả mạo!`.
