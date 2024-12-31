import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from providers.qscript import QScriptSession
from utils import convert_date_format
from tests.playwright_test import PlaywrightTestCase

class TestQScript(PlaywrightTestCase):
    """Test cases for QScript provider."""

    @pytest.fixture
    def provider_session(self, mock_page, mock_browser, test_credentials, test_patient):
        """Create a QScript session for testing."""
        from models import PatientDetails, SharedState, Credentials
        
        # Create proper objects from test data
        credentials = Credentials(
            user_name=test_credentials["QScript"]["user_name"],
            user_password=test_credentials["QScript"]["user_password"],
            PIN=test_credentials["QScript"]["PIN"]
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
        
        session = QScriptSession(credentials, patient, shared_state)
        return session

    @pytest.mark.asyncio
    async def test_login(self, initialized_session, test_credentials):
        """Test login flow including 2FA and PIN."""
        session, page = await initialized_session
        
        # Set up page elements
        username_field = self.get_mock_element(click=None, fill=None)
        next_button = self.get_mock_element(click=None)
        password_field = self.get_mock_element(click=None, fill=None)
        login_button = self.get_mock_element(click=None)
        code_field = self.get_mock_element(fill=None)
        verify_button = self.get_mock_element(click=None)
        pin_field = self.get_mock_element(fill=None)
        save_pin_button = self.get_mock_element(click=None)
        
        # Mock placeholder selectors
        page.get_by_placeholder = MagicMock(side_effect=lambda text: {
            "Enter username": username_field,
            "Enter password": password_field,
            "Verification code": code_field,
            "Enter PIN": pin_field
        }.get(text, Mock()))
        
        # Mock label and role selectors
        page.get_by_label = MagicMock(side_effect=lambda label: {
            "Next": next_button,
            "Log In": login_button,
            "Save PIN and Log In": save_pin_button
        }.get(label, Mock()))
        
        page.get_by_role = MagicMock(side_effect=lambda role, **kwargs: {
            ("button", "Verify"): verify_button
        }.get((role, kwargs.get('name')), Mock()))
        
        # Set up shared state for 2FA
        async def mock_sleep(seconds):
            # Simulate 2FA code being set after first sleep
            if not session.shared_state.QScript_code:
                session.shared_state.QScript_code = "123456"
        
        # Mock asyncio.sleep to handle 2FA waiting
        import asyncio
        original_sleep = asyncio.sleep
        asyncio.sleep = mock_sleep
        
        try:
            # Perform login
            await session.login()
        finally:
            # Restore original sleep
            asyncio.sleep = original_sleep
        
        # Verify username entry and next
        page.get_by_placeholder.assert_any_call("Enter username")
        username_field.click.assert_called_once()
        username_field.fill.assert_called_with(test_credentials["QScript"]["user_name"])
        
        page.get_by_label.assert_any_call("Next")
        next_button.click.assert_called_once()
        
        # Verify password entry and login
        page.get_by_placeholder.assert_any_call("Enter password")
        password_field.click.assert_called_once()
        password_field.fill.assert_called_with(test_credentials["QScript"]["user_password"])
        
        page.get_by_label.assert_any_call("Log In")
        login_button.click.assert_called_once()
        
        # Verify 2FA steps
        assert session.shared_state.new_2fa_request == "QScript"  # Check 2FA request set
        page.get_by_placeholder.assert_any_call("Verification code")
        code_field.fill.assert_called_once()  # Don't verify exact code as it's from shared state
        
        page.get_by_role.assert_called_with("button", name="Verify")
        verify_button.click.assert_called_once()
        
        # Verify PIN entry
        page.get_by_placeholder.assert_any_call("Enter PIN")
        pin_field.fill.assert_called_with(test_credentials["QScript"]["PIN"])
        
        page.get_by_label.assert_any_call("Save PIN and Log In")
        save_pin_button.click.assert_called_once()
        
        # Verify network idle waits
        assert page.wait_for_load_state.call_count >= 2  # Multiple network idle waits

    @pytest.mark.asyncio
    async def test_search_patient(self, initialized_session, test_patient):
        """Test patient search using data-test-id selectors."""
        session, page = await initialized_session
        
        # Set up page elements
        firstname_field = self.get_mock_element(click=None, fill=None, press=None)
        surname_field = self.get_mock_element(fill=None, press=None)
        dob_field = self.get_mock_element(fill=None)
        search_button = self.get_mock_element(click=None)
        
        # Mock data-test-id selectors
        dob_container = MagicMock()
        dob_container.get_by_placeholder = MagicMock(return_value=dob_field)
        
        page.locator = MagicMock(side_effect=lambda selector: {
            '[data-test-id="patientSearchFirstName"]': firstname_field,
            '[data-test-id="patientSearchSurname"]': surname_field,
            '[data-test-id="dateOfBirth"]': dob_container
        }.get(selector, Mock()))
        
        # Mock label selectors
        page.get_by_label = MagicMock(side_effect=lambda label: {
            "Search": search_button
        }.get(label, Mock()))
        
        # Perform search
        await session.search_patient()
        
        # Verify first name entry
        page.locator.assert_any_call('[data-test-id="patientSearchFirstName"]')
        firstname_field.click.assert_called_once()
        firstname_field.fill.assert_called_with(test_patient["given_name"])
        firstname_field.press.assert_called_with("Tab")
        
        # Verify surname entry
        page.locator.assert_any_call('[data-test-id="patientSearchSurname"]')
        surname_field.fill.assert_called_with(test_patient["family_name"])
        surname_field.press.assert_called_with("Tab")
        
        # Verify DOB entry
        page.locator.assert_any_call('[data-test-id="dateOfBirth"]')
        dob_container.get_by_placeholder.assert_called_with(" ")
        converted_dob = convert_date_format(test_patient["dob"], "%d%m%Y", "%d/%m/%Y")
        dob_field.fill.assert_called_with(converted_dob)
        
        # Verify search button click
        page.get_by_label.assert_called_with("Search")
        search_button.click.assert_called_once()

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
        assert provider_session.provider_group == "General"
        assert provider_session.credentials_key == "QScript"
