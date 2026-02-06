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
    -   **FaceID Update**:
        -   Extracts embedding using `AIEngine`.
2.  **Delete Employee (`DELETE /api/employees/<id>`)**
    -   **Cascade Delete**: Automatically deletes related `Attendance` records.
3.  **Statistics & Charts**
    -   **Top Late (`GET /api/stats/top-late`)**: Top 5 late employees (Current Month).
    -   **7-Day Chart (`GET /api/stats/chart`)**: Late vs On Time trends (Last 7 Days).
4.  **Leave Management (New)**
    -   **Core Logic**: `LeaveManager` handles approval and automatic attendance updating.
    -   **Create Request (`POST /api/leaves`)**: Submit leave request (Pending).
    -   **List Requests (`GET /api/leaves`)**: Admin sees all, Employee sees own.
    -   **Approve/Reject (`PUT /api/leaves/<id>`)**:
        -   **Approve**: Updates request status to `APPROVED` AND creates/updates `Attendance` records for the leave duration with status `ON_LEAVE`.
        -   **Reject**: Updates status to `REJECTED`.

## Verification
All endpoints have been verified using:
1.  `verify_api.py` (Unit Tests for CRUD)
2.  `test_backend_logic.py` (Backend Logic Tests)
3.  `test_top_late.py` & `test_chart_stats.py` (Stats Tests)
4.  `test_leave_management.py` (Leave Flow Tests) - **PASSED**

## Troubleshooting & Dev Notes
### Leave Management
-   **Approve Logic**: The system automatically fills `Attendance` for the requested dates. If user already checked in, it updates the status to `ON_LEAVE`.
-   **Date Format**: Ensure dates are sent as `YYYY-MM-DD`.
