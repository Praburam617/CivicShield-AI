from datetime import datetime
from app.models import Report, ReportUpdate, User

def login_user(client, username, password):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)


def test_submit_complaint_and_tracking(client, app):
    """Test full complaint creation workflow and unique reference generation."""
    login_user(client, 'test_citizen', 'CitizenPass123!')

    response = client.post('/submit-report', data={
        'title': 'Stolen Laptop Bag from Library',
        'description': 'My black backpack containing a Dell laptop and student ID was stolen from table 4 at central library.',
        'crime_category': 'Theft',
        'incident_date': '2026-11-18T10:30',
        'district': 'Central District',
        'incident_location': 'Central Library 2nd Floor, Hall B',
        'police_station': 'City Police Station',
        'declaration': 'y',
        'save_as_draft': 'false'
    }, follow_redirects=True)

    assert response.status_code == 200

    with app.app_context():
        citizen = User.query.filter_by(username='test_citizen').first()
        report = Report.query.filter_by(user_id=citizen.id).first()
        assert report is not None
        assert report.complaint_number.startswith('CS-')
        assert report.status == 'Pending'
        assert report.crime_category == 'Theft'
        assert len(report.updates) >= 1

        ref = report.complaint_number

    # Test Track Complaint
    track_resp = client.get(f'/track-report?complaint_number={ref}')
    assert track_resp.status_code == 200
    assert ref.encode() in track_resp.data


def test_complaint_access_authorization(client, app):
    """Ensure citizens cannot view other citizens' confidential dockets."""
    # Create complaint as test_citizen
    with app.app_context():
        c1 = User.query.filter_by(username='test_citizen').first()
        rep = Report(
            complaint_number='CS-2026-999001',
            user_id=c1.id,
            title='Personal Sensitive Dispute',
            description='Detailed confidential narrative here for test verification.',
            crime_category='Fraud',
            incident_date=datetime(2026, 11, 18, 12, 0),
            district='Central District',
            incident_location='Apartment 4B',
            police_station='City Police Station',
            status='Pending'
        )
        from app import db
        db.session.add(rep)
        db.session.commit()
        rep_id = rep.id

    client.get('/logout')

    # Login as other_citizen
    login_user(client, 'other_citizen', 'OtherPass123!')
    resp = client.get(f'/report/{rep_id}', follow_redirects=True)
    assert b'You do not have permission to view this complaint' in resp.data
