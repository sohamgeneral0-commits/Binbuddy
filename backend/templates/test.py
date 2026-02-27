import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import db, User, Zone

def register_citizen(name, phone, area, municipal_corporation, password, zone_id=None):
    """Register a new citizen using SQLAlchemy"""
    try:
        existing = User.query.filter_by(phone=phone).first()
        if existing:
            return False, "Phone number already registered"
        
        
        user = User(
            name=name,
            email=phone,
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
    """Register a new admin with predefined ID"""
    try:
        
        existing = User.query.filter_by(email=admin_id).first()
        if existing:
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
            return False, "Officer ID already exists"

        user = User(
            name=officer_id,
            email=officer_id,
            password=generate_password_hash(password),
            role='municipal_office', 
            is_approved=False,        
            is_active=True
        )
        
        db.session.add(user)
        db.session.commit()
        return True, {"officer_id": user.id, "message": "Registered. Waiting for approval."}
    except Exception as e:
        db.session.rollback()
        return False, str(e)


def register_worker(area, name, phone, worker_id, password):
    """Register a new worker/collector"""
    try:
   
        existing = User.query.filter_by(email=worker_id).first()
        if existing:
            return False, "Worker ID already exists"
        
        
        existing_phone = User.query.filter_by(phone=phone).first()
        if existing_phone:
            return False, "Phone number already registered"
        
        
        user = User(
            name=name,
            email=worker_id,
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

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    # frontend sends { role, id, password }
    role       = data.get('role')
    identifier = data.get('email') or data.get('id') or ''
    password   = data.get('password')

    # look up by email *or* phone
    user = None
    if identifier:
        user = User.query.filter(
            (User.email == identifier) | (User.phone == identifier)
        ).first()

    # if the client specified a role, require it to match
    if user and role and user.role != role:
        user = None

    valid = False
    if user:
        try:
            valid = check_password_hash(user.password or '', password)
        except ValueError:
            # repair broken entry: treat plaintext match as success and
            # immediately re‑hash the value.
            if user.password == password:
                valid = True
                user.password = generate_password_hash(password)
                db.session.commit()
            else:
                valid = False

    if not valid:
        return jsonify({'error': 'Invalid credentials'}), 401

    if user.role == 'municipal_office' and not user.is_approved:
        return jsonify({'error': 'Your account is pending admin approval.'}), 403

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={'role': user.role}
    )
    return jsonify({
        'access_token': access_token,
        'user': {
            'id':    user.id,
            'name':  user.name,
            'role':  user.role,
            'email': user.email
        }
    }), 200

if __name__ == "__main__":
    print("Registration module loaded successfully")
