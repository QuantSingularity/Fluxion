"""
Unit tests for User Service
Tests user registration, authentication, profile management, and security features.
"""

from typing import Any
from unittest.mock import patch

import pytest
import pytest_asyncio
from services.auth.jwt_service import DeviceInfo
from services.user.user_service import UserService, UserStatus, UserType


@pytest.mark.unit
class TestUserService:
    """Test cases for UserService"""

    @pytest_asyncio.fixture
    async def user_service(self):
        """Create user service instance for testing"""
        return UserService()

    @pytest.fixture
    def sample_user_data(self) -> Any:
        """Sample user data for testing"""
        return {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "user_type": UserType.INDIVIDUAL,
            "profile_data": {
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "+1234567890",
                "country_of_residence": "US",
            },
            "device_info": DeviceInfo(
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0 Test Browser",
                device_id="test_device_123",
            ),
        }

    @pytest.mark.asyncio
    async def test_register_user_success(self, user_service, sample_user_data):
        """Test successful user registration"""
        result = await user_service.register_user(
            email=sample_user_data["email"],
            password=sample_user_data["password"],
            user_type=sample_user_data["user_type"],
            profile_data=sample_user_data["profile_data"],
            device_info=sample_user_data["device_info"],
        )
        assert result["success"] is True
        assert "user_id" in result
        assert result["email"] == sample_user_data["email"]
        assert result["user_type"] == sample_user_data["user_type"].value
        assert result["status"] == UserStatus.PENDING_VERIFICATION.value
        assert "verification_token" in result

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, user_service, sample_user_data):
        """Test registration with duplicate email"""
        await user_service.register_user(
            email=sample_user_data["email"],
            password=sample_user_data["password"],
            user_type=sample_user_data["user_type"],
            profile_data=sample_user_data["profile_data"],
            device_info=sample_user_data["device_info"],
        )
        with pytest.raises(ValueError, match="Email already registered"):
            await user_service.register_user(
                email=sample_user_data["email"],
                password="DifferentPassword123!",
                user_type=sample_user_data["user_type"],
                profile_data=sample_user_data["profile_data"],
                device_info=sample_user_data["device_info"],
            )

    @pytest.mark.asyncio
    async def test_register_user_weak_password(self, user_service, sample_user_data):
        """Test registration with weak password"""
        with pytest.raises(
            ValueError, match="Password does not meet security requirements"
        ):
            await user_service.register_user(
                email=sample_user_data["email"],
                password="weak",
                user_type=sample_user_data["user_type"],
                profile_data=sample_user_data["profile_data"],
                device_info=sample_user_data["device_info"],
            )

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, user_service, sample_user_data):
        """Test successful user authentication"""
        registration_result = await user_service.register_user(
            email=sample_user_data["email"],
            password=sample_user_data["password"],
            user_type=sample_user_data["user_type"],
            profile_data=sample_user_data["profile_data"],
            device_info=sample_user_data["device_info"],
        )
        await user_service.verify_email(registration_result["verification_token"])
        result = await user_service.authenticate_user(
            email=sample_user_data["email"],
            password=sample_user_data["password"],
            device_info=sample_user_data["device_info"],
        )
        assert result["success"] is True
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["user_id"] == registration_result["user_id"]
        assert result["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_credentials(
        self, user_service, sample_user_data
    ):
        """Test authentication with invalid credentials"""
        await user_service.register_user(
            email=sample_user_data["email"],
            password=sample_user_data["password"],
            user_type=sample_user_data["user_type"],
            profile_data=sample_user_data["profile_data"],
            device_info=sample_user_data["device_info"],
        )
        with pytest.raises(ValueError, match="Invalid credentials"):
            await user_service.authenticate_user(
                email=sample_user_data["email"],
                password="WrongPassword123!",
                device_info=sample_user_data["device_info"],
            )

    @pytest.mark.asyncio
    async def test_authenticate_user_unverified_email(
        self, user_service, sample_user_data
    ):
        """Test authentication with unverified email"""
        await user_service.register_user(
            email=sample_user_data["email"],
            password=sample_user_data["password"],
            user_type=sample_user_data["user_type"],
            profile_data=sample_user_data["profile_data"],
            device_info=sample_user_data["device_info"],
        )
        with pytest.raises(ValueError, match="Email not verified"):
            await user_service.authenticate_user(
                email=sample_user_data["email"],
                password=sample_user_data["password"],
                device_info=sample_user_data["device_info"],
            )

    @pytest.mark.asyncio
    async def test_verify_email_success(self, user_service, sample_user_data):
        """Test successful email verification"""
        registration_result = await user_service.register_user(
            email=sample_user_data["email"],
            password=sample_user_data["password"],
            user_type=sample_user_data["user_type"],
            profile_data=sample_user_data["profile_data"],
            device_info=sample_user_data["device_info"],
        )
        result = await user_service.verify_email(
            registration_result["verification_token"]
        )
        assert result["success"] is True
        assert result["message"] == "Email verified successfully"

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, user_service):
        """Test email verification with invalid token"""
        with pytest.raises(ValueError, match="Invalid or expired verification token"):
            await user_service.verify_email("invalid_token")

    @pytest.mark.asyncio
    async def test_change_password_success(self, user_service, sample_user_data):
        """Test successful password change"""
        registration_result = await user_service.register_user(
            email=sample_user_data["email"],
            password=sample_user_data["password"],
            user_type=sample_user_data["user_type"],
            profile_data=sample_user_data["profile_data"],
            device_info=sample_user_data["device_info"],
        )
        await user_service.verify_email(registration_result["verification_token"])
        new_password = "NewSecurePassword123!"
        result = await user_service.change_password(
            user_id=registration_result["user_id"],
            current_password=sample_user_data["password"],
            new_password=new_password,
        )
        assert result["success"] is True
        assert result["message"] == "Password changed successfully"
        auth_result = await user_service.authenticate_user(
            email=sample_user_data["email"],
            password=new_password,
            device_info=sample_user_data["device_info"],
        )
        assert auth_result["success"] is True

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, user_service, sample_user_data):
        """Test password change with wrong current password"""
        registration_result = await user_service.register_user(
            email=sample_user_data["email"],
            password=sample_user_data["password"],
            user_type=sample_user_data["user_type"],
            profile_data=sample_user_data["profile_data"],
            device_info=sample_user_data["device_info"],
        )
        await user_service.verify_email(registration_result["verification_token"])
        with pytest.raises(ValueError, match="Current password is incorrect"):
            await user_service.change_password(
                user_id=registration_result["user_id"],
                current_password="WrongPassword123!",
                new_password="NewSecurePassword123!",
            )

    @pytest.mark.asyncio
    async def test_enable_mfa_success(self, user_service, sample_user_data):
        """Test successful MFA enablement"""
        registration_result = await user_service.register_user(
            email=sample_user_data["email"],
            password=sample_user_data["password"],
            user_type=sample_user_data["user_type"],
            profile_data=sample_user_data["profile_data"],
            device_info=sample_user_data["device_info"],
        )
        await user_service.verify_email(registration_result["verification_token"])
        result = await user_service.enable_mfa(registration_result["user_id"])
        assert result["success"] is True
        assert "secret_key" in result
        assert "qr_code_url" in result
        assert "backup_codes" in result
        assert len(result["backup_codes"]) == 10

    @pytest.mark.asyncio
    async def test_verify_mfa_setup_success(self, user_service, sample_user_data):
        """Test successful MFA setup verification"""
        registration_result = await user_service.register_user(
            email=sample_user_data["email"],
            password=sample_user_data["password"],
            user_type=sample_user_data["user_type"],
            profile_data=sample_user_data["profile_data"],
            device_info=sample_user_data["device_info"],
        )
        await user_service.verify_email(registration_result["verification_token"])
        await user_service.enable_mfa(registration_result["user_id"])
        with patch("pyotp.TOTP.verify", return_value=True):
            result = await user_service.verify_mfa_setup(
                user_id=registration_result["user_id"], mfa_code="123456"
            )
        assert result["success"] is True
        assert result["message"] == "MFA enabled successfully"

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, user_service, sample_user_data):
        """Test successful user profile retrieval"""
        registration_result = await user_service.register_user(
            email=sample_user_data["email"],
            password=sample_user_data["password"],
            user_type=sample_user_data["user_type"],
            profile_data=sample_user_data["profile_data"],
            device_info=sample_user_data["device_info"],
        )
        await user_service.verify_email(registration_result["verification_token"])
        profile = await user_service.get_user_profile(registration_result["user_id"])
        assert profile["user_id"] == registration_result["user_id"]
        assert profile["email"] == sample_user_data["email"]
        assert profile["user_type"] == sample_user_data["user_type"].value
        assert (
            profile["profile"]["first_name"]
            == sample_user_data["profile_data"]["first_name"]
        )
        assert (
            profile["profile"]["last_name"]
            == sample_user_data["profile_data"]["last_name"]
        )
        assert profile["status"] == UserStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self, user_service):
        """Test user profile retrieval for non-existent user"""
        with pytest.raises(ValueError, match="User not found"):
            await user_service.get_user_profile("non_existent_user_id")

    @pytest.mark.asyncio
    async def test_update_user_profile_success(self, user_service, sample_user_data):
        """Test successful user profile update"""
        registration_result = await user_service.register_user(
            email=sample_user_data["email"],
            password=sample_user_data["password"],
            user_type=sample_user_data["user_type"],
            profile_data=sample_user_data["profile_data"],
            device_info=sample_user_data["device_info"],
        )
        await user_service.verify_email(registration_result["verification_token"])
        updated_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "phone_number": "+9876543210",
        }
        result = await user_service.update_user_profile(
            user_id=registration_result["user_id"], profile_data=updated_data
        )
        assert result["success"] is True
        assert result["profile"]["first_name"] == updated_data["first_name"]
        assert result["profile"]["last_name"] == updated_data["last_name"]
        assert result["profile"]["phone_number"] == updated_data["phone_number"]

    @pytest.mark.asyncio
    async def test_password_strength_validation(self, user_service):
        """Test password strength validation"""
        weak_passwords = [
            "123456",
            "password",
            "abc123",
            "Password",
            "Password123",
            "password123!",
            "PASSWORD123!",
        ]
        for weak_password in weak_passwords:
            is_strong = user_service._validate_password_strength(weak_password)
            assert (
                is_strong is False
            ), f"Password '{weak_password}' should be considered weak"
        strong_passwords = [
            "SecurePassword123!",
            "MyStr0ng@Password",
            "C0mpl3x#P@ssw0rd",
            "V3ry$ecur3P@ss",
        ]
        for strong_password in strong_passwords:
            is_strong = user_service._validate_password_strength(strong_password)
            assert (
                is_strong is True
            ), f"Password '{strong_password}' should be considered strong"

    @pytest.mark.asyncio
    async def test_user_statistics(self, user_service, sample_user_data):
        """Test user statistics retrieval"""
        for i in range(3):
            user_data = sample_user_data.copy()
            user_data["email"] = f"test{i}@example.com"
            registration_result = await user_service.register_user(
                email=user_data["email"],
                password=user_data["password"],
                user_type=user_data["user_type"],
                profile_data=user_data["profile_data"],
                device_info=user_data["device_info"],
            )
            if i < 2:
                await user_service.verify_email(
                    registration_result["verification_token"]
                )
        stats = user_service.get_user_statistics()
        assert stats["total_users"] >= 3
        assert stats["active_users"] >= 2
        assert stats["pending_verification"] >= 1
        assert "registration_rate" in stats
        assert "verification_rate" in stats
