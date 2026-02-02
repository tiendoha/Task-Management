# Work Log – Hoàn thiện API Quản Lý Nhân Viên (Bản Nâng Cao)

## Tổng quan

Đã **triển khai xong và test ổn định** các API quản lý nhân viên nâng cao trong file `server/app.py`.
Toàn bộ luồng CRUD, bảo mật và FaceID đều hoạt động đúng như thiết kế.

---

## Các chức năng đã hoàn thành

### 1. Cập nhật nhân viên (`PUT /api/employees/<id>`)

* **Bảo mật**: Endpoint yêu cầu **Admin Token**.
* **Thông tin cơ bản**: Có thể cập nhật `name`, `email`, `phone`, `dob`, `role`, `shift_id`.

**Đổi mật khẩu**

* Bắt buộc phải gửi `oldPassword`.
* Nếu mật khẩu cũ không đúng → trả về `400` với thông báo:
  **"Mật khẩu cũ không đúng"**
* Mật khẩu mới được hash bằng `werkzeug.security` (chuẩn `pbkdf2:sha256`).

**Cập nhật FaceID**

* Nhận ảnh dạng **base64**.
* Dùng `AIEngine` để trích xuất embedding khuôn mặt.
* Nếu AI không nhận diện được mặt → trả về `400` với thông báo:
  **"Ảnh không rõ mặt, vui lòng chụp lại"**

---

### 2. Xóa nhân viên (`DELETE /api/employees/<id>`)

* **Bảo mật**: Chỉ Admin mới được gọi.
* **Xóa dây chuyền (cascade)**:

  * Tự động xóa toàn bộ dữ liệu `Attendance` liên quan để tránh lỗi khóa ngoại.
* Không tìm thấy nhân viên → `404`.
* Xóa thành công → `200`.

---

### 3. Lấy thông tin chi tiết nhân viên (`GET /api/employees/<id>`)

* Trả về đầy đủ thông tin:

  * `role`
  * Tên ca làm (`shift`)
  * Trạng thái FaceID (`face_image`: có / chưa có)

---

### 4. Lấy danh sách toàn bộ nhân viên (`GET /api/employees`)

* Trả về danh sách nhân viên kèm đầy đủ thông tin chi tiết như endpoint lấy 1 người.

---

## Kiểm tra & xác thực

Toàn bộ API đã được kiểm tra bằng script nội bộ `verify_api.py` (mock DB và AI Engine).

Kết quả:

* CRUD chạy đúng
* Kiểm tra mật khẩu hoạt động chính xác
* Xóa cascade không lỗi
* Xác thực Bearer Token OK

---

## Ghi chú khi dev & xử lý lỗi thường gặp

### 1. Lỗi xác thực Token (`401 Unauthorized`)

**Triệu chứng**

* API trả về: `"Token is missing!"`

**Cách xử lý**

* Header phải đúng định dạng:

  ```
  Authorization: Bearer <token>
  ```
* ❌ Sai: `Authorization: eyJhbGci...`
* ✅ Đúng: `Authorization: Bearer eyJhbGci...`

---

### 2. Không đổi được mật khẩu (`400 Bad Request`)

**Triệu chứng**

* Trả về: `"Mật khẩu cũ không đúng"`

**Nguyên nhân & cách fix**

* Thiếu `oldPassword` trong body
* `oldPassword` không khớp với mật khẩu hiện tại trong DB
* Hệ thống đang dùng hash `pbkdf2:sha256` (werkzeug)

---

### 3. Lỗi cập nhật FaceID

**Triệu chứng**

* Trả về: `"Ảnh không rõ mặt, vui lòng chụp lại"`

**Cách xử lý**

* Ảnh cần:

  * Ánh sáng tốt
  * Rõ mặt
  * Chỉ có **1 khuôn mặt**
* Tránh ảnh mờ, tối hoặc quay ngang quá nhiều

---

### 4. Lỗi import AI (`cv2`, `deepface`)

**Triệu chứng**

* Server không chạy
* Script test bị crash

**Cách xử lý**

```bash
pip install opencv-python deepface tensorflow
```

---
