"""
Force recreate the admin user with correct password hash
"""
from app import app
from database import db, User, Zone
import bcrypt

with app.app_context():
    # Delete old admin if exists
    old_admin = User.query.filter_by(email='admin@municipal.gov.in').first()
    if old_admin:
        print(f"Deleting old admin user (ID: {old_admin.id})")
        db.session.delete(old_admin)
        db.session.commit()
    
    # Ensure we have a zone
    zone = Zone.query.first()
    if not zone:
        zone = Zone(name='Default Zone', ward_number='W01', city='City')
        db.session.add(zone)
        db.session.flush()
        print("✅ Created default zone")
    
    # Create fresh admin user
    password = 'admin123'
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12))
    
    print(f"Creating admin user...")
    print(f"  Email: admin@municipal.gov.in")
    print(f"  Password: admin123")
    print(f"  Password Hash: {hashed.decode()}")
    
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
    
    print("\n✅ Admin user created successfully!")
    print(f"   Ready to login with: admin@municipal.gov.in / admin123")
