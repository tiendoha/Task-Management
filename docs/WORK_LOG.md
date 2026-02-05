# Work Log - Advanced Employee API Implementation

## Overview
Successfully implemented and verified the Advanced Employee Management APIs and Statistics in `server/app.py`.

### Completed Features
1.  **Update Employee (`PUT /api/employees/<id>`)**
    -   **Endpoint**: Protected by Admin Token.
    -   **Basic Info**: Updates name, email, phone, dob, role, shift_id.
    -   **Password Change**:
        -   Requires strict validation of `oldPassword`.
        -   Returns `400` with message "Mật khẩu cũ không đúng" if validation fails.
        -   Hashes new password using `werkzeug.security`.
    -   **FaceID Update**:
        -   Accepts base64 image.
        -   Extracts embedding using `AIEngine`.
        -   Returns `400` with message "Ảnh không rõ mặt, vui lòng chụp lại" if AI fails to detect face.
2.  **Delete Employee (`DELETE /api/employees/<id>`)**
    -   **Endpoint**: Protected by Admin Token.
    -   **Cascade Delete**: Automatically deletes related `Attendance` records to prevent foreign key errors.
    -   Returns `404` if user not found, `200` on success.
3.  **Get Employee (`GET /api/employees/<id>`)**
    -   **Detailed Response**: Returns object including `role`, `shift` name, and `face_image` (boolean status).
4.  **Top Late Statistics (`GET /api/stats/top-late`)**
    -   **Endpoint**: Protected by Admin Token.
    -   **Logic**: Returns top 5 employees with the most LATE records in the current month.
    -   **Format**: `[{"name": "...", "count": 5, "avatar": true}]`.
5.  **7-Day Chart Statistics (`GET /api/stats/chart`)**
    -   **Endpoint**: Protected by Admin Token.
    -   **Logic**: Aggregates `LATE` vs `ON_TIME` records for the last 7 days.
    -   **Format**:
        ```json
        {
          "labels": ["29/01", "30/01", ...],
          "data_late": [0, 1, ...],
          "data_ontime": [5, 2, ...]
        }
        ```

## Verification
All endpoints have been verified using:
1.  `verify_api.py` (Unit Tests for CRUD)
2.  `test_backend_logic.py` (Comprehensive Backend Logic Tests) - **PASSED 4/4 Test Cases**
3.  `test_top_late.py` (Statistics Logic) - **PASSED**
4.  `test_chart_stats.py` (Chart Data Logic) - **PASSED**

## Troubleshooting & Dev Notes (Common Errors)
If encountering issues during team development/testing, please check:

### 1. Token Authentication (`401 Unauthorized`)
-   **Issue**: API returns "Token is missing!".
-   **Fix**: Ensure the `Authorization` header follows the format: `Bearer <token>`.

### 2. Import Errors
-   **Issue**: `NameError: name 'func' is not defined`.
-   **Fix**: Ensure `from sqlalchemy import func` is present in `server/app.py`.

### 3. FaceID Update Fails
-   **Issue**: API returns "Ảnh không rõ mặt, vui lòng chụp lại".
-   **Fix**: The `AIEngine` failed to detect a face in the provided base64 image. Ensure the image is well-lit and contains a clear single face.
