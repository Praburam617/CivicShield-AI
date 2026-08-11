# create_admin.py
from app import create_app, db
from app.models import User

def create_admin():
    app = create_app()
    with app.app_context():
        # Check if admin already exists
        admin = User.query.filter_by(username='admin').first()
        
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                full_name='System Administrator',
                phone='1234567890',
                aadhar_number='123456789012',
                is_admin=True,
                is_active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("="*50)
            print("Admin user created successfully!")
            print("Username: admin")
            print("Password: admin123")
            print("="*50)
        else:
            admin.is_admin = True
            admin.is_active = True
            if not admin.check_password('admin123'):
                admin.set_password('admin123')
            db.session.commit()
            print("="*50)
            print("Admin user updated successfully!")
            print(f"Username: {admin.username}")
            print("Password: admin123")
            print("="*50)

if __name__ == '__main__':
    create_admin()
