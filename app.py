import subprocess
import sys
import math
import logging
import logging.handlers
import ctypes
import signal
import atexit
import bcrypt
import mysql.connector
import importlib.util
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from datetime import timedelta, datetime
import openpyxl as xw
import os
import time

# -----------------------------------
# Set up logging to Windows Event Viewer
# -----------------------------------
def setup_windows_event_log():
    try:
        handler = logging.handlers.NTEventLogHandler("IGrowBondCalculator")
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        handler.setFormatter(formatter)

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        logger.info("Starting IGrow Bond Calculator.")
        return logger
    except Exception as e:
        print(f"Failed to initialize Windows Event Log: {e}")
        sys.exit(1)

logger = setup_windows_event_log()

# -----------------------------------
# Install required packages if not present
# -----------------------------------
required_packages = {
    'Flask-Cors': 'flask_cors',
    'openpyxl': 'openpyxl',
    'bcrypt': 'bcrypt',
    'mysql-connector-python': 'mysql.connector'
}
for pip_name, module_name in required_packages.items():
    if importlib.util.find_spec(module_name) is None:
        logger.warning(f"{pip_name} not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
        logger.info(f"Installed {pip_name} successfully.")
    else:
        logger.info(f"{pip_name} already installed.")

# -----------------------------------
# Flask App Setup
# -----------------------------------
app = Flask(__name__)
app.secret_key = "igrow-super-secret-key"
app.permanent_session_lifetime = timedelta(minutes=30)
CORS(app)

BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
EXCEL_PATH = os.path.join(BASE_DIR, "data", "Bonds Calculator.xlsx")

# -----------------------------------
# Gracefully Shutdown
# -----------------------------------
def shutdown_handler(*args):
    logger.info("Shutting down IGrow Bonds Calculator.")
    try:
        for app in xw.apps:
            if not app.api.Workbooks.Count:
                app.quit()
    except Exception as e:
        logger.warning(f"Error during Excel cleanup: {e}")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)
atexit.register(shutdown_handler)

# -----------------------------------
# Force Shutdown Flask Server
# -----------------------------------
def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is not None:
        func()

# -----------------------------------
# Session Timeout Check Middleware
# -----------------------------------
@app.before_request
def session_timeout_check():
    if "user" in session:
        last_active_str = session.get("last_active")
        if last_active_str:
            last_active = datetime.fromisoformat(last_active_str)
            now = datetime.now()
            if (now - last_active) > timedelta(minutes=1):
                logger.info("Session expired. Exiting app.")
                session.clear()
                shutdown_server()
                shutdown_handler()
                app.quit()

                return jsonify({"message": "Session expired. Please log in again.", "status": "error"}), 401
        session["last_active"] = datetime.now().isoformat()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    session_timeout_check()
    try:
        logger.info("Received calculation request.")
        wb = excel.books.open(EXCEL_PATH)
        sheet = wb.sheets[0]
        sheet2 = wb.sheets[1]

        data = request.json
        rate = float(data.get("rate", 2)) / 100
        sheet2.range("H7").value = rate
        sheet2.range("H9").value = float(data.get("PropValue1", 0))
        sheet2.range("H11").value = float(data.get("PropValue2", 0))
        sheet2.range("H13").value = float(data.get("PropValue3", 0))
        sheet2.range("H15").value = float(data.get("PropValue4", 0))
        sheet2.range("H17").value = float(data.get("PropValue5", 0))

        wb.app.calculate()
        results = {
            "parameters": [
                ("TransferIncentive", round(sheet.range("H17").value, 2)),
                ("TotalComm", round(sheet.range("H20").value, 2)),
                ("RevenueRate", round(sheet.range("H23").value, 2))
            ]
        }
        wb.save(EXCEL_PATH)
        wb.close()
        excel.quit()

        logger.info("Calculation completed successfully.")
        return jsonify({"results": results})

    except Exception as e:
        logger.error(f"Error during calculation: {str(e)}")
        return jsonify({"error": str(e), "results": {}})

# -----------------------------------
# Database Config
# -----------------------------------
DB_USERNAME = "5p5ui_r4q7n"
DB_PASSWORD = "290o9522V5DOu3"
DB_NAME     = "property_calc_db"
DB_HOST     = "dedi1504.jnb1.host-h.net"
DB_PORT     = 3306

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get("username")
        password = data.get("password")

        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            database=DB_NAME,
            auth_plugin='mysql_native_password'
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM User WHERE email = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and bcrypt.checkpw(password.encode(), user["password"].encode()):
            session.permanent = True
            session["user"] = username
            session["last_active"] = datetime.now().isoformat()
            logger.info(f"Login successful for user {username}")
            return jsonify({"message": "Login successful", "status": "success", "user": user})
        else:
            logger.warning(f"Login failed for user {username}")
            return jsonify({"message": "Invalid credentials", "status": "error"})

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": str(e), "status": "error"})

@app.route('/logout', methods=['POST'])
def logout():
    user = session.get("user", "Unknown")
    session.clear()
    logger.info(f"User {user} logged out.")
    return jsonify({"message": "Logged out successfully", "status": "success"})

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get("username")
        password = data.get("password")
        email = data.get("email")

        if not username or not password or not email:
            return jsonify({"message": "Missing username, password, or email", "status": "error"})

        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM User WHERE username = %s OR email = %s", (username, email))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"message": "User with that username or email already exists", "status": "error"})

        cursor.execute(
            "INSERT INTO User (username, password, email) VALUES (%s, %s, %s)",
            (username, hashed_password, email)
        )
        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"New user registered: {username}")
        return jsonify({"message": "User registered successfully", "status": "success"})

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({"error": str(e), "status": "error"})

if __name__ == '__main__':
    try:
        app.run(host="127.0.0.1", port=5001, debug=False)
        logger.info("Flask server started successfully.")
    except Exception as e:
        logger.error(f"Failed to start Flask server: {e}")
