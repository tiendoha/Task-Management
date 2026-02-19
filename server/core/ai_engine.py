import cv2
import numpy as np
import base64
from deepface import DeepFace
import mediapipe as mp

# config
MODEL = "ArcFace"
BACKEND = "opencv"
MATCH_THRESHOLD = 0.68

class AIEngine:
    @staticmethod
    def base64_to_img(b64_str):
        if "base64," in b64_str:
            b64_str = b64_str.split(",")[1]
        bytes_data = base64.b64decode(b64_str)
        nparr = np.frombuffer(bytes_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img

    @staticmethod
    def get_embedding(img):
        try:
            res = DeepFace.represent(
                img_path=img,
                model_name=MODEL,
                enforce_detection=False,
                detector_backend=BACKEND
            )
            if res:
                return res[0]["embedding"]
            return None
        except Exception as e:
            print(f"[emb error] {e}")
            return None

    @staticmethod
    def find_best_match(emb_input, users):
        if not emb_input:
            return None, 1.0

        target = np.array(emb_input)
        best_user = None
        min_dist = float("inf")

        for u in users:
            if not u.face_encoding:
                continue
            db_emb = np.array(u.face_encoding)

            dot = np.dot(target, db_emb)
            n1 = np.linalg.norm(target)
            n2 = np.linalg.norm(db_emb)

            dist = 1.0 if n1 == 0 or n2 == 0 else 1 - (dot / (n1 * n2))

            if dist < min_dist:
                min_dist = dist
                best_user = u

        if min_dist < MATCH_THRESHOLD:
            return best_user, min_dist
        return None, min_dist


class FaceQualityEngine:
    # model 3d points (giong client)
    model_3d = np.array([
        (0.0, 0.0, 0.0),          # nose
        (0.0, -330.0, -100.0),    # chin
        (0.0, 330.0, -100.0),     # forehead
        (-165.0, 170.0, -135.0),  # left temple
        (165.0, 170.0, -135.0),   # right temple
        (-225.0, 170.0, -135.0),  # left eye out
        (225.0, 170.0, -135.0),   # right eye out
        (-150.0, 150.0, -125.0),  # left eye in
        (150.0, 150.0, -125.0),   # right eye in
        (-150.0, -150.0, -125.0), # left mouth
        (150.0, -150.0, -125.0)   # right mouth
    ], dtype="double")

    indices = [1, 152, 10, 234, 454, 33, 263, 133, 362, 61, 291]

    # mediapipe setup
    mp_mesh = mp.solutions.face_mesh
    mesh = mp_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    @staticmethod
    def check_pose(img):
        h, w, _ = img.shape
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        res = FaceQualityEngine.mesh.process(rgb)

        if not res.multi_face_landmarks:
            return "unknown", "ko tim thay mat"

        lm = res.multi_face_landmarks[0]

        pts_2d = []
        for i in FaceQualityEngine.indices:
            p = lm.landmark[i]
            pts_2d.append([p.x * w, p.y * h])
        pts_2d = np.array(pts_2d, dtype="double")

        f = w  # focal
        c = (w / 2, h / 2)
        cam_mat = np.array([
            [f, 0, c[0]],
            [0, f, c[1]],
            [0, 0, 1]
        ], dtype="double")
        dist = np.zeros((4, 1), dtype="double")

        ok, rvec, tvec = cv2.solvePnP(
            FaceQualityEngine.model_3d, pts_2d, cam_mat, dist,
            flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not ok:
            return "unknown", "tinh goc loi"

        rmat, _ = cv2.Rodrigues(rvec)
        proj = np.hstack((rmat, tvec))

        _, _, _, _, _, _, euler = cv2.decomposeProjectionMatrix(proj)
        pitch, yaw, roll = euler.flatten()

        print(f"[yaw debug] {yaw:.2f}")

        if yaw > 12:
            return "right", "quay phai"
        elif yaw < -12:
            return "left", "quay trai"
        else:
            return "center", "chinh dien ok"

    @staticmethod
    def avg_embedding(vectors):
        if not vectors:
            return None

        arr = np.array(vectors)
        mean = np.mean(arr, axis=0)
        norm = np.linalg.norm(mean)

        if norm == 0:
            return mean.tolist()
        return (mean / norm).tolist()