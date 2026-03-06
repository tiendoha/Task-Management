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
      "face_image": true,
      "is_active": true,
      "change_password_request": false,
      "must_change_password": false
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
      "face_image": true,
      "is_active": true,
      "change_password_request": false,
      "must_change_password": false
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
      "image": "data:image/jpeg;base64,...", // Optional (Updates FaceID)
      "is_active": false                 // Optional (Lock/Unlock Account)
  }
  ```
- **Response**: `{ "success": true, "message": "Cập nhật thành công!" }`

---

## 4. Timekeeping (Chấm công)

### 4.1. Check-in / Check-out
- **Endpoint**: `POST /api/checkin`
- **Quy tắc tính công & Quản lý Ca Đêm**:
    1. **work_date thay vì checkin_time**: Hệ thống mới theo dõi và nhóm phiên chấm công qua `work_date` (Chứ không lấy giờ hệ thống như trước kia). Điều này cho phép nhân sự Ca Đêm (22:00 -> 06:00 sáng hôm sau) được gộp chung vào bảng công ngày hôm trước một cách chính xác. Mọi logic so khớp sau này tự động tính tới tham số vượt qua quá nửa đêm.
    2. **Kiểm tra User đã có bảng công (Attendance) trong `work_date` hiện tại hay chưa?**
        - **Check-in (Chưa có Record)**: Sinh record mới, gán `status = PRESENT`. Trỏ cột `late_minutes` dựa theo việc lúc quẹt thẻ đã vượt quá Ca Làm Việc (`shift_start` + `grace_period_minutes`) bao lâu.
        - **Check-out (Đã có Record)**: Gọi Update record cũ, ghi `checkout_time`.
          - Sinh `early_leave_minutes` nếu giờ về bé hơn Hour của `shift_end`.
          - Sinh `overtime_minutes` nếu quẹt thẻ về vượt 10 phút sau khi tan làm.
- **Lưu ý Statuses (Đã rút gọn)**: Thay vì lưu 6 trạng thái rời rạc, Database mới quy chuẩn lại duy nhất 3 giá trị: `PRESENT` (Có mặt/Check-in), `ABSENT` (Vắng), và `ON_LEAVE` (Nghỉ Phép). Việc Muộn hay Sớm đã được định lượng bằng thông số Phút trong CSDL.

### 4.2. Chốt công tự động (Tự động hóa bằng APScheduler)
- **Chu kỳ chạy**: Cố định đúng **23:59:00** (Múi Asia/Ho_Chi_Minh).
- **Nghiệp vụ Xử lý Data**:
    1. **Thu gom rác Ca Khuyết**: Những ai Check-in nhưng Quên Check-out sẽ được Tự động Checkout vào lúc `shift_end` của Ca đó. KHÔNG bị phạt Overtime hay Early Leave (`= 0`).
    2. **Xử phạt Vắng Mặt**: Lọc tất cả Staff. Nếu không có `Attendance` Record hiện diện hôm nay VÀ không có `LeaveRequest` hợp lệ -> Cắm cờ `ABSENT`. Nếu có `LeaveRequest` hợp lệ -> Cắm cờ `ON_LEAVE`.
- **Response (Thất bại - Face Anti-Spoofing)**: Nếu đưa ảnh màn hình điện thoại hoặc ảnh in mờ, AI sẽ từ chối và cảnh báo.
  ```json
  {
    "success": false, 
    "message": "Không nhận diện được khuôn mặt: Spoofing detected: Phát hiện hình ảnh giả mạo!"
  }
  ```

### 4.3. API Truy vấn Lịch sử Điểm danh (Logs)
- **Endpoint**: `GET /api/logs?date=YYYY-MM-DD`
- **Query Parameter**: Trền param `date` (Mặc định query `today` nếu không gửi). Dùng tham số này để render bảng tổng hợp theo ngày.
- **Response Format**: Data trả về đã được bind ghép với các thông số phạt (Dành cho Dashboard/Báo Cáo Cuối Tháng).
  ```json
  [
    {
      "name": "Nguyen Van A",
      "status": "PRESENT",
      "time": "08:15:00 01/03",
      "checkout": "17:35:00 01/03",
      "late_minutes": 15,
      "early_leave_minutes": 0,
      "overtime_minutes": 10
    }
  ]
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

---

## 8. Account & Password Management (Mới)

Hệ thống cho phép Quản trị viên vô hiệu hóa tài khoản và hỗ trợ luồng Cấp/Đổi lại mật khẩu (Forgot Password) có bảo mật cao bằng Gmail SMTP.

### 8.1. Account Locking (Khóa tài khoản)
- **Endpoint**: Sửa field thông qua `PUT /api/employees/<id>`
- **Logic**: Khi Admin gọi API update truyền vào `"is_active": false`, User đó sẽ ngay lập tức bị văng lỗi cấp HTTP 403 `Tài khoản của bạn đang bị khóa` ở mọi điểm truy cập (bao gồm cả Log In lẫn Check-in API).

### 8.2. Yêu cầu Cấp lại Mật Khẩu
- **Endpoint**: `POST /api/reset-password-request`
- **Public**: Yes (Không cần Token)
- **Body**: `{ "username": "...", "email": "..." }`
- **Response**: Trả về 200 OK và đánh cờ `change_password_request = True` trong database chờ Admin phê duyệt.

### 8.3. Admin Cấp lại Mật khẩu (Reset)
- **Endpoint**: `PUT /api/reset-password/<user_id>`
- **Header**: `Authorization: Bearer <admin_token>`
- **Logic**: 
  - Tạo ngẫu nhiên chuỗi mật khẩu mạnh 10 ký tự (Kèm ký tự đặc biệt).
  - Cập nhật Database, bật cờ `must_change_password = True`.
  - Gửi Email tự động chứa mật khẩu đến địa chỉ email của User.
- **Response**: Trả về 200 OK thông báo Email đã bay.

### 8.4. Bắt buộc Đổi Mật Khẩu (Force Change)
- **Endpoint**: `PUT /api/change-password`
- **Header**: `Authorization: Bearer <user_token>` (User đăng nhập bằng Pass tạm thời)
- **Logic**: User BỊ BẮT BUỘC gọi API này để update sang Password mới vĩnh viễn (Tối thiểu 6 ký tự). Admin/Backend chặn mọi nỗ lực call API khác nếu cờ `must_change_password` vẫn đỏ.
- **Body**: `{ "new_password": "NewSecret@123" }`
- **Response**: 200 OK, tắt cờ bắt buộc đổi pass. User bắt buộc phải Login lại.
