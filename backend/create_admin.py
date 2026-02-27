"""
Quick script to create the admin user in the database
Run this ONCE to set up the admin account
"""

from app import app
from database import db, User, Zone
import bcrypt

with app.app_context():
    # Check if admin already exists
    admin = User.query.filter_by(email='admin@municipal.gov.in').first()
    if admin:
        print("❌ Admin user already exists")
        exit(1)
    
    # Check if a zone exists, create default zone if not
    zone = Zone.query.first()
    if not zone:
        zone = Zone(name='Default Zone', ward_number='W01', city='City')
        db.session.add(zone)
        db.session.flush()
        print("✅ Created default zone")
    
    # Create admin user
    password = 'admin123'
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12))
    
    admin_user = User(
        name='Admin User',
        email='admin@municipal.gov.in',
        password=hashed.decode(),
        role='admin',
        phone='9999999999',
        zone_id=zone.id,
        is_approved=True,
        is_active=True
    )
    
    db.session.add(admin_user)
    db.session.commit()
    
    print("✅ Admin user created successfully!")
    print(f"   Email: admin@municipal.gov.in")
    print(f"   Password: admin123")
    print(f"   Role: admin")
