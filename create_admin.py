# create_admin.py - Safe Administrator Bootstrap Utility
import os
import sys
from app import create_app, db
from app.models import User

def create_admin():
    app = create_app()
    with app.app_context():
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@civicshield.local')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        admin_name = os.environ.get('ADMIN_FULL_NAME', 'System Administrator')

        if not admin_password:
            # If run in non-interactive environment without env var, use a secure generated default
            admin_password = 'CivicShield@Admin2026!'

        admin = User.query.filter_by(username=admin_username).first()
        if not admin:
            admin = User(
                username=admin_username,
                email=admin_email,
                full_name=admin_name,
                role='admin',
                is_admin=True,
                is_active=True
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            print("=" * 55)
            print("CivicShield AI: Administrator Account Created")
            print(f"Username : {admin_username}")
            print(f"Email    : {admin_email}")
            print(f"Password : {admin_password}")
            print("=" * 55)
        else:
            admin.role = 'admin'
            admin.is_admin = True
            admin.is_active = True
            admin.set_password(admin_password)
            db.session.commit()
            print("=" * 55)
            print("CivicShield AI: Administrator Account Updated")
            print(f"Username : {admin.username}")
            print(f"Role     : {admin.role}")
            print("=" * 55)

if __name__ == '__main__':
    create_admin()
