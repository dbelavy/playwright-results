from playwright.async_api import Playwright, async_playwright
from models import PatientDetails, SharedState, Credentials, Session
from utils import load_credentials, convert_date_format

# Define provider requirements at module level
REQUIRED_FIELDS = ['family_name', 'given_name', 'dob']

class MedwaySession(Session):
    def __init__(self, credentials: Credentials, patient: PatientDetails, shared_state: SharedState):
        super().__init__("Medway", credentials, patient, shared_state)

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
        print(f"Starting {self.name} process")
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        await self.page.goto("https://www.medway.com.au/login")

    async def login(self) -> None:
        """Handle login process"""
        if not self.page:
            raise RuntimeError("Session not initialized")
            
        await self.page.get_by_label("Username").click()
        await self.page.get_by_label("Username").fill(self.credentials.user_name)
        await self.page.get_by_label("Password").click()
        await self.page.get_by_label("Password").fill(self.credentials.user_password)
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
        await self.page.get_by_label("Patient given name(s)").fill(self.patient.given_name)
        await self.page.get_by_label("Patient given name(s)").press("Tab")

        if self.patient.medicare_number is not None:
            medicare_field = self.page.get_by_placeholder("digit Medicare number")
            await medicare_field.fill(self.patient.medicare_number[:10])
            await medicare_field.press("Tab")

        # Convert and fill DOB
        converted_dob = convert_date_format(self.patient.dob, "%d%m%Y", "%Y-%m-%d")
        dob_field = self.page.get_by_role("textbox", name="Date of birth")
        await dob_field.fill(converted_dob)

        # Initiate search
        await self.page.get_by_role("button", name="Search").click()

async def run_medway_process(patient: PatientDetails, shared_state: SharedState):
    # Load credentials
    credentials = load_credentials(shared_state, "Medway")
    if not credentials:
        print("Failed to load Medway credentials")
        return

    # Create and run session
    session = MedwaySession(credentials, patient, shared_state)
    async with async_playwright() as playwright:
        await session.run(playwright)
