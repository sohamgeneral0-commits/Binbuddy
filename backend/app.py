"""
BinBuddy - Smart Waste Management System
Main Flask Application
"""

import os
from flask import Flask, render_template, send_from_directory, jsonify
from werkzeug.exceptions import RequestEntityTooLarge
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config
from database import db
# from mqtt_handler import mqtt_client, start_mqtt
from mqtt_handler import start_mqtt
import threading

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
CORS(app, resources={r"/api/*": {"origins": Config.ALLOWED_ORIGINS}})
jwt = JWTManager(app)
db.init_app(app)

# Register blueprints (routes)
from routes.auth import auth_bp
from routes.bins import bins_bp
from routes.complaints import complaints_bp
from routes.collections import collections_bp
from routes.reports import reports_bp
from routes.dashboard import dashboard_bp
from routes.municipal import municipal_bp
from routes.points import points_bp

app.register_blueprint(auth_bp,         url_prefix='/api/auth')
app.register_blueprint(bins_bp,         url_prefix='/api/bins')
app.register_blueprint(complaints_bp,   url_prefix='/api/complaints')
app.register_blueprint(collections_bp,  url_prefix='/api/collections')
app.register_blueprint(reports_bp,      url_prefix='/api/reports')
app.register_blueprint(dashboard_bp,    url_prefix='/api/dashboard')
app.register_blueprint(municipal_bp,    url_prefix='/api/municipal')
app.register_blueprint(points_bp,       url_prefix='/api/points')

# ─── HOMEPAGE ROUTES ───────────────────────────
@app.route('/')
@app.route('/index')
def index():
    """Serve the login/homepage"""
    return render_template('index.html')

# explicit routes for role-specific dashboards (static html files)
# these are simple pages; access control is handled client-side via JS
@app.route('/admin-dashboard.html')
def admin_dashboard():
    return render_template('admin-dashboard.html')

@app.route('/citizen-dashboard.html')
def citizen_dashboard():
    return render_template('citizen-dashboard.html')

@app.route('/worker-dashboard.html')
def worker_dashboard():
    return render_template('worker-dashboard.html')

@app.route('/municipal-dashboard.html')
def municipal_dashboard():
    return render_template('municipal-dashboard.html')


# serve uploaded files (images) from the uploads folder
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename)

# Return JSON for 413 so frontend can show a clear message
@app.errorhandler(RequestEntityTooLarge)
def handle_413(e):
    return jsonify({'error': 'File too large. Maximum size is 16 MB. Try a smaller photo or compress it.'}), 413

# Create DB tables on first run
with app.app_context():
    db.create_all()

    # ensure there is an admin account with a hashed password
    # the values can be overridden via environment variables
    from register import register_admin
    default_email = os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@municipal.gov.in')
    default_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin123')
    register_admin(default_email, default_password)

# Start MQTT listener in background thread
mqtt_thread = threading.Thread(target=start_mqtt, args=(app,), daemon=True)
mqtt_thread.start()

if __name__ == '__main__':
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5000)
