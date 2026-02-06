from datetime import timedelta
from models.db_models import db, LeaveRequest, LeaveStatus, Attendance, AttendanceStatus

class LeaveManager:
    @staticmethod
    def approve_leave_request(leave_request_id, admin_id=None):
        """
        Approves a leave request and updates Attendance records for the duration.
        """
        leave_request = LeaveRequest.query.get(leave_request_id)
        
        if not leave_request:
            return False, "Yêu cầu nghỉ phép không tồn tại"
        
        if leave_request.status != LeaveStatus.PENDING:
            return False, "Yêu cầu này đã được xử lý trước đó"
            
        # Update Status
        leave_request.status = LeaveStatus.APPROVED
        current_date = leave_request.start_date
        end_date = leave_request.end_date
        
        while current_date <= end_date:
            day_start = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = current_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            attendance = Attendance.query.filter(
                Attendance.user_id == leave_request.user_id,
                Attendance.checkin_time >= day_start,
                Attendance.checkin_time <= day_end
            ).first()
            
            if attendance:
                # Update existing
                attendance.status = AttendanceStatus.ON_LEAVE
                attendance.checkout_time = None 
            else:
                # Create new
                new_attendance = Attendance(
                    user_id=leave_request.user_id,
                    checkin_time=day_start,
                    status=AttendanceStatus.ON_LEAVE,
                    shift_id=None
                )
                db.session.add(new_attendance)
            
            current_date += timedelta(days=1)
            
        try:
            db.session.commit()
            return True, "Đã duyệt đơn nghỉ phép"
        except Exception as e:
            db.session.rollback()
            return False, str(e)
