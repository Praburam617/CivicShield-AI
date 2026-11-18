from datetime import datetime
import pytest
from app import db
from app.models import User, Report, OfficerProfile, ReportUpdate, PoliceStation


def login_user(client, username, password):
    return client.post('/login', data={
        'username': username,
        'password': password,
        'remember_me': False
    }, follow_redirects=True)


def test_station_officers_api(client, app):
    """Test dynamic station officer directory API returns correct station officers."""
    with app.app_context():
        # Create station and officers
        p1 = OfficerProfile(
            name='Karthik Raj',
            badge_number='DEMO-SI-TEST-1',
            designation='Sub Inspector',
            department='Crime Investigation',
            police_station='Madurai Town Police Station',
            is_available=True,
            active_case_count=0
        )
        p2 = OfficerProfile(
            name='Vijay Kumar',
            badge_number='DEMO-SI-TEST-2',
            designation='Sub Inspector',
            department='Law and Order',
            police_station='Madurai Town Police Station',
            is_available=True,
            active_case_count=0
        )
        p3 = OfficerProfile(
            name='Other Officer',
            badge_number='DEMO-SI-TEST-3',
            designation='Sub Inspector',
            department='Traffic',
            police_station='City Police Station',
            is_available=True,
            active_case_count=0
        )
        db.session.add_all([p1, p2, p3])
        db.session.commit()

    resp = client.get('/api/stations/Madurai%20Town%20Police%20Station/officers')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['count'] >= 2
    names = [o['name'] for o in data['officers']]
    assert 'Karthik Raj' in names
    assert 'Vijay Kumar' in names
    assert 'Other Officer' not in names


def test_station_based_assignment_validation(client, app):
    """Admin must assign officer belonging to the complaint's station; cross-station assignment rejected."""
    with app.app_context():
        citizen = User.query.filter_by(username='test_citizen').first()
        madurai_rep = Report(
            complaint_number='CS-2026-990011',
            user_id=citizen.id,
            title='Phone snatching near temple',
            description='Two individuals on bike snatched smartphone while walking.',
            crime_category='Robbery',
            incident_date=datetime(2026, 11, 18, 10, 0),
            district='Madurai',
            incident_location='West Tower Street',
            police_station='Madurai Town Police Station',
            status='Pending'
        )
        # Madurai officer
        madurai_off = OfficerProfile(
            name='Arun Kumar',
            badge_number='DEMO-INSP-TEST-MDU',
            designation='Inspector',
            department='Law and Order',
            police_station='Madurai Town Police Station',
            is_available=True,
            active_case_count=0
        )
        # Chennai officer
        chennai_off = OfficerProfile(
            name='Rajendran B',
            badge_number='DEMO-INSP-TEST-CHN',
            designation='Inspector',
            department='Law and Order',
            police_station='Chennai Central Police Station',
            is_available=True,
            active_case_count=0
        )
        db.session.add_all([madurai_rep, madurai_off, chennai_off])
        db.session.commit()

        rep_id = madurai_rep.id
        madurai_off_id = madurai_off.id
        chennai_off_id = chennai_off.id

    login_user(client, 'test_admin', 'AdminPass123!')

    # 1. Attempt assigning Chennai officer to Madurai complaint -> should be rejected
    mismatch_resp = client.post(f'/admin/complaint/{rep_id}/assign', data={
        'officer_profile_id': chennai_off_id,
        'notes': 'Test invalid station assignment'
    }, follow_redirects=True)
    assert mismatch_resp.status_code == 200
    assert b"Chennai Central Police Station" in mismatch_resp.data
    assert b"Madurai Town Police Station" in mismatch_resp.data
    assert b"belongs to" in mismatch_resp.data

    # 2. Assign valid Madurai officer -> succeeds
    valid_resp = client.post(f'/admin/complaint/{rep_id}/assign', data={
        'officer_profile_id': madurai_off_id,
        'notes': 'Investigate immediately'
    }, follow_redirects=True)
    assert valid_resp.status_code == 200
    assert b"Assigned Inspector Arun Kumar" in valid_resp.data

    with app.app_context():
        check_rep = Report.query.get(rep_id)
        assert check_rep.officer_profile_id == madurai_off_id
        assert check_rep.status == 'Under Investigation'
        check_off = OfficerProfile.query.get(madurai_off_id)
        assert check_off.active_case_count == 1


