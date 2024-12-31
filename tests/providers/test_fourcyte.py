import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from providers.fourcyte import FourCyteSession
from utils import convert_date_format, generate_2fa_code
from tests.playwright_test import PlaywrightTestCase

class TestFourCyte(PlaywrightTestCase):
    """Test cases for 4Cyte provider."""

    @pytest.fixture
    def provider_session(self, mock_page, mock_browser, test_credentials, test_patient):
        """Create a 4Cyte session for testing."""
        from models import PatientDetails, SharedState, Credentials
        
        # Create proper objects from test data
        credentials = Credentials(
            user_name=test_credentials["4cyte"]["user_name"],
            user_password=test_credentials["4cyte"]["user_password"],
            totp_secret=test_credentials["4cyte"]["totp_secret"]
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
        
        session = FourCyteSession(credentials, patient, shared_state)
        return session

    @pytest.mark.asyncio
    async def test_login(self, initialized_session, test_credentials):
        """Test login flow including 2FA and popup handling."""
        session, page = await initialized_session
        
        # Set up main page elements
        portal_link = self.get_mock_element(click=None)
        access_button = self.get_mock_element(click=None)
        
        # Set up popup page elements
        username_field = self.get_mock_element(click=None, fill=None)
        password_field = self.get_mock_element(click=None, fill=None)
        login_button = self.get_mock_element(click=None)
        code_field = self.get_mock_element(click=None, fill=None)
        submit_button = self.get_mock_element(click=None)
        patients_button = self.get_mock_element(click=None)
        break_glass_link = self.get_mock_element(click=None)
        accept_button = self.get_mock_element(click=None)
        
        # Mock popup window
        popup_page = MagicMock()
        popup_page.get_by_placeholder = MagicMock(side_effect=lambda text: {
            "Username": username_field,
            "Password": password_field,
            "-digit code": code_field
        }.get(text, Mock()))
        
        popup_page.get_by_role = MagicMock(side_effect=lambda role, **kwargs: {
            ("button", "Log in"): login_button,
            ("button", "Submit"): submit_button,
            ("button", "Patients"): patients_button,
            ("button", "Accept"): accept_button,
            ("link", " Break Glass"): break_glass_link
        }.get((role, kwargs.get('name')), Mock()))
        
        # Create an async context manager for expect_popup
        class AsyncContextManagerMock:
            async def __aenter__(self):
                info_mock = MagicMock()
                # Make value property return an async function
                async def value_func():
                    return popup_page
                # Use property to match Playwright's API
                type(info_mock).value = property(lambda self: value_func())
                return info_mock
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
                
        # Mock popup creation
        page.expect_popup = Mock(return_value=AsyncContextManagerMock())
        
        # Mock main page elements
        page.get_by_role = MagicMock(side_effect=lambda role, **kwargs: {
            ("link", "Web Results Portal"): portal_link
        }.get((role, kwargs.get('name')), Mock()))
        
        page.get_by_label = MagicMock(side_effect=lambda label: {
            "Access results portal": access_button
        }.get(label, Mock()))
        
        # Perform login
        await session.login()
        
        # Verify main page steps
        page.get_by_role.assert_any_call("link", name="Web Results Portal")
        portal_link.click.assert_called_once()
        
        page.get_by_label.assert_called_with("Access results portal")
        access_button.click.assert_called_once()
        
        # Verify popup login steps
        popup_page.get_by_placeholder.assert_any_call("Username")
        username_field.fill.assert_called_with(test_credentials["4cyte"]["user_name"])
        
        popup_page.get_by_placeholder.assert_any_call("Password")
        password_field.fill.assert_called_with(test_credentials["4cyte"]["user_password"])
        
        popup_page.get_by_role.assert_any_call("button", name="Log in")
        login_button.click.assert_called_once()
        
        # Verify 2FA steps
        popup_page.get_by_placeholder.assert_any_call("-digit code")
        code_field.fill.assert_called_once()  # Don't verify exact code as it's time-based
        
        popup_page.get_by_role.assert_any_call("button", name="Submit")
        submit_button.click.assert_called_once()
        
        # Verify navigation and break glass steps
        popup_page.get_by_role.assert_any_call("button", name="Patients")
        patients_button.click.assert_called_once()
        
        popup_page.get_by_role.assert_any_call("link", name=" Break Glass")
        break_glass_link.click.assert_called_once()
        
        popup_page.get_by_role.assert_any_call("button", name="Accept")
        accept_button.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_patient(self, initialized_session, test_patient):
        """Test patient search with combined name field."""
        session, page = await initialized_session
        
        # Set up page elements
        name_field = self.get_mock_element(fill=None)
        dob_field = self.get_mock_element(click=None, fill=None)
        search_button = self.get_mock_element(click=None)
        
        # Mock popup page elements since search happens in popup
        page.get_by_placeholder = MagicMock(side_effect=lambda text: {
            "Surname [space] First name": name_field,
            "Birth Date (Required)": dob_field
        }.get(text, Mock()))
        
        page.get_by_role = MagicMock(side_effect=lambda role, **kwargs: {
            ("button", "Search"): search_button
        }.get((role, kwargs.get('name')), Mock()))
        
        # Perform search
        await session.search_patient()
        
        # Verify patient search steps
        page.get_by_placeholder.assert_any_call("Surname [space] First name")
        name_field.fill.assert_called_with(
            f'{test_patient["family_name"]} {test_patient["given_name"]}'
        )
        
        page.get_by_placeholder.assert_any_call("Birth Date (Required)")
        dob_field.click.assert_called_once()
        
        converted_dob = convert_date_format(test_patient["dob"], "%d%m%Y", "%d/%m/%Y")
        dob_field.fill.assert_called_with(converted_dob)
        
        page.get_by_role.assert_called_with("button", name="Search")
        search_button.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_uninitialized_error(self, provider_session):
        """Test error handling for uninitialized session."""
        provider_session.page = None
        provider_session.active_page = None
        
        with pytest.raises(RuntimeError, match="Session not initialized"):
            await provider_session.login()
            
        with pytest.raises(RuntimeError, match="Session not initialized"):
            await provider_session.search_patient()

    @pytest.mark.asyncio
    async def test_required_fields(self, provider_session):
        """Test that required fields are correctly defined."""
        assert provider_session.required_fields == ['family_name', 'given_name', 'dob']
        assert provider_session.provider_group == "Pathology"
        assert provider_session.credentials_key == "4cyte"
