from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from functools import wraps
import tempfile
import os

from database import (
    authenticate_user,
    create_outpass_request,
    update_outpass_status,
    get_user_by_name,
    get_outpass_status,
    get_user_by_username,
    users_collection,
    outpasses_collection
)
from face_rec_mod import recognize_student_face
from bson.objectid import ObjectId  
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import qrcode
import ssl
import certifi
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from flask_mail import Mail as FlaskMail, Message

app = Flask(__name__)
app.secret_key = os.urandom(24)



# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'exitease.siet@gmail.com'
app.config['MAIL_PASSWORD'] = 'vigh znfd fels hepa'  # Use the App Password

mail = FlaskMail(app)

# ---------------- HELPER DECORATORS ----------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ---------------- ROUTES ----------------

@app.route('/')
def home():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    
    password = request.form['password']

    # Authenticate the user
    user = authenticate_user(username, password)
    if user:
        session['username'] = username
        session['role'] = user['role']

        # Redirect or render based on user role
        if user['role'] in ['Advisor', 'HOD', 'Warden']:
            return redirect(url_for('dashboard'))
        elif user['role'] == 'student':
            return redirect(url_for('student_dashboard'))  # changed: go to student dashboard
        elif user['role'] == 'security':
            return render_template('security.html')  # or redirect to a route if preferred
        else:
            return render_template('login.html', error="Invalid role")
    else:
        return render_template('login.html', error="Invalid credentials")


@app.route('/track_status')
@login_required
def track_status():
    user = get_user_by_username(session['username'])
    if not user:
        return redirect(url_for('logout'))

    # Get user's outpass requests
    outpasses = list(outpasses_collection.find({"roll_number": user.get('roll_number')}).sort("request_date", -1))

    # Determine approval path based on stay type
    stay_type = user.get('hosteller_or_dayscholar', '').lower()
    approval_path = ['Student', 'Advisor', 'HOD']
    if stay_type == 'hosteller':
        approval_path.append('Warden')

    return render_template('track_status.html', user=user, outpasses=outpasses, approval_path=approval_path)

@app.route('/outpass_history')
@login_required
def outpass_history():
    user = get_user_by_username(session['username'])
    if not user:
        return redirect(url_for('logout'))

    # Get ALL user's outpass requests (no limit)
    outpasses = list(outpasses_collection.find({"roll_number": user.get('roll_number')}).sort("request_date", -1))

    return render_template('outpass_history.html', user=user, outpasses=outpasses)

