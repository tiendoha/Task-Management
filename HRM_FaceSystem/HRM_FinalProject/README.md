# Hệ thống chấm công FaceID (Deep Learning Core)

## Giới thiệu
Hệ thống HRM sử dụng công nghệ nhận diện khuôn mặt Deep Learning (ArcFace) để chấm công tự động, quản lý nhân sự và lịch trình.

## Features
- **Check-in bằng khuôn mặt:** Độ chính xác cao (>99%) với model ArcFace.
- **Quản lý nhân sự:** Thêm, sửa, xóa nhân viên.
- **Chống giả mạo (Future):** Tích hợp thêm module Liveness Detection.

## Tech Stack
- **Backend:** Python 3.10+, Flask, Flask-SQLAlchemy.
- **AI Core:** DeepFace (ArcFace Model), OpenCV, TensorFlow/Keras.
- **Frontend:** ReactJS.
- **Database:** SQLite.

## Installation Guide

### 1. Yêu cầu hệ thống
- Python 3.10 trở lên.
- Node.js (cho Frontend).

### 2. Cài đặt Backend
**Bước 1:** Chạy script setup môi trường (tự động tạo venv và cài dependencies):

*   **Windows:**
    ```cmd
    setup_env.bat
    ```

*   **Linux/Mac:**
    ```bash
    chmod +x setup_env.sh
    ./setup_env.sh
    ```

**Bước 2:** Chạy Server:
```cmd
cd server
..\venv\Scripts\python app.py
```
*(Trên Linux/Mac dùng `../venv/bin/python app.py`)*

### ⚠️ LƯU Ý QUAN TRỌNG (MIGRATION & COLD START)
1.  **Dữ liệu cũ:** Nếu bạn nâng cấp từ phiên bản cũ (Dlib), **hãy xóa file `server/instance/hrm.db`** vì vector khuôn mặt 128D cũ không tương thích với model mới 512D.
2.  **Cold Start:** Lần đầu tiên chạy, hệ thống sẽ tải model weights (~500MB). Quá trình này có thể mất vài phút.
    *   Nếu Frontend báo lỗi Timeout, hãy kiên nhẫn đợi Server tải xong ở cửa sổ Console.

## 🔧 Troubleshooting (Sửa lỗi thường gặp)

### 1. Lỗi `AttributeError: module 'tensorflow' has no attribute '__version__'`
**Nguyên nhân:** Lỗi này thường do việc cài đặt TensorFlow bị xung đột hoặc corrupted (đặc biệt là `tensorflow-intel` trên Windows).
**Cách khắc phục:**
Chạy lệnh sau để cài lại sạch sẽ:
```cmd
venv\Scripts\pip uninstall -y tensorflow tensorflow-intel
venv\Scripts\pip install tensorflow==2.15.0
```

### 2. Lỗi `Dependency conflict` (Flask-Cors, Numpy)
**Nguyên nhân:** DeepFace yêu cầu nhiều thư viện con.
**Cách khắc phục:**
Đảm bảo file `requirements.txt` có nội dung sau (đã fix xung đột):
```text
deepface==0.0.93
tensorflow==2.15.0
tf-keras==2.15.0
numpy<2
Flask==3.1.2
Flask-SQLAlchemy==3.1.1
Flask-Cors==6.0.2
opencv-python
```

### 3. Lỗi Frontend Timeout khi Check-in lần đầu
**Nguyên nhân:** Do model ArcFace (500MB) đang tải xuống.
**Cách khắc phục:**
- Hãy chạy server bằng dòng lệnh trước để quan sát tiến trình tải.
- Khi nào thấy dòng chữ `Server Started` hoặc không còn download nữa thì mới mở Web.
