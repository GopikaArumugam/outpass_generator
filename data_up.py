import os
import cv2
import time
import torch
from ultralytics import YOLO

# === Step 1: Get input from user ===
student_id = input("Enter your ID number: ").strip()
if not student_id.isdigit():
    print("Invalid input. Must be digits.")
    exit()

# === Step 2: Create directory for saving ===
output_dir = os.path.join("data", student_id)
os.makedirs(output_dir, exist_ok=True)
video_path = os.path.join(output_dir, f"{student_id}.mp4")

# === Step 3: Record video for 10 seconds ===
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Cannot access webcam.")
    exit()

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
fps = 10.0
frame_width = int(cap.get(3))
frame_height = int(cap.get(4))
out = cv2.VideoWriter(video_path, fourcc, fps, (frame_width, frame_height))

print("Recording for 10 seconds... Press 'q' to stop early.")
start_time = time.time()
while True:
    ret, frame = cap.read()
    if not ret:
        break
    out.write(frame)
    cv2.imshow("Recording...", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("Stopped manually.")
        break
    if time.time() - start_time >= 10:
        print("Recording complete.")
        break

cap.release()
out.release()
cv2.destroyAllWindows()
print(f"Video saved to: {video_path}")

# === Step 4: Load YOLO model ===
model_path = "yolo/weights/yolo11n-face.pt"  # Update path if needed
if not os.path.exists(model_path):
    print(f"Model not found at {model_path}. Please check the path.")
    exit()

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"Using device: {device}")
model = YOLO(model_path)

# === Step 5: Process video and extract faces ===
cap = cv2.VideoCapture(video_path)
face_id = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    results = model(frame, conf=0.3)
    for result in results:
        if hasattr(result, "boxes") and result.boxes is not None:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                face = frame[y1:y2, x1:x2]
                if face.size == 0:
                    continue
                gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
                resized = cv2.resize(gray, (128, 128))
                face_path = os.path.join(output_dir, f"face_{face_id}.jpg")
                cv2.imwrite(face_path, resized)
                face_id += 1

cap.release()
print(f"Extracted and saved {face_id} face images in: {output_dir}")
