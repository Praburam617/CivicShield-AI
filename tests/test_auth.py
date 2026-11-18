from app.models import User

def test_register_citizen_success(client, app):
    """Test standard citizen registration without Aadhaar requirement."""
    response = client.post('/register', data={
        'full_name': 'Anand R',
        'username': 'anand_r',
        'email': 'anand@example.com',
        'phone': '9876543210',
        'password': 'SecurePassword123!',
        'confirm_password': 'SecurePassword123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(username='anand_r').first()
        assert user is not None
        assert user.role == 'citizen'
        assert user.is_active is True
        assert user.check_password('SecurePassword123!')


def test_login_and_role_redirect(client):
    """Test login with different roles redirects to appropriate portals."""
    # Citizen login
    resp_citizen = client.post('/login', data={
        'username': 'test_citizen',
        'password': 'CitizenPass123!'
    }, follow_redirects=False)
    assert resp_citizen.status_code == 302
    assert '/dashboard' in resp_citizen.headers['Location']

    client.get('/logout')

    # Officer login
    resp_officer = client.post('/login', data={
        'username': 'test_officer',
        'password': 'OfficerPass123!'
    }, follow_redirects=False)
    assert resp_officer.status_code == 302
    assert '/officer/dashboard' in resp_officer.headers['Location']

    client.get('/logout')

    # Admin login
    resp_admin = client.post('/login', data={
        'username': 'test_admin',
        'password': 'AdminPass123!'
    }, follow_redirects=False)
    assert resp_admin.status_code == 302
    assert '/admin/dashboard' in resp_admin.headers['Location']


def test_login_invalid_credentials(client):
    """Test login failure on incorrect password."""
    response = client.post('/login', data={
        'username': 'test_citizen',
        'password': 'WrongPassword123'
    }, follow_redirects=True)
    assert b'Invalid username/email or password' in response.data
