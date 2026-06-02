import pytest
from flask import Flask, session
import db
import auth
import os

@pytest.fixture
def app(temp_db, monkeypatch):
    """Create and configure a new app instance for each test."""
    app = Flask(__name__, template_folder='../templates')
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'dev'
    app.config['WTF_CSRF_ENABLED'] = False

    app.register_blueprint(auth.auth_bp)

    # Dummy route for redirect target and login_required testing
    @app.route("/")
    @auth.login_required
    def index():
        return "Index Page"

    # Mock redirect targets that aren't loaded in tests
    from flask import Blueprint
    main_bp = Blueprint('main', __name__)
    @main_bp.route("/")
    def index():
        return "Main Index"
    app.register_blueprint(main_bp)

    # Mock trigger_background_fetch to not run during tests
    monkeypatch.setattr(auth, "trigger_background_fetch", lambda: None)

    # The temp_db fixture sets db.DB_FILE, but auth.py uses config.DB_FILE
    # We must patch config.DB_FILE to point to temp_db too
    monkeypatch.setattr(auth, "DB_FILE", str(temp_db))

    return app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

def test_login_required_unauthenticated(client):
    response = client.get('/')
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_login_required_authenticated(client):
    with client.session_transaction() as sess:
        sess['user'] = 'testuser'
    response = client.get('/')
    assert response.status_code == 200
    assert b"Index Page" in response.data

def test_login_get(client):
    response = client.get('/login')
    assert response.status_code == 200

def test_login_post_invalid(client):
    response = client.post('/login', data={'username': 'testuser', 'password': 'wrongpassword'})
    assert response.status_code == 200
    # The template renders with flash message
    with client.session_transaction() as sess:
        assert 'user' not in sess

def test_login_post_valid(client):
    # Setup test user
    db.create_user('testuser', 'password123')

    response = client.post('/login', data={'username': 'testuser', 'password': 'password123'})
    assert response.status_code == 302
    assert response.headers["Location"] == "/"

    with client.session_transaction() as sess:
        assert sess['user'] == 'testuser'

def test_register_get(client):
    response = client.get('/register')
    assert response.status_code == 200

def test_register_post_success(client):
    # Setup - user should not exist
    assert db.get_user('newuser') is None

    response = client.post('/register', data={
        'username': 'newuser',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Check redirect to login
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    # Verify user created in DB
    user = db.get_user('newuser')
    assert user is not None
    assert db.check_password('password123', user['password_hash'])

def test_register_post_username_too_short(client):
    response = client.post('/register', data={
        'username': 'ab',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    assert response.status_code == 200
    assert db.get_user('ab') is None

def test_register_post_password_too_short(client):
    response = client.post('/register', data={
        'username': 'newuser',
        'password': '123',
        'confirm_password': '123'
    })
    assert response.status_code == 200
    assert db.get_user('newuser') is None

def test_register_post_password_mismatch(client):
    response = client.post('/register', data={
        'username': 'newuser',
        'password': 'password123',
        'confirm_password': 'different_password'
    })
    assert response.status_code == 200
    assert db.get_user('newuser') is None

def test_register_post_username_taken(client):
    db.create_user('existinguser', 'password123')
    response = client.post('/register', data={
        'username': 'existinguser',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    assert response.status_code == 200

def test_logout(client):
    with client.session_transaction() as sess:
        sess['user'] = 'testuser'

    response = client.get('/logout')
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    with client.session_transaction() as sess:
        assert 'user' not in sess

def test_reset_password_get(client):
    response = client.get('/reset-password')
    assert response.status_code == 200

def test_reset_password_step1_invalid_user(client):
    response = client.post('/reset-password', data={'username': 'nonexistent'})
    assert response.status_code == 200
    # Verify flash error (template renders step=1)

def test_reset_password_step1_valid_user(client, temp_db):
    db.create_user('resetuser', 'password123')
    response = client.post('/reset-password', data={'username': 'resetuser'})
    assert response.status_code == 200

    # Check DB for reset token
    import sqlite3
    conn = sqlite3.connect(temp_db)
    c = conn.cursor()
    c.execute("SELECT reset_token FROM users WHERE username = 'resetuser'")
    token = c.fetchone()[0]
    conn.close()

    assert token is not None
    # Response contains the token in the template
    assert token.encode() in response.data

def test_reset_password_step2_success(client, temp_db):
    db.create_user('resetuser2', 'password123')

    # First, generate token
    import sqlite3
    conn = sqlite3.connect(temp_db)
    c = conn.cursor()
    c.execute("UPDATE users SET reset_token = 'validtoken123' WHERE username = 'resetuser2'")
    conn.commit()
    conn.close()

    # Step 2: Set new password
    response = client.post('/reset-password', data={
        'token': 'validtoken123',
        'new_password': 'newpassword123',
        'confirm_password': 'newpassword123'
    })

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    user = db.get_user('resetuser2')
    assert db.check_password('newpassword123', user['password_hash'])

    # Token should be cleared
    conn = sqlite3.connect(temp_db)
    c = conn.cursor()
    c.execute("SELECT reset_token FROM users WHERE username = 'resetuser2'")
    token = c.fetchone()[0]
    conn.close()
    assert token is None

def test_reset_password_step2_short_password(client, temp_db):
    db.create_user('resetuser', 'password123')
    import sqlite3
    conn = sqlite3.connect(temp_db)
    c = conn.cursor()
    c.execute("UPDATE users SET reset_token = 'validtoken123' WHERE username = 'resetuser'")
    conn.commit()
    conn.close()

    response = client.post('/reset-password', data={
        'token': 'validtoken123',
        'new_password': '123',
        'confirm_password': '123'
    })

    assert response.status_code == 200
    # Password should NOT be updated
    user = db.get_user('resetuser')
    assert db.check_password('password123', user['password_hash'])

def test_reset_password_step2_password_mismatch(client, temp_db):
    db.create_user('resetuser', 'password123')
    import sqlite3
    conn = sqlite3.connect(temp_db)
    c = conn.cursor()
    c.execute("UPDATE users SET reset_token = 'validtoken123' WHERE username = 'resetuser'")
    conn.commit()
    conn.close()

    response = client.post('/reset-password', data={
        'token': 'validtoken123',
        'new_password': 'newpassword123',
        'confirm_password': 'different_password'
    })

    assert response.status_code == 200
    user = db.get_user('resetuser')
    assert db.check_password('password123', user['password_hash'])

def test_reset_password_step2_invalid_token(client):
    response = client.post('/reset-password', data={
        'token': 'invalidtoken',
        'new_password': 'newpassword123',
        'confirm_password': 'newpassword123'
    })

    assert response.status_code == 200
    # Verifies it returns to step 1
