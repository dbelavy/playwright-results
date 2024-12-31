import asyncio
from typing import Optional

from playwright.async_api import Playwright, async_playwright

from models import Credentials, PatientDetails, Session, SharedState
from utils import convert_date_format


class QScriptSession(Session):
    name = "QScript"  # Make name a class attribute
    required_fields = ["family_name", "given_name", "dob"]
    provider_group = "General"
    credentials_key = "QScript"

    def __init__(
        self,
        credentials: Credentials,
        patient: PatientDetails,
        shared_state: SharedState,
    ):
        super().__init__(credentials, patient, shared_state)

    @classmethod
    def create(
        cls, patient: PatientDetails, shared_state: SharedState
    ) -> Optional["QScriptSession"]:
        """Create a new QScript session"""
        return super().create(patient, shared_state)

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        await self.page.goto("https://hp.qscript.health.qld.gov.au/home")
        await self.page.wait_for_load_state("networkidle")

    async def login(self) -> None:
        """Handle login process including 2FA and PIN"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        # Username entry
        await self.page.get_by_placeholder("Enter username").click()
        await self.page.get_by_placeholder("Enter username").fill(
            self.credentials.user_name
        )
        await self.page.get_by_label("Next").click()
        await self.page.wait_for_load_state("networkidle")

        # Password entry
        await self.page.get_by_placeholder("Enter password").click()
        await self.page.get_by_placeholder("Enter password").fill(
            self.credentials.user_password
        )
        await self.page.wait_for_load_state("networkidle")
        await self.page.get_by_label("Log In").click()

        # Handle 2FA
        try:
            self.shared_state.new_2fa_request = "QScript"  # Tell monitor we need a code
            two_fa_code = await self.shared_state.wait_for_2fa("QScript")
            await self.page.get_by_placeholder("Verification code").fill(two_fa_code)
            await self.page.get_by_role("button", name="Verify").click()
            await self.page.wait_for_load_state("networkidle")
        except asyncio.CancelledError:
            print("QScript login cancelled - exiting")
            raise

        # Handle PIN
        await self.page.get_by_placeholder("Enter PIN").fill(self.credentials.PIN)
        await self.page.get_by_label("Save PIN and Log In").click()

    async def search_patient(self) -> None:
        """Handle patient search using data-test-id selectors"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        # Fill patient details
        await self.page.locator('[data-test-id="patientSearchFirstName"]').click()
        await self.page.locator('[data-test-id="patientSearchFirstName"]').fill(
            self.patient.given_name
        )
        await self.page.locator('[data-test-id="patientSearchFirstName"]').press("Tab")
        await self.page.locator('[data-test-id="patientSearchSurname"]').fill(
            self.patient.family_name
        )
        await self.page.locator('[data-test-id="patientSearchSurname"]').press("Tab")

        # Convert and fill DOB
        converted_dob = convert_date_format(self.patient.dob, "%d%m%Y", "%d/%m/%Y")
        await self.page.locator('[data-test-id="dateOfBirth"]').get_by_placeholder(
            " "
        ).fill(converted_dob)

        # Initiate search
        await self.page.get_by_label("Search").click()


async def QScript_process(patient: PatientDetails, shared_state: SharedState):
    # Create and run session
    session = QScriptSession.create(patient, shared_state)
    if not session:
        return
    async with async_playwright() as playwright:
        await session.run(playwright)
