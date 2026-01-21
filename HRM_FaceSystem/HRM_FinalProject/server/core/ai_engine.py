import cv2
import numpy as np
import base64
from deepface import DeepFace

# CẤU HÌNH MODEL (State-of-the-Art)
MODEL_NAME = "ArcFace"
DETECTOR_BACKEND = "opencv"
THRESHOLD = 0.68

class AIEngine:
    @staticmethod
    def base64_to_image(base64_string):
        if "base64," in base64_string:
            base64_string = base64_string.split(",")[1]
        image_bytes = base64.b64decode(base64_string)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return image

    @staticmethod
    def extract_embedding(image_input):
        try:
            # DeepFace.represent trả về list các vector 512 chiều
            results = DeepFace.represent(
                img_path=image_input,
                model_name=MODEL_NAME,
                enforce_detection=False,
                detector_backend=DETECTOR_BACKEND
            )
            if results:
                return results[0]["embedding"]
            return None
        except Exception as e:
            print(f"[AI-Error] Extract Embedding Failed: {e}")
            return None

    @staticmethod
    def find_match(input_embedding, all_users):
        best_match = None
        min_distance = float("inf")
        target_emb = np.array(input_embedding)

        for user in all_users:
            if not user.face_encoding:
                continue
            
            # Chuyển dữ liệu từ DB (đang lưu List/JSON) sang Numpy Array
            db_emb = np.array(user.face_encoding)

            # Tính Cosine Distance
            dot_product = np.dot(target_emb, db_emb)
            norm_target = np.linalg.norm(target_emb)
            norm_db = np.linalg.norm(db_emb)

            if norm_target == 0 or norm_db == 0:
                distance = 1.0
            else:
                distance = 1 - (dot_product / (norm_target * norm_db))

            if distance < min_distance:
                min_distance = distance
                best_match = user

        if min_distance < THRESHOLD:
            return best_match, min_distance
        return None, min_distance