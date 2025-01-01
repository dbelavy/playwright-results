from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from playwright.async_api import Browser, BrowserContext, Page

from models import Credentials, PatientDetails, SharedState
from tests.playwright_test import PlaywrightTestCase


# Fixtures
@pytest.fixture
def mock_page():
    """Create a mock page with async capabilities."""
    page = MagicMock(spec=Page)

    # Mock common async methods
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.wait_for_load_state = AsyncMock()

    # Mock element selection methods with default async mocks
    def mock_element(**kwargs):
        element = MagicMock()
        for key, value in kwargs.items():
            setattr(element, key, AsyncMock(return_value=value))
        return element

    page.get_by_label = MagicMock(
        side_effect=lambda label: mock_element(click=None, fill=None, press=None)
    )
    page.get_by_role = MagicMock(
        side_effect=lambda role, **kwargs: mock_element(click=None, fill=None)
    )
    page.get_by_placeholder = MagicMock(
        side_effect=lambda text: mock_element(click=None, fill=None)
    )

    return page


@pytest.fixture
def mock_browser(mock_context):
    """Create a mock browser."""
    browser = MagicMock(spec=Browser)
    browser.new_context = AsyncMock(return_value=mock_context)
    return browser


@pytest.fixture
def mock_context(mock_page):
    """Create a mock browser context."""
    context = MagicMock(spec=BrowserContext)
    context.new_page = AsyncMock(return_value=mock_page)
    return context


@pytest.fixture
def test_credentials():
    """Test credentials fixture - use environment variables in CI."""
    return {
        "MaterPath": {
            "user_name": "test_user",
            "user_password": "test_pass",
            "totp_secret": "test_secret",
        },
        "Sonic": {"user_name": "test_user", "user_password": "test_pass"}
        # Add other provider credentials as needed
    }


@pytest.fixture
def test_patient():
    """Test patient data fixture."""
    return {
        "family_name": "SMITH",
        "given_name": "JOHN",
        "dob": "01011990",
        "medicare_number": "1234567890",
        "sex": "M",
    }


# Base test class for common provider tests
class BaseProviderTest(PlaywrightTestCase):
    """Base class for provider test cases."""

    @pytest.mark.asyncio
    async def test_required_fields(self, provider_session):
        """Test that required fields are properly defined."""
        assert hasattr(provider_session, "required_fields")
        assert isinstance(provider_session.required_fields, list)
        assert len(provider_session.required_fields) > 0

    @pytest.mark.asyncio
    async def test_provider_group(self, provider_session):
        """Test provider group is set."""
        assert hasattr(provider_session, "provider_group")
        assert provider_session.provider_group in ["Pathology", "Radiology", "General"]

    @pytest.mark.asyncio
    async def test_credentials_key(self, provider_session):
        """Test credentials key is set."""
        assert hasattr(provider_session, "credentials_key")
        assert isinstance(provider_session.credentials_key, str)
