from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from providers.snp import SNPSession
from tests.playwright_test import PlaywrightTestCase
from utils import convert_date_format


class TestSNP(PlaywrightTestCase):
    """Test cases for SNP provider."""

    @pytest.fixture
    def provider_session(self, mock_page, mock_browser, test_credentials, test_patient):
        """Create an SNP session for testing."""
        from models import Credentials, PatientDetails, SharedState

        # Create proper objects from test data
        credentials = Credentials(
            user_name=test_credentials["Sonic"]["user_name"],
            user_password=test_credentials["Sonic"]["user_password"],
        )
        patient = PatientDetails(
            family_name=test_patient["family_name"],
            given_name=test_patient["given_name"],
            dob=test_patient["dob"],
            medicare_number=test_patient.get("medicare_number"),
            sex=test_patient.get("sex"),
        )
        shared_state = SharedState()
        shared_state.page = mock_page
        shared_state.browser = mock_browser

        session = SNPSession(credentials, patient, shared_state)
        return session

    @pytest.mark.asyncio
    async def test_login(self, initialized_session, test_credentials):
        """Test login flow including business selection."""
        session, page = await initialized_session

        # Set up page elements
        username_field = self.get_mock_element(click=None, fill=None)
        password_field = self.get_mock_element(click=None, fill=None)
        business_select = self.get_mock_element(select_option=None)
        login_button = self.get_mock_element(click=None)

        # Mock locator calls
        page.locator = MagicMock(
            side_effect=lambda selector: {
                "#username": username_field,
                "#password": password_field,
                "#selected-business": business_select,
            }.get(selector, Mock())
        )

        # Mock get_by_role for login button
        page.get_by_role = MagicMock(
            side_effect=lambda role, **kwargs: {("button", "Login"): login_button}.get(
                (role, kwargs.get("name")), Mock()
            )
        )

        # Perform login
        await session.login()

        # Verify login steps
        page.locator.assert_any_call("#username")
        username_field.fill.assert_called_with(test_credentials["Sonic"]["user_name"])

        page.locator.assert_any_call("#selected-business")
        business_select.select_option.assert_called_with("SNP")

        page.locator.assert_any_call("#password")
        password_field.fill.assert_called_with(
            test_credentials["Sonic"]["user_password"]
        )

        page.get_by_role.assert_called_with("button", name="Login")
        login_button.click.assert_called_once()

        # Verify waited for network idle
        page.wait_for_load_state.assert_called_with("networkidle")

    @pytest.mark.asyncio
    async def test_search_patient(self, initialized_session, test_patient):
        """Test patient search with required fields."""
        session, page = await initialized_session

        # Set up page elements
        search_link = self.get_mock_element(click=None)
        family_name_field = self.get_mock_element(click=None, fill=None, press=None)
        given_name_field = self.get_mock_element(fill=None, press=None)
        sex_field = self.get_mock_element(press=None)
        dob_field = self.get_mock_element(fill=None)
        search_button = self.get_mock_element(click=None)

        # Mock locator calls
        page.locator = MagicMock(
            side_effect=lambda selector: {
                "#familyName": family_name_field,
                "#givenName": given_name_field,
            }.get(selector, Mock())
        )

        # Mock get_by_role and other selectors
        page.get_by_role = MagicMock(
            side_effect=lambda role, **kwargs: {
                ("link", "Search"): search_link,
                ("button", "Search"): search_button,
            }.get((role, kwargs.get("name")), Mock())
        )

        page.get_by_label = MagicMock(
            side_effect=lambda label: {"Sex": sex_field}.get(label, Mock())
        )

        page.get_by_placeholder = MagicMock(
            side_effect=lambda text: {"DD/MM/YYYY": dob_field}.get(text, Mock())
        )

        # Perform search
        await session.search_patient()

        # Verify navigation to search page
        page.get_by_role.assert_any_call("link", name="Search", exact=True)
        search_link.click.assert_called_once()

        # Verify patient search steps
        page.locator.assert_any_call("#familyName")
        family_name_field.fill.assert_called_with(test_patient["family_name"])
        family_name_field.press.assert_called_with("Tab")

        page.locator.assert_any_call("#givenName")
        given_name_field.fill.assert_called_with(test_patient["given_name"])
        given_name_field.press.assert_called_with("Tab")

        # Verify sex field tab
        page.get_by_label.assert_called_with("Sex")
        sex_field.press.assert_called_with("Tab")

        # Verify DOB conversion and fill
        page.get_by_placeholder.assert_called_with("DD/MM/YYYY")
        converted_dob = convert_date_format(test_patient["dob"], "%d%m%Y", "%d/%m/%Y")
        dob_field.fill.assert_called_with(converted_dob)

        # Verify search button click
        page.get_by_role.assert_any_call("button", name="Search")
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
        assert provider_session.required_fields == ["family_name", "given_name", "dob"]
        assert provider_session.provider_group == "Pathology"
        assert provider_session.credentials_key == "Sonic"
