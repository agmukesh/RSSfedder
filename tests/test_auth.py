import pytest
from app import app
from db import create_user

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_reset_password_flash(client):
    create_user("testuser", "password123")
    response = client.post('/reset-password', data={"username": "testuser"})
    assert b"Your reset token" not in response.data
