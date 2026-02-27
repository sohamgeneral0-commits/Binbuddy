"""
BinBuddy Auth Routes - Updated for Role-Based Registration
POST /api/auth/register - Register new user based on role
POST /api/auth/login    - Login with role, ID, and password
POST /api/auth/refresh
GET  /api/auth/me
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from werkzeug.security import check_password_hash, generate_password_hash
import bcrypt
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db, User, AuditLog, Zone, Notification
from config import Config
from register import (
    register_citizen, register_admin, 
    register_municipal_corporation, register_worker
)

auth_bp = Blueprint('auth', __name__)

def _log(user_id, action, ip, details=''):
    """Write every important action to audit_logs table."""
    log = AuditLog(
        user_id    = user_id,
        action     = action,
        entity     = 'User',
        entity_id  = user_id,
        ip_address = ip,
        details    = details
    )
    db.session.add(log)

# ─── REGISTER ─────────────────────────────────
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    role = data.get('role', '').strip()

    if not role:
        return jsonify({'error': 'Missing role'}), 400

    try:
        success = False
        result  = None

        if role == 'citizen':
            # Simplified for UI matching
            success, result = register_citizen(
                name=data.get('name', ''),
                phone=data.get('phone', ''),
                area=data.get('area', 'General'),
                municipal_corporation=data.get('municipal', 'City Council'),
                password=data.get('password', '')
            )
        elif role == 'municipal_office':  # Standardized name
            success, result = register_municipal_corporation(
                city=data.get('city', ''),
                officer_id=data.get('officer_id', ''),
                password=data.get('password', '')
            )
        elif role == 'admin':
            success, result = register_admin(
                admin_id=data.get('admin_id', ''),
                password=data.get('password', '')
            )
        elif role == 'collector' or role == 'worker':
            success, result = register_worker(
                area=data.get('area', ''),
                name=data.get('name', ''),
                phone=data.get('phone', ''),
                password=data.get('password', '')
            )
        else:
            return jsonify({'error': 'Invalid role'}), 400

        if not success:
            # result contains error message from helper
            return jsonify({'error': result}), 400

        return jsonify({'message': 'Registration successful', 'data': result}), 201
    except Exception as e:
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500
# def register():
#     data = request.get_json(silent=True) or {}
#     role = data.get('role', '').strip()

#     if not role:
#         return jsonify({'error': 'Missing role'}), 400

#     try:
#         # Handle Citizen Registration
#         if role == 'citizen':
#             required_fields = ['name', 'phone', 'area', 'municipal_corporation', 'password']
#             for field in required_fields:
#                 if not data.get(field):
#                     return jsonify({'error': f'Missing field for citizen: {field}'}), 400
            
#             success, result = register_citizen(
#                 name=data['name'],
#                 phone=data['phone'],
#                 area=data['area'],
#                 municipal_corporation=data['municipal_corporation'],
#                 password=data['password']
#             )

#         # Handle Admin Registration
#         elif role == 'admin':
#             required_fields = ['admin_id', 'password']
#             for field in required_fields:
#                 if not data.get(field):
#                     return jsonify({'error': f'Missing field for admin: {field}'}), 400
            
#             success, result = register_admin(
#                 admin_id=data['admin_id'],
#                 password=data['password']
#             )

#         # Handle Municipal Corporation Registration
#         elif role == 'municipal_corporation':
#             required_fields = ['city', 'officer_id', 'password']
#             for field in required_fields:
#                 if not data.get(field):
#                     return jsonify({'error': f'Missing field for municipal corporation: {field}'}), 400
            
#             success, result = register_municipal_corporation(
#                 city=data['city'],
#                 officer_id=data['officer_id'],
#                 password=data['password']
#             )

#         # Handle Worker Registration
#         elif role == 'worker':
#             required_fields = ['area', 'name', 'phone', 'worker_id', 'password']
#             for field in required_fields:
#                 if not data.get(field):
#                     return jsonify({'error': f'Missing field for worker: {field}'}), 400
            
#             success, result = register_worker(
#                 area=data['area'],
#                 name=data['name'],
#                 phone=data['phone'],
#                 worker_id=data['worker_id'],
#                 password=data['password']
#             )

#         else:
#             return jsonify({'error': 'Invalid role'}), 400

#         if not success:
#             return jsonify({'error': result}), 400

#         return jsonify({'message': 'Registration successful', 'data': result}), 201

#     except Exception as e:
#         return jsonify({'error': f'Registration failed: {str(e)}'}), 500

# ─── LOGIN ────────────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    # frontend sends { role, id, password }; older clients may send email
    role = data.get('role')
    identifier = data.get('email') or data.get('id') or ''
    password = data.get('password')

    # look up by email or phone (we stored citizens' phone in email field, but
    # just in case a numeric id is used elsewhere we'll check phone column too)
    user = None
    if identifier:
        user = User.query.filter(
            (User.email == identifier) | (User.phone == identifier)
        ).first()

    # if role provided, ensure it matches the user; otherwise treat as failure
    # UI shows "Worker" but DB stores role as 'collector' — accept both
    if user and role:
        role_match = (user.role == role) or (role == 'worker' and user.role == 'collector')
        if not role_match:
            user = None

    # default to False and handle exceptions so bad hashes don't crash
    valid = False
    if user:
        try:
            valid = check_password_hash(user.password or '', password)
        except ValueError:
            # fix broken entry: plaintext password? upgrade to hashed
            if user.password == password:
                valid = True
                user.password = generate_password_hash(password)
                db.session.commit()
            else:
                valid = False

    if not valid:
        return jsonify({'error': 'Invalid credentials'}), 401

    # CRITICAL: Prevent unapproved municipal offices from logging in
    if user.role == 'municipal_office' and not user.is_approved:
        return jsonify({'error': 'Your account is pending admin approval.'}), 403

    access_token = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
    return jsonify({
        'access_token': access_token,
        'user': {
            'id': user.id,
            'name': user.name,
            'role': user.role,
            'email': user.email
        }
    }), 200
# def login():
#     data = request.get_json(silent=True) or {}
#     email = data.get('email', '').strip() # Changed from 'id' to 'email' to match UI
#     password = data.get('password', '')

#     user = User.query.filter((User.email == email) | (User.phone == email)).first()
    
#     if not user or not check_password_hash(user.password, password):
#         return jsonify({'error': 'Invalid credentials'}), 401

#     # FIX: Check for Approval
#     if user.role == 'municipal_office' and not user.is_approved:
#         return jsonify({'error': 'Account pending admin approval'}), 403
    
#     if not user.is_active:
#         return jsonify({'error': 'Account deactivated'}), 403

#     access_token = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
#     return jsonify({
#         'access_token': access_token,
#         'user': {'name': user.name, 'role': user.role, 'email': user.email}
#     }), 200

# def login():
#     data     = request.get_json(silent=True) or {}
#     role     = data.get('role', '').strip()
#     user_id  = data.get('id', '').strip()
#     password = data.get('password', '')
#     ip       = request.remote_addr

#     if not all([role, user_id, password]):
#         return jsonify({'error': 'Missing login credentials'}), 400

#     try:
#         user = None
        
#         # For citizens: search by phone (which is stored as email)
#         if role == 'citizen':
#             user = User.query.filter(
#                 (User.email == user_id) | (User.phone == user_id) | (User.name == user_id)
#             ).filter_by(role='citizen').first()
#         else:
#             # For other roles: search by email
#             user = User.query.filter_by(email=user_id, role=role).first()
        
#         if not user:
#             print(f"DEBUG: User not found for {role} with id={user_id}")
#             return jsonify({'error': 'Invalid credentials'}), 401
        
#         print(f"DEBUG: User found: {user.name}, checking password...")
        
#         # Verify password
#         if not check_password_hash(user.password, password):
#             print(f"DEBUG: Password mismatch for user {user.name}")
#             return jsonify({'error': 'Invalid credentials'}), 401
        
#         print(f"DEBUG: Login successful for {user.name}")
        
#         # Update last login
#         user.last_login = datetime.utcnow()
#         db.session.commit()
        
#         # Build response
#         response_user = {
#             'id': user.id,
#             'name': user.name,
#             'email': user.email,
#             'role': user.role,
#             'phone': user.phone,
#             'zone_id': user.zone_id
#         }
        
#         # Log the login action
#         _log(user.id, f'{role}_login', ip)

#         # Generate tokens
#         access_token  = create_access_token(
#             identity=str(user.id),
#             additional_claims={'role': role, 'user_id': user.id}
#         )
#         refresh_token = create_refresh_token(identity=str(user.id))

#         return jsonify({
#             'access_token' : access_token,
#             'refresh_token': refresh_token,
#             'user': response_user
#         }), 200

#     except Exception as e:
#         return jsonify({'error': f'Login failed: {str(e)}'}), 500

# Continue with existing endpoints...
# ─── REFRESH TOKEN ────────────────────────────
@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    try:
        user = User.query.get(int(identity))
        if not user:
            return jsonify({'error': 'User not found'}), 404
        new_token = create_access_token(identity=identity,
                                        additional_claims={'role': user.role})
        return jsonify({'access_token': new_token}), 200
    except:
        return jsonify({'access_token': create_access_token(identity=identity)}), 200

# ─── ME ───────────────────────────────────────
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    uid  = int(get_jwt_identity())
    try:
        user = User.query.get(uid)
        if not user:
            return jsonify({'error': 'Not found'}), 404
        return jsonify({
            'id':      user.id,
            'name':    user.name,
            'email':   user.email,
            'role':    user.role,
            'zone_id': user.zone_id,
            'phone':   user.phone
        }), 200
    except:
        return jsonify({'error': 'User lookup failed'}), 500

# ─── NOTIFICATIONS (for municipal / dashboard) ──
@auth_bp.route('/notifications', methods=['GET'])
@jwt_required()
def list_notifications():
    uid = int(get_jwt_identity())
    query = Notification.query.filter(
        (Notification.user_id == uid) | (Notification.user_id == None)
    ).order_by(Notification.created_at.desc()).limit(50)
    items = query.all()
    unread = sum(1 for n in items if not n.is_read)
    return jsonify({
        'unread_count': unread,
        'notifications': [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.type,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat() if n.created_at else None
        } for n in items]
    }), 200

@auth_bp.route('/notifications/<int:nid>/read', methods=['PUT'])
@jwt_required()
def mark_notification_read(nid):
    n = Notification.query.get_or_404(nid)
    if n.user_id and n.user_id != int(get_jwt_identity()):
        return jsonify({'error': 'Forbidden'}), 403
    n.is_read = True
    db.session.commit()
    return jsonify({'message': 'OK'}), 200

# ─── APPROVE USER (Admin only) ────────────────
@auth_bp.route('/approve/<int:user_id>', methods=['PUT'])
@jwt_required()
def approve_user(user_id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Forbidden — admins only'}), 403

    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user.is_approved = True
        _log(int(get_jwt_identity()), 'APPROVE_USER',
             request.remote_addr, f"Approved user: {user.name} ({user.email})")
        db.session.commit()
        return jsonify({'message': f'{user.name} approved successfully'}), 200
    except:
        return jsonify({'error': 'Approval failed'}), 500

# ─── LIST ALL USERS (Admin only) ──────────────
@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403

    try:
        role   = request.args.get('role')    # optional filter
        query  = User.query
        if role:
            query = query.filter_by(role=role)
        users  = query.order_by(User.created_at.desc()).all()

        return jsonify([{
            'id'         : u.id,
            'name'       : u.name,
            'email'      : u.email,
            'role'       : u.role,
            'phone'      : u.phone,
            'zone_id'    : u.zone_id,
            'is_approved': u.is_approved,
            'is_active'  : u.is_active,
            'created_at' : u.created_at.strftime('%d %b %Y, %I:%M %p'),
            'last_login' : u.last_login.strftime('%d %b %Y, %I:%M %p') if u.last_login else 'Never'
        } for u in users]), 200
    except:
        return jsonify({'error': 'Failed to fetch users'}), 500

# ─── LOGIN HISTORY (Admin only) ───────────────
@auth_bp.route('/login-logs', methods=['GET'])
@jwt_required()
def login_logs():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403

    try:
        logs = AuditLog.query\
            .filter(AuditLog.action.in_(['LOGIN_SUCCESS', 'LOGIN_FAILED', 'REGISTER']))\
            .order_by(AuditLog.created_at.desc())\
            .limit(100).all()

        result = []
        for log in logs:
            user = User.query.get(log.user_id) if log.user_id else None
            result.append({
                'id'        : log.id,
                'user_name' : user.name  if user else 'Unknown',
                'user_email': user.email if user else '—',
                'user_role' : user.role  if user else '—',
                'action'    : log.action,
                'ip_address': log.ip_address,
                'details'   : log.details,
                'time'      : log.created_at.strftime('%d %b %Y, %I:%M:%S %p')
            })
        return jsonify(result), 200
    except:
        return jsonify({'error': 'Failed to fetch logs'}), 500

# ─── DEACTIVATE USER (Admin only) ─────────────
@auth_bp.route('/users/<int:user_id>/deactivate', methods=['PUT'])
@jwt_required()
def deactivate_user(user_id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    try:
        user = User.query.get_or_404(user_id)
        user.is_active = False
        db.session.commit()
        return jsonify({'message': f'{user.name} deactivated'}), 200
    except:
        return jsonify({'error': 'Failed to deactivate user'}), 500

# ─── GET ZONES (for registration dropdown) ────
@auth_bp.route('/zones', methods=['GET'])
def get_zones():
    try:
        zones = Zone.query.all()
        return jsonify([{
            'id'         : z.id,
            'name'       : z.name,
            'ward_number': z.ward_number
        } for z in zones]), 200
    except:
        return jsonify({'error': 'Failed to fetch zones'}), 500





