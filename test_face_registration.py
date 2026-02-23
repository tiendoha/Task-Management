import cv2
import requests
import base64
import json
import time
import numpy as np
import mediapipe as mp

# Configuration
BASE_URL = "http://localhost:5000"
API_URL = f"{BASE_URL}/api/face-setup/analyze"
FINISH_URL = f"{BASE_URL}/api/face-setup/finish"
LOGIN_URL = f"{BASE_URL}/api/auth/login"
USER_ID = 1  # Change this to valid user ID in your DB

# Credentials
USERNAME = "admin"
PASSWORD = "Admin@123"

# --- MEDIA PIPE SETUP ---
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,  # Tăng độ chính xác mắt/miệng
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils
drawing_spec = mp_drawing.DrawingSpec(thickness=1, circle_radius=1)

# Improved 3D model points (generic adult head, scale phù hợp MediaPipe z ~0.01-0.05)
model_points = np.array([
    (0.0, 0.0, 0.0),          # Nose tip (landmark 1)
    (0.0, -330.0, -100.0),    # Chin (152)
    (0.0, 330.0, -100.0),     # Forehead top approx (10 or 151)
    (-165.0, 170.0, -135.0),  # Left temple (234)
    (165.0, 170.0, -135.0),   # Right temple (454)
    (-225.0, 170.0, -135.0),  # Left eye outer (33)
    (225.0, 170.0, -135.0),   # Right eye outer (263)
    (-150.0, 150.0, -125.0),  # Left eye inner approx (133)
    (150.0, 150.0, -125.0),   # Right eye inner (362)
    (-150.0, -150.0, -125.0), # Left mouth corner (61)
    (150.0, -150.0, -125.0)   # Right mouth corner (291)
], dtype="double")

# Indices tương ứng với model_points
landmark_indices = [1, 152, 10, 234, 454, 33, 263, 133, 362, 61, 291]

# Biến lưu cho smoothing (EMA)
prev_yaw = 0.0
prev_pitch = 0.0
alpha = 0.7  # 0.0 = no smooth, 1.0 = full previous

def login():
    try:
        print(f"Logging in as {USERNAME}...")
        response = requests.post(LOGIN_URL, json={"username": USERNAME, "password": PASSWORD})
        data = response.json()
        if data.get("success"):
            print(">>> Login Successful!")
            return data.get("token")
        else:
            print(">>> Login Failed:", data.get("message"))
            return None
    except Exception as e:
        print("Login Error:", e)
        return None

