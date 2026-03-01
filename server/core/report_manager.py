from datetime import datetime, timedelta
from models.db_models import db, User, Attendance, AttendanceStatus, Shift, LeaveRequest, LeaveStatus
from sqlalchemy import func
import pandas as pd
import io

class ReportManager:
    """
    Quản lý báo cáo và thống kê hệ thống
    """
    
    @staticmethod
    def calculate_work_hours(checkin_time, checkout_time):
        """Tính tổng giờ làm việc"""
        if not checkin_time or not checkout_time:
            return 0.0
        delta = checkout_time - checkin_time
        return round(delta.total_seconds() / 3600, 2)  # Convert to hours
    
    @staticmethod
    def generate_dashboard_stats(start_date=None, end_date=None):
        """
        Tạo thống kê cho Dashboard
        
        Args:
            start_date: datetime (optional) - Ngày bắt đầu filter
            end_date: datetime (optional) - Ngày kết thúc filter
        
        Returns:
            dict với đầy đủ thống kê
        """
        # Nếu không có filter, lấy hôm nay
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Tổng quan
        total_employees = User.query.filter(User.role.in_(['employee', 'admin'])).count()
        total_shifts = Shift.query.count()
        pending_leaves = LeaveRequest.query.filter_by(status=LeaveStatus.PENDING).count()
        
        # Attendance hôm nay
        logs_today = Attendance.query.filter(
            Attendance.checkin_time >= today_start,
            Attendance.checkin_time <= today_end
        ).all()
        
        present_today = len(set([l.user_id for l in logs_today]))
        late_today = len([l for l in logs_today if l.status == AttendanceStatus.LATE])
        on_leave_today = len([l for l in logs_today if l.status == AttendanceStatus.ON_LEAVE])
        absent_today = total_employees - present_today
        
        # Tính tỷ lệ đi muộn hôm nay
        late_rate_today = round((late_today / present_today * 100), 2) if present_today > 0 else 0.0
        
        result = {
            "success": True,
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "overview": {
                "total_employees": total_employees,
                "total_shifts": total_shifts,
                "pending_leaves": pending_leaves
            },
            "attendance_today": {
                "present": present_today,
                "late": late_today,
                "absent": absent_today,
                "on_leave": on_leave_today,
                "late_rate_percent": late_rate_today
            }
        }
        
        # Nếu có filter theo period
        if start_date and end_date:
            period_logs = Attendance.query.filter(
                Attendance.checkin_time >= start_date,
                Attendance.checkin_time <= end_date
            ).all()
            
            total_attendance = len(period_logs)
            on_time_count = len([l for l in period_logs if l.status == AttendanceStatus.ON_TIME])
            late_count = len([l for l in period_logs if l.status == AttendanceStatus.LATE])
            overtime_count = len([l for l in period_logs if l.status == AttendanceStatus.OVERTIME])
            on_leave_count = len([l for l in period_logs if l.status == AttendanceStatus.ON_LEAVE])
            
            # Tỷ lệ đi muộn trong period
            late_rate_period = round((late_count / total_attendance * 100), 2) if total_attendance > 0 else 0.0
            
            result["period"] = {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d")
            }
            result["period_summary"] = {
                "total_attendance": total_attendance,
                "on_time": on_time_count,
                "late": late_count,
                "overtime": overtime_count,
                "on_leave": on_leave_count,
                "late_rate_percent": late_rate_period
            }
        
        return result
    
    @staticmethod
    def export_attendance_to_excel(start_date=None, end_date=None, user_id=None):
        """
        Export dữ liệu attendance ra Excel với Summary
        
        Args:
            start_date: datetime (optional)
            end_date: datetime (optional)
            user_id: int (optional) - Filter theo user
        
        Returns:
            BytesIO object chứa Excel file
        """
        from sqlalchemy.orm import joinedload
        
        # Build query with eager loading
        query = Attendance.query.options(
            joinedload(Attendance.user),
            joinedload(Attendance.shift)
        )
        
        if start_date:
            query = query.filter(Attendance.checkin_time >= start_date)
        if end_date:
            query = query.filter(Attendance.checkin_time <= end_date)
        if user_id:
            query = query.filter(Attendance.user_id == user_id)
        
        logs = query.order_by(Attendance.checkin_time.desc()).all()
        
        # Prepare detail data
        detail_data = []
        for idx, log in enumerate(logs, start=1):
            work_hours = ReportManager.calculate_work_hours(log.checkin_time, log.checkout_time)
            
            # Safe access to relationships
            user_id = log.user_id
            user_name = log.user.name if log.user else f"User #{user_id}"
            shift_name = log.shift.name if log.shift else "Không xác định"
            
            detail_data.append({
                "STT": idx,
                "Mã NV": user_id,
                "Họ Tên": user_name,
                "Ca Làm Việc": shift_name,
                "Ngày": log.checkin_time.strftime("%Y-%m-%d") if log.checkin_time else "",
                "Check-in": log.checkin_time.strftime("%H:%M:%S") if log.checkin_time else "",
                "Check-out": log.checkout_time.strftime("%H:%M:%S") if log.checkout_time else "-",
                "Tổng Giờ": work_hours,
                "Trạng Thái": log.status.value if hasattr(log.status, 'value') else str(log.status),
                "Ghi Chú": ""
            })
        
        # Prepare summary data
        total_records = len(logs)
        on_time_count = len([l for l in logs if l.status == AttendanceStatus.ON_TIME])
        late_count = len([l for l in logs if l.status == AttendanceStatus.LATE])
        overtime_count = len([l for l in logs if l.status == AttendanceStatus.OVERTIME])
        on_leave_count = len([l for l in logs if l.status == AttendanceStatus.ON_LEAVE])
        total_work_hours = sum([ReportManager.calculate_work_hours(l.checkin_time, l.checkout_time) for l in logs])
        
        late_rate = round((late_count / total_records * 100), 2) if total_records > 0 else 0.0
        
        summary_data = [
            {"Chỉ Số": "Tổng Số Bản Ghi", "Giá Trị": total_records},
            {"Chỉ Số": "Đúng Giờ", "Giá Trị": on_time_count},
            {"Chỉ Số": "Đi Muộn", "Giá Trị": late_count},
            {"Chỉ Số": "Tăng Ca", "Giá Trị": overtime_count},
            {"Chỉ Số": "Nghỉ Phép", "Giá Trị": on_leave_count},
            {"Chỉ Số": "Tỷ Lệ Đi Muộn (%)", "Giá Trị": late_rate},
            {"Chỉ Số": "Tổng Giờ Làm Việc", "Giá Trị": round(total_work_hours, 2)},
            {"Chỉ Số": "Ngày Xuất Báo Cáo", "Giá Trị": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        ]
        
        # Create Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet 1: Summary
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, index=False, sheet_name='Tổng Quan')
            
            # Sheet 2: Detail (handle empty data)
            if detail_data:
                df_detail = pd.DataFrame(detail_data)
            else:
                # Create empty DataFrame with column headers
                df_detail = pd.DataFrame(columns=[
                    "STT", "Mã NV", "Họ Tên", "Ca Làm Việc", "Ngày", 
                    "Check-in", "Check-out", "Tổng Giờ", "Trạng Thái", "Ghi Chú"
                ])
            df_detail.to_excel(writer, index=False, sheet_name='Chi Tiết Chấm Công')
            
            # Sheet 3: By User Summary (if not filtered by user_id)
            if not user_id and logs:
                user_stats = []
                unique_users = set([l.user_id for l in logs])
                for uid in unique_users:
                    user_logs = [l for l in logs if l.user_id == uid]
                    # Get user from the log's relationship (already loaded)
                    user_name = user_logs[0].user.name if user_logs and user_logs[0].user else f"User #{uid}"
                    
                    user_late = len([l for l in user_logs if l.status == AttendanceStatus.LATE])
                    user_total = len(user_logs)
                    user_work_hours = sum([ReportManager.calculate_work_hours(l.checkin_time, l.checkout_time) for l in user_logs])
                    
                    user_stats.append({
                        "Mã NV": uid,
                        "Họ Tên": user_name,
                        "Tổng Lần Chấm Công": user_total,
                        "Số Lần Muộn": user_late,
                        "Tỷ Lệ Muộn (%)": round((user_late / user_total * 100), 2) if user_total > 0 else 0.0,
                        "Tổng Giờ Làm": round(user_work_hours, 2)
                    })
                
                if user_stats:
                    df_user_stats = pd.DataFrame(user_stats)
                    df_user_stats.to_excel(writer, index=False, sheet_name='Thống Kê Theo NV')
                df_user_stats.to_excel(writer, index=False, sheet_name='Thống Kê Theo NV')
        
        output.seek(0)
        return output
