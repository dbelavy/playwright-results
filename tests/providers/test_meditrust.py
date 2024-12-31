import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from providers.meditrust import MediTrustSession
from utils import generate_2fa_code
from tests.playwright_test import PlaywrightTestCase

class TestMediTrust(PlaywrightTestCase):
    """Test cases for MediTrust provider."""

    @pytest.fixture
    def provider_session(self, mock_page, mock_browser, test_credentials):
        """Create a MediTrust session for testing."""
        from models import SharedState, Credentials
        
        # Create proper objects from test data
        credentials = Credentials(
            user_name=test_credentials["Meditrust"]["user_name"],
            user_password=test_credentials["Meditrust"]["user_password"],
            totp_secret=test_credentials["Meditrust"]["totp_secret"]
        )
        shared_state = SharedState()
        shared_state.page = mock_page
        shared_state.browser = mock_browser
        
        # Note: patient is optional for MediTrust
        session = MediTrustSession(credentials, None, shared_state)
        return session

    @pytest.mark.asyncio
    async def test_login(self, initialized_session, test_credentials):
        """Test login flow including 2FA."""
        session, page = await initialized_session
        
        # Set up page elements
        login_link = self.get_mock_element(click=None)
        username_field = self.get_mock_element(click=None, fill=None)
        password_field = self.get_mock_element(click=None, fill=None)
        login_button = self.get_mock_element(click=None)
        code_field = self.get_mock_element(click=None, fill=None)
        submit_button = self.get_mock_element(click=None)
        
        # Mock role selectors
        page.get_by_role = MagicMock(side_effect=lambda role, **kwargs: {
            ("link", " Login"): login_link,
            ("button", "Login"): login_button,
            ("button", "Submit"): submit_button
        }.get((role, kwargs.get('name')), Mock()))
        
        # Mock label selectors
        page.get_by_label = MagicMock(side_effect=lambda label: {
            "Username:": username_field,
            "Password:": password_field
        }.get(label, Mock()))
        
        # Mock placeholder selectors
        page.get_by_placeholder = MagicMock(side_effect=lambda text: {
            "Authentication Code": code_field
        }.get(text, Mock()))
        
        # Perform login
        await session.login()
        
        # Verify initial login steps
        page.get_by_role.assert_any_call("link", name=" Login")
        login_link.click.assert_called_once()
        
        page.get_by_label.assert_any_call("Username:")
        username_field.click.assert_called_once()
        username_field.fill.assert_called_with(test_credentials["Meditrust"]["user_name"])
        
        page.get_by_label.assert_any_call("Password:")
        password_field.click.assert_called_once()
        password_field.fill.assert_called_with(test_credentials["Meditrust"]["user_password"])
        
        page.get_by_role.assert_any_call("button", name="Login")
        login_button.click.assert_called_once()
        
        # Verify 2FA steps
        page.get_by_placeholder.assert_called_with("Authentication Code")
        code_field.click.assert_called_once()
        code_field.fill.assert_called_once()  # Don't verify exact code as it's time-based
        
        page.get_by_role.assert_any_call("button", name="Submit")
        submit_button.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_patient(self, initialized_session):
        """Test that search_patient is a no-op."""
        session, page = await initialized_session
        
        # search_patient should do nothing
        await session.search_patient()
        
        # Verify no interactions with page
        page.get_by_role.assert_not_called()
        page.get_by_label.assert_not_called()
        page.get_by_placeholder.assert_not_called()

    @pytest.mark.asyncio
    async def test_uninitialized_error(self, provider_session):
        """Test error handling for uninitialized session."""
        provider_session.page = None
        
        with pytest.raises(RuntimeError, match="Session not initialized"):
            await provider_session.login()

    @pytest.mark.asyncio
    async def test_required_fields(self, provider_session):
        """Test that required fields is empty."""
        assert provider_session.required_fields == []  # No required fields
        assert provider_session.provider_group == "Other"
        assert provider_session.credentials_key == "Meditrust"

    @pytest.mark.asyncio
    async def test_create_without_patient(self, mock_page, mock_browser, test_credentials):
        """Test that create works without patient details."""
        from models import SharedState, Credentials
        
        # Create session without patient
        shared_state = SharedState()
        shared_state.page = mock_page
        shared_state.browser = mock_browser
        
        session = MediTrustSession.create(None, shared_state)
        
        # Verify session was created successfully
        assert session is not None
        assert session.patient is None
        # Verify credentials structure without comparing exact values
        assert hasattr(session.credentials, 'user_name')
        assert hasattr(session.credentials, 'user_password')
        assert hasattr(session.credentials, 'totp_secret')
        assert session.credentials.PIN is None
        assert session.credentials.postcode is None
        assert session.credentials.suburb is None
        assert session.credentials.PRODA_full_name is None
