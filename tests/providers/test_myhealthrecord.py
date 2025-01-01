from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock

import pytest

from providers.myhealthrecord import MyHealthRecordSession
from tests.playwright_test import PlaywrightTestCase
from utils import convert_date_format


class TestMyHealthRecord(PlaywrightTestCase):
    """Test cases for My Health Record provider."""

    @pytest.fixture
    def provider_session(self, mock_page, mock_browser, test_credentials, test_patient):
        """Create a My Health Record session for testing."""
        from models import Credentials, PatientDetails, SharedState

        # Create proper objects from test data
        credentials = Credentials(
            user_name=test_credentials["PRODA"]["user_name"],
            user_password=test_credentials["PRODA"]["user_password"],
            PRODA_full_name=test_credentials["PRODA"]["PRODA_full_name"],
        )
        patient = PatientDetails(
            family_name=test_patient["family_name"],
            given_name=test_patient["given_name"],
            dob=test_patient["dob"],
            medicare_number=test_patient["medicare_number"],
            sex=test_patient["sex"],
        )
        shared_state = SharedState()
        shared_state.page = mock_page
        shared_state.browser = mock_browser

        session = MyHealthRecordSession(credentials, patient, shared_state)
        return session

    @pytest.mark.asyncio
    async def test_login(self, initialized_session, test_credentials):
        """Test login flow including 2FA and provider selection."""
        session, page = await initialized_session

        # Set up page elements
        username_field = self.get_mock_element(click=None, fill=None)
        password_field = self.get_mock_element(click=None, fill=None)
        login_button = self.get_mock_element(click=None)
        code_field = self.get_mock_element(click=None, fill=None)
        mhr_link = self.get_mock_element(click=None)
        provider_radio = self.get_mock_element(click=None)
        submit_button = self.get_mock_element(click=None)

        # Mock label selectors
        page.get_by_label = MagicMock(
            side_effect=lambda label, **kwargs: {
                "Username": username_field,
                "Password": password_field,
                "Enter Code": code_field,
            }.get(label, Mock())
        )

        # Mock role selectors
        page.get_by_role = MagicMock(
            side_effect=lambda role, **kwargs: {
                ("button", "Login"): login_button,
                ("link", "My Health Record"): mhr_link,
            }.get((role, kwargs.get("name")), Mock())
        )

        # Mock click and wait_for_selector for provider selection
        page.click = AsyncMock()
        page.wait_for_selector = AsyncMock()

        # Mock keyboard for Enter press
        page.keyboard = MagicMock()
        page.keyboard.press = AsyncMock()

        # Mock wait_for_2fa to return immediately
        async def mock_wait_for_2fa(provider_name: str) -> str:
            return "123456"

        # Replace wait_for_2fa with our mock
        session.shared_state.wait_for_2fa = mock_wait_for_2fa

        # Perform login
        await session.login()

        # Verify initial login steps
        page.get_by_label.assert_any_call("Username")
        username_field.click.assert_called_once()
        username_field.fill.assert_called_with(test_credentials["PRODA"]["user_name"])

        page.get_by_label.assert_any_call("Password", exact=True)
        password_field.click.assert_called_once()
        password_field.fill.assert_called_with(
            test_credentials["PRODA"]["user_password"]
        )

        page.get_by_role.assert_any_call("button", name="Login", exact=True)
        login_button.click.assert_called_once()

        # Verify 2FA steps
        page.get_by_label.assert_any_call("Enter Code")
        code_field.click.assert_called_once()
        code_field.fill.assert_called_with(
            "123456"
        )  # We know the exact code from our mock
        page.keyboard.press.assert_called_with("Enter")

        # Verify navigation to My Health Record
        page.get_by_role.assert_any_call("link", name="My Health Record")
        mhr_link.click.assert_called_once()

        # Verify provider selection
        page.click.assert_any_call(
            f'input[name="radio1"][value="{test_credentials["PRODA"]["PRODA_full_name"]}"]'
        )
        page.wait_for_selector.assert_called_with("input#submitValue", state="visible")
        page.click.assert_any_call("input#submitValue")

        # Verify network idle waits
        assert (
            page.wait_for_load_state.call_count >= 3
        )  # Multiple network idle waits in the flow

    @pytest.mark.asyncio
    async def test_search_patient(self, initialized_session, test_patient):
        """Test patient search with all required fields."""
        session, page = await initialized_session

        # Set up page elements
        surname_element = self.get_mock_element(click=None, fill=None, press=None)
        dob_field = self.get_mock_element(fill=None)
        gender_radio = self.get_mock_element(check=None)
        medicare_radio = self.get_mock_element(check=None)
        medicare_field = self.get_mock_element(click=None, fill=None)
        search_button = self.get_mock_element(click=None)

        # Mock query_selector for surname
        element_mock = MagicMock()
        element_mock.click = AsyncMock()
        element_mock.fill = AsyncMock()
        element_mock.press = AsyncMock()
        page.query_selector = AsyncMock(return_value=element_mock)

        # Mock placeholder selectors
        page.get_by_placeholder = MagicMock(
            side_effect=lambda text: {
                "DD-Mmm-YYYY": dob_field,
                "Medicare number with IRN": medicare_field,
            }.get(text, Mock())
        )

        # Mock label selectors for gender
        page.get_by_label = MagicMock(
            side_effect=lambda label, **kwargs: {
                "Male": gender_radio if test_patient["sex"] == "M" else Mock(),
                "Female": gender_radio if test_patient["sex"] == "F" else Mock(),
                "Intersex": gender_radio if test_patient["sex"] == "I" else Mock(),
                "Not Stated": gender_radio
                if test_patient["sex"] not in ["M", "F", "I"]
                else Mock(),
                "Medicare": medicare_radio,
            }.get(label, Mock())
        )

        # Mock role selectors
        page.get_by_role = MagicMock(
            side_effect=lambda role, **kwargs: {
                ("button", "Search"): search_button
            }.get((role, kwargs.get("name")), Mock())
        )

        # Perform search
        await session.search_patient()

        # Verify surname entry
        page.query_selector.assert_called_with("#lname")
        element_mock.click.assert_called_once()
        element_mock.fill.assert_called_with(test_patient["family_name"])
        element_mock.press.assert_called_with("Tab")

        # Verify DOB entry
        page.get_by_placeholder.assert_any_call("DD-Mmm-YYYY")
        converted_dob = convert_date_format(test_patient["dob"], "%d%m%Y", "%d/%m/%Y")
        dob_field.fill.assert_called_with(converted_dob)

        # Verify gender selection
        if test_patient["sex"] == "M":
            page.get_by_label.assert_any_call("Male", exact=True)
        elif test_patient["sex"] == "F":
            page.get_by_label.assert_any_call("Female")
        elif test_patient["sex"] == "I":
            page.get_by_label.assert_any_call("Intersex")
        else:
            page.get_by_label.assert_any_call("Not Stated")
        gender_radio.check.assert_called_once()

        # Verify Medicare details
        page.get_by_label.assert_any_call("Medicare")
        medicare_radio.check.assert_called_once()

        page.get_by_placeholder.assert_any_call("Medicare number with IRN")
        medicare_field.click.assert_called_once()
        medicare_field.fill.assert_called_with(test_patient["medicare_number"])

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
        assert provider_session.required_fields == [
            "family_name",
            "dob",
            "medicare_number",
            "sex",
        ]
        assert provider_session.provider_group == "General"
        assert provider_session.credentials_key == "PRODA"
