# Hướng dẫn test API với Postman (Update for Auth & RBAC)

Tôi đã cập nhật file `HRM_FaceID.postman_collection.json` để hỗ trợ quy trình xác thực JWT. Bạn hãy làm theo các bước sau:

## 1. Import lại vào Postman
- Nếu đã import bản cũ, hãy xóa đi hoặc ghi đè (Replace).
- Mở Postman -> Chọn nút **Import** (trên cùng bên trái) -> Kéo thả file `HRM_FaceID.postman_collection.json` vào.

## 2. Chuẩn bị ảnh Base64 (Như cũ)
- Dùng [Base64 Image Encoder](https://www.base64-image.de/) để có chuỗi ảnh khuôn mặt.

## 3. Test theo kịch bản (QUAN TRỌNG: Làm theo thứ tự)

### Bước 1: Đăng nhập Admin (Login) - BẮT BUỘC
- Mở Request **"1. Đăng nhập (Login - Lấy Token)"**.
- Body đã điền sẵn `admin` / `Admin@123` (Tài khoản mặc định).
- Bấm **Send**.
- *Kỳ vọng:* Trả về `{"success": true, "token": "..."}`.
- **Tự động:** Postman sẽ tự lưu Token này vào biến môi trường `jwt_token` để dùng cho các bước sau.

### Bước 2: Tạo nhân viên mới (Admin Only)
- Mở Request **"2. Tạo nhân viên mới (Admin Only)"**.
- Vào Tab **Authorization**, đảm bảo Type là "Bearer Token" và Token là `{{jwt_token}}`.
- Vào Tab **Body**, dán chuỗi Base64 ảnh vào trường `"image"`.
- Bấm **Send**.
- *Kỳ vọng:* Trả về thông tin nhân viên mới tạo.

### Bước 3: Chấm công (Public API)
- Mở Request **"3. Chấm công (Check-in - Public)"**.
- API này công khai, không cần Token.
- Dán chuỗi Base64 ảnh vào Body -> Bấm **Send**.

### Bước 4: Lấy DS Nhân viên (Admin Only)
- Mở Request **"4. Lấy DS Nhân viên (Admin Only)"**.
- API này yêu cầu Token Admin (đã tự động điền).
- Bấm **Send** -> Trả về danh sách tất cả nhân viên.

### Bước 5: Đăng ký khuôn mặt 3 góc (Analyze & Finish)
*Quy trình này dành cho Frontend/Kiosk để đăng ký khuôn mặt.*
1. **API Analyze (`POST /api/face-setup/analyze`)**:
   - Headers: `Authorization: Bearer {{jwt_token}}`
   - Body: Truyền ảnh Base64 và `current_step` (`center`, `left`, `right`).
   - Kết quả: Nhận mảng `embedding` nếu thành công.
2. **API Finish (`POST /api/face-setup/finish`)**:
   - Body: Truyền `user_id` và mảng các `embeddings` (chứa 3 mảng `embedding` thu được từ bước 1).
   - Kết quả: Server tính trung bình và lưu dữ liệu.
