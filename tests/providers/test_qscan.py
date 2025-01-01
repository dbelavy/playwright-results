from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock

import pytest

from providers.qscan import QScanSession
from tests.playwright_test import PlaywrightTestCase
from utils import convert_date_format


class TestQScan(PlaywrightTestCase):
    """Test cases for QScan provider."""

    @pytest.fixture
    def provider_session(self, mock_page, mock_browser, test_credentials, test_patient):
        """Create a QScan session for testing."""
        from models import Credentials, PatientDetails, SharedState

        # Create proper objects from test data
        credentials = Credentials(
            user_name=test_credentials["QScan"]["user_name"],
            user_password=test_credentials["QScan"]["user_password"],
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

        session = QScanSession(credentials, patient, shared_state)
        return session

    @pytest.mark.asyncio
    async def test_login(self, initialized_session, test_credentials):
        """Test login flow including password change handling."""
        session, page = await initialized_session

        # Set up page elements
        username_field = self.get_mock_element(click=None, fill=None)
        password_field = self.get_mock_element(click=None, fill=None)
        login_button = self.get_mock_element(click=None)

        # Mock placeholder selectors
        page.get_by_placeholder = MagicMock(
            side_effect=lambda text: {
                "Username": username_field,
                "Password": password_field,
            }.get(text, Mock())
        )

        # Mock role selectors
        page.get_by_role = MagicMock(
            side_effect=lambda role, **kwargs: {("button",): login_button}.get(
                (role,), Mock()
            )
        )

        # Mock URL property for password change check
        url_mock = PropertyMock(side_effect=["changePassword", "main"])
        type(page).url = url_mock

        # Mock goto for password change redirect
        page.goto = AsyncMock()

        # Perform login
        await session.login()

        # Verify username entry
        page.get_by_placeholder.assert_any_call("Username")
        username_field.click.assert_called_once()
        username_field.fill.assert_called_with(test_credentials["QScan"]["user_name"])

        # Verify password entry
        page.get_by_placeholder.assert_any_call("Password")
        password_field.click.assert_called_once()
        password_field.fill.assert_called_with(
            test_credentials["QScan"]["user_password"]
        )

        # Verify login button click
        page.get_by_role.assert_called_with("button")
        login_button.click.assert_called_once()

        # Verify password change handling
        page.goto.assert_called_with("https://www.qscaniq.com.au/Portal/app#/")

        # Verify network idle waits
        assert page.wait_for_load_state.call_count >= 2  # Multiple network idle waits

    @pytest.mark.asyncio
    async def test_search_patient(self, initialized_session, test_patient):
        """Test patient search with Break Glass workflow."""
        session, page = await initialized_session

        # Set up page elements
        break_glass_button = self.get_mock_element(click=None)
        checkbox = self.get_mock_element(click=None)
        check_patient_button = self.get_mock_element(click=None)
        access_button = self.get_mock_element(click=None)

        # Mock locator calls
        page.locator = MagicMock(
            side_effect=lambda selector: {
                "a.btn.portalButton.selfServeButton[title='Access restricted studies']": break_glass_button,
                "input#gwt-uid-1[type='checkbox']": checkbox,
                "button.gwt-Button.checkPatientButton": check_patient_button,
                "button.gwt-Button.accessButton": access_button,
                "div.gwt-HTML:text('A patient that matches your search criteria was found:')": MagicMock(
                    wait_for=AsyncMock(return_value=True)
                ),
            }.get(selector, Mock())
        )

        # Mock keyboard
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()
        page.keyboard.type = AsyncMock()

        # Mock timeout
        page.wait_for_timeout = AsyncMock()

        # Perform search
        await session.search_patient()

        # Verify Break Glass click
        page.locator.assert_any_call(
            "a.btn.portalButton.selfServeButton[title='Access restricted studies']"
        )
        break_glass_button.click.assert_called_once()

        # Verify timeout after Break Glass
        page.wait_for_timeout.assert_any_call(1000)

        # Verify checkbox click
        page.locator.assert_any_call("input#gwt-uid-1[type='checkbox']")
        checkbox.click.assert_called_once()

        # Verify keyboard navigation and input
        page.keyboard.press.assert_any_call("Tab")  # Skip patient ID
        page.keyboard.type.assert_any_call(
            f"{test_patient['family_name']},{test_patient['given_name']}"
        )
        page.keyboard.press.assert_any_call("Tab")  # To DOB field

        # Verify DOB entry
        dob = convert_date_format(test_patient["dob"], "%d%m%Y", "%Y%m%d")
        page.keyboard.type.assert_any_call(dob)

        # Verify Check Patient button click
        page.locator.assert_any_call("button.gwt-Button.checkPatientButton")
        check_patient_button.click.assert_called_once()

        # Verify patient found handling
        page.locator.assert_any_call(
            "div.gwt-HTML:text('A patient that matches your search criteria was found:')"
        )
        page.locator.assert_any_call("button.gwt-Button.accessButton")
        access_button.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_patient_not_found(self, initialized_session, test_patient):
        """Test patient search when no match is found."""
        session, page = await initialized_session

        # Set up page elements similar to test_search_patient
        break_glass_button = self.get_mock_element(click=None)
        checkbox = self.get_mock_element(click=None)
        check_patient_button = self.get_mock_element(click=None)

        # Mock locator calls but with "not found" message
        page.locator = MagicMock(
            side_effect=lambda selector: {
                "a.btn.portalButton.selfServeButton[title='Access restricted studies']": break_glass_button,
                "input#gwt-uid-1[type='checkbox']": checkbox,
                "button.gwt-Button.checkPatientButton": check_patient_button,
                "div.gwt-HTML:text('A patient that matches your search criteria was found:')": MagicMock(
                    wait_for=AsyncMock(side_effect=Exception("Not found"))
                ),
                "div.gwt-HTML:text('No patient that matches your search criteria was found.')": MagicMock(
                    wait_for=AsyncMock(return_value=True)
                ),
            }.get(selector, Mock())
        )

        # Mock keyboard and timeout
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()
        page.keyboard.type = AsyncMock()
        page.wait_for_timeout = AsyncMock()

        # Perform search
        await session.search_patient()

        # Verify search steps up to result check
        page.locator.assert_any_call(
            "div.gwt-HTML:text('No patient that matches your search criteria was found.')"
        )

        # Verify no access button click
        assert not any(
            call[0][0] == "button.gwt-Button.accessButton"
            for call in page.locator.call_args_list
        )

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
        assert provider_session.provider_group == "Radiology"
        assert provider_session.credentials_key == "QScan"
