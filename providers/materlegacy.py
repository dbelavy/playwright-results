# Define provider requirements at module level
REQUIRED_FIELDS = ['family_name', 'given_name', 'dob']

from playwright.async_api import Playwright, async_playwright
from models import PatientDetails, SharedState, Credentials, Session
from utils import load_credentials, convert_date_format

class MaterLegacySession(Session):
    def __init__(self, credentials: Credentials, patient: PatientDetails, shared_state: SharedState):
        super().__init__("MaterLegacy", credentials, patient, shared_state)

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
        print(f"Starting {self.name} process")
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        await self.page.goto("https://laboratoryresults.mater.org.au/cis/cis.dll")

    async def login(self) -> None:
        """Handle login process"""
        if not self.page:
            raise RuntimeError("Session not initialized")
            
        await self.page.locator("input[name=\"salamiloginlogin\"]").click()
        await self.page.locator("input[name=\"salamiloginlogin\"]").fill(self.credentials.user_name)
        await self.page.locator("input[name=\"salamiloginpassword\"]").click()
        await self.page.locator("input[name=\"salamiloginpassword\"]").fill(self.credentials.user_password)
        await self.page.get_by_role("button", name="Login").click()
        await self.page.wait_for_load_state("networkidle")

    async def search_patient(self) -> None:
        """Handle patient search"""
        if not self.page:
            raise RuntimeError("Session not initialized")
            
        await self.page.get_by_role("cell", name="Welcome to the Mater").get_by_role("link").nth(1).click()
        await self.page.locator("input[name=\"surname\"]").click()
        await self.page.locator("input[name=\"surname\"]").fill(self.patient.family_name)
        await self.page.locator("input[name=\"firstname\"]").click()
        await self.page.locator("input[name=\"firstname\"]").fill(self.patient.given_name)

        # Convert and fill DOB
        converted_dob = convert_date_format(self.patient.dob, "%d%m%Y", "%d/%m/%Y")
        await self.page.locator("input[name=\"dob\"]").click()
        await self.page.locator("input[name=\"dob\"]").fill(converted_dob)
        
        await self.page.get_by_role("button", name="Search").click()

async def run_materlegacy_process(patient: PatientDetails, shared_state: SharedState):
    # Load credentials
    credentials = load_credentials(shared_state, "MaterLegacy")
    if not credentials:
        print("Failed to load MaterLegacy credentials")
        return

    # Create and run session
    session = MaterLegacySession(credentials, patient, shared_state)
    async with async_playwright() as playwright:
        await session.run(playwright)