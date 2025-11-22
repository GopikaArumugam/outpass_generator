import face_recognition
import cv2
import os
import pickle
import numpy as np

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

                # ✅ Check if encoding already exists
                if os.path.exists(pkl_path):
                    with open(pkl_path, "rb") as f:
                        encoding = pickle.load(f)
                    enc_list.append(encoding)
                else:
                    image = face_recognition.load_image_file(img_path)
                    encs = face_recognition.face_encodings(image)
                    if encs:
                        encoding = encs[0]
                        enc_list.append(encoding)
                        with open(pkl_path, "wb") as f:
                            pickle.dump(encoding, f)
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
if not ret:
    print("❌ Failed to capture image from camera.")
    cam.release()
    exit(1)

cv2.imwrite("live.jpg", frame)
cam.release()

# Step 3: Encode captured photo
live_img = face_recognition.load_image_file("live.jpg")
live_encs = face_recognition.face_encodings(live_img)

if not live_encs:
    print("❌ No face found.")
    exit(1)

live_enc = live_encs[0]

# Step 4: Compare with known faces using custom threshold
threshold = 0.4  # 🔧 Increase this if matches are failing (default face_recognition uses 0.6)
found = False

for reg_num, enc_list in known_faces.items():
    distances = face_recognition.face_distance(enc_list, live_enc)
    min_distance = np.min(distances)

    print(f"🔍 Checking {reg_num} - Min Distance: {min_distance:.4f}")

    if min_distance < threshold:
        print(f"✅ Match found! Register Number: {reg_num} (Distance: {min_distance:.4f})")

        # ✅ Store result in a file
        with open("matched_rollnumber.txt", "w") as f:
            f.write(reg_num)
        print("📁 Saved to matched_rollnumber.txt")
        found = True
        break

if not found:
    print("❌ No match found. All distances above threshold.")
