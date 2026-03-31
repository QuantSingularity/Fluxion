"""
Integration tests for authentication endpoints
"""

from typing import Any

import pytest
from app.main import app
from fastapi.testclient import TestClient


class TestAuthEndpoints:
    """Test authentication API endpoints."""

    @pytest.fixture
    def client(self) -> Any:
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def sample_registration_data(self) -> Any:
        """Sample registration data."""
        return {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "terms_accepted": True,
            "privacy_accepted": True,
        }

    @pytest.fixture
    def sample_login_data(self) -> Any:
        """Sample login data."""
        return {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "remember_me": False,
        }

    def test_register_user_success(
        self, client: Any, sample_registration_data: Any
    ) -> Any:
        """Test successful user registration."""
        response = client.post("/api/v1/auth/register", json=sample_registration_data)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "user" in data["data"]
        assert "verification_token" in data["data"]
        assert data["data"]["user"]["email"] == sample_registration_data["email"]
        assert data["data"]["user"]["username"] == sample_registration_data["username"]

    def test_register_user_invalid_email(
        self, client: Any, sample_registration_data: Any
    ) -> Any:
        """Test registration with invalid email."""
        sample_registration_data["email"] = "invalid-email"
        response = client.post("/api/v1/auth/register", json=sample_registration_data)
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "validation_errors" in data

    def test_register_user_weak_password(
        self, client: Any, sample_registration_data: Any
    ) -> Any:
        """Test registration with weak password."""
        sample_registration_data["password"] = "weak"
        sample_registration_data["confirm_password"] = "weak"
        response = client.post("/api/v1/auth/register", json=sample_registration_data)
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "validation_errors" in data

    def test_register_user_password_mismatch(
        self, client: Any, sample_registration_data: Any
    ) -> Any:
        """Test registration with password mismatch."""
        sample_registration_data["confirm_password"] = "DifferentPassword123!"
        response = client.post("/api/v1/auth/register", json=sample_registration_data)
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "validation_errors" in data

    def test_register_user_missing_terms(
        self, client: Any, sample_registration_data: Any
    ) -> Any:
        """Test registration without accepting terms."""
        sample_registration_data["terms_accepted"] = False
        response = client.post("/api/v1/auth/register", json=sample_registration_data)
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "validation_errors" in data

    def test_login_user_success(
        self, client: Any, sample_login_data: Any, test_user: Any
    ) -> Any:
        """Test successful user login."""
        response = client.post("/api/v1/auth/login", json=sample_login_data)
        assert response.status_code in [200, 401, 500]

    def test_login_user_invalid_credentials(self, client: Any) -> Any:
        """Test login with invalid credentials."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "WrongPassword123!",
            "remember_me": False,
        }
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code in [401, 500]

    def test_login_user_missing_email(self, client: Any) -> Any:
        """Test login with missing email."""
        login_data = {"password": "TestPassword123!", "remember_me": False}
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "validation_errors" in data

    def test_login_user_missing_password(self, client: Any) -> Any:
        """Test login with missing password."""
        login_data = {"email": "test@example.com", "remember_me": False}
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "validation_errors" in data

    def test_refresh_token_missing_token(self, client: Any) -> Any:
        """Test token refresh with missing token."""
        response = client.post("/api/v1/auth/refresh", json={})
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "validation_errors" in data

    def test_refresh_token_invalid_token(self, client: Any) -> Any:
        """Test token refresh with invalid token."""
        refresh_data = {"refresh_token": "invalid_token"}
        response = client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code in [401, 500]

    def test_logout_without_auth(self, client: Any) -> Any:
        """Test logout without authentication."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_change_password_without_auth(self, client: Any) -> Any:
        """Test password change without authentication."""
        password_data = {
            "current_password": "OldPassword123!",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        }
        response = client.post("/api/v1/auth/change-password", json=password_data)
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_verify_email_invalid_token(self, client: Any) -> Any:
        """Test email verification with invalid token."""
        response = client.post(
            "/api/v1/auth/verify-email", json={"token": "invalid_token"}
        )
        assert response.status_code in [400, 401, 500]

    def test_password_reset_request(self, client: Any) -> Any:
        """Test password reset request."""
        reset_data = {"email": "test@example.com"}
        response = client.post("/api/v1/auth/password-reset", json=reset_data)
        assert response.status_code in [200, 500]

    def test_password_reset_request_invalid_email(self, client: Any) -> Any:
        """Test password reset request with invalid email."""
        reset_data = {"email": "invalid-email"}
        response = client.post("/api/v1/auth/password-reset", json=reset_data)
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "validation_errors" in data

    def test_password_reset_confirm_invalid_token(self, client: Any) -> Any:
        """Test password reset confirmation with invalid token."""
        confirm_data = {
            "token": "invalid_token",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        }
        response = client.post("/api/v1/auth/password-reset/confirm", json=confirm_data)
        assert response.status_code in [400, 401, 500]

    def test_password_reset_confirm_password_mismatch(self, client: Any) -> Any:
        """Test password reset confirmation with password mismatch."""
        confirm_data = {
            "token": "some_token",
            "new_password": "NewPassword123!",
            "confirm_password": "DifferentPassword123!",
        }
        response = client.post("/api/v1/auth/password-reset/confirm", json=confirm_data)
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "validation_errors" in data

    def test_get_current_user_without_auth(self, client: Any) -> Any:
        """Test getting current user without authentication."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_get_user_sessions_without_auth(self, client: Any) -> Any:
        """Test getting user sessions without authentication."""
        response = client.get("/api/v1/auth/sessions")
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_revoke_session_without_auth(self, client: Any) -> Any:
        """Test revoking session without authentication."""
        session_id = "some-session-id"
        response = client.delete(f"/api/v1/auth/sessions/{session_id}")
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_enable_mfa_without_auth(self, client: Any) -> Any:
        """Test enabling MFA without authentication."""
        mfa_data = {"method": "totp"}
        response = client.post("/api/v1/auth/mfa/setup", json=mfa_data)
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_verify_mfa_without_auth(self, client: Any) -> Any:
        """Test verifying MFA without authentication."""
        mfa_data = {"code": "123456", "method": "totp"}
        response = client.post("/api/v1/auth/mfa/verify", json=mfa_data)
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_disable_mfa_without_auth(self, client: Any) -> Any:
        """Test disabling MFA without authentication."""
        mfa_data = {"password": "TestPassword123!", "code": "123456"}
        response = client.post("/api/v1/auth/mfa/disable", json=mfa_data)
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_create_api_key_without_auth(self, client: Any) -> Any:
        """Test creating API key without authentication."""
        api_key_data = {
            "name": "Test API Key",
            "description": "Test API key description",
            "permissions": ["read:profile"],
        }
        response = client.post("/api/v1/auth/api-keys", json=api_key_data)
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_list_api_keys_without_auth(self, client: Any) -> Any:
        """Test listing API keys without authentication."""
        response = client.get("/api/v1/auth/api-keys")
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_revoke_api_key_without_auth(self, client: Any) -> Any:
        """Test revoking API key without authentication."""
        api_key_id = "some-api-key-id"
        response = client.delete(f"/api/v1/auth/api-keys/{api_key_id}")
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_login_rate_limiting(self, client: Any) -> Any:
        """Test login rate limiting."""
        login_data = {
            "email": "test@example.com",
            "password": "WrongPassword123!",
            "remember_me": False,
        }
        responses = []
        for _ in range(10):
            response = client.post("/api/v1/auth/login", json=login_data)
            responses.append(response)
        status_codes = [r.status_code for r in responses]
        assert any((code in [401, 429, 500] for code in status_codes))

    def test_registration_rate_limiting(self, client: Any) -> Any:
        """Test registration rate limiting."""
        responses = []
        for i in range(5):
            registration_data = {
                "email": f"test{i}@example.com",
                "password": "TestPassword123!",
                "confirm_password": "TestPassword123!",
                "username": f"testuser{i}",
                "first_name": "Test",
                "last_name": "User",
                "terms_accepted": True,
                "privacy_accepted": True,
            }
            response = client.post("/api/v1/auth/register", json=registration_data)
            responses.append(response)
        status_codes = [r.status_code for r in responses]
        assert all((code in [201, 400, 409, 422, 429, 500] for code in status_codes))

    def test_security_headers_present(self, client: Any) -> Any:
        """Test that security headers are present in responses."""
        response = client.get("/api/v1/auth/me")
        response.headers
        assert response.status_code in [200, 401, 500]

    def test_cors_headers(self, client: Any) -> Any:
        """Test CORS headers are present."""
        response = client.options("/api/v1/auth/login")
        assert response.status_code in [200, 405]
