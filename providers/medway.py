from typing import Optional
import asyncio
from playwright.async_api import Playwright, async_playwright

from models import Credentials, PatientDetails, Session, SharedState
from utils import convert_date_format


class MedwaySession(Session):
    name = "Medway"  # Make name a class attribute
    required_fields = ["family_name", "given_name", "dob"]
    provider_group = "Pathology"
    credentials_key = "Medway"

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
    ) -> Optional["MedwaySession"]:
        """Create a new Medway session"""
        return super().create(patient, shared_state)

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        await self.page.goto("https://www.medway.com.au/login")

    async def login(self) -> None:
        """Handle login process"""
        if not self.page:
            raise RuntimeError("Session not initialized")
        
        await self.page.wait_for_load_state("networkidle")
        await asyncio.sleep(1)
        await self.page.get_by_label("Username").click()
        await self.page.get_by_label("Username").fill(self.credentials.user_name)
        await self.page.get_by_label("Password").click()
        await self.page.get_by_label("Password").fill(self.credentials.user_password)
        await self.page.get_by_label("Password").press("Enter")
        await asyncio.sleep(2)
        await self.page.get_by_label("Username").click()
        await self.page.get_by_label("Username").fill(self.credentials.user_name)
        await self.page.get_by_label("Password").click()
        await self.page.get_by_label("Password").fill(self.credentials.user_password)
        await asyncio.sleep(1)
        # await self.page.get_by_label("Password").press("Enter")
        await self.page.get_by_role("button", name="Log in").click()

        await self.page.wait_for_load_state("networkidle")

    async def search_patient(self) -> None:
        """Handle patient search"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        await self.page.get_by_label("Patient surname").click()
        await self.page.get_by_label("Patient surname").fill(self.patient.family_name)
        await self.page.get_by_label("Patient surname").press("Tab")
        await self.page.get_by_label("Patient given name(s)").click()
        given_name_field = self.page.get_by_label("Patient given name(s)")
        await given_name_field.fill(self.patient.given_name)
        await self.page.get_by_label("Patient given name(s)").press("Tab")

        # Keep this code just in case we change things later.
        # It can cause issues if the medicare number is wrong. Trying to use minimum dataset.
        # if self.patient.medicare_number is not None:
        #    medicare_field = self.page.get_by_placeholder("digit Medicare number")
        #    await medicare_field.fill(self.patient.medicare_number[:10])
        #    await medicare_field.press("Tab")

        # Convert and fill DOB
        converted_dob = convert_date_format(self.patient.dob, "%d%m%Y", "%Y-%m-%d")
        dob_field = self.page.get_by_role("textbox", name="Date of birth")
        await dob_field.fill(converted_dob)

        # Initiate search
        await self.page.get_by_role("button", name="Search").click()


async def Medway_process(patient: PatientDetails, shared_state: SharedState):
    # Create and run session
    session = MedwaySession.create(patient, shared_state)
    if not session:
        return
    async with async_playwright() as playwright:
        await session.run(playwright)
