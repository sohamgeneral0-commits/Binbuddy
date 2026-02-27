"""
BinBuddy Reports API
GET /api/reports/summary
GET /api/reports/zone/<zone_id>
GET /api/reports/collections-daily
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from database import db, Bin, Collection, Complaint, User
from sqlalchemy import func
from datetime import datetime, date, timedelta

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/summary', methods=['GET'])
@jwt_required()
def summary():
    total_bins       = Bin.query.filter_by(is_active=True).count()
    full_bins        = Bin.query.filter_by(status='full').count()
    half_bins        = Bin.query.filter_by(status='half').count()
    empty_bins       = Bin.query.filter_by(status='empty').count()
    today_start      = datetime.combine(date.today(), datetime.min.time())
    collected_today  = Collection.query.filter(Collection.collected_at >= today_start).count()
    open_complaints  = Complaint.query.filter_by(status='open').count()
    active_collectors= User.query.filter_by(role='collector', is_approved=True, is_active=True).count()

    return jsonify({
        'total_bins':        total_bins,
        'full_bins':         full_bins,
        'half_bins':         half_bins,
        'empty_bins':        empty_bins,
        'collected_today':   collected_today,
        'open_complaints':   open_complaints,
        'active_collectors': active_collectors
    }), 200

@reports_bp.route('/collections-daily', methods=['GET'])
@jwt_required()
def collections_daily():
    """Last 7 days collection counts."""
    result = []
    for i in range(6, -1, -1):
        day   = date.today() - timedelta(days=i)
        start = datetime.combine(day, datetime.min.time())
        end   = datetime.combine(day + timedelta(days=1), datetime.min.time())
        count = Collection.query.filter(
            Collection.collected_at >= start,
            Collection.collected_at < end
        ).count()
        result.append({'date': day.isoformat(), 'count': count})
    return jsonify(result), 200

@reports_bp.route('/zone-status', methods=['GET'])
@jwt_required()
def zone_status():
    """Fill level breakdown per zone."""
    from database import Zone
    zones  = Zone.query.all()
    result = []
    for z in zones:
        bins = Bin.query.filter_by(zone_id=z.id, is_active=True).all()
        result.append({
            'zone':    z.name,
            'ward':    z.ward_number,
            'full':    sum(1 for b in bins if b.status == 'full'),
            'half':    sum(1 for b in bins if b.status == 'half'),
            'empty':   sum(1 for b in bins if b.status == 'empty'),
            'total':   len(bins)
        })
    return jsonify(result), 200
