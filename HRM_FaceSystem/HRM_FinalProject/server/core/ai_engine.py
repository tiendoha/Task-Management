import face_recognition
import cv2
import numpy as np
from scipy.spatial import distance as dist

class AIEngine:
    def __init__(self):
        self.TOLERANCE = 0.5
        self.EYE_AR_THRESH = 0.20 # Ngưỡng mở mắt (dưới 0.2 là nhắm/giả mạo)

    # Hàm tính tỉ lệ mở mắt
    def eye_aspect_ratio(self, eye):
        # Tính khoảng cách dọc (mí trên - mí dưới)
        A = dist.euclidean(eye[1], eye[5])
        B = dist.euclidean(eye[2], eye[4])
        # Tính khoảng cách ngang (góc mắt)
        C = dist.euclidean(eye[0], eye[3])
        # Công thức EAR
        ear = (A + B) / (2.0 * C)
        return ear

    def process_image(self, image_np, known_encodings, known_ids):
        # 1. Xử lý ảnh
        small_frame = cv2.resize(image_np, (0, 0), fx=0.5, fy=0.5)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # 2. Tìm vị trí khuôn mặt
        face_locations = face_recognition.face_locations(rgb_small_frame)
        if not face_locations:
            return None, False, "Không tìm thấy khuôn mặt"

        # 3. KIỂM TRA LIVENESS (Mắt mở hay nhắm?)
        # Lấy 68 điểm đặc trưng trên mặt
        face_landmarks_list = face_recognition.face_landmarks(rgb_small_frame, face_locations)
        is_real = True # Mặc định tạm tin là thật
        
        if face_landmarks_list:
            for face_landmark in face_landmarks_list:
                leftEye = face_landmark['left_eye']
                rightEye = face_landmark['right_eye']
                
                leftEAR = self.eye_aspect_ratio(leftEye)
                rightEAR = self.eye_aspect_ratio(rightEye)
                
                # Trung bình 2 mắt
                avgEAR = (leftEAR + rightEAR) / 2.0
                
                # Nếu mắt nhắm quá kỹ hoặc không rõ ràng -> Nghi ngờ giả mạo
                if avgEAR < self.EYE_AR_THRESH:
                    is_real = False

        # 4. Nhận diện danh tính
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        found_id = None
        
        for face_encoding in face_encodings:
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            
            if face_distances[best_match_index] < self.TOLERANCE:
                found_id = known_ids[best_match_index]
                break 

        return found_id, is_real, "Success"