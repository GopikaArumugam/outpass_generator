import face_recognition
import cv2
import os
import pickle
import numpy as np
from PIL import Image  # <-- Add this import

# Step 1: Load all encodings from each student's folder
known_faces = {}
dataset_path = "dataset"

for reg_num in os.listdir(dataset_path):
    person_folder = os.path.join(dataset_path, reg_num)
    if os.path.isdir(person_folder):
        enc_list = []
        for img_file in os.listdir(person_folder):
            if img_file.endswith((".jpg", ".png", ".jpeg")):
                img_path = os.path.join(person_folder, img_file)
                pkl_path = img_path + ".pkl"

                if os.path.exists(pkl_path):
                    with open(pkl_path, "rb") as f:
                        encoding = pickle.load(f)
                    enc_list.append(encoding)
                else:
                    try:
                        print(f"🖼 Loading: {img_path}")
                        # Use PIL to ensure RGB
                        with Image.open(img_path) as pil_img:
                            rgb_img = pil_img.convert("RGB")
                            image = np.array(rgb_img)
                            # Ensure correct dtype and shape
                            if image.dtype != np.uint8:
                                image = image.astype(np.uint8)
                            if len(image.shape) != 3 or image.shape[2] != 3:
                                raise ValueError(f"Image at {img_path} is not a 3-channel RGB image.")
                            print(f"Image shape: {image.shape}, dtype: {image.dtype}")  # <-- Add this line
                        encs = face_recognition.face_encodings(image)
                        if encs:
                            encoding = encs[0]
                            enc_list.append(encoding)
                            with open(pkl_path, "wb") as f:
                                pickle.dump(encoding, f)
                        else:
                            print(f"⚠️ No face found in {img_path}")
                    except Exception as e:
                        print(f"❌ Error processing {img_path}: {e}")

        if enc_list:
            known_faces[reg_num] = enc_list
            print(f"✅ Loaded {len(enc_list)} encodings for {reg_num}")

# Step 2: Capture live photo
cam = cv2.VideoCapture(0)
if not cam.isOpened():
    print("❌ Could not open camera. Please check your camera connection.")
    exit(1)

print("📸 Capturing live photo... Look at the camera!")
ret, frame = cam.read()
cam.release()

if not ret:
    print("❌ Failed to capture image from camera.")
    exit(1)

# Convert BGR to RGB using OpenCV, then force to 8-bit RGB using PIL
rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
rgb_frame = Image.fromarray(rgb_frame).convert("RGB")
rgb_frame = np.array(rgb_frame)
# Ensure correct dtype and shape
if rgb_frame.dtype != np.uint8:
    rgb_frame = rgb_frame.astype(np.uint8)
if len(rgb_frame.shape) != 3 or rgb_frame.shape[2] != 3:
    raise ValueError("Captured frame is not a 3-channel RGB image.")

# Optional: Save image for debugging
cv2.imwrite("live.jpg", frame)

# Step 3: Encode captured photo
print(f"Live frame shape: {rgb_frame.shape}, dtype: {rgb_frame.dtype}")  # <-- Add this line
live_encs = face_recognition.face_encodings(rgb_frame)

if not live_encs:
    print("❌ No face found in the captured image.")
    exit(1)

live_enc = live_encs[0]

# Step 4: Compare with known faces using custom threshold
threshold = 0.4
found = False

for reg_num, enc_list in known_faces.items():
    distances = face_recognition.face_distance(enc_list, live_enc)
    min_distance = np.min(distances)

    print(f"🔍 Checking {reg_num} - Min Distance: {min_distance:.4f}")

    if min_distance < threshold:
        print(f"✅ Match found! Register Number: {reg_num} (Distance: {min_distance:.4f})")
        with open("matched_rollnumber.txt", "w") as f:
            f.write(reg_num)
        print("📁 Saved to matched_rollnumber.txt")
        found = True
        break

if not found:
    print("❌ No match found. All distances above threshold.")
