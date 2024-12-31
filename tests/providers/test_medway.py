import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from providers.medway import MedwaySession
from utils import convert_date_format
from tests.playwright_test import PlaywrightTestCase

class TestMedway(PlaywrightTestCase):
    """Test cases for Medway provider."""

    @pytest.fixture
    def provider_session(self, mock_page, mock_browser, test_credentials, test_patient):
        """Create a Medway session for testing."""
        from models import PatientDetails, SharedState, Credentials
        
        # Create proper objects from test data
        credentials = Credentials(
            user_name=test_credentials["Medway"]["user_name"],
            user_password=test_credentials["Medway"]["user_password"]
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
        
        session = MedwaySession(credentials, patient, shared_state)
        return session

    @pytest.mark.asyncio
    async def test_login(self, initialized_session, test_credentials):
        """Test login flow using get_by_label selectors."""
        session, page = await initialized_session
        
        # Set up page elements
        username_element = self.get_mock_element(click=None, fill=None)
        password_element = self.get_mock_element(click=None, fill=None)
        login_button = self.get_mock_element(click=None)
        
        self.setup_page_elements(
            page,
            label_elements={
                "Username": username_element,
                "Password": password_element
            },
            role_elements={
                ("button", "Log in"): login_button
            }
        )
        
        # Perform login
        await session.login()
        
        # Verify login steps
        page.get_by_label.assert_any_call("Username")
        username_element.fill.assert_called_with(test_credentials["Medway"]["user_name"])
        
        page.get_by_label.assert_any_call("Password")
        password_element.fill.assert_called_with(test_credentials["Medway"]["user_password"])
        
        page.get_by_role.assert_called_with("button", name="Log in")
        login_button.click.assert_called_once()
        
        # Verify waited for network idle
        page.wait_for_load_state.assert_called_with("networkidle")

    @pytest.mark.asyncio
    async def test_search_patient(self, initialized_session, test_patient):
        """Test patient search with required fields."""
        session, page = await initialized_session
        
        # Set up page elements
        surname_element = self.get_mock_element(click=None, fill=None, press=None)
        given_name_element = self.get_mock_element(click=None, fill=None, press=None)
        dob_element = self.get_mock_element(fill=None)
        search_button = self.get_mock_element(click=None)
        
        self.setup_page_elements(
            page,
            label_elements={
                "Patient surname": surname_element,
                "Patient given name(s)": given_name_element
            },
            role_elements={
                ("textbox", "Date of birth"): dob_element,
                ("button", "Search"): search_button
            }
        )
        
        # Perform search
        await session.search_patient()
        
        # Verify patient search steps
        page.get_by_label.assert_any_call("Patient surname")
        surname_element.fill.assert_called_with(test_patient["family_name"])
        surname_element.press.assert_called_with("Tab")
        
        page.get_by_label.assert_any_call("Patient given name(s)")
        given_name_element.fill.assert_called_with(test_patient["given_name"])
        given_name_element.press.assert_called_with("Tab")
        
        # Verify DOB conversion and fill
        page.get_by_role.assert_any_call("textbox", name="Date of birth")
        converted_dob = convert_date_format(test_patient["dob"], "%d%m%Y", "%Y-%m-%d")
        dob_element.fill.assert_called_with(converted_dob)
        
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
        assert provider_session.credentials_key == "Medway"
