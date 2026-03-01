from datetime import datetime
from models.db_models import db, User, Attendance, AttendanceStatus, Payroll

class SalaryManager:
    """
    Quản lý tính lương tự động cho nhân viên
    """
    
    # Constants - Có thể override từ frontend
    DEFAULT_PENALTY_PER_LATE = 50000  # 50k/lần muộn
    WORKDAYS_PER_MONTH = 26  # Công chuẩn/tháng
    BONUS_THRESHOLD_DAYS = 300  # Ngưỡng thưởng: > 300 ngày/năm
    BONUS_AMOUNT = 5000000  # 5 triệu
    
    @staticmethod
    def calculate_salary_for_user(user_id, month, year):
        """
        Tính lương cho 1 nhân viên trong tháng (chưa lưu vào DB)
        
        Args:
            user_id: ID nhân viên
            month: Tháng (1-12)
            year: Năm (VD: 2026)
        
        Returns:
            dict với các thông tin lương, hoặc None nếu user không tồn tại
        """
        user = User.query.get(user_id)
        if not user:
            return None
        
        # Xác định khoảng thời gian của tháng
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        # Query attendance trong tháng
        attendances = Attendance.query.filter(
            Attendance.user_id == user_id,
            Attendance.checkin_time >= start_date,
            Attendance.checkin_time < end_date
        ).all()
        
        # Đếm số công (ON_TIME + ON_LEAVE)
        total_workdays = len([
            a for a in attendances 
            if a.status in [AttendanceStatus.ON_TIME, AttendanceStatus.ON_LEAVE]
        ])
        
        # Đếm số lần đi muộn
        late_count = len([
            a for a in attendances 
            if a.status == AttendanceStatus.LATE
        ])
        
        # Tính số ngày làm việc trong năm để check bonus
        year_start = datetime(year, 1, 1)
        year_end = datetime(year, 12, 31, 23, 59, 59)
        year_attendances = Attendance.query.filter(
            Attendance.user_id == user_id,
            Attendance.checkin_time >= year_start,
            Attendance.checkin_time <= year_end,
            Attendance.status.in_([AttendanceStatus.ON_TIME, AttendanceStatus.ON_LEAVE])
        ).count()
        
        # Tính bonus tự động
        auto_bonus = SalaryManager.BONUS_AMOUNT if year_attendances > SalaryManager.BONUS_THRESHOLD_DAYS else 0.0
        
        # Tính lương
        base_salary = user.base_salary or 0.0
        gross_salary = (base_salary / SalaryManager.WORKDAYS_PER_MONTH) * total_workdays
        total_penalty = late_count * SalaryManager.DEFAULT_PENALTY_PER_LATE
        net_salary = gross_salary - total_penalty + auto_bonus
        
        return {
            "user_id": user.id,
            "user_name": user.name,
            "username": user.username,
            "month": month,
            "year": year,
            
            # Thông số đầu vào (có thể override từ FE)
            "base_salary": base_salary,
            "total_workdays": total_workdays,
            "late_count": late_count,
            "penalty_per_late": SalaryManager.DEFAULT_PENALTY_PER_LATE,
            "bonus": auto_bonus,
            "year_workdays": year_attendances,  # Để FE hiển thị
            
            # Kết quả tính toán
            "gross_salary": round(gross_salary, 2),
            "total_penalty": total_penalty,
            "net_salary": round(net_salary, 2)
        }
    
    @staticmethod
    def calculate_salary_for_all(month, year):
        """
        Tính lương cho TẤT CẢ nhân viên trong tháng
        
        Returns:
            List[dict] - Danh sách lương của tất cả nhân viên
        """
        users = User.query.all()
        results = []
        
        for user in users:
            salary_data = SalaryManager.calculate_salary_for_user(user.id, month, year)
            if salary_data:
                results.append(salary_data)
        
        return results
    
    @staticmethod
    def confirm_payroll(payroll_data, confirmed_by_user_id):
        """
        Confirm và lưu lương vào bảng Payroll
        
        Args:
            payroll_data: dict chứa thông tin lương (có thể đã được override từ FE)
            confirmed_by_user_id: ID của admin confirm
        
        Returns:
            (success: bool, message: str, payroll_id: int or None)
        """
        user_id = payroll_data.get('user_id')
        month = payroll_data.get('month')
        year = payroll_data.get('year')
        
        # Validate
        if not user_id or not month or not year:
            return False, "Thiếu thông tin bắt buộc (user_id, month, year)", None
        
        user = User.query.get(user_id)
        if not user:
            return False, "Nhân viên không tồn tại", None
        
        # Kiểm tra đã tồn tại chưa
        existing = Payroll.query.filter_by(
            user_id=user_id,
            month=month,
            year=year
        ).first()
        
        if existing:
            return False, f"Lương tháng {month}/{year} của nhân viên này đã được confirm", None
        
        # Lấy các giá trị từ payroll_data (đã có thể được override từ FE)
        base_salary = payroll_data.get('base_salary', 0.0)
        total_workdays = payroll_data.get('total_workdays', 0)
        late_count = payroll_data.get('late_count', 0)
        penalty_per_late = payroll_data.get('penalty_per_late', SalaryManager.DEFAULT_PENALTY_PER_LATE)
        bonus = payroll_data.get('bonus', 0.0)
        
        # Tính lại kết quả (để đảm bảo consistency)
        gross_salary = (base_salary / SalaryManager.WORKDAYS_PER_MONTH) * total_workdays
        total_penalty = late_count * penalty_per_late
        net_salary = gross_salary - total_penalty + bonus
        
        # Tạo Payroll record
        new_payroll = Payroll(
            user_id=user_id,
            month=month,
            year=year,
            base_salary=base_salary,
            total_workdays=total_workdays,
            late_count=late_count,
            penalty_per_late=penalty_per_late,
            bonus=bonus,
            gross_salary=round(gross_salary, 2),
            total_penalty=total_penalty,
            net_salary=round(net_salary, 2),
            confirmed_by=confirmed_by_user_id,
            notes=payroll_data.get('notes', '')
        )
        
        try:
            db.session.add(new_payroll)
            db.session.commit()
            return True, "Đã confirm và lưu lương thành công", new_payroll.id
        except Exception as e:
            db.session.rollback()
            return False, f"Lỗi lưu database: {str(e)}", None
    
    @staticmethod
    def get_payroll_history(user_id=None, month=None, year=None):
        """
        Lấy lịch sử lương đã confirm
        
        Args:
            user_id: Lọc theo user (None = tất cả)
            month: Lọc theo tháng (None = tất cả)
            year: Lọc theo năm (None = tất cả)
        
        Returns:
            List[dict] - Danh sách lương đã confirm
        """
        query = Payroll.query
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        if month:
            query = query.filter_by(month=month)
        if year:
            query = query.filter_by(year=year)
        
        payrolls = query.order_by(Payroll.year.desc(), Payroll.month.desc()).all()
        
        return [p.to_dict() for p in payrolls]
