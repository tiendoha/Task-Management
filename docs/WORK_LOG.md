# Work Log - Advanced Employee API Implementation

## Overview
Successfully implemented and verified the Advanced Employee Management APIs in `server/app.py`.

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
4.  **Get All Employees (`GET /api/employees`)**
    -   **List Response**: Returns list of all employees with detailed info.

## Verification
All endpoints have been verified using:
1.  `verify_api.py` (Unit Tests for CRUD)
2.  `test_backend_logic.py` (Comprehensive Backend Logic Tests) - **PASSED 4/4 Test Cases**

### Test Case Results
1.  **Shift Management**:
    -   POST Create: **PASS**
    -   PUT Update: **PASS**
    -   GET List: **PASS**
2.  **Employee CRUD**:
    -   POST Create (Full fields): **PASS**
    -   GET Detail (Check shift_name, email): **PASS**
    -   PUT Update: **PASS**
3.  **Password Security**:
    -   Wrong oldPassword -> 400: **PASS**
    -   Correct oldPassword -> 200: **PASS**
4.  **Attendance Logic**:
    -   Auto-detect Shift (Ca Sang) based on Mock Time (08:10): **PASS**
    -   Status "Đúng giờ": **PASS**

## Troubleshooting & Dev Notes (Common Errors)
If encountering issues during team development/testing, please check:

### 1. Token Authentication (`401 Unauthorized`)
-   **Issue**: API returns "Token is missing!".
-   **Fix**: Ensure the `Authorization` header follows the format: `Bearer <token>`.
    -   *Correct*: `Authorization: Bearer eyJhbGci...`
    -   *Incorrect*: `Authorization: eyJhbGci...`

### 2. Password Update Fails (`400 Bad Request`)
-   **Issue**: API returns "Mật khẩu cũ không đúng".
-   **Fix**: Ensure `oldPassword` is sent in the request body and matches the current database hash. The system uses `pbkdf2:sha256` by default via `werkzeug.security`.

### 3. FaceID Update Fails
-   **Issue**: API returns "Ảnh không rõ mặt, vui lòng chụp lại".
-   **Fix**: The `AIEngine` failed to detect a face in the provided base64 image. Ensure the image is well-lit and contains a clear single face.

### 4. Import Errors (`cv2`, `deepface`)
-   **Issue**: Server crashes on start or verification script fails.
-   **Fix**: Ensure all AI dependencies are installed: `pip install opencv-python deepface tensorflow`.
