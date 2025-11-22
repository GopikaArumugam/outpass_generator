import os
import pickle
import face_recognition
import numpy as np

# Global cache
ENCODING_CACHE = {}

def load_dataset_encodings(dataset_path="dataset"):
    known_faces = {}
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
                        image = face_recognition.load_image_file(img_path)
                        encs = face_recognition.face_encodings(image)
                        if encs:
                            encoding = encs[0]
                            enc_list.append(encoding)
                            with open(pkl_path, "wb") as f:
                                pickle.dump(encoding, f)
            if enc_list:
                known_faces[reg_num] = enc_list
    return known_faces

# Load encodings once at startup
if not ENCODING_CACHE:
    ENCODING_CACHE = load_dataset_encodings()

def recognize_student_face(live_image_path, threshold=0.4):
    known_faces = ENCODING_CACHE

    live_img = face_recognition.load_image_file(live_image_path)
    live_encs = face_recognition.face_encodings(live_img)
    if not live_encs:
        return {"status": "no_face_detected", "message": "No face detected in the captured image."}

    live_enc = live_encs[0]

    for reg_num, enc_list in known_faces.items():
        distances = face_recognition.face_distance(enc_list, live_enc)
        min_distance = np.min(distances)
        if min_distance < threshold:
            return {"status": "matched", "reg_num": reg_num}

    return {"status": "no_match", "message": "Face detected, but no match found."}
