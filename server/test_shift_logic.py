import requests
import unittest
from unittest.mock import patch, MagicMock
from app import app, db
from models.db_models import User, Shift, Attendance, UserRole, AttendanceStatus
from datetime import datetime, timedelta
import json

class TestShiftManagement(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            print(f"DEBUG: URI is {app.config['SQLALCHEMY_DATABASE_URI']}")
            db.drop_all() # Ensure clean state
            db.create_all()
            
            # Create Admin manually for auth tests
            from werkzeug.security import generate_password_hash
            # Use 'User' model
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin', role=UserRole.ADMIN, name='Administrator')
                admin.password = generate_password_hash('Admin@123')
                db.session.add(admin)
                db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    # ... existing get_admin_token ...
    def get_admin_token(self):
        res = self.app.post('/api/auth/login', json={
            "username": "admin",
            "password": "Admin@123"
        })
        if res.status_code != 200:
             print(f"Login failed: {res.json}")
        return res.json.get('token')

    # ... existing test_shift_crud ...
    def test_shift_crud(self):
        token = self.get_admin_token()
        headers = {'Authorization': f'Bearer {token}'}

        # 1. Create Shift
        res = self.app.post('/api/shifts', json={
            "name": "Test Shift",
            "start_time": "08:00:00",
            "end_time": "17:00:00",
            "grace_period_minutes": 10
        }, headers=headers) 
        self.assertEqual(res.status_code, 200)
        shift_id = res.json['shift']['id']

        # 2. Get Shifts
        res = self.app.get('/api/shifts')
        data = res.json
        self.assertTrue(any(s['name'] == "Test Shift" for s in data))

        # 3. Update Shift (Protected)
        res = self.app.put(f'/api/shifts/{shift_id}', json={
            "name": "Updated Shift",
            "grace_period_minutes": 20
        }, headers=headers)
        self.assertEqual(res.status_code, 200)

        # Verify Update
        res = self.app.get('/api/shifts')
        updated_shift = next(s for s in res.json if s['id'] == shift_id)
        self.assertEqual(updated_shift['name'], "Updated Shift")
        self.assertEqual(updated_shift['grace_period_minutes'], 20)

    @patch('server.app.base64_to_image')
    @patch('core.ai_engine.AIEngine.extract_embedding')
    @patch('core.ai_engine.AIEngine.find_match')
    def test_checkin_logic(self, mock_find, mock_extract, mock_b64):
        # Mock base64_to_image to return a dummy image (not None)
        mock_b64.return_value = "dummy_image_object"

        # Setup: Create Shift and User
        with app.app_context():
            s = Shift(name="Morning", start_time="08:00:00", end_time="12:00:00")
            db.session.add(s)
            
            u = User(username="user1", name="User One", role=UserRole.EMPLOYEE)
            u.face_encoding = [0.1] * 128 
            u.shift = s
            db.session.add(u)
            db.session.commit()
            user_id = u.id

        # Mock AI
        mock_extract.return_value = [0.1] * 128
        
        # find_match logic in app.py:
        # matched_user, distance = ai_engine.find_match(...)
        # We need mock_find to return (UserObject, distance)
        # BUT UserObject implies one attached to session? 
        # Since we use scoped session, if we pass a user object created in 'setUp' inside 'test_checkin_logic' context?
        # Ideally, mock_find side_effect should query the DB to get the user, to mimic reality.
        
        def side_effect_find(emb, users):
            # Query db inside the running request context? 
            # 'users' arg is passed from app.py: users = User.query.all()
            # So 'users' contains real DB objects.
            # We just need to find "User One" from that list.
            found = next((u for u in users if u.name == "User One"), None)
            return found, 0.0

        mock_find.side_effect = side_effect_find

        # 1. Test Check-in (On Time)
        with patch('server.app.datetime') as mock_dt:
             params = {
                 'year': 2024, 'month': 1, 'day': 1, 
                 'hour': 8, 'minute': 5, 'second': 0
             }
             mock_now = datetime(**params)
             mock_dt.now.return_value = mock_now
             # Need side_effect for strptime because app.py calls it strictly
             mock_dt.strptime.side_effect = datetime.strptime

             res = self.app.post('/api/checkin', json={"image": "data:image/png;base64,dummy"})
             
             if res.status_code != 200:
                 print(f"Checkin failed: {res.json}")
                 
             self.assertEqual(res.status_code, 200)
             self.assertEqual(res.json['type'], 'CHECK_IN')
             self.assertEqual(res.json['status'], 'Đúng giờ')

        # 2. Test Check-in (Late) - Check-out logic
        # If we call again, it should be Check-out because previous step created Attendance.
        # But we need to ensure MORE than 60s has passed.
        # So we mock time to 08:20 (15 mins later).
        with patch('server.app.datetime') as mock_dt:
             params_late = {
                 'year': 2024, 'month': 1, 'day': 1, 
                 'hour': 8, 'minute': 20, 'second': 0
             }
             mock_now_late = datetime(**params_late)
             mock_dt.now.return_value = mock_now_late
             mock_dt.strptime.side_effect = datetime.strptime
             
             res = self.app.post('/api/checkin', json={"image": "data:image/png;base64,dummy"})
             self.assertEqual(res.status_code, 200)
             # Should be check-out
             self.assertEqual(res.json['type'], 'CHECK_OUT')

if __name__ == '__main__':
    unittest.main()
