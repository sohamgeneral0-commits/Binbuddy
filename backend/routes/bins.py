"""
BinBuddy Bins API
GET    /api/bins/           - list all bins (with optional ?zone_id=&status=)
GET    /api/bins/<id>       - single bin detail
POST   /api/bins/           - create bin (admin)
PUT    /api/bins/<id>       - update bin (admin)
DELETE /api/bins/<id>       - deactivate bin (admin)
POST   /api/bins/iot-update - IoT device HTTP fallback update (no auth, device_token)
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime
from database import db, Bin, Notification, AuditLog, User

bins_bp = Blueprint('bins', __name__)

IOT_DEVICE_SECRET = 'binbuddy-iot-secret-2024'  # move to config in production

# ─── LIST BINS ───────────────────────────────
@bins_bp.route('/', methods=['GET'])
@jwt_required()
def list_bins():
    query   = Bin.query.filter_by(is_active=True)
    zone_id = request.args.get('zone_id', type=int)
    status  = request.args.get('status')
    # If caller is a worker/collector and no explicit zone_id provided,
    # restrict results to the worker's assigned zone for data privacy.
    try:
        claims = get_jwt()
        if not zone_id and claims.get('role') in ('collector', 'worker'):
            uid = int(get_jwt_identity())
            # import here to avoid circular import at module load time
            from database import User as _User
            user = _User.query.get(uid)
            if user and user.zone_id:
                zone_id = user.zone_id
    except Exception:
        # If anything goes wrong evaluating JWT or user, fall back to no filter
        zone_id = zone_id
    if zone_id:
        query = query.filter_by(zone_id=zone_id)
    if status:
        query = query.filter_by(status=status)
    bins = query.order_by(Bin.fill_level.desc()).all()
    return jsonify([_serialize(b) for b in bins]), 200

# ─── SINGLE BIN ──────────────────────────────
@bins_bp.route('/<int:bin_id>', methods=['GET'])
@jwt_required()
def get_bin(bin_id):
    b = Bin.query.get_or_404(bin_id)
    return jsonify(_serialize(b)), 200

# ─── CREATE BIN (admin) ──────────────────────
@bins_bp.route('/', methods=['POST'])
@jwt_required()
def create_bin():
    _require_role('admin')
    data = request.get_json(silent=True) or {}
    required = ['bin_code', 'latitude', 'longitude', 'zone_id']
    for f in required:
        if not data.get(f):
            return jsonify({'error': f'Missing: {f}'}), 400

    if Bin.query.filter_by(bin_code=data['bin_code']).first():
        return jsonify({'error': 'bin_code already exists'}), 409

    b = Bin(
        bin_code      = data['bin_code'],
        location_name = data.get('location_name', ''),
        latitude      = float(data['latitude']),
        longitude     = float(data['longitude']),
        capacity_cm   = int(data.get('capacity_cm', 100)),
        zone_id       = int(data['zone_id']),
        device_id     = data.get('device_id')
    )
    db.session.add(b)
    db.session.commit()
    return jsonify({'message': 'Bin created', 'id': b.id}), 201

# ─── UPDATE BIN (admin) ──────────────────────
@bins_bp.route('/<int:bin_id>', methods=['PUT'])
@jwt_required()
def update_bin(bin_id):
    _require_role('admin')
    b    = Bin.query.get_or_404(bin_id)
    data = request.get_json(silent=True) or {}
    for field in ['location_name', 'latitude', 'longitude', 'capacity_cm', 'zone_id', 'device_id']:
        if field in data:
            setattr(b, field, data[field])
    db.session.commit()
    return jsonify({'message': 'Updated'}), 200

# ─── DEACTIVATE BIN (admin) ──────────────────
@bins_bp.route('/<int:bin_id>', methods=['DELETE'])
@jwt_required()
def delete_bin(bin_id):
    _require_role('admin')
    b = Bin.query.get_or_404(bin_id)
    b.is_active = False
    db.session.commit()
    return jsonify({'message': 'Bin deactivated'}), 200

# ─── IoT HTTP FALLBACK (no JWT, use device secret) ───
# routes/bins.py

@bins_bp.route('/iot-update', methods=['POST'])
def iot_update():
    # ... auth check ...
    data = request.get_json()
    b = Bin.query.filter_by(bin_code=data['bin_code']).first()
    
    # Logic: If sensor sends distance_cm, calculate fill %
    # Bin height is 22cm. If distance is 2cm, it's 90% full.
    if 'distance_cm' in data:
        dist = float(data['distance_cm'])
        capacity = b.capacity_cm or 22
        fill = max(0, min(100, ((capacity - dist) / capacity) * 100))
        b.fill_level = round(fill, 2)
        b.distance_cm = dist
    else:
        b.fill_level = float(data.get('fill_level', 0))

    # Update Status
    if b.fill_level >= 90: b.status = 'full'
    elif b.fill_level >= 50: b.status = 'half'
    else: b.status = 'empty'
    
    db.session.commit()
    return jsonify({'status': 'updated'}), 200

# @bins_bp.route('/iot-update', methods=['POST'])
# def iot_update():
    token = request.headers.get('X-Device-Token')
    if token != IOT_DEVICE_SECRET:
        return jsonify({'error': 'Unauthorized device'}), 401

    data       = request.get_json(silent=True) or {}
    bin_code   = data.get('bin_code')
    fill_level = float(data.get('fill_level', 0))
    battery    = float(data.get('battery', 100))

    b = Bin.query.filter_by(bin_code=bin_code, is_active=True).first()
    if not b:
        return jsonify({'error': 'Bin not found'}), 404

    b.fill_level    = round(fill_level, 2)
    b.battery_level = round(battery, 2)
    b.last_updated  = datetime.utcnow()

    if fill_level >= 80:
        b.status = 'full'
        n = Notification(title=f'Bin {bin_code} FULL',
                         message=f'{b.location_name}: {fill_level:.0f}%',
                         type='alert')
        db.session.add(n)
    elif fill_level >= 50:
        b.status = 'half'
    else:
        b.status = 'empty'

    db.session.commit()
    return jsonify({'message': 'ok'}), 200

# ─── MAP DATA (public-ish, just needs valid JWT) ───
@bins_bp.route('/map-data', methods=['GET'])
@jwt_required()
def map_data():
    """Lightweight endpoint for Google Maps markers."""
    query = Bin.query.filter_by(is_active=True)
    # Apply same zone restriction for collectors/workers
    try:
        claims = get_jwt()
        zone_param = request.args.get('zone_id', type=int)
        if not zone_param and claims.get('role') in ('collector', 'worker'):
            uid = int(get_jwt_identity())
            from database import User as _User
            user = _User.query.get(uid)
            if user and user.zone_id:
                query = query.filter_by(zone_id=user.zone_id)
    except Exception:
        pass
    bins = query.all()
    return jsonify([{
        'id':            b.id,
        'bin_code':      b.bin_code,
        'lat':           b.latitude,
        'lng':           b.longitude,
        'fill_level':    b.fill_level,
        'status':        b.status,
        'location_name': b.location_name
    } for b in bins]), 200


# ─── DEBUG INFO (development only) ─────────────────
@bins_bp.route('/debug-info', methods=['GET'])
@jwt_required()
def debug_info():
    claims = get_jwt()
    try:
        uid = int(get_jwt_identity())
        user = User.query.get(uid)
    except Exception:
        user = None
    total_bins = Bin.query.filter_by(is_active=True).count()
    zone_bins = None
    if user and user.zone_id:
        zone_bins = Bin.query.filter_by(is_active=True, zone_id=user.zone_id).count()
    return jsonify({
        'claims': claims,
        'user': {'id': user.id if user else None, 'zone_id': user.zone_id if user else None},
        'total_bins': total_bins,
        'zone_bins': zone_bins
    }), 200

# ─── Helpers ─────────────────────────────────
def _serialize(b):
    return {
        'id':            b.id,
        'bin_code':      b.bin_code,
        'location_name': b.location_name,
        'latitude':      b.latitude,
        'longitude':     b.longitude,
        'capacity_cm':   b.capacity_cm,
        'fill_level':    b.fill_level,
        'status':        b.status,
        'battery_level': b.battery_level,
        'zone_id':       b.zone_id,
        'device_id':     b.device_id,
        'distance_cm':   getattr(b, 'distance_cm', None),   # ← ADD THIS LINE
        'last_updated':  b.last_updated.isoformat() if b.last_updated else None
    }

# ─── SINGLE BIN BY CODE (dashboard live refresh) ───
@bins_bp.route('/live/<bin_code>', methods=['GET'])
@jwt_required()
def get_live_bin(bin_code):
    b = Bin.query.filter_by(bin_code=bin_code, is_active=True).first()
    if not b:
        return jsonify({'error': f'Bin {bin_code} not found'}), 404
    return jsonify(_serialize(b)), 200

def _require_role(*roles):
    claims = get_jwt()
    if claims.get('role') not in roles:
        from flask import abort
        abort(403)
