# Hướng dẫn test API với Postman

Tôi đã tạo file `HRM_FaceID.postman_collection.json` ở thư mục gốc. Bạn hãy làm theo các bước sau:

## 1. Import vào Postman
- Mở Postman -> Chọn nút **Import** (trên cùng bên trái).
- Kéo thả file `HRM_FaceID.postman_collection.json` vào.

## 2. Chuẩn bị ảnh Base64
Vì API nhận diện khuôn mặt yêu cầu ảnh dạng Base64 string, bạn cần convert một ảnh chụp khuôn mặt sang chuỗi văn bản.
- **Cách 1:** Vào trang [Base64 Image Encoder](https://www.base64-image.de/). Upload ảnh của bạn -> Copy đoạn code trong nút "Copy Image" (hoặc copy string và thêm tiền tố `data:image/jpeg;base64,` vào đầu).
- **Cách 2:** Dùng tool online bất kỳ tìm từ khóa "image to base64".

## 3. Test theo kịch bản

### Bước 1: Đăng ký (Register)
- Mở Request **"1. Đăng ký (Register)"**.
- Vào Tab **Body**.
- Tìm trường `"image"` và dán chuỗi Base64 ảnh khuôn mặt bạn vào (thay thế dòng `...(Dán_Base64_vào_đây)...`).
- Bấm **Send**.
- *Kỳ vọng:* Trả về `{"success": true, "message": "Thêm nhân viên thành công!"}`.

### Bước 2: Kiểm tra (Check-in)
- Mở Request **"2. Chấm công (Check-in)"**.
- Vào Tab **Body**.
- Dán cùng chuỗi Base64 đó (hoặc ảnh khác của cùng một người) vào trường `"image"`.
- Bấm **Send**.
- *Kỳ vọng:* Trả về tên của bạn và trạng thái (`Done`/`Late`).
- *Lưu ý:* Lần đầu bấm Send có thể mất 3-5s để Server load model.

### Bước 3: Xem danh sách
- Chạy Request **"3. Lấy DS Nhân viên"** để xem user bạn vừa tạo đã vào DB chưa.
