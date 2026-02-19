import numpy as np
import sys
import os

# them duong dan server vao path
sys.path.append(os.path.join(os.getcwd(), 'server'))

# mock cv2, mediapipe, deepface de test ko can cai dat
from unittest.mock import MagicMock
sys.modules["cv2"] = MagicMock()
sys.modules["mediapipe"] = MagicMock()
sys.modules["deepface"] = MagicMock()

try:
    from core.ai_engine import FaceQualityEngine
    print("[ok] import FaceQualityEngine thanh cong (dung mock)")
except ImportError as e:
    print(f"[loi] import FaceQualityEngine that bai: {e}")
    sys.exit(1)


def test_avg_emb():
    print("test tinh trung binh vector...")
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    # mean = [0.5, 0.5]
    # norm = sqrt(0.5) ≈ 0.707
    # expected ≈ [0.707, 0.707]

    avg = FaceQualityEngine.avg_embedding([v1, v2])
    print(f"input: {v1} va {v2}")
    print(f"output: {avg}")

    expected = 1.0 / np.sqrt(2)
    if abs(avg[0] - expected) < 0.0001 and abs(avg[1] - expected) < 0.0001:
        print("[ok] tinh trung binh va normalize dung")
    else:
        print(f"[loi] ket qua sai. mong doi ~{expected:.4f}, nhan duoc {avg[0]:.4f}")


if __name__ == "__main__":
    test_avg_emb()