def test_cross_officer_isolation(client, app):
    """An officer cannot view or update cases not assigned to them."""
    with app.app_context():
        citizen = User.query.filter_by(username='test_citizen').first()
        officer_user = User.query.filter_by(username='test_officer').first()

        # Case assigned to test_officer
        my_case = Report(
            complaint_number='CS-2026-990022',
            user_id=citizen.id,
            title='My Assigned Case',
            description='Detailed investigation ongoing for this specific case.',
            crime_category='Theft',
            incident_date=datetime(2026, 11, 18, 9, 0),
            district='Central District',
            incident_location='Main Market',
            police_station='City Police Station',
            status='Under Investigation',
            assigned_officer_id=officer_user.id
        )

        # Other case assigned to someone else
        other_case = Report(
            complaint_number='CS-2026-990033',
            user_id=citizen.id,
            title='Other Officer Case',
            description='Case handled by a different officer completely.',
            crime_category='Fraud',
            incident_date=datetime(2026, 11, 18, 14, 0),
            district='Central District',
            incident_location='North Commercial Wing',
            police_station='City Police Station',
            status='Under Investigation',
            assigned_officer_id=999999
        )
        db.session.add_all([my_case, other_case])
        db.session.commit()

        my_case_id = my_case.id
        other_case_id = other_case.id

    client.get('/logout')
    login_user(client, 'test_officer', 'OfficerPass123!')

    # Allowed: view own case
    my_resp = client.get(f'/officer/case/{my_case_id}')
    assert my_resp.status_code == 200
    assert b"My Assigned Case" in my_resp.data

    # Blocked: view other case -> redirected to /officer/cases with danger alert
    forbidden_resp = client.get(f'/officer/case/{other_case_id}', follow_redirects=True)
    assert forbidden_resp.status_code == 200
    assert b"Access denied. You are only authorized to access cases specifically assigned to your profile." in forbidden_resp.data

    # Blocked: attempt to update other case
    update_forbidden = client.post(f'/officer/case/{other_case_id}/update', data={
        'status': 'Resolved',
        'remarks': 'Unauthorized closure'
    }, follow_redirects=True)
    assert update_forbidden.status_code == 200
    assert b"Access denied. You cannot modify a case not assigned to you." in update_forbidden.data


def test_officer_directory_and_account_provisioning(client, app):
    """Admin can view officers, toggle availability, and provision a login account."""
    with app.app_context():
        unlinked_off = OfficerProfile(
            name='Karthik Raj',
            badge_number='DEMO-SI-PROV-1',
            designation='Sub Inspector',
            department='Crime Investigation',
            police_station='Madurai Town Police Station',
            is_available=True,
            active_case_count=0,
            user_id=None
        )
        db.session.add(unlinked_off)
        db.session.commit()
        off_id = unlinked_off.id

    login_user(client, 'test_admin', 'AdminPass123!')

    # 1. Manage officers page displays the officer as 'Directory Only'
    dir_resp = client.get('/admin/officers')
    assert dir_resp.status_code == 200
    assert b"Karthik Raj" in dir_resp.data
    assert b"Directory Only" in dir_resp.data

    # 2. Toggle availability
    toggle_resp = client.post(f'/admin/officers/{off_id}/toggle-status', follow_redirects=True)
    assert toggle_resp.status_code == 200
    assert b"is now marked as unavailable" in toggle_resp.data

    # 3. Provision login account
    prov_resp = client.post(f'/admin/officers/{off_id}/provision-account', data={
        'username': 'karthik.raj',
        'email': 'karthik.raj@civicshield.example',
        'password': 'KarthikPass123!'
    }, follow_redirects=True)
    assert prov_resp.status_code == 200
    assert b"Login account created for Karthik Raj" in prov_resp.data

    # 4. Verify new user was created in database and linked
    with app.app_context():
        new_user = User.query.filter_by(username='karthik.raj').first()
        assert new_user is not None
        assert new_user.role == 'officer'
        assert new_user.check_password('KarthikPass123!')
        off = OfficerProfile.query.get(off_id)
        assert off.user_id == new_user.id
        assert off.has_account is True

    # 5. Newly provisioned officer logs in successfully
    client.get('/logout')
    login_new = login_user(client, 'karthik.raj', 'KarthikPass123!')
    assert login_new.status_code == 200
    assert b"Officer Dashboard" in login_new.data or b"karthik.raj" in login_new.data
