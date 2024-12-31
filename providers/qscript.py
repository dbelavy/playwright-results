from playwright.async_api import Playwright, async_playwright, Page
from models import PatientDetails, SharedState, Credentials, Session
from utils import load_credentials, convert_date_format
import asyncio

# Define provider metadata at module level
REQUIRED_FIELDS = ['family_name', 'given_name', 'dob']
PROVIDER_GROUP = "General"
CREDENTIALS_KEY = "QScript"  # Matches the key in credentials.json

class QScriptSession(Session):
    def __init__(self, credentials: Credentials, patient: PatientDetails, shared_state: SharedState):
        super().__init__("QScript", credentials, patient, shared_state)

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
        print(f"Starting {self.name} process")
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
        await self.page.get_by_placeholder("Enter username").fill(self.credentials.user_name)
        await self.page.get_by_label("Next").click()
        await self.page.wait_for_load_state("networkidle")

        # Password entry
        await self.page.get_by_placeholder("Enter password").click()
        await self.page.get_by_placeholder("Enter password").fill(self.credentials.user_password)
        await self.page.wait_for_load_state("networkidle")
        await self.page.get_by_label("Log In").click()

        # Handle 2FA
        self.shared_state.new_2fa_request = "QScript"
        while not self.shared_state.QScript_code:
            await asyncio.sleep(1)

        two_fa_code = self.shared_state.QScript_code
        self.shared_state.QScript_code = None
        await self.page.get_by_placeholder("Verification code").fill(two_fa_code)
        await self.page.get_by_role("button", name="Verify").click()
        await self.page.wait_for_load_state("networkidle")

        # Handle PIN
        await self.page.get_by_placeholder("Enter PIN").fill(self.credentials.PIN)
        await self.page.get_by_label("Save PIN and Log In").click()

    async def search_patient(self) -> None:
        """Handle patient search using data-test-id selectors"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        # Fill patient details
        await self.page.locator("[data-test-id=\"patientSearchFirstName\"]").click()
        await self.page.locator("[data-test-id=\"patientSearchFirstName\"]").fill(self.patient.given_name)
        await self.page.locator("[data-test-id=\"patientSearchFirstName\"]").press("Tab")
        await self.page.locator("[data-test-id=\"patientSearchSurname\"]").fill(self.patient.family_name)
        await self.page.locator("[data-test-id=\"patientSearchSurname\"]").press("Tab")

        # Convert and fill DOB
        converted_dob = convert_date_format(self.patient.dob, "%d%m%Y", "%d/%m/%Y")
        await self.page.locator("[data-test-id=\"dateOfBirth\"]").get_by_placeholder(" ").fill(converted_dob)

        # Initiate search
        await self.page.get_by_label("Search").click()

async def run_QScript_process(patient: PatientDetails, shared_state: SharedState):
    # Load credentials
    credentials = load_credentials(shared_state, "QScript")
    if not credentials:
        print("Failed to load QScript credentials")
        return

    # Create and run session
    session = QScriptSession(credentials, patient, shared_state)
    async with async_playwright() as playwright:
        await session.run(playwright)
