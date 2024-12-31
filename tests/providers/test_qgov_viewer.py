import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from providers.qgov_viewer import QGovViewerSession
from utils import convert_date_format, convert_gender
from tests.playwright_test import PlaywrightTestCase

class TestQGovViewer(PlaywrightTestCase):
    """Test cases for QGov Viewer provider."""

    @pytest.fixture
    def provider_session(self, mock_page, mock_browser, test_credentials, test_patient):
        """Create a QGov Viewer session for testing."""
        from models import PatientDetails, SharedState, Credentials
        
        # Create proper objects from test data
        credentials = Credentials(
            user_name=test_credentials["QGov"]["user_name"],
            user_password=test_credentials["QGov"]["user_password"]
        )
        patient = PatientDetails(
            family_name=test_patient["family_name"],
            given_name=test_patient["given_name"],
            dob=test_patient["dob"],
            medicare_number=test_patient["medicare_number"],
            sex=test_patient["sex"]
        )
        shared_state = SharedState()
        shared_state.page = mock_page
        shared_state.browser = mock_browser
        
        session = QGovViewerSession(credentials, patient, shared_state)
        return session

    @pytest.mark.asyncio
    async def test_login(self, initialized_session, test_credentials):
        """Test login flow."""
        session, page = await initialized_session
        
        # Set up page elements
        login_link = self.get_mock_element(click=None)
        email_field = self.get_mock_element(fill=None)
        password_field = self.get_mock_element(fill=None)
        login_button = self.get_mock_element(click=None)
        
        # Mock wait_for_selector
        page.wait_for_selector = AsyncMock(return_value=MagicMock())
        
        # Mock role selectors
        page.get_by_role = MagicMock(side_effect=lambda role, **kwargs: {
            ("link", "Log in"): login_link,
            ("button", "Log in"): login_button
        }.get((role, kwargs.get('name')), Mock()))
        
        # Mock placeholder and label selectors
        page.get_by_placeholder = MagicMock(side_effect=lambda text: {
            "Your email address": email_field
        }.get(text, Mock()))
        
        page.get_by_label = MagicMock(side_effect=lambda label: {
            "Password": password_field
        }.get(label, Mock()))
        
        # Perform login
        await session.login()
        
        # Verify wait for login link
        page.wait_for_selector.assert_any_call('a:text("Log in")', state='visible')
        
        # Verify login link click
        page.get_by_role.assert_any_call("link", name="Log in")
        login_link.click.assert_called_once()
        
        # Verify wait for email field
        page.wait_for_selector.assert_any_call('input[placeholder="Your email address"]', state='visible')
        
        # Verify email entry
        page.get_by_placeholder.assert_called_with("Your email address")
        email_field.fill.assert_called_with(test_credentials["QGov"]["user_name"])
        
        # Verify wait for password field
        page.wait_for_selector.assert_any_call('input[type="password"]', state='visible')
        
        # Verify password entry
        page.get_by_label.assert_called_with("Password")
        password_field.fill.assert_called_with(test_credentials["QGov"]["user_password"])
        
        # Verify login button click
        page.get_by_role.assert_any_call("button", name="Log in")
        login_button.click.assert_called_once()
        
        # Verify wait for navigation
        page.wait_for_load_state.assert_called_with("domcontentloaded")

    @pytest.mark.asyncio
    async def test_search_patient(self, initialized_session, test_patient):
        """Test patient search with popup handling."""
        session, page = await initialized_session
        
        # Set up page elements
        medicare_field = self.get_mock_element(fill=None)
        gender_select = self.get_mock_element(select_option=None)
        dob_field = self.get_mock_element(fill=None, press=None)
        surname_field = self.get_mock_element(fill=None)
        search_button = self.get_mock_element(click=None)
        viewer_link = self.get_mock_element(click=None)
        
        # Mock locator for Medicare field
        page.locator = MagicMock(side_effect=lambda selector: {
            "#MedicareNumber": medicare_field
        }.get(selector, Mock()))
        
        # Mock wait_for_selector
        page.wait_for_selector = AsyncMock(return_value=MagicMock())
        
        # Mock label and placeholder selectors
        page.get_by_label = MagicMock(side_effect=lambda label: {
            "Sex": gender_select,
            "Patient Surname": surname_field
        }.get(label, Mock()))
        
        page.get_by_placeholder = MagicMock(side_effect=lambda text: {
            "DD/MM/YYYY": dob_field
        }.get(text, Mock()))
        
        # Mock role selectors
        page.get_by_role = MagicMock(side_effect=lambda role, **kwargs: {
            ("button", "Search"): search_button,
            ("link", "The Viewer"): viewer_link
        }.get((role, kwargs.get('name')), Mock()))
        
        # Mock popup event handler
        page.on = Mock()
        
        # Perform search
        await session.search_patient()
        
        # Verify Medicare field
        page.wait_for_selector.assert_any_call('#MedicareNumber', state='visible')
        page.locator.assert_called_with("#MedicareNumber")
        medicare_field.fill.assert_called_with(test_patient["medicare_number"])
        
        # Verify gender selection
        page.get_by_label.assert_any_call("Sex")
        gender_select.select_option.assert_called_with(convert_gender(test_patient["sex"], "M1F2I3"))
        
        # Verify DOB entry
        page.get_by_placeholder.assert_called_with("DD/MM/YYYY")
        converted_dob = convert_date_format(test_patient["dob"], "%d%m%Y", "%d/%m/%Y")
        dob_field.fill.assert_called_with(converted_dob)
        dob_field.press.assert_called_with("Tab")
        
        # Verify surname entry
        page.get_by_label.assert_any_call("Patient Surname")
        surname_field.fill.assert_called_with(test_patient["family_name"])
        
        # Verify search button click
        page.get_by_role.assert_any_call("button", name="Search")
        search_button.click.assert_called_once()
        
        # Verify popup handling setup - just check event name, not exact handler
        page.on.assert_called_once()
        assert page.on.call_args[0][0] == "popup"  # First arg should be event name
        
        # Verify viewer link click with timeout
        page.get_by_role.assert_any_call("link", name="The Viewer")
        viewer_link.click.assert_called_with(timeout=30000)

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
        assert provider_session.required_fields == ['family_name', 'dob', 'medicare_number', 'sex']
        assert provider_session.provider_group == "General"
        assert provider_session.credentials_key == "QGov"

    @pytest.mark.asyncio
    async def test_initialize_urls(self, initialized_session):
        """Test that initialization uses correct URLs."""
        session, page = await initialized_session
        
        # Verify both URLs were loaded in order
        assert page.goto.call_count == 2
        page.goto.assert_any_call("https://hpp.health.qld.gov.au/my.policy")
        page.goto.assert_any_call("https://hpp.health.qld.gov.au/")
