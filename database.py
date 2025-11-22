from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os
import pytz  # Install pytz if not already installed

from flask import Flask, request, redirect, url_for, session, jsonify, render_template
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database connection details
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")  # You can set the URI using an environment variable
DB_NAME = "exitease"  # Your database name

# MongoDB client initialization
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Collection names
users_collection = db["users"]
outpasses_collection = db["outpasses"]
approvers_collection = db["users"]
irregular_logs_collection = db["irregular_logs"]  # <-- Add this line
activity_logs_collection = db["activity_logs"]

def get_user_by_username(username):
    """Fetch a user from the database by username."""
    return users_collection.find_one({"username": username})

def get_user_by_name(name):
    """Fetch a user from the database by name."""
    return users_collection.find_one({"name": name})

def create_outpass_request(outpass_request):
    """Create a new outpass request."""
    try:
        # Assume the input time is in Indian Standard Time (IST) or take it as provided
        if "leave_time" in outpass_request and isinstance(outpass_request["leave_time"], str):
            # Take the leave_time as it is without conversion
            outpass_request["leave_time"] = outpass_request["leave_time"]

        if "return_time" in outpass_request and isinstance(outpass_request["return_time"], str):
            # Take the return_time as it is without conversion
            outpass_request["return_time"] = outpass_request["return_time"]

        # Insert the outpass request into the database
        result = outpasses_collection.insert_one(outpass_request)
        return result.inserted_id
    except Exception as e:
        print("Error inserting outpass request:", str(e))
        raise

def get_outpass_status(username):
    """Fetch the status of the most recent outpass request for a user."""
    outpass = outpasses_collection.find_one({"student_name": username}, sort=[("request_date", -1)])
    return outpass["status"] if outpass else "No requests found"

def update_outpass_status(outpass_id, status):
    """Update the status of an outpass request."""
    result = outpasses_collection.update_one({"_id": ObjectId(outpass_id)}, {"$set": {"status": status}})
    return result.modified_count > 0

def get_advisor_by_dept_and_year(dept, year):
    """Fetch the advisor for a specific department and year."""
    advisor = approvers_collection.find_one({"role": "Advisor", "dept": dept, "year": year})
    return advisor["name"] if advisor else None

def get_user_by_id(user_id):
    """Fetch a user from the database by user ID."""
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    return user

def authenticate_user(username, password):
    """Authenticate a user by username and password."""
    return users_collection.find_one({"username": username, "password": password})

def get_previous_outpasses(student_id):
    return [
        {"reason": "Medical", "leave_time": "2025-04-25 10:00", "status": "Approved"},
        {"reason": "Personal", "leave_time": "2025-03-14 15:00", "status": "Pending"},
    ]

def get_requested_outpasses():
    """Fetch all outpasses with status 'Requested'."""
    return db.outpasses.find({ "status": "Requested" })


