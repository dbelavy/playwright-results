import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from providers.mater_pathology import MaterPathologySession
from utils import convert_date_format, generate_2fa_code
from tests.playwright_test import PlaywrightTestCase

class TestMaterPathology(PlaywrightTestCase):
    """Test cases for Mater Pathology provider."""

    @pytest.fixture
    def provider_session(self, mock_page, mock_browser, test_credentials, test_patient):
        """Create a Mater Pathology session for testing."""
        from models import PatientDetails, SharedState, Credentials
        
        # Create proper objects from test data
        credentials = Credentials(
            user_name=test_credentials["MaterPath"]["user_name"],
            user_password=test_credentials["MaterPath"]["user_password"],
            totp_secret=test_credentials["MaterPath"]["totp_secret"]
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
        
        session = MaterPathologySession(credentials, patient, shared_state)
        return session

    @pytest.mark.asyncio
    async def test_login(self, initialized_session, test_credentials):
        """Test login flow including 2FA."""
        session, page = await initialized_session
        
        # Set up page elements
        external_button = self.get_mock_element(click=None)
        username_field = self.get_mock_element(click=None, fill=None)
        next_button = self.get_mock_element(click=None)
        password_field = self.get_mock_element(fill=None)
        verify_button = self.get_mock_element(click=None)
        authenticator_link = self.get_mock_element(click=None)
        code_field = self.get_mock_element(click=None, fill=None)
        
        # Mock role selectors
        page.get_by_role = MagicMock(side_effect=lambda role, **kwargs: {
            ("button", "I am an External Practitioner"): external_button,
            ("button", "Next"): next_button,
            ("button", "Verify"): verify_button
        }.get((role, kwargs.get('name')), Mock()))
        
        # Mock label selectors
        page.get_by_label = MagicMock(side_effect=lambda label: {
            "Username": username_field,
            "Password": password_field,
            "Enter code": code_field,
            "Select Password.": Mock(click=AsyncMock())
        }.get(label, Mock()))
        
        # Mock wait_for_selector for password field visibility check
        page.wait_for_selector = AsyncMock(side_effect=lambda selector, **kwargs: {
            'input[type="Password"]': MagicMock(),
            'a:text("Verify with something else")': MagicMock(click=AsyncMock()),
            'a[aria-label="Select Google Authenticator"]': authenticator_link
        }.get(selector, Mock()))
        
        # Mock locator for authenticator selection
        page.locator = MagicMock(side_effect=lambda selector: {
            'a[aria-label="Select Google Authenticator"]': authenticator_link
        }.get(selector, Mock()))
        
        # Perform login
        await session.login()
        
        # Verify external practitioner selection
        page.get_by_role.assert_any_call("button", name="I am an External Practitioner")
        external_button.click.assert_called_once()
        
        # Verify username entry
        page.get_by_label.assert_any_call("Username")
        username_field.click.assert_called_once()
        username_field.fill.assert_called_with(test_credentials["MaterPath"]["user_name"])
        
        page.get_by_role.assert_any_call("button", name="Next")
        next_button.click.assert_called_once()
        
        # Verify password entry
        page.wait_for_selector.assert_any_call('input[type="Password"]', state="visible", timeout=2000)
        page.get_by_label.assert_any_call("Password")
        password_field.fill.assert_called_with(test_credentials["MaterPath"]["user_password"])
        
        # Verify 2FA steps
        page.wait_for_selector.assert_any_call('a[aria-label="Select Google Authenticator"]', timeout=2000)
        authenticator_link.click.assert_called_once()
        
        page.get_by_label.assert_any_call("Enter code")
        code_field.click.assert_called_once()
        code_field.fill.assert_called_once()  # Don't verify exact code as it's time-based
        
        page.get_by_role.assert_any_call("button", name="Verify")
        verify_button.click.assert_called()  # Called multiple times in the flow
        
        # Verify network idle waits
        assert page.wait_for_load_state.call_count >= 3  # Multiple network idle waits in the flow

    @pytest.mark.asyncio
    async def test_search_patient(self, initialized_session, test_patient):
        """Test patient search."""
        session, page = await initialized_session
        
        # Set up page elements
        surname_field = self.get_mock_element(click=None, fill=None)
        firstname_field = self.get_mock_element(click=None, fill=None)
        dob_field = self.get_mock_element(fill=None)
        search_button = self.get_mock_element(click=None)
        
        # Mock placeholder selectors
        page.get_by_placeholder = MagicMock(side_effect=lambda text: {
            "Surname": surname_field,
            "First Name": firstname_field,
            "Date of Birth": dob_field
        }.get(text, Mock()))
        
        # Mock role selectors
        page.get_by_role = MagicMock(side_effect=lambda role, **kwargs: {
            ("button", "Search"): search_button
        }.get((role, kwargs.get('name')), Mock()))
        
        # Perform search
        await session.search_patient()
        
        # Verify patient details entry
        page.get_by_placeholder.assert_any_call("Surname")
        surname_field.click.assert_called_once()
        surname_field.fill.assert_called_with(test_patient["family_name"])
        
        page.get_by_placeholder.assert_any_call("First Name")
        firstname_field.click.assert_called_once()
        firstname_field.fill.assert_called_with(test_patient["given_name"])
        
        # Verify DOB entry
        page.get_by_placeholder.assert_any_call("Date of Birth")
        converted_dob = convert_date_format(test_patient["dob"], "%d%m%Y", "%Y-%m-%d")
        dob_field.fill.assert_called_with(converted_dob)
        
        # Verify search button click
        page.get_by_role.assert_called_with("button", name="Search")
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
        assert provider_session.provider_group == "Pathology"
        assert provider_session.credentials_key == "MaterPath"
