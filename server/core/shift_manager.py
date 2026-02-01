from datetime import datetime, timedelta
from models.db_models import Shift, AttendanceStatus

class ShiftManager:
    @staticmethod
    def get_matching_shift(current_time_obj):
        """
        Tìm ca làm việc phù hợp với giờ hiện tại.
        Logic: Giờ hiện tại nằm trong khoảng [Start - 30p, End]
        """
        # current_time_str = current_time_obj.strftime("%H:%M:%S")
        all_shifts = Shift.query.all()
        
        # Get just the time component for comparison
        now = current_time_obj.time()
        
        for shift in all_shifts:
            # Chuyển string DB thành object time để so sánh
            # DB format expected: "HH:MM:SS"
            try:
                shift_start = datetime.strptime(shift.start_time, "%H:%M:%S").time()
                shift_end = datetime.strptime(shift.end_time, "%H:%M:%S").time()
                
                # Check buffer period (30 mins before)
                # Need to do date math, so use a dummy date
                dummy_date = datetime(2000, 1, 1) # Arbitrary date
                start_dt = dummy_date.replace(hour=shift_start.hour, minute=shift_start.minute, second=shift_start.second)
                end_dt = dummy_date.replace(hour=shift_end.hour, minute=shift_end.minute, second=shift_end.second)
                
                start_buffer_dt = start_dt - timedelta(minutes=30)
                
                # Convert current time to dummy date for comparison
                now_dt = dummy_date.replace(hour=now.hour, minute=now.minute, second=now.second)

                # Logic: Is now within [Start - 30, End]?
                if start_buffer_dt <= now_dt <= end_dt:
                    return shift
            except ValueError:
                # Handle cases where time format in DB might be wrong
                continue
                 
        return None # Không thuộc ca nào -> OT

    @staticmethod
    def calculate_status(checkin_time, shift):
        """Xác định Đúng giờ hay Đi muộn"""
        if not shift:
            return AttendanceStatus.OVERTIME
            
        try:
            shift_start = datetime.strptime(shift.start_time, "%H:%M:%S")
            # Ghép ngày hiện tại vào giờ của Shift để so sánh
            shift_start_dt = checkin_time.replace(hour=shift_start.hour, minute=shift_start.minute, second=start.second if hasattr(shift_start, 'second') else 0)
            
            # Use strict HH:MM:SS parsing from above, so shift_start has all components.
            # But just to be safe with replace logic:
            shift_start_dt = checkin_time.replace(
                hour=shift_start.hour, 
                minute=shift_start.minute, 
                second=shift_start.second, 
                microsecond=0
            )
            
            # Thêm thời gian ân hạn (Grace Period)
            allowed_late_time = shift_start_dt + timedelta(minutes=shift.grace_period_minutes)
            
            if checkin_time > allowed_late_time:
                return AttendanceStatus.LATE
            else:
                return AttendanceStatus.ON_TIME
        except Exception as e:
            print(f"Error calculating status: {e}")
            return AttendanceStatus.ON_TIME # Fallback logic
