import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from providers.qxr import QXRSession
from utils import convert_date_format
from tests.playwright_test import PlaywrightTestCase

class TestQXR(PlaywrightTestCase):
    """Test cases for QXR provider."""

    @pytest.fixture
    def provider_session(self, mock_page, mock_browser, test_credentials, test_patient):
        """Create a QXR session for testing."""
        from models import PatientDetails, SharedState, Credentials
        
        # Create proper objects from test data
        credentials = Credentials(
            user_name=test_credentials["QXR"]["user_name"],
            user_password=test_credentials["QXR"]["user_password"]
        )
        patient = PatientDetails(
            family_name=test_patient["family_name"],
            given_name=test_patient["given_name"],
            dob=test_patient["dob"],
            medicare_number=test_patient.get("medicare_number"),
            sex=test_patient.get("sex")
        )
        shared_state = SharedState()
        shared_state.page = mock_page
        shared_state.browser = mock_browser
        
        session = QXRSession(credentials, patient, shared_state)
        return session

    @pytest.mark.asyncio
    async def test_login(self, initialized_session, test_credentials):
        """Test login flow."""
        session, page = await initialized_session
        
        # Set up page elements
        username_field = self.get_mock_element(click=None, fill=None)
        password_field = self.get_mock_element(click=None, fill=None)
        login_button = self.get_mock_element(click=None)
        
        # Mock placeholder selectors
        page.get_by_placeholder = MagicMock(side_effect=lambda text: {
            "Username": username_field,
            "Password": password_field
        }.get(text, Mock()))
        
        # Mock role selectors
        page.get_by_role = MagicMock(side_effect=lambda role, **kwargs: {
            ("button",): login_button
        }.get((role,), Mock()))
        
        # Perform login
        await session.login()
        
        # Verify username entry
        page.get_by_placeholder.assert_any_call("Username")
        username_field.click.assert_called_once()
        username_field.fill.assert_called_with(test_credentials["QXR"]["user_name"])
        
        # Verify password entry
        page.get_by_placeholder.assert_any_call("Password")
        password_field.click.assert_called_once()
        password_field.fill.assert_called_with(test_credentials["QXR"]["user_password"])
        
        # Verify login button click
        page.get_by_role.assert_called_with("button")
        login_button.click.assert_called_once()
        
        # Verify network idle wait
        page.wait_for_load_state.assert_called_with("networkidle")

    @pytest.mark.asyncio
    async def test_search_patient(self, initialized_session, test_patient):
        """Test patient search with DOB popup handling."""
        session, page = await initialized_session
        
        # Set up page elements
        search_field = self.get_mock_element(click=None, fill=None)
        arrow = self.get_mock_element(click=None, wait_for=None)
        dob_field = self.get_mock_element(click=None, fill=None, wait_for=None)
        search_button = self.get_mock_element(click=None, wait_for=None)
        
        # Mock placeholder selectors
        page.get_by_placeholder = MagicMock(side_effect=lambda text: {
            "Search patient name, id,": search_field,
            "DD/MM/YYYY": dob_field
        }.get(text, Mock()))
        
        # Mock locator for arrow
        arrow_locator = MagicMock()
        arrow_locator.first = arrow
        page.locator = MagicMock(side_effect=lambda selector: {
            "div.arrow.arrow-up": arrow_locator
        }.get(selector, Mock()))
        
        # Mock role selector for search button
        button_mock = MagicMock()
        button_mock.nth = MagicMock(return_value=search_button)
        page.get_by_role = MagicMock(side_effect=lambda role: {
            "button": button_mock
        }.get(role, Mock()))
        
        # Mock screenshot for error handling
        page.screenshot = AsyncMock()
        
        # Mock timeout
        page.wait_for_timeout = AsyncMock()
        
        # Perform search
        await session.search_patient()
        
        # Verify search field interaction
        page.get_by_placeholder.assert_any_call("Search patient name, id,")
        search_field.click.assert_called_once()
        search_field.fill.assert_called_with(f"{test_patient['family_name']}, {test_patient['given_name']}")
        
        # Verify arrow interaction
        page.locator.assert_called_with("div.arrow.arrow-up")
        arrow.wait_for.assert_called_with(state="visible", timeout=5000)
        arrow.click.assert_called_once()
        
        # Verify timeout after arrow click
        page.wait_for_timeout.assert_any_call(1000)
        
        # Verify DOB entry
        page.get_by_placeholder.assert_any_call("DD/MM/YYYY")
        dob_field.wait_for.assert_called_with(state="visible", timeout=5000)
        dob_field.click.assert_called_once()
        converted_dob = convert_date_format(test_patient["dob"], "%d%m%Y", "%d/%m/%Y")
        dob_field.fill.assert_called_with(converted_dob)
        
        # Verify search button interaction
        page.get_by_role.assert_called_with("button")
        button_mock.nth.assert_called_with(1)
        search_button.wait_for.assert_called_with(state="visible", timeout=5000)
        search_button.click.assert_called_once()
        
        # Verify network idle waits
        assert page.wait_for_load_state.call_count >= 2  # Multiple network idle waits

    @pytest.mark.asyncio
    async def test_search_patient_error_handling(self, initialized_session, test_patient):
        """Test error handling in patient search."""
        session, page = await initialized_session
        
        # Set up page elements with arrow that raises exception
        search_field = self.get_mock_element(click=None, fill=None)
        
        # Mock locator for arrow to raise error during wait_for
        arrow_locator = MagicMock()
        arrow_locator.first = MagicMock(
            wait_for=AsyncMock(side_effect=Exception("Arrow not found"))
        )
        
        # Mock placeholder selectors
        page.get_by_placeholder = MagicMock(side_effect=lambda text: {
            "Search patient name, id,": search_field
        }.get(text, Mock()))
        
        # Mock locator to return our failing arrow
        page.locator = MagicMock(side_effect=lambda selector: {
            "div.arrow.arrow-up": arrow_locator
        }.get(selector, Mock()))
        
        # Mock screenshot for error handling
        page.screenshot = AsyncMock()
        
        # Verify error handling
        with pytest.raises(Exception, match="Arrow not found"):
            await session.search_patient()
        
        # Verify screenshot was taken
        page.screenshot.assert_called_with(path="qxr_error.png")

    @pytest.mark.asyncio
    async def test_uninitialized_error(self, provider_session):
        """Test error handling for uninitialized session."""
        provider_session.page = None
        
        with pytest.raises(RuntimeError, match="Session not initialized"):
            await provider_session.login()
            
        with pytest.raises(RuntimeError, match="Session not initialized"):
            await provider_session.search_patient()

    @pytest.mark.asyncio
    async def test_required_fields(self, provider_session):
        """Test that required fields are correctly defined."""
        assert provider_session.required_fields == ['family_name', 'given_name', 'dob']
        assert provider_session.provider_group == "Radiology"
        assert provider_session.credentials_key == "QXR"