@app.route('/test_qr')
@login_required
def test_qr():
    # Test QR code generation
    test_data = {
        "name": "Test Student",
        "class": "CSE 2023",
        "reg_number": "12345",
        "roll_number": "714022202001",
        "requested_time": "2025-01-01 10:00:00",
        "leave_time": "2025-01-01 14:00",
        "return_time": "2025-01-01 18:00",
        "reason": "Test",
        "approved_by": "Test",
        "approved_time": str(datetime.utcnow())
    }

    qr_path = generate_qr_code(test_data)
    if qr_path:
        return f"QR code generated successfully: {qr_path}"
    else:
        return "QR code generation failed - check console logs"

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_user_by_username(session['username'])
    if not user:
        return redirect(url_for('logout'))

    role = session['role'].lower()
    username = session['username']

    # Query for pending requests based on the role
    if role == 'advisor':
        pending_requests = list(outpasses_collection.find({
            "advisor": username,
            "$or": [
                {"status": "Requested"},
                {"status": f"Meet in Person requested by {username}"},
                {"status": "Met"}
            ]
        }))
    elif role == 'hod':
        pending_requests = list(outpasses_collection.find({
            "hod": username,
            "$or": [
                {"status": "Accepted by Advisor"},
                {"status": f"Meet in Person requested by {username}"},
                {"status": "Met"}
            ]
        }))
    elif role == 'warden':
        pending_requests = list(outpasses_collection.find({
            "warden": username,
            "$or": [
                {"status": "Accepted by HOD"},
                {"status": f"Meet in Person requested by {username}"},
                {"status": "Met"}
            ]
        }))
    else:
        pending_requests = []

    # Query for emergency requests based on the role and status
    if role == 'advisor':
        emergency_requests = list(outpasses_collection.find({
            "advisor": username,
            "is_emergency": True,
            "$or": [
                {"status": "Requested"},
                {"status": f"Meet in Person requested by {username}"},
                {"status": "Met"}
            ]
        }))
    elif role == 'hod':
        emergency_requests = list(outpasses_collection.find({
            "hod": username,
            "is_emergency": True,
            "$or": [
                {"status": "Accepted by Advisor"},
                {"status": f"Meet in Person requested by {username}"},
                {"status": "Met"}
            ]
        }))
    elif role == 'warden':
        emergency_requests = list(outpasses_collection.find({
            "warden": username,
            "is_emergency": True,
            "$or": [
                {"status": "Accepted by HOD"},
                {"status": f"Meet in Person requested by {username}"},
                {"status": "Met"}
            ]
        }))
    else:
        emergency_requests = []

    # Query for previously accepted requests
    if role == 'advisor':
        accepted_requests = list(outpasses_collection.find({
            "advisor": username,
            "status": {"$regex": "Accepted by.*"}
        }))
    elif role == 'hod':
        accepted_requests = list(outpasses_collection.find({
            "hod": username,
            "status": {"$regex": "Accepted by.*"}
        }))
    elif role == 'warden':
        accepted_requests = list(outpasses_collection.find({
            "warden": username,
            "status": {"$regex": "Accepted by.*"}
        }))
    else:
        accepted_requests = []

    return render_template(
        'dashboard.html',
        pending_requests=pending_requests,
        emergency_requests=emergency_requests,
        accepted_requests=accepted_requests
    )


@app.route('/chatbot')
@login_required
def chatbot():
    user = get_user_by_username(session['username'])
    if not user:
        return redirect(url_for('logout'))

    name = user.get('name', session['username'])
    roll_number = user.get('roll_number')  # Fetch roll number
    return render_template('chatbot.html', name=name, roll_number=roll_number)


@app.route('/create_outpass', methods=['POST'])
@login_required
def create_outpass():
    
    try:
        data = request.get_json()
        roll_number = data.get('roll_number')
        leave_time = data.get('leave_time')
        return_time = data.get('return_time')
        reason = data.get('reason')
        is_emergency = data.get('is_emergency', False)

        if not roll_number or not leave_time or not return_time or not reason:
            return jsonify({'status': 'error', 'message': 'All fields are required.'}), 400

        # Fetch user details from the database
        user = get_user_by_username(session['username'])
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found.'}), 404

        # Extract student details
        student_name = user.get('name')  # Name of the user
        year = user.get('year')
        dept = user.get('dept')
        room_number = user.get('room_number')
        hosteller_or_dayscholar = user.get('hosteller_or_dayscholar', 'Dayscholar')

        # Fetch Advisor details
        advisor = users_collection.find_one({"role": "Advisor", "dept": dept, "year": year})
        advisor_username = advisor['username'] if advisor else None
        print(f"Advisor fetched: {advisor_username}")

        # Fetch HOD details
        hod = users_collection.find_one({"role": "HOD", "dept": dept})
        hod_username = hod['username'] if hod else None
        print(f"HOD fetched: {hod_username}")

        # Fetch Warden details (if hosteller)
        warden_username = None
        if hosteller_or_dayscholar == "Hosteller" and room_number:
            wardens = users_collection.find({"role": "Warden"})
            for warden in wardens:
                room_range = warden.get("room_number_range")  # Example: "201-220"
                if room_range:
                    start, end = map(int, room_range.split('-'))
                    if start <= int(room_number) <= end:
                        warden_username = warden['username']
                        break
        print(f"Warden fetched: {warden_username}")

        # Convert leave_time and return_time to datetime objects
        leave_time_dt = datetime.strptime(leave_time, "%Y-%m-%d %H:%M")
        return_time_dt = datetime.strptime(return_time, "%Y-%m-%d %H:%M")

        # Ensure leave_time is before return_time
        if leave_time_dt >= return_time_dt:
            return jsonify({'status': 'error', 'message': 'Leave time must be before return time.'}), 400

        # Check for overlapping time ranges
        overlapping_request = outpasses_collection.find_one({
            "roll_number": roll_number,
            "$or": [
                {"leave_time": {"$lt": return_time}, "return_time": {"$gt": leave_time}}
            ]
        })

        if overlapping_request:
            overlapping_leave_time = overlapping_request.get("leave_time")
            overlapping_return_time = overlapping_request.get("return_time")
            return jsonify({
                'status': 'error',
                'message': f'An outpass request already exists for the time range '
                           f'{overlapping_leave_time} to {overlapping_return_time}.'
            }), 400

        # Create the outpass request
        outpass_request = {
            "student_name": student_name,  # Name of the user
            "roll_number": roll_number,
            "leave_time": leave_time,
            "return_time": return_time,
            "reason": reason,
            "status": "Requested",
            "is_emergency": is_emergency,
            "request_date": datetime.utcnow(),
            "year": year,  # Year of the student
            "dept": dept,  # Department of the student
            "advisor": advisor_username,  # Advisor's username
            "hod": hod_username,          # HOD's username
            "warden": warden_username     # Warden's username
        }

        result = outpasses_collection.insert_one(outpass_request)
        return jsonify({'status': 'success', 'outpass_id': str(result.inserted_id)})

    except Exception as e:
        print("Error in /create_outpass:", str(e))
        return jsonify({'status': 'error', 'message': 'An internal error occurred. Please try again.'}), 500




