from models.db_models import db, User, Attendance, Payroll, AttendanceStatus
from sqlalchemy import extract
from datetime import datetime

class SalaryManager:
    @staticmethod
    def calculate_monthly_payroll(month, year):

        STANDARD_WORKING_DAYS = 26.0
        MINUTES_IN_WORKDAY = 8.0 * 60.0

        now = datetime.now()

        # Lấy tất cả user đang active và không phải admin
        users = User.query.filter(
            User.is_active == True,
            User.username != "admin"
        ).all()

        results = []

        for user in users:

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

                if att.status in [AttendanceStatus.PRESENT, AttendanceStatus.ON_LEAVE]:
                    total_working_days += 1.0

                total_late_minutes += att.late_minutes
                total_early_minutes += att.early_leave_minutes
                total_overtime_minutes += att.overtime_minutes

            base_salary = user.base_salary or 0.0
            daily_salary = base_salary / STANDARD_WORKING_DAYS

            minute_penalty = daily_salary / MINUTES_IN_WORKDAY
            deductions = minute_penalty * (total_late_minutes + total_early_minutes)

            ot_bonus_per_minute = minute_penalty * 1.5
            overtime_bonus = total_overtime_minutes * ot_bonus_per_minute

            net_salary = (daily_salary * total_working_days) - deductions + overtime_bonus
            net_salary = max(0.0, net_salary)

            payroll = Payroll.query.filter_by(
                user_id=user.id,
                month=month,
                year=year
            ).first()

            # Nếu đã trả lương thì bỏ qua
            if payroll and payroll.is_paid:
                continue

            # Nếu tháng cũ và chưa có payroll thì KHÔNG tạo mới
            if not payroll and (month != now.month or year != now.year):
                continue

            # Nếu chưa có payroll và là tháng hiện tại → tạo mới
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

            return {
                "success": True,
                "message": f"Tính lương tháng {month}/{year} hoàn tất.",
                "data": results
            }

        except Exception as e:
            db.session.rollback()

            return {
                "success": False,
                "message": f"Lỗi DB khi tính lương: {str(e)}"
            }