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

def safe_float(val):
    try:
        return float(str(val).replace("R", "").replace(",", "").replace("%", "").strip())
    except:
        return 0.0

@app.route('/calculate', methods=['POST'])
def calculate():
    session_timeout_check()
    try:
        logger.info("Received calculation request.")

        wb = xw.load_workbook(EXCEL_PATH, data_only=True)
        igrow_input = wb["IGrow Internal Input"]
        input_data = wb["Input Data"]
        transfer_fees = wb["Transfer Fees"]

        data = request.json
        rate = float(data.get("rate", 2)) / 100
        prop_values = [
            float(data.get("PropValue1", 0)),
            float(data.get("PropValue2", 0)),
            float(data.get("PropValue3", 0)),
            float(data.get("PropValue4", 0)),
            float(data.get("PropValue5", 0))
        ]

        total_prop_value = sum(prop_values)

        def safe_float(val):
            try:
                return float(str(val).replace("R", "").replace(",", "").replace("%", "").strip())
            except:
                return 0.0

        thresholds = [500001, 1000001, 1500001, 2000001, 2500001, 3000001, 3500001,
                      4000001, 4500001, 5000001, 5500001, 6000001, 7000001, 8000001, 9000001, 10000001]
        columns = ['B', 'C', 'D', 'E', 'F', 'G', 'H',
                   'I', 'J', 'K', 'L', 'M', 'O', 'Q', 'S', 'U']

        def calculate_transfer_fee(val):
            for i, threshold in enumerate(thresholds):
                if val < threshold:
                    col = columns[i]
                    unit_cost = safe_float(transfer_fees[f"{col}6"].value)
                    multiplier = safe_float(transfer_fees[f"{col}7"].value)
                    return unit_cost * multiplier
            return 0.0

        multipliers = [safe_float(input_data[f"E{i}"].value) for i in range(20, 25)]

        commission_base = safe_float(input_data["G19"].value)
        commission_parts = [commission_base * multipliers[i] if prop_values[i] > 0 else 0.0 for i in range(4)]
        total_commission = sum(commission_parts)

        incentive_parts = [calculate_transfer_fee(prop_values[i]) * multipliers[i] if prop_values[i] > 0 else 0.0 for i in range(4)]
        total_incentive = sum(incentive_parts)

        total = total_commission + total_incentive
        ctotal = total + total_incentive;
        revenue_rate = (total / total_prop_value) * 100 if total_prop_value > 0 else 0.0

        results = {
            "parameters": [
                ("TransferIncentive", round(total_incentive, 2)),
                ("TotalComm", round(ctotal, 2)),
                ("RevenueRate", round(revenue_rate, 2))
            ]
        }

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
