
import cv2
import requests
import base64
import json
import time

# Configuration
API_URL = "http://localhost:5000/api/checkin"

def checkin():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open webcam. Trying index 1...")
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
             print("Cannot open any webcam.")
             return

    print("--- ATTENDANCE CHECK-IN ---")
    print("Press 'c' to Check-in/Check-out, 'q' to quit.")
    
    last_status = ""
    last_name = ""
    message_color = (0, 255, 0)
    display_message = "Ready"

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Display UI
        cv2.putText(frame, "Press 'c' to Check-in", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
        
        if last_name:
             cv2.putText(frame, f"User: {last_name}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
             cv2.putText(frame, f"Status: {last_status}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, message_color, 2)
             cv2.putText(frame, f"Msg: {display_message}", (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)

        cv2.imshow('Attendance Check-in', frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('c'):
            # Convert to base64
            _, buffer = cv2.imencode('.jpg', frame)
            img_str = base64.b64encode(buffer).decode('utf-8')
            
            payload = {
                "image": "data:image/jpeg;base64," + img_str
            }
            
            try:
                print("Sending request...")
                cv2.putText(frame, "Sending...", (20, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.imshow('Attendance Check-in', frame)
                cv2.waitKey(1)
                
                response = requests.post(API_URL, json=payload)
                data = response.json()
                print("Response:", json.dumps(data, indent=2, ensure_ascii=False))
                
                if data.get("success"):
                    last_name = data.get("name", "Unknown")
                    last_status = data.get("status", "Success")
                    display_message = data.get("message", "")
                    message_color = (0, 255, 0) # Green
                else:
                    last_name = ""
                    last_status = "FAILED"
                    display_message = data.get("message", "Unknown Error")
                    message_color = (0, 0, 255) # Red

            except Exception as e:
                print("Error:", e)
                display_message = f"Error: {str(e)}"
                message_color = (0, 0, 255)
        
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    checkin()
