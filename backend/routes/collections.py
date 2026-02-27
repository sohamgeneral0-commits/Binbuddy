"""
BinBuddy Collections API
POST /api/collections/         - mark bin as collected
GET  /api/collections/         - list collections
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime
from database import db, Collection, Bin

collections_bp = Blueprint('collections', __name__)

@collections_bp.route('/', methods=['GET'])
@jwt_required()
def list_collections():
    items = Collection.query.order_by(Collection.collected_at.desc()).limit(200).all()
    return jsonify([{
        'id':           c.id,
        'bin_id':       c.bin_id,
        'collector_id': c.collector_id,
        'collected_at': c.collected_at.isoformat(),
        'fill_at_collection': c.fill_at_collection,
        'notes':        c.notes
    } for c in items]), 200

@collections_bp.route('/', methods=['POST'])
@jwt_required()
def mark_collected():
    claims = get_jwt()
    if claims.get('role') not in ('admin', 'collector'):
        return jsonify({'error': 'Forbidden'}), 403

    uid  = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    bin_id = data.get('bin_id')
    if not bin_id:
        return jsonify({'error': 'bin_id required'}), 400

    b = Bin.query.get_or_404(bin_id)

    coll = Collection(
        bin_id              = bin_id,
        collector_id        = uid,
        fill_at_collection  = b.fill_level,
        notes               = data.get('notes', '')
    )
    db.session.add(coll)

    # Reset bin
    b.fill_level   = 0.0
    b.status       = 'collected'
    b.last_updated = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Bin marked as collected', 'id': coll.id}), 201
