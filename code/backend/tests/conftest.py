"""
Pytest configuration and fixtures for Fluxion backend tests
"""

import asyncio
from datetime import datetime
from typing import Any, AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from app.main import app
from config.database import Base
from fastapi.testclient import TestClient
from models.user import KYCStatus, User, UserRole, UserStatus
from services.auth.jwt_service import JWTService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def jwt_service() -> JWTService:
    """Create JWT service instance."""
    return JWTService()


@pytest_asyncio.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6QJgLppF5.",
        first_name="Test",
        last_name="User",
        status=UserStatus.ACTIVE,
        role=UserRole.USER,
        is_email_verified=True,
        kyc_status=KYCStatus.APPROVED,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(test_db: AsyncSession) -> User:
    """Create an admin test user."""
    user = User(
        id=uuid4(),
        email="admin@example.com",
        username="admin",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6QJgLppF5.",
        first_name="Admin",
        last_name="User",
        status=UserStatus.ACTIVE,
        role=UserRole.ADMIN,
        is_email_verified=True,
        kyc_status=KYCStatus.APPROVED,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User, jwt_service: JWTService) -> dict:
    """Create authentication headers for test user."""
    token_data = {
        "user_id": str(test_user.id),
        "email": test_user.email,
        "role": test_user.role.value,
    }
    access_token = jwt_service.create_access_token(token_data)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_auth_headers(admin_user: User, jwt_service: JWTService) -> dict:
    """Create authentication headers for admin user."""
    token_data = {
        "user_id": str(admin_user.id),
        "email": admin_user.email,
        "role": admin_user.role.value,
    }
    access_token = jwt_service.create_access_token(token_data)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def sample_transaction_data() -> dict:
    """Sample transaction data for testing."""
    return {
        "transaction_type": "deposit",
        "amount": "1000.50",
        "currency": "USDC",
        "from_address": "0x742d35Cc6634C0532925a3b8D0C9964F8b2Ac9d2",
        "to_address": "0x8ba1f109551bD432803012645Hac136c",
        "network": "ethereum",
    }


@pytest.fixture
def sample_kyc_data() -> dict:
    """Sample KYC data for testing."""
    return {
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": "1990-01-01",
        "nationality": "US",
        "document_type": "passport",
        "document_number": "123456789",
        "address_line1": "123 Main St",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001",
        "country": "US",
    }


@pytest.fixture
def sample_portfolio_data() -> dict:
    """Sample portfolio data for testing."""
    return {
        "name": "Test Portfolio",
        "description": "A test portfolio",
        "portfolio_type": "default",
        "investment_strategy": "balanced",
    }


@pytest.fixture
def mock_blockchain_response() -> dict:
    """Mock blockchain API response."""
    return {
        "transaction_hash": "0x1234567890abcdef",
        "block_number": 18500000,
        "block_hash": "0xabcdef1234567890",
        "status": "success",
        "gas_used": 21000,
        "gas_price": "20000000000",
    }


class MockExternalService:
    """Mock external service for testing."""

    def __init__(self) -> None:
        self.calls = []

    async def call_api(self, endpoint: str, data: dict = None) -> dict:
        """Mock API call."""
        self.calls.append({"endpoint": endpoint, "data": data})
        return {"status": "success", "data": data or {}}


@pytest.fixture
def mock_external_service() -> MockExternalService:
    """Create mock external service."""
    return MockExternalService()


def create_test_user_data(**kwargs) -> dict:
    """Create test user data with defaults."""
    default_data = {
        "email": f"test{uuid4().hex[:8]}@example.com",
        "password": "TestPassword123!",
        "confirm_password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
        "terms_accepted": True,
        "privacy_accepted": True,
    }
    default_data.update(kwargs)
    return default_data


def create_test_transaction_data(**kwargs) -> dict:
    """Create test transaction data with defaults."""
    default_data = {
        "transaction_type": "deposit",
        "amount": "100.00",
        "currency": "USDC",
        "from_address": "0x742d35Cc6634C0532925a3b8D0C9964F8b2Ac9d2",
        "to_address": "0x8ba1f109551bD432803012645Hac136c",
        "network": "ethereum",
    }
    default_data.update(kwargs)
    return default_data


class TestUtils:
    """Test utility functions."""

    @staticmethod
    def assert_response_success(response: Any, expected_status: int = 200) -> Any:
        """Assert response is successful."""
        assert response.status_code == expected_status
        data = response.json()
        assert data.get("success") is True
        return data

    @staticmethod
    def assert_response_error(response: Any, expected_status: int = 400) -> Any:
        """Assert response is an error."""
        assert response.status_code == expected_status
        data = response.json()
        assert data.get("success") is False
        assert "error" in data
        return data

    @staticmethod
    def assert_validation_error(response: Any) -> Any:
        """Assert response is a validation error."""
        assert response.status_code == 422
        data = response.json()
        assert data.get("success") is False
        assert "validation_errors" in data
        return data


@pytest.fixture
def test_utils() -> TestUtils:
    """Provide test utilities."""
    return TestUtils()


async def async_test_helper():
    """Helper for async tests."""
    await asyncio.sleep(0.01)
    return True


async def create_test_records(db: AsyncSession, model_class, count: int = 5, **kwargs):
    """Create multiple test records."""
    records = []
    for i in range(count):
        record_data = kwargs.copy()
        record_data.update(
            {
                "id": uuid4(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )
        record = model_class(**record_data)
        db.add(record)
        records.append(record)
    await db.commit()
    return records


@pytest.fixture
def performance_timer() -> Any:
    """Timer for performance tests."""
    import time

    class Timer:

        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return Timer()


@pytest.fixture(autouse=True)
async def cleanup_test_data():
    """Cleanup test data after each test."""
    yield
