"""
Migrate database to add points and rewards system
"""
import sys
sys.path.insert(0, 'c:/Users/USER/Desktop/binbuddy/backend')

from app import app
from database import db
from sqlalchemy import inspect, text

with app.app_context():
    # Get database connection
    inspector = inspect(db.engine)
    
    # Check and add columns to users table
    users_columns = [col['name'] for col in inspector.get_columns('users')]
    
    with db.engine.begin() as conn:
        if 'points' not in users_columns:
            try:
                conn.execute(text('ALTER TABLE users ADD COLUMN points INT DEFAULT 0'))
                print("✅ Added 'points' column to users table")
            except Exception as e:
                print(f"⚠️  'points' column: {e}")
        
        if 'tier' not in users_columns:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN tier VARCHAR(50) DEFAULT 'bronze'"))
                print("✅ Added 'tier' column to users table")
            except Exception as e:
                print(f"⚠️  'tier' column: {e}")
        
        # Check if rewards table exists, if not create it
        tables = inspector.get_table_names()
        
        if 'rewards' not in tables:
            try:
                conn.execute(text("""
                    CREATE TABLE rewards (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        points_required INT NOT NULL,
                        category VARCHAR(50),
                        reward_type ENUM('discount','voucher','gift','badge') DEFAULT 'voucher',
                        value VARCHAR(100),
                        is_active TINYINT(1) DEFAULT 1,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_points (points_required)
                    ) ENGINE=InnoDB
                """))
                print("✅ Created 'rewards' table")
            except Exception as e:
                print(f"⚠️  'rewards' table: {e}")
        else:
            # Check if columns exist and add them if missing, and fix id column
            rewards_columns = [col['name'] for col in inspector.get_columns('rewards')]
            
            # Fix the ID column if it's not autoincrement
            try:
                conn.execute(text("ALTER TABLE rewards MODIFY COLUMN id INT AUTO_INCREMENT PRIMARY KEY"))
                print("✅ Fixed 'id' column to be AUTO_INCREMENT in rewards table")
            except:
                pass  # Might already be correct
            
            missing_columns = {
                'reward_type': "VARCHAR(50) DEFAULT 'voucher'",
                'value': "VARCHAR(100)",
                'is_active': "TINYINT(1) DEFAULT 1"
            }
            
            for col, col_def in missing_columns.items():
                if col not in rewards_columns:
                    try:
                        conn.execute(text(f"ALTER TABLE rewards ADD COLUMN {col} {col_def}"))
                        print(f"✅ Added '{col}' column to rewards table")
                    except Exception as e:
                        print(f"⚠️  '{col}' column: {e}")
        
        if 'points_ledger' not in tables:
            try:
                conn.execute(text("""
                    CREATE TABLE points_ledger (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        complaint_id INT,
                        points_earned INT NOT NULL,
                        reason VARCHAR(255),
                        action_type ENUM('complaint_filed','complaint_resolved','complaint_validated','early_resolve','quality_report') DEFAULT 'complaint_filed',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE SET NULL,
                        INDEX idx_user (user_id),
                        INDEX idx_complaint (complaint_id),
                        INDEX idx_date (created_at)
                    ) ENGINE=InnoDB
                """))
                print("✅ Created 'points_ledger' table")
            except Exception as e:
                print(f"⚠️  'points_ledger' table: {e}")
        
        if 'user_rewards' not in tables:
            try:
                conn.execute(text("""
                    CREATE TABLE user_rewards (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        reward_id INT NOT NULL,
                        redeemed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        status ENUM('pending','claimed','expired') DEFAULT 'pending',
                        claim_code VARCHAR(100) UNIQUE,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (reward_id) REFERENCES rewards(id) ON DELETE CASCADE,
                        INDEX idx_user (user_id),
                        INDEX idx_status (status)
                    ) ENGINE=InnoDB
                """))
                print("✅ Created 'user_rewards' table")
            except Exception as e:
                print(f"⚠️  'user_rewards' table: {e}")

print("\n✅ Database migration completed!")