def analyze_pose_local(image):
    global prev_yaw, prev_pitch

    img_h, img_w, _ = image.shape
    img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(img_rgb)
    
    status = "center"
    yaw = 0.0
    pitch = 0.0
    roll = 0.0
    landmarks_detected = False

    if results.multi_face_landmarks:
        landmarks_detected = True
        face_landmarks = results.multi_face_landmarks[0]
        
        image_points = []
        for idx in landmark_indices:
            lm = face_landmarks.landmark[idx]
            x = lm.x * img_w
            y = lm.y * img_h
            image_points.append([x, y])
        image_points = np.array(image_points, dtype="double")

        focal_length = img_w * 1.0
        center = (img_w / 2.0, img_h / 2.0)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype="double")
        dist_coeffs = np.zeros((4, 1), dtype="double")
        
        success, rotation_vector, translation_vector = cv2.solvePnP(
            model_points, image_points, camera_matrix, dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )
        
        if success:

            # Convert Rotation Vector to Rotation Matrix
            rmat, _ = cv2.Rodrigues(rotation_vector)
            
            # Combine to Projection Matrix [R|t]
            proj_matrix = np.hstack((rmat, translation_vector))
            
            # Decompose to get Euler Angles
            _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(proj_matrix)
            pitch, yaw, roll = euler_angles.flatten()  # now this works correctly (3 items)
            
            # Smoothing EMA
            yaw   = alpha * yaw   + (1 - alpha) * prev_yaw
            pitch = alpha * pitch + (1 - alpha) * prev_pitch
            prev_yaw, prev_pitch = yaw, pitch

            # Vẽ vector mũi
            nose_3d = np.array([(0.0, 0.0, 1000.0)], dtype="double")
            nose_2d_proj, _ = cv2.projectPoints(nose_3d, rotation_vector, translation_vector,
                                                camera_matrix, dist_coeffs)
            p1 = (int(image_points[0][0]), int(image_points[0][1]))
            p2 = (int(nose_2d_proj[0][0][0]), int(nose_2d_proj[0][0][1]))
            cv2.line(image, p1, p2, (0, 255, 0), 3)

            if yaw > 12:
                status = "right"
            elif yaw < -12:
                status = "left"
            else:
                status = "center"

            # Debug
            cv2.putText(image, f"Yaw: {yaw:.1f}°", (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
            cv2.putText(image, f"Pitch: {pitch:.1f}°", (20, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
            cv2.putText(image, f"Roll: {roll:.1f}°", (20, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 2)

    return image, status, yaw, landmarks_detected
    
def capture_and_send(step, token):
    global prev_yaw, prev_pitch
    prev_yaw = 0.0
    prev_pitch = 0.0  # Reset smooth mỗi step mới

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open webcam 0. Trying 1...")
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print("Cannot open any webcam.")
            return None

    print(f"--- Step: {step.upper()} ---")
    print("Press 's' to capture and send, 'q' to quit this step.")
    
    headers = {"Authorization": f"Bearer {token}"}

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        preview_frame = frame.copy()
        preview_frame, detected_pose, yaw, has_face = analyze_pose_local(preview_frame)
        
        color = (0, 0, 255)  # Red
        if detected_pose == step:
            color = (0, 255, 0)  # Green
            
        cv2.putText(preview_frame, f"Target: {step.upper()}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 0), 3)
        cv2.putText(preview_frame, f"Detected: {detected_pose.upper()} (Yaw: {yaw:.1f}°)", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        if not has_face:
            cv2.putText(preview_frame, "NO FACE DETECTED", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

        cv2.imshow(f'Capture for {step}', preview_frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('s'):
            # Send RAW frame (không có overlay)
            _, buffer = cv2.imencode('.jpg', frame)
            img_str = base64.b64encode(buffer).decode('utf-8')
            
            payload = {
                "image": "data:image/jpeg;base64," + img_str,
                "current_step": step
            }
            
            try:
                print(f"Sending request for {step}...")
                response = requests.post(API_URL, json=payload, headers=headers)
                try:
                    data = response.json()
                except Exception as json_err:
                    print(f"Error parsing JSON! HTTP {response.status_code}")
                    print(f"Server Response: {response.text}")
                    cv2.putText(preview_frame, "SERVER ERROR", (20, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                    cv2.imshow(f'Capture for {step}', preview_frame)
                    cv2.waitKey(1000)
                    continue

                print(data)
                if data.get("success"):
                    print(">>> SUCCESS!")
                    cap.release()
                    cv2.destroyAllWindows()
                    return data.get("embedding")
                else:
                    print(">>> FAILED:", data.get("message"))
            except Exception as e:
                print("Error:", e)
        
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    return None

def main():
    print("Starting Face Registration Test Client...")
    
    token = login()
    if not token:
        print("Cannot proceed without token.")
        return
    
    embeddings = []
    
    # 1. Center
    emb = capture_and_send("center", token)
    if emb: embeddings.append(emb)
    else: return

    # 2. Left
    emb = capture_and_send("left", token)
    if emb: embeddings.append(emb)
    else: return

    # 3. Right
    emb = capture_and_send("right", token)
    if emb: embeddings.append(emb)
    else: return
    
    print("\n--- All steps done. Finishing registration... ---")
    payload = {
        "user_id": USER_ID,
        "embeddings": embeddings
    }
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(FINISH_URL, json=payload, headers=headers)
        print("Finish Response:", json.dumps(response.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print("Error finishing:", e)

if __name__ == "__main__":
    main()