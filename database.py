# database.py

import json
import os

USER_DB = "data/users.json"

def init_db():
    """Create the users file if it doesn't exist"""
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(USER_DB):
        with open(USER_DB, "w") as f:
            json.dump({}, f)

def load_users():
    """Load all users from JSON file"""
    init_db()
    with open(USER_DB, "r") as f:
        return json.load(f)

def save_users(users):
    """Save users to JSON file"""
    with open(USER_DB, "w") as f:
        json.dump(users, f, indent=4)

def user_exists(username):
    """Check if username already exists"""
    users = load_users()
    return username in users

def add_user(username, hashed_password, email):
    """Add new user to database"""
    users = load_users()
    users[username] = {
        "password": hashed_password,
        "email": email
    }
    save_users(users)

def get_user(username):
    """Get user data by username"""
    users = load_users()
    return users.get(username, None)