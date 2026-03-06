import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import os
import sys

# Force the app to use an in-memory database for testing so we don't pollute the real one
os.environ['TESTING'] = 'true'
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from app import app, db
from models.db_models import User, Shift, Attendance, UserRole, AttendanceStatus

# Create a mock datetime class to control time
class MockDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls._current_time

class TestAttendanceLogic(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

        # Create Shifts
        self.day_shift = Shift(name="Ca Ngay", start_time="08:00:00", end_time="17:00:00", grace_period_minutes=15)
        self.night_shift = Shift(name="Ca Dem", start_time="22:00:00", end_time="06:00:00", grace_period_minutes=15)
        db.session.add_all([self.day_shift, self.night_shift])
        
        # Create User
        self.user = User(username="testuser", role=UserRole.EMPLOYEE, name="Test User", face_encoding=b'fake', is_active=True)
        db.session.add(self.user)
        db.session.commit()

        # Mock AIEngine to bypass face recognition
        self.patcher1 = patch('app.AIEngine.base64_to_image', return_value="fake_img")
        self.patcher2 = patch('app.AIEngine.get_embedding', return_value=([0.1], "OK"))
        self.patcher3 = patch('app.AIEngine.find_match', return_value=(self.user, 0.0))
        self.patcher1.start()
        self.patcher2.start()
        self.patcher3.start()

    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        self.patcher3.stop()
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        
    def do_checkin(self):
        return self.client.post('/api/checkin', json={"image": "dummy_base64_string"})

    @patch('app.datetime', MockDatetime)
    @patch('core.shift_manager.datetime', MockDatetime)
    def test_day_shift_late_and_early_leave(self):
        print("\n--- TEST: Day Shift (Late In, Early Out) ---")
        # 1. Simulate check-in at 08:20 (20 mins late, grace is 15 so it's strictly > start + grace)
        # Wait, the rule is checkin > shift_start + grace -> late minutes = checkin - shift_start
        # 08:20 - 08:00 = 20 mins late.
        MockDatetime._current_time = datetime(2026, 3, 6, 8, 20, 0)
        
        res = self.do_checkin()
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['type'], 'CHECK_IN')
        
        att = Attendance.query.first()
        self.assertIsNotNone(att)
        self.assertEqual(att.work_date, datetime(2026, 3, 6).date())
        self.assertEqual(att.late_minutes, 20)
        self.assertEqual(att.status, AttendanceStatus.PRESENT)
        print(f"Check-in at 08:20: Late = {att.late_minutes}m")

        # Simulate time passing to bypass 60s cooldown
        MockDatetime._current_time = datetime(2026, 3, 6, 16, 50, 0) # 10 mins early
        
        res = self.do_checkin()
        data = res.get_json()
        self.assertEqual(data['type'], 'CHECK_OUT')
        
        att = Attendance.query.first()
        self.assertEqual(att.early_leave_minutes, 10)
        self.assertEqual(att.overtime_minutes, 0)
        print(f"Check-out at 16:50: Early leave = {att.early_leave_minutes}m")

    @patch('app.datetime', MockDatetime)
    @patch('core.shift_manager.datetime', MockDatetime)
    def test_night_shift_overtime(self):
        print("\n--- TEST: Night Shift (22:00 - 06:00, Overtime) ---")
        # 1. Sim check-in at 21:55
        MockDatetime._current_time = datetime(2026, 3, 6, 21, 55, 0)
        res = self.do_checkin()
        
        att = Attendance.query.first()
        self.assertEqual(att.work_date, datetime(2026, 3, 6).date())
        self.assertEqual(att.late_minutes, 0)
        print(f"Check-in at 21:55: Late = {att.late_minutes}m, Work Date = {att.work_date}")

        # 2. Sim check-out at 06:30 the NEXT day (30 mins overtime)
        MockDatetime._current_time = datetime(2026, 3, 7, 6, 30, 0)
        res = self.do_checkin()
        print("Checkout JSON Response:", res.get_json())
        
        all_atts = Attendance.query.all()
        print("All Attendances in DB:")
        for a in all_atts:
            print(f"ID={a.id}, User={a.user_id}, Date={a.work_date}, In={a.checkin_time}, Out={a.checkout_time}, OT={a.overtime_minutes}")
            
        att = Attendance.query.first()
        self.assertEqual(att.early_leave_minutes, 0)
        self.assertEqual(att.overtime_minutes, 30)
        # Verify it mapped back to the correct work_date (Mar 6)
        self.assertEqual(att.work_date, datetime(2026, 3, 6).date())
        print(f"Check-out at 06:30 (next day): Overtime = {att.overtime_minutes}m, Work Date = {att.work_date}")

if __name__ == '__main__':
    unittest.main(verbosity=2)
