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
            try:
                shift_start = datetime.strptime(shift.start_time, "%H:%M:%S").time()
                shift_end = datetime.strptime(shift.end_time, "%H:%M:%S").time()
                
                # Retrieve literal current date bounds
                base_date = current_time_obj.date()
                start_dt = datetime.combine(base_date, shift_start)
                end_dt = datetime.combine(base_date, shift_end)
                
                if shift_end <= shift_start:
                    # Night shift definition (e.g., 22:00 - 06:00)
                    # Nếu giờ hiện tại < 12h trưa, ngầm hiểu là Ca đêm của ngày hôm qua vắt sang
                    if current_time_obj.time() < datetime.strptime("12:00:00", "%H:%M:%S").time():
                        start_dt -= timedelta(days=1)
                    else:
                        end_dt += timedelta(days=1)
                
                start_buffer_dt = start_dt - timedelta(minutes=60) # Tới sớm 1 tiếng
                end_buffer_dt = end_dt + timedelta(minutes=60)     # Quẹt trễ lúc về 1 tiếng
                
                if start_buffer_dt <= current_time_obj <= end_buffer_dt:
                    return shift
            except ValueError:
                continue
                 
        return None

    @staticmethod
    def calculate_status(checkin_time, shift):
        """Xác định Đúng giờ hay Đi muộn"""
        if not shift:
            return AttendanceStatus.OVERTIME
            
        try:
            shift_start = datetime.strptime(shift.start_time, "%H:%M:%S")
            shift_start_dt = checkin_time.replace(
                hour=shift_start.hour, 
                minute=shift_start.minute, 
                second=shift_start.second, 
                microsecond=0
            )
            
            start_window = shift_start_dt - timedelta(minutes=15)
            
            if start_window <= checkin_time <= shift_start_dt:
                return AttendanceStatus.ON_TIME
            elif checkin_time > shift_start_dt:
                return AttendanceStatus.LATE
            else:
                return AttendanceStatus.ON_TIME # Fallback if checking in way too early
                
        except Exception as e:
            print(f"Error calculating status: {e}")
            return AttendanceStatus.ON_TIME # Fallback logic
