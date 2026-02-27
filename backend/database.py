"""
BinBuddy Database Models (SQLAlchemy ORM)
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ─────────────────────────────────────────────
# ZONES / WARDS
# ─────────────────────────────────────────────
class Zone(db.Model):
    __tablename__ = 'zones'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    ward_number = db.Column(db.String(20), unique=True, nullable=False)
    city        = db.Column(db.String(100), default='City')
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    bins        = db.relationship('Bin', backref='zone', lazy=True)
    users       = db.relationship('User', backref='zone', lazy=True)

# ─────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────
class User(db.Model):
    __tablename__ = 'users'
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(120), nullable=False)
    email        = db.Column(db.String(200), unique=True, nullable=False)
    password     = db.Column(db.String(255), nullable=False)  # bcrypt hash
    role         = db.Column(db.Enum('admin','collector','citizen','municipal_office'), default='citizen')
    phone        = db.Column(db.String(20))
    zone_id      = db.Column(db.Integer, db.ForeignKey('zones.id'), nullable=True)
    is_approved  = db.Column(db.Boolean, default=False)  # admin must approve collectors
    is_active    = db.Column(db.Boolean, default=True)
    points       = db.Column(db.Integer, default=0)
    tier         = db.Column(db.String(50), default='bronze')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    last_login   = db.Column(db.DateTime, nullable=True)

    # collections  = db.relationship('Collection', backref='collector', lazy=True)
    # complaints   = db.relationship('Complaint', backref='citizen', lazy=True)
    collections  = db.relationship('Collection', backref='collector', lazy=True, foreign_keys='Collection.collector_id')
    complaints   = db.relationship('Complaint', backref='citizen', lazy=True, foreign_keys='Complaint.citizen_id')
    points_ledger = db.relationship('PointsLedger', backref='user', lazy=True, foreign_keys='PointsLedger.user_id')
    user_rewards = db.relationship('UserReward', backref='user', lazy=True)

# ─────────────────────────────────────────────
# BINS
# ─────────────────────────────────────────────
class Bin(db.Model):
    __tablename__ = 'bins'
    id            = db.Column(db.Integer, primary_key=True)
    bin_code      = db.Column(db.String(50), unique=True, nullable=False)  # e.g. BIN-W01-001
    location_name = db.Column(db.String(200))
    # latitude      = db.Column(db.Float, nullable=False)
    # longitude     = db.Column(db.Float, nullable=False)
    # GPS (latitude | longitude) Latitude: 20.8812 | Longitude: 77.747151
    latitude  = db.Column(db.Float, default=20.8812)
    longitude = db.Column(db.Float, default=77.747151)
    capacity_cm   = db.Column(db.Integer, default=100)   # bin depth in cm
    fill_level    = db.Column(db.Float, default=0.0)     # % 0-100
    status        = db.Column(db.Enum('empty','half','full','collected','maintenance'), default='empty')
    zone_id       = db.Column(db.Integer, db.ForeignKey('zones.id'), nullable=False)
    last_updated  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    battery_level = db.Column(db.Float, default=100.0)   # IoT device battery %
    distance_cm   = db.Column(db.Float, default=0.0)     # ← ADD THIS LINE    
    device_id     = db.Column(db.String(100), unique=True)  # ESP8266/ESP32 MAC or ID
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    collections   = db.relationship('Collection', backref='bin', lazy=True)
    complaints    = db.relationship('Complaint', backref='bin', lazy=True)

# ─────────────────────────────────────────────
# COLLECTIONS (garbage pickup events)
# ─────────────────────────────────────────────
class Collection(db.Model):
    __tablename__ = 'collections'
    id             = db.Column(db.Integer, primary_key=True)
    bin_id         = db.Column(db.Integer, db.ForeignKey('bins.id'), nullable=False)
    collector_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    collected_at   = db.Column(db.DateTime, default=datetime.utcnow)
    fill_at_collection = db.Column(db.Float)    # fill% when collected
    notes          = db.Column(db.Text)
    verified       = db.Column(db.Boolean, default=False)

# ─────────────────────────────────────────────
# COMPLAINTS
# ─────────────────────────────────────────────
class Complaint(db.Model):
    __tablename__ = 'complaints'
    id           = db.Column(db.Integer, primary_key=True)
    citizen_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bin_id       = db.Column(db.Integer, db.ForeignKey('bins.id'), nullable=True)
    category     = db.Column(db.Enum('overflow','damage','missing','smell','other'), default='overflow')
    description  = db.Column(db.Text)
    image_path   = db.Column(db.String(300))
    status       = db.Column(db.Enum('open','in_progress','resolved','closed'), default='open')
    priority     = db.Column(db.Enum('low','medium','high'), default='medium')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at  = db.Column(db.DateTime, nullable=True)
    assigned_to  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolution_photo_path = db.Column(db.String(300), nullable=True)  # worker uploads when marking complete
    overdue_notification_sent = db.Column(db.Boolean, default=False)   # notify municipal once when >5h

# ─────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────
class Notification(db.Model):
    __tablename__ = 'notifications'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # NULL = broadcast
    title       = db.Column(db.String(200))
    message     = db.Column(db.Text)
    type        = db.Column(db.Enum('alert','info','warning','success'), default='info')
    is_read     = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

# ─────────────────────────────────────────────
# TRUCKS (optional)
# ─────────────────────────────────────────────
class Truck(db.Model):
    __tablename__ = 'trucks'
    id            = db.Column(db.Integer, primary_key=True)
    vehicle_number= db.Column(db.String(50), unique=True, nullable=False)
    driver_name   = db.Column(db.String(120))
    zone_id       = db.Column(db.Integer, db.ForeignKey('zones.id'), nullable=True)
    status        = db.Column(db.Enum('available','on_route','maintenance'), default='available')
    last_lat      = db.Column(db.Float)
    last_lng      = db.Column(db.Float)
    last_seen     = db.Column(db.DateTime)

# ─────────────────────────────────────────────
# AUDIT LOGS
# ─────────────────────────────────────────────
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action     = db.Column(db.String(200))
    entity     = db.Column(db.String(100))
    entity_id  = db.Column(db.Integer)
    details    = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────────
# REWARDS & POINTS SYSTEM
# ─────────────────────────────────────────────
class Reward(db.Model):
    __tablename__ = 'rewards'
    id               = db.Column(db.Integer, primary_key=True)
    name             = db.Column(db.String(255), nullable=False)
    description      = db.Column(db.Text)
    points_required  = db.Column(db.Integer, nullable=False)
    category         = db.Column(db.String(50))  # e.g., 'voucher', 'gift', 'discount'
    reward_type      = db.Column(db.Enum('discount','voucher','gift','badge'), default='voucher')
    value            = db.Column(db.String(100))  # e.g., '500', 'Pizza Voucher', etc
    is_active        = db.Column(db.Boolean, default=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    user_rewards     = db.relationship('UserReward', backref='reward', lazy=True)

class PointsLedger(db.Model):
    __tablename__ = 'points_ledger'
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=True)
    points_earned = db.Column(db.Integer, nullable=False)
    reason       = db.Column(db.String(255))
    action_type  = db.Column(db.Enum('complaint_filed','complaint_resolved','complaint_validated','early_resolve','quality_report'), default='complaint_filed')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

class UserReward(db.Model):
    __tablename__ = 'user_rewards'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reward_id   = db.Column(db.Integer, db.ForeignKey('rewards.id'), nullable=False)
    redeemed_at = db.Column(db.DateTime, default=datetime.utcnow)
    status      = db.Column(db.Enum('pending','claimed','expired'), default='pending')
    claim_code  = db.Column(db.String(100), unique=True)

# ─────────────────────────────────────────────
# BIN REQUESTS (municipal requests for new bin planting)
# ─────────────────────────────────────────────
class BinRequest(db.Model):
    __tablename__ = 'bin_requests'
    id           = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    zone_id      = db.Column(db.Integer, db.ForeignKey('zones.id'), nullable=True)
    location_name= db.Column(db.String(200))
    latitude     = db.Column(db.Float, default=0)
    longitude    = db.Column(db.Float, default=0)
    notes        = db.Column(db.Text)
    status       = db.Column(db.Enum('pending','approved','rejected'), default='pending')
    reviewed_by  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at  = db.Column(db.DateTime, nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
