import asyncio
from typing import Optional

from playwright.async_api import Playwright, async_playwright

from models import Credentials, PatientDetails, Session, SharedState
from utils import convert_date_format


class MyHealthRecordSession(Session):
    name = "My Health Record"  # Make name a class attribute
    required_fields = ["family_name", "dob", "medicare_number", "sex"]
    provider_group = "General"
    credentials_key = "PRODA"

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
    ) -> Optional["MyHealthRecordSession"]:
        """Create a new My Health Record session"""
        return super().create(patient, shared_state)

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        await self.page.goto(
            "https://proda.humanservices.gov.au/prodalogin/pages/public/login.jsf?TAM_OP=login&USER"
        )
        await self.page.wait_for_load_state("networkidle")

    async def login(self) -> None:
        """Handle login process including 2FA"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        # Initial login
        await self.page.get_by_label("Username").click()
        await self.page.get_by_label("Username").fill(self.credentials.user_name)
        await self.page.get_by_label("Password", exact=True).click()
        await self.page.get_by_label("Password", exact=True).fill(
            self.credentials.user_password
        )
        await self.page.get_by_role("button", name="Login", exact=True).click()
        await self.page.wait_for_load_state("networkidle")

        # Handle 2FA
        try:
            self.shared_state.new_2fa_request = "PRODA"  # Tell monitor we need a code
            two_fa_code = await self.shared_state.wait_for_2fa("PRODA")
            await self.page.get_by_label("Enter Code").click()
            await self.page.get_by_label("Enter Code").fill(two_fa_code)
            print('MyHR waiting for click the 2FA "Next" button')
            await asyncio.sleep(0.2)  # Short delay for UI
            await self.page.keyboard.press("Enter")
        except asyncio.CancelledError:
            print("MyHealthRecord login cancelled - exiting")
            raise

        # Navigate to MyHealthRecord
        print("Clicking through to my health record")
        await self.page.get_by_role("link", name="My Health Record").click()
        await self.page.wait_for_load_state("networkidle")

        # Select provider
        await self.page.click(
            f'input[name="radio1"][value="{self.credentials.PRODA_full_name}"]'
        )
        await self.page.wait_for_selector("input#submitValue", state="visible")
        await self.page.wait_for_load_state("networkidle")
        await self.page.click("input#submitValue")

        # Added pause between pages to prevent failures
        await asyncio.sleep(5)
        await self.page.wait_for_load_state("networkidle")

    async def search_patient(self) -> None:
        """Handle patient search"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        print("Filling in patient details")

        # Fill family name using query selector for reliability
        element_handle = await self.page.query_selector("#lname")
        await element_handle.click()
        await element_handle.fill(self.patient.family_name)
        await element_handle.press("Tab")

        # Convert and fill DOB
        converted_dob = convert_date_format(self.patient.dob, "%d%m%Y", "%d/%m/%Y")
        await self.page.get_by_placeholder("DD-Mmm-YYYY").fill(converted_dob)

        # Handle gender selection
        if self.patient.sex == "M":
            await self.page.get_by_label("Male", exact=True).check()
        elif self.patient.sex == "F":
            await self.page.get_by_label("Female").check()
        elif self.patient.sex == "I":
            await self.page.get_by_label("Intersex").check()
        else:
            await self.page.get_by_label("Not Stated").check()

        # Fill Medicare details
        await self.page.get_by_label("Medicare").check()
        await self.page.get_by_placeholder("Medicare number with IRN").click()
        await self.page.get_by_placeholder("Medicare number with IRN").fill(
            self.patient.medicare_number
        )

        # Initiate search
        await self.page.get_by_role("button", name="Search").click()


async def MyHealthRecord_process(patient: PatientDetails, shared_state: SharedState):
    # Create and run session
    session = MyHealthRecordSession.create(patient, shared_state)
    if not session:
        return
    async with async_playwright() as playwright:
        await session.run(playwright)
