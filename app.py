from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import qrcode
import base64
from io import BytesIO
import datetime
import os
import json
from flask_cors import CORS
import logging
from flask_cors import cross_origin
from PIL import Image, ImageDraw

app = Flask(__name__, static_folder='static')
app.secret_key = 'SIMON!'

CORS(app, resources={r"/*": {"origins": "*"}})
logging.basicConfig(level=logging.DEBUG)  # Enable logging for debugging


# MySQL database connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="don05@Simon",
    database="bikesystem",
    port = 3307
)
cursor = conn.cursor(dictionary=True)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --------------------- ROUTES --------------------- #


@app.route('/')
def home():
    return send_from_directory("scanner", "scanner.html")
# Admin Login
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
        admin = cursor.fetchone()
        
        if admin and check_password_hash(admin['password'], password):
            session['admin'] = admin['username']
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()  # Fetch the user data

    
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    for user in users:
        print(f"User: {user['name']}, Image Path: {user['image_path']}")  # Debug print
    


    cursor.execute("""
        SELECT name, email, type, entry_time, exit_time
        FROM usage_logs
    """)
    logs = cursor.fetchall()

    return render_template('admin_dashboard.html', users=users, logs=logs)


@app.route('/admin/generate-pass', methods=['POST'])
def admin_generate_pass():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    # Get user_id from the form
    user_id = request.form['user_id']
    
    # Fetch the user's details from the database using the user_id
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('admin_dashboard'))
    
    # Retrieve image filename from the database
    image_filename = user.get('image_path')  # Ensure 'image_path' is a column in your users table
    
    # Set a default image if no image is found for the user
    if not image_filename:
        image_filename = "default_image.jpg"  # A fallback image stored in your 'static/uploads' folder

    # Generate QR Code data
    user_email = user['email']
    qr_data = f"Name: {user['name']}\nEmail: {user_email}\nType: {user['user_type']}"
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    # Save the QR Code to memory as a base64-encoded string
    qr_image = BytesIO()
    qr.make_image(fill='black', back_color='white').save(qr_image)
    qr_image.seek(0)
    qr_base64 = base64.b64encode(qr_image.read()).decode('utf-8')
    
    # Update the user's pass status to active in the database
    cursor.execute("UPDATE users SET pass_status = 'active' WHERE id = %s", (user_id,))
    conn.commit()

    # Render the same page to display the QR code and user's image
    return render_template(
        'generate_pass.html',
        qr_code=qr_base64,
        user=user,
        image_filename=image_filename,  # Pass the retrieved image filename to the template
        success=True
    )

@app.route('/admin/pass/<int:user_id>/<action>', methods=['POST'])
def manage_pass(user_id, action):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    # Process the action, disable or enable the user's pass
    if action == 'disable':
        cursor.execute("UPDATE users SET pass_status = 'disabled' WHERE id = %s", (user_id,))
    elif action == 'enable':
        cursor.execute("UPDATE users SET pass_status = 'active' WHERE id = %s", (user_id,))
    
    conn.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user'] = user  # Store user details in session
            return redirect(url_for('user_dashboard'))  
        else:
            flash('Invalid email or password', 'error')

    return render_template('login.html')


@app.route('/user/dashboard', methods=['GET'])
def user_dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))  


    user = session['user']  
    print("Image Path for User:", user.get('image_path'))  # Debug statement
   
    return render_template('user_dashboard.html', user=user)


@app.route('/user/generate_pass', methods=['POST'])
def generate_pass():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user = session['user']
    
    
    
    
   
    # Generate details
    qr_data = f"Name: {user['name']}\nEmail: {user['email']}\nType: {user['user_type']}"
       
    
    
    # Generate QR code
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(qr_data)  # Add JSON data
    qr.make(fit=True)

    # Save the QR code to memory as a base64-encoded string
    qr_image = BytesIO()
    qr.make_image(fill='black', back_color='white').save(qr_image)
    qr_image.seek(0)
    qr_base64 = base64.b64encode(qr_image.read()).decode('utf-8')

    # Render the template with the generated QR code
    return render_template('generate_pass.html', user=user, qr_code=qr_base64)




