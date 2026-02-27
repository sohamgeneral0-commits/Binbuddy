"""
Fix rewards table and seed data
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
        with db.engine.begin() as conn:
            # Drop the old rewards table if it exists (fresh start)
            try:
                conn.execute(text("DROP TABLE IF EXISTS user_rewards"))
                print("✅ Dropped user_rewards table if it existed")
            except:
                pass
            
            try:
                conn.execute(text("DROP TABLE IF EXISTS rewards"))
                print("✅ Dropped rewards table if it existed")
            except:
                pass
            
            # Create fresh rewards table
            conn.execute(text("""
                CREATE TABLE rewards (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    points_required INT NOT NULL,
                    category VARCHAR(50),
                    reward_type VARCHAR(50) DEFAULT 'voucher',
                    value VARCHAR(100),
                    is_active TINYINT(1) DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_points (points_required)
                ) ENGINE=InnoDB
            """))
            print("✅ Created fresh rewards table")
            
            # Recreate user_rewards table
            conn.execute(text("""
                CREATE TABLE user_rewards (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    reward_id INT NOT NULL,
                    redeemed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'pending',
                    claim_code VARCHAR(100) UNIQUE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (reward_id) REFERENCES rewards(id) ON DELETE CASCADE,
                    INDEX idx_user (user_id),
                    INDEX idx_status (status)
                ) ENGINE=InnoDB
            """))
            print("✅ Created fresh user_rewards table")
            
            # Insert rewards
            for name, desc, points, reward_type, value in rewards_data:
                conn.execute(text("""
                    INSERT INTO rewards (name, description, points_required, category, reward_type, value, is_active)
                    VALUES (:name, :desc, :points, :category, :type, :value, 1)
                """), {
                    'name': name,
                    'desc': desc,
                    'points': points,
                    'category': reward_type,
                    'type': reward_type,
                    'value': value
                })
            
            print(f"✅ Successfully seeded {len(rewards_data)} rewards")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
