from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from providers.i_med import IMedSession
from tests.playwright_test import PlaywrightTestCase
from utils import convert_date_format


class TestIMed(PlaywrightTestCase):
    """Test cases for IMed provider."""

    @pytest.fixture
    def provider_session(self, mock_page, mock_browser, test_credentials, test_patient):
        """Create an IMed session for testing."""
        from models import Credentials, PatientDetails, SharedState

        # Create proper objects from test data
        credentials = Credentials(
            user_name=test_credentials["IMed"]["user_name"],
            user_password=test_credentials["IMed"]["user_password"],
            postcode=test_credentials["IMed"]["postcode"],
            suburb=test_credentials["IMed"]["suburb"],
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

        session = IMedSession(credentials, patient, shared_state)
        return session

    @pytest.mark.asyncio
    async def test_login(self, initialized_session, test_credentials):
        """Test login flow including location selection and popup."""
        session, page = await initialized_session

        # Set up main page elements
        postcode_input = self.get_mock_element(click=None, fill=None, press=None)
        suburb_button = self.get_mock_element(click=None)
        access_button = self.get_mock_element(click=None)

        # Set up popup page elements
        username_field = self.get_mock_element(fill=None)
        password_field = self.get_mock_element(fill=None)
        login_button = self.get_mock_element(click=None)

        # Mock popup window
        popup_page = MagicMock()
        popup_page.locator = MagicMock(
            side_effect=lambda selector: {
                '[data-testid="SingleLineTextInputField-FormControl"][name="uid"]': username_field,
                '[data-testid="SingleLineTextInputField-FormControl"][name="password"]': password_field,
            }.get(selector, Mock())
        )

        popup_page.get_by_test_id = MagicMock(
            side_effect=lambda test_id: {"login-button": login_button}.get(
                test_id, Mock()
            )
        )

        popup_page.wait_for_load_state = AsyncMock()
        popup_page.evaluate = AsyncMock()  # For the element check after login

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
        page.get_by_test_id = MagicMock(
            side_effect=lambda test_id: {"dropdownInput": postcode_input}.get(
                test_id, Mock()
            )
        )

        page.get_by_role = MagicMock(
            side_effect=lambda role, **kwargs: {
                ("button", test_credentials["IMed"]["suburb"]): suburb_button,
                ("button", "ACCESS I-MED ONLINE"): access_button,
            }.get((role, kwargs.get("name")), Mock())
        )

        # Perform login
        await session.login()

        # Verify location selection steps
        page.get_by_test_id.assert_any_call("dropdownInput")
        postcode_input.fill.assert_called_with(test_credentials["IMed"]["postcode"])
        postcode_input.press.assert_called_with("Enter")

        page.get_by_role.assert_any_call(
            "button", name=test_credentials["IMed"]["suburb"]
        )
        suburb_button.click.assert_called_once()

        # Verify popup trigger
        page.get_by_role.assert_any_call("button", name="ACCESS I-MED ONLINE")
        access_button.click.assert_called_once()

        # Verify popup login steps
        popup_page.locator.assert_any_call(
            '[data-testid="SingleLineTextInputField-FormControl"][name="uid"]'
        )
        username_field.fill.assert_called_with(test_credentials["IMed"]["user_name"])

        popup_page.locator.assert_any_call(
            '[data-testid="SingleLineTextInputField-FormControl"][name="password"]'
        )
        password_field.fill.assert_called_with(
            test_credentials["IMed"]["user_password"]
        )

        popup_page.get_by_test_id.assert_called_with("login-button")
        login_button.click.assert_called_once()

        # Verify wait for load and element check
        popup_page.wait_for_load_state.assert_called_with("networkidle")
        popup_page.evaluate.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_patient(self, initialized_session, test_patient):
        """Test patient search with all options."""
        session, page = await initialized_session

        # Set up page elements
        name_field = self.get_mock_element(fill=None)
        dob_field = self.get_mock_element(click=None, type=None)
        search_button = self.get_mock_element(click=None)

        # Set up filter buttons
        referred_by_me = self.get_mock_element(click=None)
        referred_by_anyone = self.get_mock_element(click=None)
        all_practices = self.get_mock_element(click=None)
        past_week = self.get_mock_element(click=None)
        all_time = self.get_mock_element(click=None)

        # Mock locator for name field
        page.locator = MagicMock(
            side_effect=lambda selector: {
                '[data-testid="SingleLineTextInputField-FormControl"][name="nameOrPatientId"]': name_field
            }.get(selector, Mock())
        )

        # Mock test ID selectors
        page.get_by_test_id = MagicMock(
            side_effect=lambda test_id: {
                "DOB-input-field-form-control": dob_field,
                "mobile-search": search_button,
            }.get(test_id, Mock())
        )

        # Mock role selectors for filter buttons
        page.get_by_role = MagicMock(
            side_effect=lambda role, **kwargs: {
                ("button", "Referred by me"): referred_by_me,
                ("button", "Referred by anyone"): referred_by_anyone,
                ("button", "All listed practices"): all_practices,
                ("button", "Past week"): past_week,
                ("button", "All time"): all_time,
            }.get((role, kwargs.get("name")), Mock())
        )

        # Perform search
        await session.search_patient()

        # Verify patient details entry
        page.locator.assert_called_with(
            '[data-testid="SingleLineTextInputField-FormControl"][name="nameOrPatientId"]'
        )
        name_field.fill.assert_called_with(
            f'{test_patient["given_name"]} {test_patient["family_name"]}'
        )

        # Verify DOB entry
        page.get_by_test_id.assert_any_call("DOB-input-field-form-control")
        dob_field.click.assert_called_once()
        dob_field.type.assert_called_with(
            convert_date_format(test_patient["dob"], "%d%m%Y", "%d/%m/%Y")
        )

        # Verify filter button clicks
        page.get_by_role.assert_any_call("button", name="Referred by me")
        referred_by_me.click.assert_called_once()

        page.get_by_role.assert_any_call("button", name="Referred by anyone")
        referred_by_anyone.click.assert_called_once()

        page.get_by_role.assert_any_call("button", name="All listed practices")
        assert all_practices.click.call_count == 2  # Called twice in implementation

        page.get_by_role.assert_any_call("button", name="Past week")
        past_week.click.assert_called_once()

        page.get_by_role.assert_any_call("button", name="All time")
        all_time.click.assert_called_once()

        # Verify search button click
        page.get_by_test_id.assert_any_call("mobile-search")
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
        assert provider_session.required_fields == ["family_name", "given_name", "dob"]
        assert provider_session.provider_group == "Radiology"
        assert provider_session.credentials_key == "IMed"
