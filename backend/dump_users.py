from app import app
from database import User

with app.app_context():
    users = User.query.order_by(User.id).all()
    for u in users:
        print(u.id, u.email, u.phone, u.role)
