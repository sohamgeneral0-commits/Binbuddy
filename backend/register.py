import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import db, User, Zone


# helper functions --------------------------------------------------------

def _is_hash_string(pwhash: str) -> bool:
    """Return True if the value looks like a werkzeug hash (method$salt$hash)."""
    if not pwhash or '$' not in pwhash:
        return False
    parts = pwhash.split('$')
    # valid hashes have at least three parts and a non-empty method
    return len(parts) >= 3 and bool(parts[0])


def _ensure_hashed(user: User, raw_password: str) -> None:
    """If the user has a non‑hash password, hash the given raw_password and save.

    This allows us to automatically upgrade accounts that were created with
    plaintext or empty passwords.
    """
    if not _is_hash_string(user.password):
        user.password = generate_password_hash(raw_password)
        db.session.commit()

def register_citizen(name, phone, area, municipal_corporation, password, zone_id=None):
    """Register a new citizen using SQLAlchemy.

    If a record already exists but the stored password is not a valid hash,
    we re‑hash the provided password and keep the existing user rather than
    failing with "already registered".  This helps recover accounts that
    were created incorrectly.
    """
    try:
        existing = User.query.filter_by(phone=phone).first()
        if existing:
            if not _is_hash_string(existing.password):
                _ensure_hashed(existing, password)
                return True, {"user_id": existing.id, "message": "Password updated"}
            return False, "Phone number already registered"

        user = User(
            name=name,
            email=phone,  # Use phone as email if not provided
            password=generate_password_hash(password),
            role='citizen',
            phone=phone,
            zone_id=zone_id,
            is_approved=False,
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        return True, {"user_id": user.id, "message": "Citizen registered successfully"}
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def register_admin(admin_id, password):
    """Register a new admin with predefined ID.

    If the account already exists but the password is not a valid hash, update
    it to the new value instead of failing.  This lets you call
    ``register_admin`` again to reset a broken admin row.
    """
    try:
        existing = User.query.filter_by(email=admin_id).first()
        if existing:
            if not _is_hash_string(existing.password):
                _ensure_hashed(existing, password)
                return True, {"admin_id": existing.id, "message": "Admin password updated"}
            return False, "Admin ID already exists"

        user = User(
            name=admin_id,
            email=admin_id,
            password=generate_password_hash(password),
            role='admin',
            is_approved=True,
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        return True, {"admin_id": user.id, "message": "Admin registered successfully"}
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def register_municipal_corporation(city, officer_id, password):
    try:
        existing = User.query.filter_by(email=officer_id).first()
        if existing:
            if not _is_hash_string(existing.password):
                _ensure_hashed(existing, password)
                return True, {"officer_id": existing.id, "message": "Password updated. Waiting for approval."}
            return False, "Officer ID already exists"

        user = User(
            name=officer_id,
            email=officer_id,
            password=generate_password_hash(password),
            role='municipal_office', # MUST match database.py Enum
            is_approved=False,        # Set to False so Admin must approve
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        return True, {"officer_id": user.id, "message": "Registered. Waiting for approval."}
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def register_worker(area, name, phone, password):
    """Register a new worker/collector using phone as identifier"""
    try:
        # Check if phone already registered
        existing = User.query.filter_by(phone=phone).first()
        if existing:
            if not _is_hash_string(existing.password):
                _ensure_hashed(existing, password)
                return True, {"worker_id": existing.id, "message": "Worker password updated"}
            return False, "Phone number already registered"
        
        # Create worker user
        user = User(
            name=name,
            email=phone,  # Use phone as email/identifier
            password=generate_password_hash(password),
            role='collector',
            phone=phone,
            is_approved=False,
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        return True, {"worker_id": user.id, "message": "Worker registered successfully"}
    except Exception as e:
        db.session.rollback()
        return False, str(e)

# The helper ``login_user`` and custom password check functions were
# previously defined here but they duplicated Werkzeug's logic and were
# incorrectly implemented.  All authentication now happens in
# ``routes/auth.py`` using ``werkzeug.security`` helpers.  The functions
# below are intentionally removed to avoid confusion.

if __name__ == "__main__":
    print("Registration module loaded successfully")
