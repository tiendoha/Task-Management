# HRM FaceID Client (Frontend)

Đây là giao diện người dùng (ReactJS) cho hệ thống chấm công FaceID.

## 🛠️ Yêu cầu cài đặt
- **Node.js**: Phiên bản 18 trở lên (Khuyến nghị 20+).
- **npm** hoặc **yarn**.

## 🚀 Hướng dẫn cài đặt & Chạy

### 1. Cài đặt thư viện
Mở terminal tại thư mục `client` và chạy lệnh:
```bash
npm install
```
*(Nếu quá trình cài đặt bị lỗi, hãy thử `npm install --force` hoặc xóa thư mục `node_modules` rồi cài lại).*

### 2. Khởi chạy dự án (Môi trường Dev)
```bash
npm run dev
```
Sau khi chạy xong, truy cập vào đường dẫn hiển thị trên terminal (thường là `http://localhost:5173`).

### 3. Build Production (Khi triển khai thật)
```bash
npm run build
npm run preview
```

## 📦 Các thư viện chính
Dự án sử dụng các thư viện sau (đã khai báo trong `package.json`):
- **React 19**: Core framework.
- **Vite**: Build tool siêu tốc.
- **Axios**: Gọi API xuống Backend (Flask).
- **Bootstrap 5**: Giao diện (CSS).
- **React-Bootstrap**: Component Bootstrap cho React.
- **React-Webcam**: Xử lý Camera để chụp ảnh khuôn mặt.
- **Chart.js / React-Chartjs-2**: Vẽ biểu đồ thống kê.

## ⚠️ Lưu ý quan trọng
- **Backend phải đang chạy**: Đảm bảo bạn đã bật Server Flask (Port 5000) trước khi sử dụng Frontend, nếu không sẽ lỗi kết nối.
- **Camera**: Trình duyệt có thể yêu cầu cấp quyền Camera, hãy chọn **Allow**.
