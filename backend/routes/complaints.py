"""
BinBuddy Complaints API
GET  /api/complaints/          - list (admin: all, citizen: own)
POST /api/complaints/          - submit complaint
PUT  /api/complaints/<id>      - update status (admin/collector)
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
from config import Config
from database import db, Complaint, User, Bin, Notification, PointsLedger

complaints_bp = Blueprint('complaints', __name__)

@complaints_bp.route('/', methods=['GET'])
@jwt_required()
def list_complaints():
    uid    = int(get_jwt_identity())
    claims = get_jwt()
    role   = claims.get('role')

    query = Complaint.query
    if role == 'citizen':
        query = query.filter_by(citizen_id=uid)
    # admin, municipal_office, collector, worker (and any other role) see ALL complaints
    # so workers can complete any complaint

    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    items = query.order_by(Complaint.created_at.desc()).all()
    # For overdue complaints, send notification to municipal once
    _send_overdue_notifications_if_needed(items)
    return jsonify([_ser(c) for c in items]), 200

@complaints_bp.route('/', methods=['POST'])
@jwt_required()
def submit_complaint():
    try:
        uid  = int(get_jwt_identity())
        # Handle both JSON and form-data
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = request.form.to_dict() or {}

        image_path = None
        # accept either 'photo' or 'image' file field from the client
        file = None
        if 'photo' in request.files:
            file = request.files['photo']
        elif 'image' in request.files:
            file = request.files['image']

        if file and file.filename and _allowed(file.filename):
            fname = secure_filename(file.filename)
            save_dir = os.path.join(Config.UPLOAD_FOLDER, 'complaints')
            os.makedirs(save_dir, exist_ok=True)
            # include timestamp to avoid name collisions
            import time
            fpath = os.path.join(save_dir, f"{uid}_{int(time.time())}_{fname}")
            file.save(fpath)
            image_path = fpath

        c = Complaint(
            citizen_id  = uid,
            bin_id      = data.get('bin_id'),
            category    = data.get('category', 'other'),
            description = data.get('description', ''),
            image_path  = image_path,
            priority    = data.get('priority', 'medium')
        )
        db.session.add(c)
        db.session.commit()
        
        # Award points to citizen for filing complaint
        _award_points(uid, c.id, 10, 'complaint_filed', 'Filed a complaint')
        
        return jsonify({'message': 'Complaint submitted', 'id': c.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Complaint submission failed: {str(e)}'}), 500

def _send_overdue_notifications_if_needed(items):
    """For each overdue complaint, create one notification for municipal users if not already sent."""
    try:
        for c in items:
            if c.status in ('resolved', 'closed') or not c.created_at:
                continue
            threshold = c.created_at + timedelta(hours=5)
            if datetime.utcnow() < threshold:
                continue
            if getattr(c, 'overdue_notification_sent', False):
                continue
            municipal_users = User.query.filter_by(role='municipal_office', is_active=True).all()
            for u in municipal_users:
                n = Notification(
                    user_id=u.id,
                    title='Overdue complaint',
                    message=f'Complaint #{c.id} ({c.category}) has not been completed within 5 hours. Please follow up.',
                    type='alert'
                )
                db.session.add(n)
            c.overdue_notification_sent = True
        db.session.commit()
    except Exception:
        db.session.rollback()


@complaints_bp.route('/<int:cid>', methods=['PUT'])
@jwt_required()
def update_complaint(cid):
    claims = get_jwt()
    if claims.get('role') not in ('admin', 'collector', 'worker', 'municipal_office'):
        return jsonify({'error': 'Forbidden'}), 403

    c = Complaint.query.get_or_404(cid)
    data = request.get_json(silent=True) or {}
    # Support multipart: worker completes with photo
    if not data and request.form:
        data = request.form.to_dict() or {}
    if request.files and 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename and _allowed(file.filename):
            import time
            save_dir = os.path.join(Config.UPLOAD_FOLDER, 'complaints', 'resolved')
            os.makedirs(save_dir, exist_ok=True)
            fpath = os.path.join(save_dir, f"resolved_{cid}_{int(time.time())}_{secure_filename(file.filename)}")
            file.save(fpath)
            c.resolution_photo_path = fpath
    if request.files and 'image' in request.files and not c.resolution_photo_path:
        file = request.files['image']
        if file and file.filename and _allowed(file.filename):
            import time
            save_dir = os.path.join(Config.UPLOAD_FOLDER, 'complaints', 'resolved')
            os.makedirs(save_dir, exist_ok=True)
            fpath = os.path.join(save_dir, f"resolved_{cid}_{int(time.time())}_{secure_filename(file.filename)}")
            file.save(fpath)
            c.resolution_photo_path = fpath

    if data.get('status') == 'resolved':
        # Worker must upload photo to complete (admin/municipal can resolve without photo)
        role = claims.get('role')
        if role in ('collector', 'worker') and not c.resolution_photo_path and not request.files:
            return jsonify({'error': 'Please upload a photo to mark this complaint as complete'}), 400
        
        # Award points to worker for resolving complaint
        worker_id = claims.get('sub') if isinstance(claims.get('sub'), int) else int(claims.get('sub', 0))
        points = 30  # Base points for resolving
        
        # Bonus: early resolution (within 24 hours)
        if c.created_at and (datetime.utcnow() - c.created_at) <= timedelta(hours=24):
            points += 20
            reason = 'Resolved complaint within 24 hours'
            action_type = 'early_resolve'
        else:
            reason = 'Resolved complaint'
            action_type = 'complaint_resolved'
        
        _award_points(worker_id, c.id, points, action_type, reason)
        
        c.status = 'resolved'
        c.resolved_at = datetime.utcnow()
    elif 'status' in data:
        c.status = data['status']
        if data['status'] == 'resolved':
            c.resolved_at = datetime.utcnow()
    if 'priority' in data:
        c.priority = data['priority']
    if 'assigned_to' in data:
        c.assigned_to = data['assigned_to']
    db.session.commit()
    return jsonify({'message': 'Updated'}), 200

def _ser(c):
    assigned_worker = User.query.get(c.assigned_to) if c.assigned_to else None
    bin_loc = c.bin.location_name if c.bin else None
    zone_id = c.bin.zone_id if c.bin else None
    zone = c.bin.zone if c.bin else None
    area_name = (zone.name if zone else None) or (f"Ward {zone_id}" if zone_id else "General")
    # Overdue: not resolved and created > 5 hours ago
    overdue = False
    if c.status not in ('resolved', 'closed') and c.created_at:
        threshold = c.created_at + timedelta(hours=5)
        overdue = datetime.utcnow() >= threshold
    return {
        'id':          c.id,
        'citizen_id':  c.citizen_id,
        'bin_id':      c.bin_id,
        'bin_location': bin_loc,
        'category':    c.category,
        'description': c.description,
        'status':      c.status,
        'priority':    c.priority,
        'created_at':  c.created_at.isoformat(),
        'resolved_at': c.resolved_at.isoformat() if c.resolved_at else None,
        'image_path':   c.image_path,
        'image_url':    (('/' + c.image_path.replace('\\', '/')) if c.image_path else None),
        'citizen_name': getattr(c.citizen, 'name', None),
        'citizen_phone': getattr(c.citizen, 'phone', None),
        'assigned_to':  c.assigned_to,
        'assigned_to_name': (assigned_worker.name if assigned_worker else None),
        'zone_id':     zone_id,
        'area':        area_name,
        'is_overdue':  overdue,
        'resolution_photo_path': getattr(c, 'resolution_photo_path', None),
        'resolution_photo_url':  (('/' + c.resolution_photo_path.replace('\\', '/')) if getattr(c, 'resolution_photo_path', None) else None),
    }

def _allowed(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def _award_points(user_id, complaint_id, points, action_type, reason):
    """Award points to a user and update tier"""
    try:
        user = User.query.get(user_id)
        if not user:
            return
        
        # Create points ledger entry
        ledger = PointsLedger(
            user_id=user_id,
            complaint_id=complaint_id,
            points_earned=points,
            action_type=action_type,
            reason=reason
        )
        db.session.add(ledger)
        
        # Update user's total points and tier
        user.points += points
        user.tier = _get_user_tier(user.points)
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error awarding points: {e}")

def _get_user_tier(points):
    """Calculate user tier based on points"""
    if points >= 5000:
        return 'platinum'
    elif points >= 2000:
        return 'gold'
    elif points >= 800:
        return 'silver'
    else:
        return 'bronze'
