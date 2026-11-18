import os
import pytest
from app import create_app, db
from app.models import User, Report, ReportUpdate, PoliceStation, CrimeCategory, OfficerProfile
from config import Config, BASE_DIR


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    PROTECTED_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'instance', 'test_uploads')


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        # Seed test admin
        admin = User(username='test_admin', email='admin@test.local', full_name='Test Admin', role='admin', is_admin=True, is_active=True)
        admin.set_password('AdminPass123!')
        db.session.add(admin)

        # Seed test officer
        officer = User(username='test_officer', email='officer@test.local', full_name='Officer Sharma', role='officer', badge_number='TN-TEST-99', police_station='City Police Station', is_admin=False, is_active=True)
        officer.set_password('OfficerPass123!')
        db.session.add(officer)
        db.session.flush()

        # Seed test officer profile
        profile = OfficerProfile(
            name='Officer Sharma',
            badge_number='TN-TEST-99',
            designation='Inspector',
            department='Law and Order',
            police_station='City Police Station',
            is_available=True,
            active_case_count=0,
            user_id=officer.id
        )
        db.session.add(profile)

        # Seed test citizen
        citizen = User(username='test_citizen', email='citizen@test.local', full_name='Citizen Kumar', role='citizen', is_admin=False, is_active=True)
        citizen.set_password('CitizenPass123!')
        db.session.add(citizen)

        # Seed second citizen
        other_citizen = User(username='other_citizen', email='other@test.local', full_name='Other Person', role='citizen', is_admin=False, is_active=True)
        other_citizen.set_password('OtherPass123!')
        db.session.add(other_citizen)

        db.session.commit()
        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()
