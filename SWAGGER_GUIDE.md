# 📚 Hướng Dẫn Sử Dụng Swagger API Documentation

## 🚀 Cài Đặt & Khởi Động

### 1. Cài đặt dependencies mới
```bash
cd server
pip install flasgger
```

Hoặc cài toàn bộ từ requirements.txt:
```bash
pip install -r requirements.txt
```

### 2. Khởi động server
```bash
python app.py
```

Server sẽ chạy tại: `http://localhost:5000`

---

## 📖 Truy Cập Swagger UI

Mở trình duyệt và truy cập:
```
http://localhost:5000/api-docs/
```

Bạn sẽ thấy giao diện Swagger UI với đầy đủ API documentation.

---

## 🔐 Test API Với JWT Authentication

### Bước 1: Đăng nhập để lấy token

1. Tìm endpoint **POST /api/auth/login** trong mục **Authentication**
2. Click vào **"Try it out"**
3. Nhập thông tin đăng nhập:
```json
{
  "username": "admin",
  "password": "Admin@123"
}
```
4. Click **"Execute"**
5. Copy **token** từ response

### Bước 2: Cấu hình Authorization

1. Click vào nút **"Authorize"** (biểu tượng ổ khóa) ở đầu trang
2. Nhập token theo format:
```
Bearer <your_token_here>
```
Ví dụ:
```
Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```
3. Click **"Authorize"**
4. Click **"Close"**

### Bước 3: Test các API cần authentication

Bây giờ bạn có thể test tất cả API có biểu tượng ổ khóa (🔒).

---

## 📚 Các Nhóm API

### 🔐 Authentication
- **POST /api/auth/login** - Đăng nhập
- **PUT /api/profile** - Cập nhật profile (🔒)

### 👥 Employees (Admin only)
- **GET /api/employees** - Danh sách nhân viên (🔒)
- **POST /api/employees** - Thêm nhân viên (🔒)
- **PUT /api/employees/{id}** - Sửa nhân viên (🔒)
- **DELETE /api/employees/{id}** - Xóa nhân viên (🔒)
- **GET /api/employees/{id}** - Chi tiết nhân viên (🔒)

### ⏰ Attendance
- **POST /api/checkin** - Chấm công bằng Face Recognition

### 🎭 Face Setup (Admin only)
- **POST /api/face-setup/analyze** - Phân tích góc mặt (🔒)
- **POST /api/face-setup/finish** - Hoàn tất đăng ký 3 góc (🔒)

### 🕐 Shifts
- **GET /api/shifts** - Danh sách ca làm việc
- **POST /api/shifts** - Tạo ca mới (🔒 Admin)
- **PUT /api/shifts/{id}** - Sửa ca (🔒 Admin)

### 🏖️ Leave Management
- **GET /api/leaves** - Danh sách đơn nghỉ phép (🔒)
- **POST /api/leaves** - Tạo đơn nghỉ phép (🔒)
- **PUT /api/leaves/{id}** - Duyệt/từ chối đơn (🔒 Admin)

### 💰 Payroll (NEW!)
- **GET /api/payroll/calculate** - Tính lương tất cả NV (🔒 Admin)
- **GET /api/payroll/calculate/me** - Xem lương của mình (🔒)
- **POST /api/payroll/confirm** - Confirm và lưu lương (🔒 Admin)
- **GET /api/payroll/history** - Lịch sử lương đã confirm (🔒)

### 📊 Reports
- **GET /api/stats** - Thống kê tổng quan
- **GET /api/stats/top-late** - Top 5 người đi muộn (🔒 Admin)
- **GET /api/stats/chart** - Biểu đồ 7 ngày (🔒 Admin)
- **GET /api/logs** - Log chấm công
- **GET /api/export_excel** - Export Excel

---

## 💡 Ví Dụ Test Flow

### Flow 1: Quản lý nhân viên

1. **Đăng nhập** → Lấy token
2. **GET /api/employees** → Xem danh sách
3. **POST /api/employees** → Thêm nhân viên mới với thông tin:
```json
{
  "username": "nva",
  "password": "123456",
  "name": "Nguyễn Văn A",
  "email": "nva@company.com",
  "phone": "0123456789",
  "role": "employee",
  "shift_id": 1,
  "base_salary": 10000000
}
```

### Flow 2: Tính lương

1. **GET /api/payroll/calculate?month=2&year=2026** → Xem bảng lương preview
2. Chỉnh sửa số liệu nếu cần (ở frontend)
3. **POST /api/payroll/confirm** → Confirm và lưu lương:
```json
{
  "user_id": 1,
  "month": 2,
  "year": 2026,
  "base_salary": 10000000,
  "total_workdays": 22,
  "late_count": 3,
  "penalty_per_late": 50000,
  "bonus": 5000000,
  "notes": "Thưởng hoàn thành dự án"
}
```
4. **GET /api/payroll/history** → Xem lịch sử đã confirm

### Flow 3: Chấm công bằng khuôn mặt

1. **POST /api/checkin** với body:
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```
(Cần có ảnh base64 thật từ camera)

---

## 🎯 Tips & Tricks

### 1. Test nhanh với cURL
Copy cURL command từ Swagger UI và chạy trong terminal:
```bash
curl -X POST "http://localhost:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@123"}'
```

### 2. Debug Response
- Swagger hiển thị cả Request và Response
- Xem HTTP status code để biết lỗi
- Đọc message trong response body

### 3. Schema Validation
- Swagger tự động validate input theo schema
- Các field **required** được đánh dấu rõ ràng
- Kiểu dữ liệu (string, integer, number) được check tự động

---

## 🐛 Troubleshooting

### Lỗi "401 Unauthorized"
→ Token hết hạn hoặc chưa authorize. Đăng nhập lại và lấy token mới.

### Lỗi "403 Forbidden"
→ Không có quyền truy cập. Endpoint này chỉ dành cho Admin.

### Lỗi "400 Bad Request"
→ Dữ liệu input sai format. Kiểm tra lại schema trong Swagger.

### Swagger UI không load
→ Kiểm tra:
1. Server có đang chạy không?
2. Port 5000 có bị chiếm không?
3. Có cài `flasgger` chưa?

---

## 📝 Notes

- Token JWT có hạn **24 giờ**
- Default Admin: `admin / Admin@123`
- Base64 image cho Face Recognition phải có prefix: `data:image/jpeg;base64,...`
- Payroll bonus tự động nếu làm > 300 ngày/năm

---

## 🚀 Next Steps

1. Test tất cả API endpoints
2. Kiểm tra validation rules
3. Verify JWT authentication
4. Test Payroll module mới
5. Export Postman collection từ Swagger (nếu cần)

---

**Happy Testing! 🎉**
