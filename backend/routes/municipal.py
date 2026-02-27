"""
Municipal endpoints: requests for new bins, summaries
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime
from database import db, BinRequest, Bin, User

municipal_bp = Blueprint('municipal', __name__)


def _require_role(roles):
    claims = get_jwt()
    if claims.get('role') not in roles:
        from flask import abort
        abort(403)


@municipal_bp.route('/requests', methods=['POST'])
@jwt_required()
def create_request():
    claims = get_jwt()
    if claims.get('role') != 'municipal_office':
        return jsonify({'error': 'Forbidden'}), 403
    uid = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    req = BinRequest(
        requester_id = uid,
        zone_id      = data.get('zone_id'),
        location_name= data.get('location_name'),
        latitude     = float(data.get('latitude', 0)),
        longitude    = float(data.get('longitude', 0)),
        notes        = data.get('notes', '')
    )
    db.session.add(req)
    db.session.commit()
    return jsonify({'message': 'Request submitted', 'id': req.id}), 201


@municipal_bp.route('/requests', methods=['GET'])
@jwt_required()
def list_requests():
    claims = get_jwt()
    role = claims.get('role')
    uid = int(get_jwt_identity())
    if role == 'admin':
        items = BinRequest.query.order_by(BinRequest.created_at.desc()).all()
    elif role == 'municipal_office':
        # show requests from this municipal (same zone) or created by this user
        user = User.query.get(uid)
        items = BinRequest.query.filter(
            (BinRequest.requester_id == uid) | (BinRequest.zone_id == user.zone_id)
        ).order_by(BinRequest.created_at.desc()).all()
    else:
        return jsonify({'error': 'Forbidden'}), 403

    def ser(r):
        return {
            'id': r.id,
            'requester_id': r.requester_id,
            'zone_id': r.zone_id,
            'location_name': r.location_name,
            'latitude': r.latitude,
            'longitude': r.longitude,
            'notes': r.notes,
            'status': r.status,
            'reviewed_by': r.reviewed_by,
            'reviewed_at': r.reviewed_at.isoformat() if r.reviewed_at else None,
            'created_at': r.created_at.isoformat()
        }

    return jsonify([ser(i) for i in items]), 200


@municipal_bp.route('/requests/<int:rid>/approve', methods=['PUT'])
@jwt_required()
def approve_request(rid):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    req = BinRequest.query.get_or_404(rid)
    data = request.get_json(silent=True) or {}
    # create Bin
    b = Bin(
        bin_code = data.get('bin_code', f'BIN-NEW-{rid}'),
        location_name = req.location_name or data.get('location_name',''),
        latitude = req.latitude or float(data.get('latitude', 0)),
        longitude = req.longitude or float(data.get('longitude', 0)),
        zone_id = req.zone_id or data.get('zone_id'),
        capacity_cm = int(data.get('capacity_cm', 100)),
        device_id = data.get('device_id')
    )
    db.session.add(b)
    req.status = 'approved'
    req.reviewed_by = int(get_jwt_identity())
    req.reviewed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Request approved', 'bin_id': b.id}), 200


@municipal_bp.route('/requests/<int:rid>/reject', methods=['PUT'])
@jwt_required()
def reject_request(rid):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    req = BinRequest.query.get_or_404(rid)
    req.status = 'rejected'
    req.reviewed_by = int(get_jwt_identity())
    req.reviewed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Request rejected'}), 200


@municipal_bp.route('/bins-summary', methods=['GET'])
@jwt_required()
def bins_summary():
    claims = get_jwt()
    role = claims.get('role')
    uid = int(get_jwt_identity())
    if role == 'admin':
        # return counts per municipal (users with municipal_office role)
        municipals = User.query.filter_by(role='municipal_office').all()
        out = []
        for m in municipals:
            count = Bin.query.filter_by(zone_id=m.zone_id, is_active=True).count()
            out.append({'municipal_id': m.id, 'municipal_name': m.name, 'zone_id': m.zone_id, 'working_bins': count})
        return jsonify(out), 200
    elif role == 'municipal_office':
        user = User.query.get(uid)
        count = Bin.query.filter_by(zone_id=user.zone_id, is_active=True).count()
        return jsonify({'municipal_id': user.id, 'municipal_name': user.name, 'zone_id': user.zone_id, 'working_bins': count}), 200
    else:
        return jsonify({'error': 'Forbidden'}), 403
