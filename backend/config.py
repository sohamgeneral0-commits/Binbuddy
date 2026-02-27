"""
BinBuddy Configuration
Copy this file to config_local.py and fill in your values.
"""
import os
from datetime import timedelta

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'binbuddy-super-secret-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'True') == 'True'

    # Database (MySQL)
    DB_HOST     = os.environ.get('DB_HOST', 'localhost')
    DB_USER     = os.environ.get('DB_USER', 'binbuddy_user')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'binbuddy_pass')
    DB_NAME     = os.environ.get('DB_NAME', 'binbuddy_db')
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY        = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-binbuddy')
    JWT_ACCESS_TOKEN_EXPIRES  = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # MQTT (Mosquitto Broker)
    MQTT_BROKER_HOST = os.environ.get('MQTT_BROKER_HOST', 'localhost')
    MQTT_BROKER_PORT = int(os.environ.get('MQTT_BROKER_PORT', 1883))
    MQTT_KEEPALIVE   = 60
    MQTT_TOPIC_BASE  = 'binbuddy'

    # Security
    # ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5500').split(',')
    # FIXED — added localhost:5000 and 127.0.0.1:5000
    ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000,http://localhost:3000,http://localhost:5500').split(',')
    BCRYPT_LOG_ROUNDS = 12

    # File uploads (complaint + resolution photos)
    UPLOAD_FOLDER   = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB (phone photos can be large)
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
