from models.db_models import db, User, Attendance, Payroll, AttendanceStatus
from sqlalchemy import extract

class SalaryManager:
    @staticmethod
    def calculate_monthly_payroll(month, year):
        """
        Calculates and creates/updates Payroll entries for all ACTIVE employees
        for the given month and year based on their Attendance logs.
        """
        STANDARD_WORKING_DAYS = 26.0
        MINUTES_IN_WORKDAY = 8.0 * 60.0
        
        # Lấy tất cả user đang active
        users = User.query.filter_by(is_active=True).all()
        
        results = []
        for user in users:
            # Thu thập điểm danh trong tháng và năm
            attendances = Attendance.query.filter(
                Attendance.user_id == user.id,
                extract('month', Attendance.work_date) == month,
                extract('year', Attendance.work_date) == year
            ).all()
            
            total_working_days = 0.0
            total_late_minutes = 0
            total_early_minutes = 0
            total_overtime_minutes = 0
            
            for att in attendances:
                # Ngày công thực tế (PRESENT / ON_LEAVE được tính là 1 công)
                if att.status in [AttendanceStatus.PRESENT, AttendanceStatus.ON_LEAVE]:
                    total_working_days += 1.0
                    
                total_late_minutes += att.late_minutes
                total_early_minutes += att.early_leave_minutes
                total_overtime_minutes += att.overtime_minutes
            
            # Toán học tính lương
            base_salary = user.base_salary if user.base_salary else 0.0
            daily_salary = base_salary / STANDARD_WORKING_DAYS
            
            # Phạt đi muộn/về sớm
            minute_penalty = daily_salary / MINUTES_IN_WORKDAY
            deductions = minute_penalty * (total_late_minutes + total_early_minutes)
            
            # Tăng ca
            ot_bonus_per_minute = minute_penalty * 1.5
            overtime_bonus = total_overtime_minutes * ot_bonus_per_minute
            
            # Lương Net
            net_salary = (daily_salary * total_working_days) - deductions + overtime_bonus
            net_salary = max(0.0, net_salary) # Không được âm
            
            # Cập nhật hoặc lưu mới Payload vào DB
            payroll = Payroll.query.filter_by(user_id=user.id, month=month, year=year).first()
            if not payroll:
                payroll = Payroll(user_id=user.id, month=month, year=year)
                db.session.add(payroll)
                
            payroll.base_salary = base_salary
            payroll.total_working_days = total_working_days
            payroll.total_late_minutes = total_late_minutes
            payroll.total_early_minutes = total_early_minutes
            payroll.total_overtime_minutes = total_overtime_minutes
            payroll.deductions = deductions
            payroll.overtime_bonus = overtime_bonus
            payroll.net_salary = net_salary
            payroll.is_paid = False
            
            results.append({
                "user_id": user.id,
                "name": user.name,
                "net_salary": net_salary
            })
            
        try:
            db.session.commit()
            return {"success": True, "message": f"Chốt lương tháng {month}/{year} hoàn tất.", "data": results}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": f"Lỗi DB khi tính lương: {str(e)}"}