@app.route('/verify-student', methods=['POST'])
def verify_student():
    try:
        photo = request.files.get('photo')
        if not photo:
            return jsonify({'status': 'error', 'message': 'No photo received'})

        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            photo.save(tmp.name)
            temp_path = tmp.name

        # Run face recognition
        result = recognize_student_face(temp_path)
        os.remove(temp_path)

        if result["status"] == "matched":
            reg_num = result["reg_num"]
            # Find user by reg_number
            user = users_collection.find_one({"reg_number": reg_num})
            if not user:
                return jsonify({'status': 'error', 'message': f'Register number {reg_num} not found in database.'})

            roll_number = user.get("roll_number")
            # Search for outpass approved by Warden
            outpass = outpasses_collection.find_one({"roll_number": roll_number, "status": "Accepted by Warden"})
            if outpass:
                # Convert ObjectId to string for JSON serialization
                outpass['_id'] = str(outpass['_id'])
                return jsonify({'status': 'allowed', 'reg_number': reg_num, 'outpass': outpass})
            else:
                return jsonify({'status': 'no_outpass', 'reg_number': reg_num, 'message': 'No approved outpass found for this student.'})
        elif result["status"] == "no_face_detected":
            return jsonify({'status': 'error', 'message': 'No face detected'})
        elif result["status"] == "no_match":
            return jsonify({'status': 'error', 'message': 'Face not recognized'})
        else:
            return jsonify({'status': 'error', 'message': 'Unknown error'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/check_status', methods=['GET'])
@login_required
def check_status():
    try:
        # Get the logged-in user's roll number
        user = get_user_by_username(session['username'])
        roll_number = user.get('roll_number')

        if not roll_number:
            return jsonify({"status": "error", "message": "Roll number not found for the user."}), 404

        # Fetch all outpass requests for the roll number
        outpasses = list(outpasses_collection.find({"roll_number": roll_number}).sort("request_date", -1))

        if not outpasses:
            return jsonify({"status": "error", "message": "No outpass requests found for this roll number."}), 404

        # Format the outpass data for the response
        outpass_list = []
        for outpass in outpasses:
            outpass_list.append({
                "student_name": outpass.get("student_name"),
                "requested_date": outpass.get("request_date").strftime("%Y-%m-%d %H:%M:%S"),
                "leave_time": outpass.get("leave_time"),
                "return_time": outpass.get("return_time"),
                "reason": outpass.get("reason"),
                "status": outpass.get("status")
            })

        return jsonify({"status": "success", "outpasses": outpass_list})

    except Exception as e:
        print("Error in /check_status:", str(e))
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500


@app.route('/approve_outpass/<outpass_id>', methods=['POST'])
@login_required
def approve_outpass(outpass_id):
    if session['role'] not in ['advisor', 'hod', 'warden']:
        return redirect(url_for('home'))

    approval_status = request.form.get('approval_status')
    if not approval_status:
        return "Missing approval status", 400

    updated = update_outpass_status(outpass_id, approval_status)

    if updated:
        # TODO: Implement notification logic to student or parent
        pass

    return redirect(url_for('dashboard'))

@app.route('/previous_outpasses')
def previous_outpasses():
    if 'username' not in session:
        return jsonify({'status': 'unauthorized'}), 401

    student_id = session['username']
    # You must implement this function in your database module
    outpasses = get_previous_outpasses(student_id)  # List of dicts

    return jsonify({'status': 'success', 'outpasses': outpasses})


def get_previous_outpasses(student_id):
    # This is just a mock version, update with your real DB query
    return [
        {"reason": "Medical", "leave_time": "2025-04-25 10:00", "status": "Approved"},
        {"reason": "Personal", "leave_time": "2025-03-14 15:00", "status": "Pending"},
    ]

@app.route('/process_outpass/<outpass_id>', methods=['POST'])
@login_required
def process_outpass(outpass_id):
    print(f"=== PROCESS_OUTPASS ROUTE CALLED ===")
    print(f"Outpass ID: {outpass_id}")
    try:
        action = request.form.get('action')
        print(f"Action received: {action}")
        user = get_user_by_username(session['username'])  # Get the logged-in user's details
        user_role = user.get('role')  # Fetch the role of the user (e.g., Advisor, HOD, Warden)

        if not action:
            flash('Action is required.', 'error')
            return redirect(url_for('dashboard'))  # Redirect to the dashboard

        # Fetch the outpass request from the database
        outpass = outpasses_collection.find_one({"_id": ObjectId(outpass_id)})
        if not outpass:
            flash('Outpass request not found.', 'error')
            return redirect(url_for('dashboard'))  # Redirect to the dashboard

        roll_number = outpass.get('roll_number')
        student = users_collection.find_one({"roll_number": roll_number})
        student_email = student.get('mail') if student else None

        if not student_email:
            flash('Student email not found. Unable to send notification.', 'error')
            return redirect(url_for('dashboard'))

        # Update the status based on the action
        if action == "Accepted":
            print(f"=== ACCEPTANCE BUTTON CLICKED ===")
            print(f"Action: {action}, User Role: {user_role}, Session User: {session['username']}")
            print(f"Outpass ID: {outpass_id}")
            new_status = f"Accepted by {user_role}"
            print(f"New status will be: {new_status}")

            # Check if this is the final approval (Warden for hostellers, HOD for day scholars)
            print(f"Checking final approval for {user_role}, session user: {session['username']}")
            print(f"Outpass data - warden: {outpass.get('warden')}, hod: {outpass.get('hod')}, roll_number: {outpass.get('roll_number')}")

            is_final_approval = False
            if user_role == "warden":
                print(f"Warden approval detected, checking if assigned warden matches session user")
                if outpass.get('warden') == session['username']:
                    is_final_approval = True
                    print("FINAL APPROVAL: Warden match - QR code will be generated")
                else:
                    print(f"Warden mismatch: outpass.warden={outpass.get('warden')} != session.username={session['username']}")
            elif user_role == "hod":
                print(f"HOD approval detected, checking student type")
                day_scholar_check = users_collection.find_one({"roll_number": roll_number})
                if day_scholar_check:
                    student_type = day_scholar_check.get('hosteller_or_dayscholar', '').lower()
                    print(f"Student type: {student_type}")
                    if student_type == 'dayscholar':
                        is_final_approval = True
                        print("FINAL APPROVAL: Day scholar + HOD - QR code will be generated")
                    else:
                        print(f"Not final approval: student is {student_type}, not dayscholar")
                else:
                    print("ERROR: Could not find student record for final approval check")

            if is_final_approval:
                # Send confirmation email
                subject = "Your Outpass Request Fully Approved"
                message = (
                    f"Dear {student.get('name')},\n\n"
                    f"Your outpass request has been fully approved.\n\n"
                    f"Details:\n"
                    f"Leave Time: {outpass.get('leave_time')}\n"
                    f"Return Time: {outpass.get('return_time')}\n"
                    f"Reason: {outpass.get('reason')}\n\n"
                    f"Thank you."
                )
                send_email(student_email, subject, message)
                flash(f'Outpass fully approved and confirmation sent to {student_email}.', 'success')
            else:
                # Send a simple email notification for intermediate acceptance
                subject = "Outpass Request Accepted"
                message = (
                    f"Dear {student.get('name')},\n\n"
                    f"Your outpass request has been accepted by {user_role}.\n\n"
                    f"Leave Time: {outpass.get('leave_time')}\n"
                    f"Return Time: {outpass.get('return_time')}\n\n"
                    f"Thank you."
                )
                send_email(student_email, subject, message)

        elif action == "Rejected":
            new_status = f"Rejected by {user_role}"

            # Send an email notification for rejection
            subject = "Outpass Request Rejected"
            message = (
                f"Dear {student.get('name')},\n\n"
                f"Your outpass request has been rejected by {user_role}.\n\n"
                f"Leave Time: {outpass.get('leave_time')}\n"
                f"Return Time: {outpass.get('return_time')}\n\n"
                f"Thank you."
            )
            send_email(student_email, subject, message)

        elif action == "Meet in Person":
            new_status = f"Meet in Person requested by {session['username']}"

            # Send an email notification for meeting in person
            subject = "Meet in Person Request for Outpass"
            message = (
                f"Dear {student.get('name')},\n\n"
                f"Your outpass request for the time range {outpass.get('leave_time')} to {outpass.get('return_time')} "
                f"requires you to meet in person with {user_role}.\n\n"
                f"Please contact the {user_role} as soon as possible.\n\n"
                f"Thank you."
            )
            send_email(student_email, subject, message)

        elif action == "Met":
            new_status = "Met"

            # Send an email notification that the student has met
            subject = "Outpass Meeting Completed"
            message = (
                f"Dear {student.get('name')},\n\n"
                f"You have successfully met with {user_role} for your outpass request "
                f"(Leave: {outpass.get('leave_time')} to Return: {outpass.get('return_time')}).\n\n"
                f"The request is now pending final approval.\n\n"
                f"Thank you."
            )
            send_email(student_email, subject, message)

        else:
            flash('Invalid action.', 'error')
            return redirect(url_for('dashboard'))  # Redirect to the dashboard

        # Update the outpass request in the database
        outpasses_collection.update_one(
            {"_id": ObjectId(outpass_id)},
            {"$set": {"status": new_status, "processed_by": session['username']}}
        )

        flash(f'Outpass request {action.lower()} successfully.', 'success')
        return redirect(url_for('dashboard'))  # Redirect to the dashboard

    except Exception as e:
        print("Error in /process_outpass:", str(e))
        flash('An internal error occurred. Please try again.', 'error')
        return redirect(url_for('dashboard'))  # Redirect to the dashboard

def send_email(to_email, subject, message):
    try:
        msg = Message(subject, sender='exitease.siet@gmail.com', recipients=[to_email])
        msg.body = message
        mail.send(msg)  # This uses Flask-Mail's `mail` object
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Error sending email: {e}")

def send_email_with_attachment(to_email, subject, message, attachment_path):
    try:
        msg = Message(subject, sender='exitease.siet@gmail.com', recipients=[to_email])
        msg.body = message

        # Attach the QR code file
        if os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as attachment:
                msg.attach(
                    filename=os.path.basename(attachment_path),
                    content_type="image/png",
                    data=attachment.read()
                )
        else:
            print(f"Attachment not found: {attachment_path}u")
            return

        mail.send(msg)
        print(f"Email with QR code sent to {to_email}")
    except Exception as e:
        print("Error sending email with attachment:", str(e))

@app.route('/logout')
def logout():
    username = session.get('username')  # capture before clearing
    session.clear()
    print("Session Username:", username)
    return redirect(url_for('home'))

@app.route('/student_dashboard')
@login_required
def student_dashboard():
    user = get_user_by_username(session['username'])
    if not user:
        return redirect(url_for('logout'))

    name = user.get('name', session['username'])
    roll_number = user.get('roll_number')

    # fetch advisor / hod / warden based on student's dept/year/room
    dept = user.get('dept')
    year = user.get('year')
    room_number = user.get('room_number')
    hosteller_or_dayscholar = user.get('hosteller_or_dayscholar', 'Dayscholar')

    advisor_name = None
    hod_name = None
    warden_name = None

    try:
        # Advisor (match by dept + year)
        advisor = users_collection.find_one({"role": "Advisor", "dept": dept, "year": year})
        if advisor:
            advisor_name = advisor.get('name') or advisor.get('username')

        # HOD (match by dept)
        hod = users_collection.find_one({"role": "HOD", "dept": dept})
        if hod:
            hod_name = hod.get('name') or hod.get('username')

        # Warden (only for hostellers) - match room range if provided
        if hosteller_or_dayscholar.lower() == "hosteller" and room_number:
            for w in users_collection.find({"role": "Warden"}):
                room_range = w.get("room_number_range")
                if room_range:
                    try:
                        start, end = map(int, room_range.split('-'))
                        if start <= int(room_number) <= end:
                            warden_name = w.get('name') or w.get('username')
                            break
                    except Exception:
                        continue
    except Exception as e:
        print("Error fetching advisor/hod/warden:", str(e))

    # optional: fetch student's outpasses
    try:
        outpasses = list(outpasses_collection.find({"roll_number": roll_number}).sort("request_date", -1))
    except Exception:
        outpasses = []

    return render_template(
        'stud_dash.html',
        user=user,
        name=name,
        roll_number=roll_number,
        outpasses=outpasses,
        advisor_name=advisor_name,
        hod_name=hod_name,
        warden_name=warden_name
    )

# ----------    ------ MAIN ----------------

if __name__ == '__main__':
    # Disable the reloader on Windows to avoid "An operation was attempted on something that is not a socket"
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

def generate_qr_code(data_dict):
    try:
        print("Starting QR code generation...")
        import json

        # Check if qrcode is available
        try:
            import qrcode
            print("QR code library imported successfully")
        except ImportError as ie:
            print(f"QR code library not available: {ie}")
            return None

        # Convert dictionary to JSON string for QR code
        qr_data = json.dumps(data_dict)
        print(f"QR data prepared: {len(qr_data)} characters")

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        print("QR code matrix generated")

        # Save the QR code to a file
        filename = f"{data_dict['roll_number']}_outpass.png"
        qr_code_path = os.path.join("static", "qr_codes", filename)

        print(f"Attempting to save QR code to: {qr_code_path}")

        # Ensure the directory exists
        os.makedirs(os.path.dirname(qr_code_path), exist_ok=True)
        print(f"Directory created/verified: {os.path.dirname(qr_code_path)}")

        # Generate and save the QR code
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img.save(qr_code_path)

        # Verify file was created
        if os.path.exists(qr_code_path):
            file_size = os.path.getsize(qr_code_path)
            print(f"QR code saved successfully: {qr_code_path} ({file_size} bytes)")
        else:
            print(f"ERROR: QR code file was not created at {qr_code_path}")
            return None

        # Return just the filename for storage in database
        return filename
    except Exception as e:
        print(f"Error generating QR code: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
