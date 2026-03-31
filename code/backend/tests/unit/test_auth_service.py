"""
Unit tests for authentication service
"""

from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from models.user import UserRole, UserStatus
from schemas.auth import PasswordChange, UserLogin, UserRegister
from services.auth.auth_service import AuthenticationError, AuthService
from services.auth.jwt_service import JWTService
from services.auth.mfa_service import MFAService
from services.auth.security_service import SecurityService
from services.auth.session_service import SessionService


class TestAuthService:
    """Test authentication service functionality."""

    @pytest_asyncio.fixture
    async def auth_service(self):
        """Create auth service with mocked dependencies."""
        jwt_service = JWTService()
        mfa_service = MFAService()
        session_service = SessionService()
        security_service = SecurityService()
        return AuthService(jwt_service, mfa_service, session_service, security_service)

    @pytest_asyncio.fixture
    async def sample_user_register(self):
        """Sample user registration data."""
        return UserRegister(
            email="test@example.com",
            password="TestPassword123!",
            confirm_password="TestPassword123!",
            username="testuser",
            first_name="Test",
            last_name="User",
            terms_accepted=True,
            privacy_accepted=True,
        )

    @pytest_asyncio.fixture
    async def sample_user_login(self):
        """Sample user login data."""
        return UserLogin(
            email="test@example.com", password="TestPassword123!", remember_me=False
        )

    async def test_register_user_success(
        self, test_db, auth_service, sample_user_register
    ):
        """Test successful user registration."""
        user, token = await auth_service.register_user(
            test_db, sample_user_register, "127.0.0.1", "test-agent"
        )
        assert user is not None
        assert user.email == sample_user_register.email
        assert user.username == sample_user_register.username
        assert user.status == UserStatus.PENDING
        assert user.role == UserRole.USER
        assert not user.is_email_verified
        assert token is not None
        assert len(token) > 0

    async def test_register_user_duplicate_email(
        self, test_db, auth_service, sample_user_register
    ):
        """Test registration with duplicate email."""
        await auth_service.register_user(
            test_db, sample_user_register, "127.0.0.1", "test-agent"
        )
        with pytest.raises(
            AuthenticationError, match="User with this email already exists"
        ):
            await auth_service.register_user(
                test_db, sample_user_register, "127.0.0.1", "test-agent"
            )

    async def test_register_user_duplicate_username(
        self, test_db, auth_service, sample_user_register
    ):
        """Test registration with duplicate username."""
        await auth_service.register_user(
            test_db, sample_user_register, "127.0.0.1", "test-agent"
        )
        duplicate_username_data = sample_user_register.copy()
        duplicate_username_data.email = "different@example.com"
        with pytest.raises(AuthenticationError, match="Username already taken"):
            await auth_service.register_user(
                test_db, duplicate_username_data, "127.0.0.1", "test-agent"
            )

    async def test_authenticate_user_success(
        self, test_db, auth_service, test_user, sample_user_login
    ):
        """Test successful user authentication."""
        test_user.email = sample_user_login.email
        test_user.hashed_password = auth_service._hash_password(
            sample_user_login.password
        )
        test_user.is_email_verified = True
        test_user.status = UserStatus.ACTIVE
        await test_db.commit()
        user, token_response, session = await auth_service.authenticate_user(
            test_db, sample_user_login, "127.0.0.1", "test-agent"
        )
        assert user is not None
        assert user.email == sample_user_login.email
        assert token_response is not None
        assert token_response.access_token is not None
        assert token_response.refresh_token is not None
        assert token_response.token_type == "bearer"
        assert session is not None
        assert session.is_active

    async def test_authenticate_user_invalid_email(
        self, test_db, auth_service, sample_user_login
    ):
        """Test authentication with invalid email."""
        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            await auth_service.authenticate_user(
                test_db, sample_user_login, "127.0.0.1", "test-agent"
            )

    async def test_authenticate_user_invalid_password(
        self, test_db, auth_service, test_user, sample_user_login
    ):
        """Test authentication with invalid password."""
        test_user.email = sample_user_login.email
        test_user.hashed_password = auth_service._hash_password("WrongPassword123!")
        test_user.is_email_verified = True
        test_user.status = UserStatus.ACTIVE
        await test_db.commit()
        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            await auth_service.authenticate_user(
                test_db, sample_user_login, "127.0.0.1", "test-agent"
            )

    async def test_authenticate_user_locked_account(
        self, test_db, auth_service, test_user, sample_user_login
    ):
        """Test authentication with locked account."""
        test_user.email = sample_user_login.email
        test_user.hashed_password = auth_service._hash_password(
            sample_user_login.password
        )
        test_user.status = UserStatus.LOCKED
        test_user.is_email_verified = True
        await test_db.commit()
        with pytest.raises(AuthenticationError, match="Account is locked"):
            await auth_service.authenticate_user(
                test_db, sample_user_login, "127.0.0.1", "test-agent"
            )

    async def test_authenticate_user_unverified_email(
        self, test_db, auth_service, test_user, sample_user_login
    ):
        """Test authentication with unverified email."""
        test_user.email = sample_user_login.email
        test_user.hashed_password = auth_service._hash_password(
            sample_user_login.password
        )
        test_user.is_email_verified = False
        test_user.status = UserStatus.ACTIVE
        await test_db.commit()
        with pytest.raises(AuthenticationError, match="Email not verified"):
            await auth_service.authenticate_user(
                test_db, sample_user_login, "127.0.0.1", "test-agent"
            )

    async def test_change_password_success(self, test_db, auth_service, test_user):
        """Test successful password change."""
        old_password = "OldPassword123!"
        new_password = "NewPassword123!"
        test_user.hashed_password = auth_service._hash_password(old_password)
        await test_db.commit()
        password_data = PasswordChange(
            current_password=old_password,
            new_password=new_password,
            confirm_password=new_password,
        )
        await auth_service.change_password(
            test_db, test_user.id, password_data, "127.0.0.1", "test-agent"
        )
        await test_db.refresh(test_user)
        assert auth_service._verify_password(new_password, test_user.hashed_password)
        assert test_user.password_changed_at is not None

    async def test_change_password_invalid_current(
        self, test_db, auth_service, test_user
    ):
        """Test password change with invalid current password."""
        old_password = "OldPassword123!"
        new_password = "NewPassword123!"
        test_user.hashed_password = auth_service._hash_password(old_password)
        await test_db.commit()
        password_data = PasswordChange(
            current_password="WrongPassword123!",
            new_password=new_password,
            confirm_password=new_password,
        )
        with pytest.raises(AuthenticationError, match="Invalid current password"):
            await auth_service.change_password(
                test_db, test_user.id, password_data, "127.0.0.1", "test-agent"
            )

    async def test_verify_email_success(self, test_db, auth_service, test_user):
        """Test successful email verification."""
        test_user.is_email_verified = False
        test_user.status = UserStatus.PENDING
        await test_db.commit()
        token = "valid_verification_token"
        auth_service._extract_user_id_from_token = lambda token: test_user.id
        verified_user = await auth_service.verify_email(
            test_db, token, "127.0.0.1", "test-agent"
        )
        assert verified_user.id == test_user.id
        assert verified_user.is_email_verified
        assert verified_user.status == UserStatus.ACTIVE

    async def test_verify_email_already_verified(
        self, test_db, auth_service, test_user
    ):
        """Test email verification when already verified."""
        test_user.is_email_verified = True
        test_user.status = UserStatus.ACTIVE
        await test_db.commit()
        token = "valid_verification_token"
        auth_service._extract_user_id_from_token = lambda token: test_user.id
        with pytest.raises(AuthenticationError, match="Email already verified"):
            await auth_service.verify_email(test_db, token, "127.0.0.1", "test-agent")

    async def test_logout_user_success(self, test_db, auth_service, test_user):
        """Test successful user logout."""
        session_id = uuid4()
        auth_service.session_service.invalidate_session = lambda db, sid: None
        await auth_service.logout_user(
            test_db, test_user.id, session_id, "127.0.0.1", "test-agent"
        )

    def test_hash_password(self, auth_service: Any) -> Any:
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = auth_service._hash_password(password)
        assert hashed != password
        assert len(hashed) > 0
        assert auth_service._verify_password(password, hashed)

    def test_verify_password(self, auth_service: Any) -> Any:
        """Test password verification."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = auth_service._hash_password(password)
        assert auth_service._verify_password(password, hashed)
        assert not auth_service._verify_password(wrong_password, hashed)

    def test_generate_verification_token(self, auth_service: Any) -> Any:
        """Test verification token generation."""
        token = auth_service._generate_verification_token()
        assert token is not None
        assert len(token) == 32
        assert token.isalnum()

    async def test_handle_failed_login(self, test_db, auth_service, test_user):
        """Test failed login handling."""
        initial_attempts = test_user.failed_login_attempts
        await auth_service._handle_failed_login(
            test_db, test_user, "127.0.0.1", "test-agent"
        )
        assert test_user.failed_login_attempts == initial_attempts + 1

    async def test_handle_failed_login_lockout(self, test_db, auth_service, test_user):
        """Test account lockout after max failed attempts."""
        from config.settings import settings

        test_user.failed_login_attempts = settings.auth.MAX_LOGIN_ATTEMPTS - 1
        await auth_service._handle_failed_login(
            test_db, test_user, "127.0.0.1", "test-agent"
        )
        assert test_user.failed_login_attempts == settings.auth.MAX_LOGIN_ATTEMPTS
        assert test_user.status == UserStatus.LOCKED
        assert test_user.locked_until is not None

    async def test_get_user_by_email(self, test_db, auth_service, test_user):
        """Test getting user by email."""
        found_user = await auth_service._get_user_by_email(test_db, test_user.email)
        assert found_user is not None
        assert found_user.id == test_user.id
        assert found_user.email == test_user.email

    async def test_get_user_by_email_not_found(self, test_db, auth_service):
        """Test getting user by email when not found."""
        found_user = await auth_service._get_user_by_email(
            test_db, "nonexistent@example.com"
        )
        assert found_user is None

    async def test_get_user_by_username(self, test_db, auth_service, test_user):
        """Test getting user by username."""
        found_user = await auth_service._get_user_by_username(
            test_db, test_user.username
        )
        assert found_user is not None
        assert found_user.id == test_user.id
        assert found_user.username == test_user.username

    async def test_get_user_by_id(self, test_db, auth_service, test_user):
        """Test getting user by ID."""
        found_user = await auth_service._get_user_by_id(test_db, test_user.id)
        assert found_user is not None
        assert found_user.id == test_user.id
