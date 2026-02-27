"""
Seed sample rewards into the database - with schema verification
"""
import sys
sys.path.insert(0, 'c:/Users/USER/Desktop/binbuddy/backend')

from app import app
from database import db
from sqlalchemy import text

rewards_data = [
    ('Coffee Voucher', 'Free coffee at local cafe', 500, 'voucher', '₹200'),
    ('Lunch Voucher', 'Lunch voucher at municipal cafeteria', 1000, 'voucher', '₹500'),
    ('Movie Ticket', 'Movie ticket at local cinema', 800, 'discount', '₹300'),
    ('Shopping Voucher', 'General shopping discount voucher', 1500, 'voucher', '₹750'),
    ('Gold Badge', 'Gold tier badge on profile', 2000, 'badge', 'gold_badge'),
    ('Special Gift Pack', 'Premium gift package from municipality', 3000, 'gift', 'Premium Kit'),
    ('Platinum Badge', 'Platinum tier badge on profile', 5000, 'badge', 'platinum_badge'),
    ('Special Bonus Voucher', 'Extra bonus voucher for top workers', 2500, 'voucher', '₹1000'),
]

with app.app_context():
    try:
        # Check if rewards already exist using raw SQL
        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM rewards"))
            count = result.scalar()
            
            if count > 0:
                print(f"❌ Rewards already exist ({count} records). Skipping seed.")
                sys.exit(0)
            
            # Insert rewards directly using raw SQL
            # Let MySQL auto-increment the ID
            for name, desc, points, reward_type, value in rewards_data:
                sql = text("""
                    INSERT INTO rewards (name, description, points_required, category, reward_type, value, is_active)
                    VALUES (:name, :desc, :points, :category, :type, :value, 1)
                """)
                conn.execute(sql, {
                    'name': name,
                    'desc': desc,
                    'points': points,
                    'category': reward_type,  # Using reward_type as category too
                    'type': reward_type,
                    'value': value
                })
            
            conn.commit()
            print(f"✅ Successfully seeded {len(rewards_data)} rewards")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

