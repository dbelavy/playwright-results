from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from providers.mater_legacy import MaterLegacySession
from tests.playwright_test import PlaywrightTestCase
from utils import convert_date_format


class TestMaterLegacy(PlaywrightTestCase):
    """Test cases for Mater Legacy provider."""

    @pytest.fixture
    def provider_session(self, mock_page, mock_browser, test_credentials, test_patient):
        """Create a Mater Legacy session for testing."""
        from models import Credentials, PatientDetails, SharedState

        # Create proper objects from test data
        credentials = Credentials(
            user_name=test_credentials["MaterLegacy"]["user_name"],
            user_password=test_credentials["MaterLegacy"]["user_password"],
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

        session = MaterLegacySession(credentials, patient, shared_state)
        return session

    @pytest.mark.asyncio
    async def test_login(self, initialized_session, test_credentials):
        """Test login flow."""
        session, page = await initialized_session

        # Set up page elements
        username_field = self.get_mock_element(click=None, fill=None)
        password_field = self.get_mock_element(click=None, fill=None)
        login_button = self.get_mock_element(click=None)

        # Mock locator calls
        page.locator = MagicMock(
            side_effect=lambda selector: {
                'input[name="salamiloginlogin"]': username_field,
                'input[name="salamiloginpassword"]': password_field,
            }.get(selector, Mock())
        )

        # Mock role selectors
        page.get_by_role = MagicMock(
            side_effect=lambda role, **kwargs: {("button", "Login"): login_button}.get(
                (role, kwargs.get("name")), Mock()
            )
        )

        # Perform login
        await session.login()

        # Verify login steps
        page.locator.assert_any_call('input[name="salamiloginlogin"]')
        username_field.click.assert_called_once()
        username_field.fill.assert_called_with(
            test_credentials["MaterLegacy"]["user_name"]
        )

        page.locator.assert_any_call('input[name="salamiloginpassword"]')
        password_field.click.assert_called_once()
        password_field.fill.assert_called_with(
            test_credentials["MaterLegacy"]["user_password"]
        )

        page.get_by_role.assert_called_with("button", name="Login")
        login_button.click.assert_called_once()

        # Verify wait for load
        page.wait_for_load_state.assert_called_with("networkidle")

    @pytest.mark.asyncio
    async def test_search_patient(self, initialized_session, test_patient):
        """Test patient search."""
        session, page = await initialized_session

        # Set up page elements
        welcome_link = self.get_mock_element(click=None)
        surname_field = self.get_mock_element(click=None, fill=None)
        firstname_field = self.get_mock_element(click=None, fill=None)
        dob_field = self.get_mock_element(click=None, fill=None)
        search_button = self.get_mock_element(click=None)

        # Mock welcome cell and link
        welcome_cell = MagicMock()
        welcome_cell.get_by_role = MagicMock(
            return_value=MagicMock(nth=lambda n: welcome_link)
        )

        # Mock locator calls
        page.locator = MagicMock(
            side_effect=lambda selector: {
                'input[name="surname"]': surname_field,
                'input[name="firstname"]': firstname_field,
                'input[name="dob"]': dob_field,
            }.get(selector, Mock())
        )

        # Mock role selectors
        page.get_by_role = MagicMock(
            side_effect=lambda role, **kwargs: {
                ("cell", "Welcome to the Mater"): welcome_cell,
                ("button", "Search"): search_button,
            }.get((role, kwargs.get("name")), Mock())
        )

        # Perform search
        await session.search_patient()

        # Verify welcome link click
        page.get_by_role.assert_any_call("cell", name="Welcome to the Mater")
        welcome_cell.get_by_role.assert_called_with("link")
        welcome_link.click.assert_called_once()

        # Verify patient details entry
        page.locator.assert_any_call('input[name="surname"]')
        surname_field.click.assert_called_once()
        surname_field.fill.assert_called_with(test_patient["family_name"])

        page.locator.assert_any_call('input[name="firstname"]')
        firstname_field.click.assert_called_once()
        firstname_field.fill.assert_called_with(test_patient["given_name"])

        # Verify DOB entry
        page.locator.assert_any_call('input[name="dob"]')
        dob_field.click.assert_called_once()
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
        assert provider_session.credentials_key == "MaterLegacy"
