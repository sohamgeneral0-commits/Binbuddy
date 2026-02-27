"""
BinBuddy Points & Rewards API
GET  /api/points/user              - get user's current points and tier
GET  /api/points/rewards            - list available rewards
GET  /api/points/leaderboard        - top earners (by role or global)
GET  /api/points/ledger             - transaction history
POST /api/points/redeem/<reward_id> - redeem a reward
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime
from database import db, User, Reward, PointsLedger, UserReward, Complaint
from sqlalchemy import desc

points_bp = Blueprint('points', __name__)

# ─────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────
def get_user_tier(points):
    """Calculate tier based on points"""
    if points >= 5000:
        return 'platinum'
    elif points >= 2000:
        return 'gold'
    elif points >= 800:
        return 'silver'
    else:
        return 'bronze'

def add_points(user_id, complaint_id, points_earned, action_type, reason):
    """Helper to add points and update user tier"""
    try:
        user = User.query.get(user_id)
        if not user:
            return False
        
        # Create ledger entry
        entry = PointsLedger(
            user_id=user_id,
            complaint_id=complaint_id,
            points_earned=points_earned,
            action_type=action_type,
            reason=reason
        )
        db.session.add(entry)
        
        # Update user points and tier
        user.points += points_earned
        user.tier = get_user_tier(user.points)
        
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error adding points: {e}")
        return False

# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@points_bp.route('/user', methods=['GET'])
@jwt_required()
def get_user_points():
    """Get current user's points and tier"""
    uid = int(get_jwt_identity())
    user = User.query.get(uid)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'id': user.id,
        'name': user.name,
        'points': user.points,
        'tier': user.tier,
        'role': user.role,
        'next_tier_points': _get_next_tier_threshold(user.points)
    }), 200

@points_bp.route('/user/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_points_public(user_id):
    """Get public points info for any user (for leaderboards)"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'id': user.id,
        'name': user.name,
        'points': user.points,
        'tier': user.tier,
        'role': user.role
    }), 200

@points_bp.route('/rewards', methods=['GET'])
@jwt_required()
def list_rewards():
    """List all available rewards"""
    role = request.args.get('role')  # Filter by role if needed
    rewards = Reward.query.filter_by(is_active=True).order_by(Reward.points_required).all()
    
    return jsonify([{
        'id': r.id,
        'name': r.name,
        'description': r.description,
        'points_required': r.points_required,
        'category': r.category,
        'reward_type': r.reward_type,
        'value': r.value
    } for r in rewards]), 200

@points_bp.route('/leaderboard', methods=['GET'])
@jwt_required()
def get_leaderboard():
    """Get top earners leaderboard"""
    role = request.args.get('role')  # Filter by collector/citizen if needed
    limit = request.args.get('limit', 50, type=int)
    
    query = User.query.filter_by(is_active=True)
    if role:
        query = query.filter_by(role=role)
    
    top_users = query.order_by(desc(User.points)).limit(limit).all()
    
    return jsonify([{
        'rank': idx + 1,
        'id': u.id,
        'name': u.name,
        'points': u.points,
        'tier': u.tier,
        'role': u.role,
        'zone': u.zone.name if u.zone else 'N/A'
    } for idx, u in enumerate(top_users)]), 200

@points_bp.route('/ledger', methods=['GET'])
@jwt_required()
def get_points_ledger():
    """Get user's points transaction history"""
    uid = int(get_jwt_identity())
    limit = request.args.get('limit', 50, type=int)
    
    entries = PointsLedger.query.filter_by(user_id=uid).order_by(
        PointsLedger.created_at.desc()
    ).limit(limit).all()
    
    return jsonify([{
        'id': e.id,
        'complaint_id': e.complaint_id,
        'points_earned': e.points_earned,
        'action_type': e.action_type,
        'reason': e.reason,
        'created_at': e.created_at.isoformat() if e.created_at else None
    } for e in entries]), 200

@points_bp.route('/redeem/<int:reward_id>', methods=['POST'])
@jwt_required()
def redeem_reward(reward_id):
    """Redeem a reward"""
    uid = int(get_jwt_identity())
    user = User.query.get(uid)
    reward = Reward.query.get(reward_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if not reward:
        return jsonify({'error': 'Reward not found'}), 404
    if not reward.is_active:
        return jsonify({'error': 'Reward is no longer available'}), 400
    if user.points < reward.points_required:
        return jsonify({
            'error': 'Insufficient points',
            'required': reward.points_required,
            'current': user.points
        }), 400
    
    try:
        # Create redemption record
        import string
        import random
        claim_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        user_reward = UserReward(
            user_id=uid,
            reward_id=reward_id,
            claim_code=claim_code
        )
        
        # Deduct points
        user.points -= reward.points_required
        user.tier = get_user_tier(user.points)
        
        # Add ledger entry for the deduction
        ledger = PointsLedger(
            user_id=uid,
            points_earned=-reward.points_required,
            action_type='reward_redeemed',
            reason=f'Redeemed: {reward.name}'
        )
        
        db.session.add(user_reward)
        db.session.add(ledger)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Reward redeemed successfully',
            'claim_code': claim_code,
            'reward': reward.name,
            'remaining_points': user.points
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@points_bp.route('/user-rewards', methods=['GET'])
@jwt_required()
def get_user_redeemed_rewards():
    """Get user's redeemed rewards"""
    uid = int(get_jwt_identity())
    limit = request.args.get('limit', 100, type=int)
    
    user_rewards = UserReward.query.filter_by(user_id=uid).order_by(
        UserReward.redeemed_at.desc()
    ).limit(limit).all()
    
    return jsonify([{
        'id': ur.id,
        'reward_name': ur.reward.name,
        'claim_code': ur.claim_code,
        'status': ur.status,
        'redeemed_at': ur.redeemed_at.isoformat() if ur.redeemed_at else None
    } for ur in user_rewards]), 200

# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def _get_next_tier_threshold(current_points):
    """Get points needed for next tier"""
    tiers = {
        'bronze': 800,
        'silver': 2000,
        'gold': 5000,
        'platinum': float('inf')
    }
    
    if current_points >= 5000:
        return None  # Already at max tier
    elif current_points >= 2000:
        return {'tier': 'gold', 'points_needed': 5000 - current_points}
    elif current_points >= 800:
        return {'tier': 'silver', 'points_needed': 2000 - current_points}
    else:
        return {'tier': 'silver', 'points_needed': 800 - current_points}