@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']
        valid_until = request.form.get('valid_until')
        
        # Hash the password
        hashed_password = generate_password_hash(password, method='scrypt')

        # Handle image upload
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

        def allowed_file(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

        if 'image' in request.files and allowed_file(request.files['image'].filename):
            image = request.files['image']
            image_filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename).replace("\\", "/")
            image.save(image_path)
            image_file = f"uploads/{image_filename}"  # Save the relative path to the image
        else:
            image_file = None
        
        if user_type == "Bicycle":
            bike_color = request.form['bike_color']
            bike_type = request.form['bike_type']
            cursor.execute("""
                INSERT INTO users (name, email, password, user_type, bike_color, bike_type, valid_until, image_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, email, hashed_password, user_type, bike_color, bike_type, valid_until, image_file))
        elif user_type == "Motorbike":
            motorbike_registration = request.form['motorbike_registration']
            motorbike_model = request.form['motorbike_model']
            cursor.execute("""
                INSERT INTO users (name, email, password, user_type, motorbike_registration, motorbike_model, valid_until, image_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, email, hashed_password, user_type, motorbike_registration, motorbike_model, valid_until, image_file))
        elif user_type == "Car":
            car_color = request.form['car_color']
            car_model = request.form['car_model']
            car_registration = request.form['car_registration']
            cursor.execute("""
                INSERT INTO users (name, email, password, user_type, car_color, car_model, car_registration, valid_until, image_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, email, hashed_password, user_type, car_color, car_model, car_registration, valid_until, image_file))

        conn.commit()
        return redirect(url_for('login'))
    return render_template('register.html')





@app.route('/scan_qr', methods=['POST'])
@cross_origin()
def scan_qr():
    """
    Handles QR code data sent from the frontend.
    Logs entry/exit times for users based on QR code data.
    """
    try:
        # Get JSON data from the request
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid or missing JSON data"}), 400

        # Extract QR data
        qr_data = data.get('qrData')
        if not qr_data:
            return jsonify({"error": "Missing 'qrData' in the request body"}), 400

        # Clean and parse the QR data string
        qr_data = qr_data.replace("\\n", "\n").strip().strip('"')
        parsed_data = {}
        for line in qr_data.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                parsed_data[key.strip().lower()] = value.strip()

        # Extract fields
        name = parsed_data.get("name")
        email = parsed_data.get("email")
        user_type = parsed_data.get("type")

        # Validate required fields
        if not all([name, email, user_type]):
            return jsonify({"error": "Invalid data. 'name', 'email', and 'type' are required."}), 400

        # Log received and parsed data
        app.logger.info(f"Received QR Data: {qr_data}")
        app.logger.info(f"Parsed QR Data: {parsed_data}")
        app.logger.info(f"Extracted Name: {name}, Email: {email}, Type: {user_type}")

        # Check if the user exists in the database
        cursor.execute("""
            SELECT * FROM users WHERE email = %s AND name = %s
        """, (email, name))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": f"User {name} with email {email} not found in the database."}), 404

        # Check for an active (entry-only) log
        cursor.execute("""
            SELECT * FROM usage_logs
            WHERE name = %s AND email = %s AND exit_time IS NULL
            ORDER BY entry_time DESC LIMIT 1
        """, (name, email))
        active_log = cursor.fetchone()

        if active_log:
            # Log exists -> Update with exit time
            exit_time = datetime.datetime.now()
            cursor.execute("""
                UPDATE usage_logs
                SET exit_time = %s
                WHERE id = %s
            """, (exit_time, active_log['id']))
            conn.commit()

            return jsonify({
                "success": True,
                "message": f"Exit time logged successfully for user {name}.",
                "log_entry": {
                    "name": name,
                    "email": email,
                    "type": user_type,
                    "entry_time": active_log['entry_time'],
                    "exit_time": exit_time.isoformat()
                }
            }), 200
        else:
            # No active log -> Create a new entry
            entry_time = datetime.datetime.now()
            cursor.execute("""
                INSERT INTO usage_logs (name, email, type, entry_time)
                VALUES (%s, %s, %s, %s)
            """, (name, email, user_type, entry_time))
            conn.commit()

            return jsonify({
                "success": True,
                "message": f"Entry time logged successfully for user {name}.",
                "log_entry": {
                    "name": name,
                    "email": email,
                    "type": user_type,
                    "entry_time": entry_time.isoformat(),
                    "exit_time": None
                }
            }), 200

    except Exception as e:
        app.logger.error(f"An error occurred while processing QR data: {str(e)}")
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port = 500)
