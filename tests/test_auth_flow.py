import pytest
from app import app
from db import create_user, check_password, get_user
import sqlite3
from config import DB_FILE

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_reset_password_flow(client):
    create_user("testuser2", "password123")

    # Step 1: Request reset
    response = client.post('/reset-password', data={"username": "testuser2"})
    assert b"If an account exists, a password reset token has been sent." in response.data

    # Get token from DB since we are stubbing email
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT reset_token FROM users WHERE username = 'testuser2'")
    token = c.fetchone()[0]
    conn.close()

    assert token is not None

    # Step 2: Use token to reset password
    response2 = client.post('/reset-password', data={
        "token": token,
        "new_password": "newpassword456",
        "confirm_password": "newpassword456"
    })

    # Should redirect to login
    assert response2.status_code == 302
    assert response2.headers['Location'] == '/login'

    # Verify new password works
    user = get_user("testuser2")
    assert check_password("newpassword456", user['password_hash'])
