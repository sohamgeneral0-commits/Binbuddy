from app import app

with app.app_context():
    from register import register_admin
    from database import User

    result = register_admin('admin@municipal.gov.in', 'admin123')
    print('register_admin returned', result)
    u = User.query.filter_by(email='admin@municipal.gov.in').first()
    print('stored password:', repr(u.password))
