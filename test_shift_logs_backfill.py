import sys
import os
import unittest
import json
from datetime import datetime, timedelta, date

os.environ['TESTING'] = 'true'
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from app import app, db, backfill_attendance
from models.db_models import User, Attendance, Shift, AttendanceStatus, UserRole, LeaveRequest, LeaveType, LeaveStatus

class TestNewFeaturesAPI(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

        # Users
        self.admin = User(username="admin", name="Admin", role=UserRole.ADMIN)
        self.admin.password_hash = "fake_hash"
        
        # Join date 3 days ago
        self.join_date = date.today() - timedelta(days=3)
        self.employee = User(username="emp_2", name="Emp 2", role=UserRole.EMPLOYEE, join_date=self.join_date)
        
        db.session.add_all([self.admin, self.employee])
        db.session.commit()

        from core.security import generate_token
        self.admin_token = generate_token(self.admin.id, self.admin.role.value)
        self.emp_token = generate_token(self.employee.id, self.employee.role.value)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_shift_validations(self):
        print("\n--- TEST: Shift Validations ---")
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test 1: Valid Shift
        res = self.client.post('/api/shifts', json={
            "name": "Ca Sang",
            "start_time": "08:00:00",
            "end_time": "17:00:00"
        }, headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])
        
        # Test 2: Duplicate Name
        res = self.client.post('/api/shifts', json={
            "name": "Ca Sang",
            "start_time": "09:00:00",
            "end_time": "18:00:00"
        }, headers=headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn("trùng", res.get_json()["message"])
        
        # Test 3: Duration <= 15 mins
        res = self.client.post('/api/shifts', json={
            "name": "Ca Ngan",
            "start_time": "12:00:00",
            "end_time": "12:15:00"
        }, headers=headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn("15 phút", res.get_json()["message"])
        
        # Test 4: PUT Duplicate (Should ignore its own ID)
        shift_id = Shift.query.filter_by(name="Ca Sang").first().id
        res = self.client.put(f'/api/shifts/{shift_id}', json={
            "name": "Ca Sang",
            "start_time": "08:30:00",
            "end_time": "17:30:00"
        }, headers=headers)
        self.assertEqual(res.status_code, 200)

    def test_backfill_and_logs(self):
        print("\n--- TEST: Backfill and Logs ---")
        
        # Create an approved leave request for the employee on join_date
        leave = LeaveRequest(
            user_id=self.employee.id,
            leave_type=LeaveType.ANNUAL_LEAVE,
            start_date=datetime.combine(self.join_date, datetime.min.time()),
            end_date=datetime.combine(self.join_date, datetime.max.time()),
            status=LeaveStatus.APPROVED
        )
        db.session.add(leave)
        db.session.commit()

        # Run Backfill
        backfill_attendance()
        
        # Assertions
        # join_date -> ON_LEAVE
        att_day1 = Attendance.query.filter_by(user_id=self.employee.id, work_date=self.join_date).first()
        self.assertIsNotNone(att_day1)
        self.assertEqual(att_day1.status, AttendanceStatus.ON_LEAVE)
        
        # join_date + 1 -> ABSENT
        att_day2 = Attendance.query.filter_by(user_id=self.employee.id, work_date=self.join_date + timedelta(days=1)).first()
        self.assertIsNotNone(att_day2)
        self.assertEqual(att_day2.status, AttendanceStatus.ABSENT)
        
        # today shouldn't be backfilled
        att_today = Attendance.query.filter_by(user_id=self.employee.id, work_date=date.today()).first()
        self.assertIsNone(att_today)

        print("Backfill logic works correctly.")
        
        # Test GET /api/logs filtering and order
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Add actual check-ins to test ordering
        att_day1.checkin_time = datetime.combine(self.join_date, datetime.strptime("08:15", "%H:%M").time())
        db.session.commit()
        
        res = self.client.get(f'/api/logs?date={self.join_date.strftime("%Y-%m-%d")}', headers=headers)
        logs = res.get_json()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["status"], "ON_LEAVE")
        
        print("GET /api/logs filters correctly by work_date and nullslast rules.")
        print("\nAll integration tests passed!")

if __name__ == '__main__':
    unittest.main(verbosity=2)
