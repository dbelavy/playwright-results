from playwright.async_api import Playwright, async_playwright, Page
from models import PatientDetails, SharedState, Credentials, Session
from utils import load_credentials, convert_date_format, convert_gender
from playwright._impl._errors import TimeoutError
from typing import Optional
import asyncio

class QGovViewerSession(Session):
    name = "QGov Viewer"  # Make name a class attribute
    required_fields = ['family_name', 'dob', 'medicare_number', 'sex']
    provider_group = "General"
    credentials_key = "QGov"
    
    def __init__(self, credentials: Credentials, patient: PatientDetails, shared_state: SharedState):
        super().__init__(credentials, patient, shared_state)

    @classmethod
    def create(cls, patient: PatientDetails, shared_state: SharedState) -> Optional['QGovViewerSession']:
        """Create a new QGov Viewer session"""
        return super().create(patient, shared_state)

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        await self.page.goto("https://hpp.health.qld.gov.au/my.policy")
        await self.page.goto("https://hpp.health.qld.gov.au/")

    async def login(self) -> None:
        """Handle login process"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        # Wait for and click login link
        await self.page.wait_for_selector('a:text("Log in")', state='visible')
        await self.page.get_by_role("link", name="Log in").click()

        # Wait for email field and fill credentials
        await self.page.wait_for_selector('input[placeholder="Your email address"]', state='visible')
        await self.page.get_by_placeholder("Your email address").fill(self.credentials.user_name)
        
        # Wait for password field and fill
        await self.page.wait_for_selector('input[type="password"]', state='visible')
        await self.page.get_by_label("Password").fill(self.credentials.user_password)
        
        # Click login and wait for navigation
        await self.page.get_by_role("button", name="Log in").click()
        await self.page.wait_for_load_state("domcontentloaded")

    async def search_patient(self) -> None:
        """Handle patient search"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        # Wait for Medicare field and fill
        await self.page.wait_for_selector('#MedicareNumber', state='visible')
        await self.page.locator("#MedicareNumber").fill(self.patient.medicare_number)

        # Handle gender selection with conversion
        gender = convert_gender(self.patient.sex, "M1F2I3")
        await self.page.get_by_label("Sex").select_option(gender)

        # Convert and fill DOB
        converted_dob = convert_date_format(self.patient.dob, "%d%m%Y", "%d/%m/%Y")
        await self.page.get_by_placeholder("DD/MM/YYYY").fill(converted_dob)
        await self.page.get_by_placeholder("DD/MM/YYYY").press("Tab")

        # Fill surname and search
        await self.page.get_by_label("Patient Surname").fill(self.patient.family_name)
        await self.page.get_by_role("button", name="Search").click()

        # Handle popup
        async def handle_popup(popup):
            await popup.wait_for_load_state()

        # Set up popup handler first
        print("Waiting for popup")
        self.page.on("popup", handle_popup)

        # Click viewer with timeout handling
        print("Clicking on the Viewer")
        try:
            await self.page.get_by_role("link", name="The Viewer").click(timeout=30000)
        except TimeoutError:
            print("Timeout occurred while trying to click 'The Viewer' link.")

async def QGovViewer_process(patient: PatientDetails, shared_state: SharedState):
    # Create and run session
    session = QGovViewerSession.create(patient, shared_state)
    if not session:
        return
    async with async_playwright() as playwright:
        await session.run(playwright)
