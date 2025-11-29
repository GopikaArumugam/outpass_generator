# Exitease: A Chatbot-Based Outpass Generator

Exitease is a smart, chatbot-based outpass generator designed for educational institutions. It simplifies the outpass request and approval workflow using a rule‑based chatbot, multi‑level verification, and face‑scan based security checks.

---

## 📝 Project Overview

Exitease allows students to request outpasses through a rule‑based chatbot. The request moves through a structured approval hierarchy:

1. **Student initiates an outpass request** through the chatbot.
2. **Advisor reviews** the request.
3. If approved by Advisor, the request is **sent to HOD**.
4. If the student is a **hosteller**, after HOD approval the request goes to the **Warden**.
5. Once fully approved, the student can proceed to the gate.
6. **Security scans the student's face** at the gate.

   * If a valid outpass exists for that time window, the student is allowed to exit.
7. On return:

   * If the student returns **late**, the system marks it as an **irregular activity**.
   * This information is shown to the **Advisor, HOD, and Warden**.

---

## 🚀 Features

* Rule‑based chatbot for requesting outpasses.
* Multi‑level approval workflow: Advisor → HOD → Warden.
* Face‑scan verification at the security gate.
* Automatic irregular activity tracking.
* Admin view for approvals and activity logs.

---

## 📂 Project Structure (Simplified)

* `app.py` → Main Flask application
* `data_up.py` → Insert student data
* `static/` → Frontend assets

---

## 🛠 How to Run This Project

Follow these steps to run Exitease on your system:

### 1️⃣ Clone the Repository

```
git clone <repo-url>
cd exitease
```

### 2️⃣ Install Requirements

```
pip install -r requirements.txt
```

### 3️⃣ Install CMake and Visual Studio Build Tools (required for dlib/face-recognition)

To run face-recognition libraries on Windows, you must install both:

#### ✅ CMake

Download and install from the official CMake website.

#### ✅ Visual Studio Build Tools

1. Download **Microsoft Visual Studio Build Tools**.
2. During installation, select:

   * **Desktop development with C++**
   * Make sure **MSVC v142 or above**, **Windows SDK**, and **C++ CMake tools** are checked.

These tools provide the C++ compiler required to build libraries like `dlib`.

---

### 4️⃣ Run the App

```
python app.py
```

Your application will start running on the local server.

---

## 👩‍🎓 Adding Student Data

You can insert student information into the database using the script:

```
python data_up.py
```

## 📁 Users JSON File

A `users.json` file is included in the project. It contains predefined user accounts (students, advisors, HODs, wardens, etc.) used for authentication and role-based access.

Place the JSON file in the appropriate directory (usually the project root or a `data/` folder) and ensure your loading script reads from it correctly.

Use the script below to insert student data (face) into the database.

```
python data_up.py
```

---

## 📌 Notes

* Make sure MongoDB or your chosen DB is running.
* If using face recognition, ensure your camera is connected and accessible.

---

**Exitease – Smart, Secure, and Efficient Outpass Management** 🚀
