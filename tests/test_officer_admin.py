from datetime import datetime
from app.models import Report, User, AuditLog
from app import db

def login_user(client, username, password):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)


def test_admin_and_officer_rbac(client):
    """Ensure ordinary citizens cannot access admin or officer routes."""
    login_user(client, 'test_citizen', 'CitizenPass123!')

    # Try admin console
    admin_resp = client.get('/admin/dashboard', follow_redirects=True)
    assert b'Access restricted to system administrators' in admin_resp.data

    # Try officer portal
    officer_resp = client.get('/officer/dashboard', follow_redirects=True)
    assert b'Access restricted to authorized police officers' in officer_resp.data


def test_admin_assign_officer_and_officer_update(client, app):
    """Test full cycle: Admin assigns officer -> Officer updates status."""
    with app.app_context():
        c1 = User.query.filter_by(username='test_citizen').first()
        rep = Report(
            complaint_number='CS-2026-888001',
            user_id=c1.id,
            title='Commercial Break-in',
            description='Warehouse locks broken and electronic goods looted overnight.',
            crime_category='Burglary',
            incident_date=datetime(2026, 11, 18, 3, 0),
            district='Central District',
            incident_location='Industrial Estate Shed 5',
            police_station='City Police Station',
            status='Pending'
        )
        db.session.add(rep)
        db.session.commit()
        rep_id = rep.id
        officer = User.query.filter_by(username='test_officer').first()
        officer_id = officer.id

    client.get('/logout')

    # 1. Admin assigns officer
    login_user(client, 'test_admin', 'AdminPass123!')
    assign_resp = client.post(f'/admin/complaint/{rep_id}/assign', data={
        'officer_id': officer_id,
        'notes': 'Please inspect site and collect CCTV footage'
    }, follow_redirects=True)
    assert assign_resp.status_code == 200

    with app.app_context():
        updated_rep = Report.query.get(rep_id)
        assert updated_rep.assigned_officer_id == officer_id
        assert updated_rep.status in ('Under Investigation', 'Assigned')

    client.get('/logout')

    # 2. Officer inspects and updates status
    login_user(client, 'test_officer', 'OfficerPass123!')
    update_resp = client.post(f'/officer/case/{rep_id}/update', data={
        'status': 'Evidence Collected',
        'remarks': 'CCTV footage and fingerprint samples recovered from main door.',
        'is_internal': False
    }, follow_redirects=True)
    assert update_resp.status_code == 200

    with app.app_context():
        final_rep = Report.query.get(rep_id)
        assert final_rep.status == 'Evidence Collected'

        # Verify audit trail was logged
        audit_entry = AuditLog.query.filter_by(action='OFFICER_CASE_UPDATED', resource_id=str(rep_id)).first()
        assert audit_entry is not None
